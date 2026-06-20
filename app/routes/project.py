import csv
import io
import json
from datetime import datetime

from flask import Blueprint, Response, render_template, request, send_file, session

from app.models.employee import all_employees, distinct_roles
from app.routes.auth import current_user, login_required
from app.services.groq_service import generate_ai_plan
from app.database import get_db
from app.utils.pdf_generator import build_pdf_report
from app.utils.scoring_engine import generate_assignment
from app.utils import PREFERRED_ROLES


project_bp = Blueprint("project", __name__)


@project_bp.get("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        user=current_user(),
        preferred_roles=PREFERRED_ROLES,
        employee_roles=distinct_roles(),
    )


@project_bp.post("/generate-plan")
@login_required
def generate_plan():
    payload = request.get_json(silent=True) or {}
    project_name = (payload.get("project_name") or "").strip()
    if not project_name:
        return {"ok": False, "error": "Project Name is required."}, 400

    preferred_roles = payload.get("preferred_roles") or []
    if not isinstance(preferred_roles, list):
        preferred_roles = [preferred_roles]

    project = {
        "project_name": project_name,
        "description": payload.get("description", ""),
        "duration": payload.get("duration", ""),
        "team_size": payload.get("team_size") or 5,
        "technology_preferences": payload.get("technology_preferences", ""),
        "preferred_roles": preferred_roles,
    }

    employees = all_employees()
    if not employees:
        return {"ok": False, "error": "Upload employees before generating an assignment."}, 400

    deterministic = generate_assignment(employees, project)
    ai_plan = generate_ai_plan(
        project,
        deterministic["selected_team"],
        deterministic["candidate_pool"],
    )
    report_id = save_report(project, deterministic, ai_plan)
    session["last_report_id"] = report_id

    return {"ok": True, "project": project, "deterministic": deterministic, "ai_plan": ai_plan}


@project_bp.get("/export/pdf")
@login_required
def export_pdf():
    report = load_report()
    if not report:
        return {"error": "No report is available to export."}, 404
    pdf = build_pdf_report(report["project"], report["deterministic"], report["ai_plan"])
    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="project_assignment_report.pdf",
    )


@project_bp.get("/export/csv")
@login_required
def export_csv():
    report = load_report()
    if not report:
        return {"error": "No report is available to export."}, 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Name",
            "Assigned Role",
            "Final Score",
            "Skills Match %",
            "Role Match %",
            "Performance Score",
            "Experience Score",
            "Availability Score",
            "Reason",
            "Weakness",
        ]
    )
    for member in report["deterministic"].get("selected_team", []):
        writer.writerow(
            [
                member["name"],
                member["assigned_role"],
                member["final_score"],
                member["skills_match"],
                member["role_match"],
                member["performance_score"],
                member["experience_score"],
                member["availability_score"],
                member["reason"],
                member["weakness"],
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=project_assignment_report.csv"},
    )


def save_report(project, deterministic, ai_plan):
    user = current_user()
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO assignment_reports
            (user_id, project_name, project_payload, deterministic_result, ai_result, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            project["project_name"],
            json.dumps(project),
            json.dumps(deterministic),
            json.dumps(ai_plan),
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    return cursor.lastrowid


def load_report():
    report_id = session.get("last_report_id")
    user = current_user()
    if not report_id or not user:
        return None

    row = get_db().execute(
        """
        SELECT * FROM assignment_reports
        WHERE id = ? AND user_id = ?
        """,
        (report_id, user["id"]),
    ).fetchone()
    if not row:
        return None
    return {
        "project": json.loads(row["project_payload"]),
        "deterministic": json.loads(row["deterministic_result"]),
        "ai_plan": json.loads(row["ai_result"]),
    }
