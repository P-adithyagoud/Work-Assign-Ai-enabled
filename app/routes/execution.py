import json
import os
import re
import uuid
from datetime import datetime

from flask import Blueprint, current_app, request, send_file
from werkzeug.utils import secure_filename

from app.models.employee import all_employees
from app.routes.auth import current_user, login_required, roles_required
from app.services.execution_service import (
    PRIORITIES,
    PROJECT_STATUSES,
    TASK_STATUSES,
    ai_assistant_answer,
    ai_sprint_plan,
    ai_task_breakdown,
    build_forecast,
    calculate_analytics,
    calculate_team_health,
    detect_risks,
    enrich_project,
    enrich_task,
    generate_workload_alerts,
    json_loads,
    row_to_dict,
    rows_to_dicts,
    workload_by_employee,
)
from app.database import get_db


execution_bp = Blueprint("execution", __name__)

ALLOWED_FILE_EXTENSIONS = {"pdf", "docx", "xlsx", "png", "jpg", "jpeg"}
WRITE_ROLES = ("Admin", "Project Manager")


@execution_bp.get("/projects")
@login_required
def list_projects():
    db = get_db()
    employees = employee_dicts()
    employees_by_id = {employee["employee_id"]: employee for employee in employees}
    rows = db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
    projects = []
    for row in rows:
        project = dict(row)
        tasks = rows_to_dicts(
            db.execute("SELECT * FROM tasks WHERE project_id = ?", (project["id"],)).fetchall()
        )
        risks = rows_to_dicts(
            db.execute("SELECT * FROM risks WHERE project_id = ?", (project["id"],)).fetchall()
        )
        health = calculate_team_health(project, tasks, employees, risks)
        project["health_score"] = health["score"]
        project["health_status"] = health["status"]
        projects.append(enrich_project(project, tasks, employees_by_id, risks))
    return {"ok": True, "projects": projects, "statuses": PROJECT_STATUSES, "priorities": PRIORITIES}


@execution_bp.post("/projects")
@login_required
@roles_required(*WRITE_ROLES)
def create_project():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or payload.get("project_name") or "").strip()
    if not name:
        return {"ok": False, "error": "Project name is required."}, 400

    status = valid_choice(payload.get("status"), PROJECT_STATUSES, "Planning")
    priority = valid_choice(payload.get("priority"), PRIORITIES, "Medium")
    progress = clamp_int(payload.get("progress", 0), 0, 100)
    team_member_ids = payload.get("team_member_ids") or []
    if not isinstance(team_member_ids, list):
        team_member_ids = [team_member_ids]

    now = now_iso()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO projects
            (name, description, status, progress, deadline, priority, health_score, owner_id, team_member_ids, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            payload.get("description", ""),
            status,
            progress,
            payload.get("deadline", ""),
            priority,
            100,
            current_user()["id"],
            json.dumps(team_member_ids),
            now,
            now,
        ),
    )
    project_id = cursor.lastrowid
    log_activity(project_id, None, "Project created", f"{name} was created.")
    create_notification(project_id, None, "project", "Project created", f"{name} is ready for execution planning.")
    db.commit()
    return {"ok": True, "project": get_project(project_id)}, 201


@execution_bp.get("/tasks")
@login_required
def list_tasks():
    project_id = request.args.get("project_id")
    db = get_db()
    params = []
    query = "SELECT * FROM tasks WHERE 1=1"
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    query += " ORDER BY CASE status WHEN 'To Do' THEN 1 WHEN 'In Progress' THEN 2 WHEN 'Review' THEN 3 WHEN 'Blocked' THEN 4 WHEN 'Completed' THEN 5 ELSE 6 END, due_date ASC"
    employees_by_id = {employee["employee_id"]: employee for employee in employee_dicts()}
    tasks = [enrich_task(row, employees_by_id) for row in db.execute(query, params).fetchall()]
    return {"ok": True, "tasks": tasks, "statuses": TASK_STATUSES, "priorities": PRIORITIES}


@execution_bp.post("/tasks")
@login_required
@roles_required(*WRITE_ROLES)
def create_task():
    payload = request.get_json(silent=True) or {}
    project_id = payload.get("project_id")
    title = (payload.get("title") or "").strip()
    if not project_id or not title:
        return {"ok": False, "error": "project_id and title are required."}, 400

    db = get_db()
    if not db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
        return {"ok": False, "error": "Project not found."}, 404

    dependencies = normalize_dependencies(payload.get("dependencies"))
    now = now_iso()
    cursor = db.execute(
        """
        INSERT INTO tasks
            (project_id, title, description, assignee_employee_id, priority, due_date, estimated_hours,
             story_points, status, dependencies, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            title,
            payload.get("description", ""),
            payload.get("assignee_employee_id", ""),
            valid_choice(payload.get("priority"), PRIORITIES, "Medium"),
            payload.get("due_date", ""),
            to_float(payload.get("estimated_hours"), 0),
            clamp_int(payload.get("story_points", 1), 1, 40),
            valid_choice(payload.get("status"), TASK_STATUSES, "To Do"),
            json.dumps(dependencies),
            current_user()["id"],
            now,
            now,
        ),
    )
    task_id = cursor.lastrowid
    insert_dependencies(task_id, dependencies)
    log_activity(project_id, task_id, "Task created", title)
    create_notification(project_id, task_id, "task", "Task assigned", f"{title} was added to the board.")
    update_project_rollups(project_id)
    db.commit()
    return {"ok": True, "task": get_task(task_id)}, 201


@execution_bp.patch("/tasks")
@login_required
@roles_required(*WRITE_ROLES)
def patch_task():
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("id")
    if not task_id:
        return {"ok": False, "error": "Task id is required."}, 400
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        return {"ok": False, "error": "Task not found."}, 404

    allowed = {
        "title",
        "description",
        "assignee_employee_id",
        "priority",
        "due_date",
        "estimated_hours",
        "story_points",
        "status",
        "dependencies",
    }
    updates = {}
    for key, value in payload.items():
        if key not in allowed:
            continue
        if key == "status":
            value = valid_choice(value, TASK_STATUSES, task["status"])
        elif key == "priority":
            value = valid_choice(value, PRIORITIES, task["priority"])
        elif key == "estimated_hours":
            value = to_float(value, task["estimated_hours"])
        elif key == "story_points":
            value = clamp_int(value, 1, 40)
        elif key == "dependencies":
            value = json.dumps(normalize_dependencies(value))
        updates[key] = value

    if not updates:
        return {"ok": False, "error": "No valid fields to update."}, 400

    updates["updated_at"] = now_iso()
    set_clause = ", ".join(f"{key} = ?" for key in updates)
    db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", [*updates.values(), task_id])
    if "dependencies" in updates:
        db.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
        insert_dependencies(task_id, json_loads(updates["dependencies"], []))
    log_activity(task["project_id"], task_id, "Task updated", json.dumps(updates))
    if "status" in updates and updates["status"] != task["status"]:
        create_notification(
            task["project_id"],
            task_id,
            "task",
            "Task status changed",
            f"{task['title']} moved from {task['status']} to {updates['status']}.",
        )
    update_project_rollups(task["project_id"])
    db.commit()
    return {"ok": True, "task": get_task(task_id)}


@execution_bp.post("/tasks/breakdown")
@login_required
@roles_required(*WRITE_ROLES)
def breakdown_tasks():
    payload = request.get_json(silent=True) or {}
    requirements = (payload.get("requirements") or "").strip()
    if not requirements:
        return {"ok": False, "error": "Requirements are required."}, 400
    result = ai_task_breakdown(requirements, employee_dicts())
    create_notification(None, None, "ai", "AI task breakdown ready", "Review generated tasks before adding them.")
    return {"ok": True, "breakdown": result}


@execution_bp.post("/sprints/generate")
@login_required
@roles_required(*WRITE_ROLES)
def generate_sprint():
    payload = request.get_json(silent=True) or {}
    project_id = payload.get("project_id")
    if not project_id:
        return {"ok": False, "error": "project_id is required."}, 400
    project = get_project(project_id)
    if not project:
        return {"ok": False, "error": "Project not found."}, 404
    tasks = get_project_tasks(project_id)
    employees = employee_dicts()
    capacity = to_float(payload.get("capacity_hours"), 120)
    plan = ai_sprint_plan(project, tasks, employees, capacity)
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO sprints (project_id, name, start_date, end_date, capacity_hours, plan_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            payload.get("name") or f"Sprint {datetime.utcnow().strftime('%Y-%m-%d')}",
            payload.get("start_date", ""),
            payload.get("end_date", ""),
            capacity,
            json.dumps(plan),
            now_iso(),
        ),
    )
    log_activity(project_id, None, "Sprint generated", "AI sprint plan generated.")
    create_notification(project_id, None, "ai", "Sprint plan generated", "Review sprint scope and owners.")
    db.commit()
    return {"ok": True, "sprint_id": cursor.lastrowid, "plan": plan}


@execution_bp.post("/risks/analyze")
@login_required
@roles_required(*WRITE_ROLES)
def analyze_risks():
    payload = request.get_json(silent=True) or {}
    project_id = payload.get("project_id")
    project = get_project(project_id)
    if not project:
        return {"ok": False, "error": "Project not found."}, 404
    tasks = get_project_tasks(project_id)
    employees = employee_dicts()
    risks = detect_risks(project, tasks, employees)
    db = get_db()
    for risk in risks:
        db.execute(
            """
            INSERT INTO risks (project_id, risk, probability, impact, mitigation, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                risk["risk"],
                risk["probability"],
                risk["impact"],
                risk["mitigation"],
                "system",
                now_iso(),
            ),
        )
    log_activity(project_id, None, "Risk analysis generated", f"{len(risks)} risks detected.")
    create_notification(project_id, None, "risk", "Risk analysis complete", f"{len(risks)} risks detected.")
    update_project_rollups(project_id)
    db.commit()
    return {"ok": True, "risks": risks}


@execution_bp.get("/risks")
@login_required
def list_risks():
    project_id = request.args.get("project_id")
    query = "SELECT * FROM risks WHERE 1=1"
    params = []
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    query += " ORDER BY created_at DESC"
    return {"ok": True, "risks": rows_to_dicts(get_db().execute(query, params).fetchall())}


@execution_bp.get("/analytics")
@login_required
def analytics():
    db = get_db()
    project_id = request.args.get("project_id")
    projects = rows_to_dicts(db.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall())
    if project_id:
        projects = [project for project in projects if str(project["id"]) == str(project_id)]
    tasks = rows_to_dicts(db.execute("SELECT * FROM tasks").fetchall())
    if project_id:
        tasks = [task for task in tasks if str(task["project_id"]) == str(project_id)]
    risks = rows_to_dicts(db.execute("SELECT * FROM risks").fetchall())
    if project_id:
        risks = [risk for risk in risks if str(risk["project_id"]) == str(project_id)]
    result = calculate_analytics(projects, tasks, employee_dicts(), risks)
    result["workload"] = workload_by_employee(tasks, employee_dicts())
    result["workload_alerts"] = generate_workload_alerts(result["workload"])
    return {"ok": True, "analytics": result}


@execution_bp.post("/assistant/chat")
@login_required
def assistant_chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("message") or payload.get("question") or "").strip()
    project_id = payload.get("project_id")
    if not question:
        return {"ok": False, "error": "Message is required."}, 400
    context = build_project_context(project_id)
    answer = ai_assistant_answer(question, context)
    create_notification(project_id, None, "ai", "Assistant response generated", question[:120])
    return {"ok": True, "response": answer}


@execution_bp.get("/comments")
@login_required
def list_comments():
    project_id = request.args.get("project_id")
    task_id = request.args.get("task_id")
    query = "SELECT c.*, u.name AS user_name FROM comments c JOIN users u ON u.id = c.user_id WHERE 1=1"
    params = []
    if project_id:
        query += " AND c.project_id = ?"
        params.append(project_id)
    if task_id:
        query += " AND c.task_id = ?"
        params.append(task_id)
    query += " ORDER BY c.created_at DESC"
    rows = get_db().execute(query, params).fetchall()
    comments = []
    for row in rows:
        item = dict(row)
        item["mentions"] = json_loads(item.get("mentions"), [])
        comments.append(item)
    return {"ok": True, "comments": comments}


@execution_bp.post("/comments")
@login_required
def add_comment():
    payload = request.get_json(silent=True) or {}
    body = (payload.get("body") or "").strip()
    if not body:
        return {"ok": False, "error": "Comment body is required."}, 400
    mentions = re.findall(r"@([A-Za-z0-9_. -]+)", body)
    project_id = payload.get("project_id")
    task_id = payload.get("task_id")
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO comments (project_id, task_id, parent_id, user_id, body, mentions, attachment_file_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            task_id,
            payload.get("parent_id"),
            current_user()["id"],
            body,
            json.dumps(mentions),
            payload.get("attachment_file_id"),
            now_iso(),
        ),
    )
    log_activity(project_id, task_id, "Comment added", body[:160])
    for mention in mentions:
        create_notification(project_id, task_id, "mention", "You were mentioned", f"Comment mentions @{mention}.")
    db.commit()
    return {"ok": True, "comment_id": cursor.lastrowid}, 201


@execution_bp.get("/files")
@login_required
def list_files():
    project_id = request.args.get("project_id")
    search = (request.args.get("search") or "").lower()
    query = "SELECT * FROM files WHERE 1=1"
    params = []
    if project_id:
        query += " AND project_id = ?"
        params.append(project_id)
    if search:
        query += " AND LOWER(original_name) LIKE ?"
        params.append(f"%{search}%")
    query += " ORDER BY created_at DESC"
    return {"ok": True, "files": rows_to_dicts(get_db().execute(query, params).fetchall())}


@execution_bp.post("/files/upload")
@login_required
def upload_file():
    uploaded = request.files.get("file")
    if not uploaded:
        return {"ok": False, "error": "File is required."}, 400
    extension = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
    if extension not in ALLOWED_FILE_EXTENSIONS:
        return {"ok": False, "error": "Unsupported file type."}, 400

    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)
    original = secure_filename(uploaded.filename)
    existing_versions = get_db().execute(
        "SELECT COUNT(*) AS total FROM files WHERE original_name = ? AND project_id IS ?",
        (original, request.form.get("project_id")),
    ).fetchone()["total"]
    version = existing_versions + 1
    stored_name = f"{uuid.uuid4().hex}_{original}"
    path = os.path.join(upload_dir, stored_name)
    uploaded.save(path)

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO files (project_id, task_id, uploaded_by, original_name, stored_name, file_type, version, size_bytes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.form.get("project_id"),
            request.form.get("task_id"),
            current_user()["id"],
            original,
            stored_name,
            extension,
            version,
            os.path.getsize(path),
            now_iso(),
        ),
    )
    log_activity(request.form.get("project_id"), request.form.get("task_id"), "File uploaded", original)
    create_notification(request.form.get("project_id"), request.form.get("task_id"), "file", "File uploaded", original)
    db.commit()
    return {"ok": True, "file_id": cursor.lastrowid, "version": version}, 201


@execution_bp.get("/files/<int:file_id>/download")
@login_required
def download_file(file_id):
    row = get_db().execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "File not found."}, 404
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], row["stored_name"])
    if not os.path.exists(path):
        return {"ok": False, "error": "Stored file is missing."}, 404
    return send_file(path, as_attachment=True, download_name=row["original_name"])


@execution_bp.get("/notifications")
@login_required
def notifications():
    status_filter = request.args.get("status", "all")
    query = "SELECT * FROM notifications WHERE user_id IS NULL OR user_id = ?"
    params = [current_user()["id"]]
    if status_filter == "unread":
        query += " AND is_read = 0"
    elif status_filter == "read":
        query += " AND is_read = 1"
    query += " ORDER BY created_at DESC LIMIT 100"
    return {"ok": True, "notifications": rows_to_dicts(get_db().execute(query, params).fetchall())}


@execution_bp.patch("/notifications/read")
@login_required
def mark_notifications_read():
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids") or []
    if not isinstance(ids, list):
        ids = [ids]
    db = get_db()
    if ids:
        placeholders = ",".join("?" for _ in ids)
        db.execute(f"UPDATE notifications SET is_read = 1 WHERE id IN ({placeholders})", ids)
    else:
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id IS NULL OR user_id = ?", (current_user()["id"],))
    db.commit()
    return {"ok": True}


@execution_bp.get("/activity")
@login_required
def activity():
    project_id = request.args.get("project_id")
    query = "SELECT a.*, u.name AS user_name FROM activity_logs a LEFT JOIN users u ON u.id = a.user_id WHERE 1=1"
    params = []
    if project_id:
        query += " AND a.project_id = ?"
        params.append(project_id)
    query += " ORDER BY a.created_at DESC LIMIT 100"
    return {"ok": True, "activity": rows_to_dicts(get_db().execute(query, params).fetchall())}


@execution_bp.get("/forecast")
@login_required
def forecast():
    project_id = request.args.get("project_id")
    project = get_project(project_id) if project_id else latest_project()
    if not project:
        return {"ok": True, "forecast": {}}
    forecast_payload = build_forecast(project, get_project_tasks(project["id"]), employee_dicts(), get_project_risks(project["id"]))
    return {"ok": True, "forecast": forecast_payload}


@execution_bp.get("/workload")
@login_required
def workload():
    project_id = request.args.get("project_id")
    tasks = get_project_tasks(project_id) if project_id else rows_to_dicts(get_db().execute("SELECT * FROM tasks").fetchall())
    metrics = workload_by_employee(tasks, employee_dicts())
    return {"ok": True, "workload": metrics, "alerts": generate_workload_alerts(metrics)}


def get_project(project_id):
    if not project_id:
        return None
    row = get_db().execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        return None
    project = dict(row)
    project["team_member_ids"] = json_loads(project.get("team_member_ids"), [])
    return project


def latest_project():
    row = get_db().execute("SELECT * FROM projects ORDER BY updated_at DESC LIMIT 1").fetchone()
    return row_to_dict(row)


def get_task(task_id):
    row = get_db().execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return enrich_task(row, {employee["employee_id"]: employee for employee in employee_dicts()}) if row else None


def get_project_tasks(project_id):
    if not project_id:
        return []
    rows = get_db().execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,)).fetchall()
    return [enrich_task(row) for row in rows]


def get_project_risks(project_id):
    if not project_id:
        return []
    return rows_to_dicts(get_db().execute("SELECT * FROM risks WHERE project_id = ?", (project_id,)).fetchall())


def build_project_context(project_id=None):
    db = get_db()
    project = get_project(project_id) if project_id else latest_project()
    projects = [project] if project else []
    tasks = get_project_tasks(project["id"]) if project else rows_to_dicts(db.execute("SELECT * FROM tasks").fetchall())
    employees = employee_dicts()
    risks = get_project_risks(project["id"]) if project else rows_to_dicts(db.execute("SELECT * FROM risks").fetchall())
    analytics = calculate_analytics(projects, tasks, employees, risks)
    workload = workload_by_employee(tasks, employees)
    forecast_payload = build_forecast(project, tasks, employees, risks) if project else {}
    return {
        "project": project,
        "tasks": tasks[:50],
        "risks": risks[:20],
        "analytics": analytics,
        "workload": workload,
        "forecast": forecast_payload,
    }


def update_project_rollups(project_id):
    project = get_project(project_id)
    if not project:
        return
    tasks = get_project_tasks(project_id)
    risks = get_project_risks(project_id)
    health = calculate_team_health(project, tasks, employee_dicts(), risks)
    progress = round(sum(1 for task in tasks if task["status"] == "Completed") / len(tasks) * 100) if tasks else 0
    get_db().execute(
        "UPDATE projects SET progress = ?, health_score = ?, updated_at = ? WHERE id = ?",
        (progress, health["score"], now_iso(), project_id),
    )


def insert_dependencies(task_id, dependencies):
    db = get_db()
    for dependency in dependencies:
        try:
            depends_on = int(dependency)
        except (TypeError, ValueError):
            continue
        db.execute(
            "INSERT INTO task_dependencies (task_id, depends_on_task_id, created_at) VALUES (?, ?, ?)",
            (task_id, depends_on, now_iso()),
        )


def normalize_dependencies(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def create_notification(project_id, task_id, notification_type, title, message, user_id=None):
    get_db().execute(
        """
        INSERT INTO notifications (user_id, project_id, task_id, type, title, message, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (user_id, project_id, task_id, notification_type, title, message, now_iso()),
    )


def log_activity(project_id, task_id, action, details=""):
    user = current_user()
    get_db().execute(
        """
        INSERT INTO activity_logs (project_id, task_id, user_id, action, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (project_id, task_id, user["id"] if user else None, action, details, now_iso()),
    )


def employee_dicts():
    return rows_to_dicts(all_employees())


def valid_choice(value, choices, fallback):
    return value if value in choices else fallback


def clamp_int(value, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return minimum


def to_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")
