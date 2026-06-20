import json
from collections import defaultdict
from datetime import date, datetime, timedelta

from app.services.groq_service import ask_groq_json


TASK_STATUSES = ["To Do", "In Progress", "Review", "Blocked", "Completed"]
PROJECT_STATUSES = ["Planning", "In Progress", "Review", "Completed", "On Hold", "Cancelled"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_dicts(rows):
    return [dict(row) for row in rows]


def json_loads(value, default):
    try:
        return json.loads(value) if value else default
    except json.JSONDecodeError:
        return default


def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def enrich_task(task, employees_by_id=None):
    item = dict(task)
    item["dependencies"] = json_loads(item.get("dependencies"), [])
    if employees_by_id:
        item["assignee"] = employees_by_id.get(item.get("assignee_employee_id"))
    return item


def enrich_project(project, tasks=None, employees_by_id=None, risks=None):
    item = dict(project)
    member_ids = json_loads(item.get("team_member_ids"), [])
    item["team_member_ids"] = member_ids
    item["team_members"] = [
        employees_by_id[employee_id]
        for employee_id in member_ids
        if employees_by_id and employee_id in employees_by_id
    ]
    if tasks is not None:
        item["task_count"] = len(tasks)
        item["completed_tasks"] = sum(1 for task in tasks if task["status"] == "Completed")
        item["progress"] = calculate_progress(tasks)
    if risks is not None:
        item["open_risks"] = len(risks)
    return item


def calculate_progress(tasks):
    if not tasks:
        return 0
    return round((sum(1 for task in tasks if task["status"] == "Completed") / len(tasks)) * 100)


def calculate_team_health(project, tasks, employees, risks):
    completion = calculate_progress(tasks)
    workload = workload_score(tasks, employees)
    deadline = deadline_score(project, tasks)
    availability = availability_score(employees)
    risk = risk_score(risks)
    score = round(
        (completion * 0.30)
        + (workload * 0.25)
        + (deadline * 0.20)
        + (availability * 0.15)
        + (risk * 0.10),
        2,
    )
    return {
        "score": score,
        "status": health_status(score),
        "components": {
            "task_completion": completion,
            "workload_balance": workload,
            "deadline_adherence": deadline,
            "availability": availability,
            "risk_level": risk,
        },
    }


def health_status(score):
    if score >= 80:
        return "Healthy"
    if score >= 60:
        return "Watch"
    return "At Risk"


def workload_score(tasks, employees):
    if not employees:
        return 70
    loads = workload_by_employee(tasks, employees)
    if not loads:
        return 100
    utilizations = [item["utilization"] for item in loads]
    overloaded = sum(1 for value in utilizations if value > 100)
    if overloaded:
        return max(35, 85 - (overloaded * 18))
    spread = max(utilizations) - min(utilizations)
    return max(45, round(100 - spread * 0.5, 2))


def deadline_score(project, tasks):
    deadline = parse_iso(project.get("deadline"))
    if not deadline:
        return 82
    today = date.today()
    overdue_open = 0
    for task in tasks:
        due = parse_iso(task.get("due_date"))
        if due and due < today and task["status"] != "Completed":
            overdue_open += 1
    if overdue_open:
        return max(20, 100 - overdue_open * 20)
    days_left = (deadline - today).days
    if days_left < 0 and project.get("status") != "Completed":
        return 30
    return 92


def availability_score(employees):
    if not employees:
        return 80
    available = sum(1 for employee in employees if employee.get("availability") == "Available")
    return round((available / len(employees)) * 100, 2)


def risk_score(risks):
    if not risks:
        return 100
    impact_weight = {"Low": 8, "Medium": 16, "High": 26, "Critical": 38}
    penalty = sum(impact_weight.get(risk.get("impact"), 16) for risk in risks)
    return max(15, 100 - penalty)


def workload_by_employee(tasks, employees):
    employee_map = {employee["employee_id"]: employee for employee in employees}
    hours = defaultdict(float)
    for task in tasks:
        assignee = task.get("assignee_employee_id")
        if assignee and task.get("status") != "Completed":
            hours[assignee] += float(task.get("estimated_hours") or 0)
    metrics = []
    for employee_id, employee in employee_map.items():
        capacity = 40 if employee.get("availability") == "Available" else 20
        assigned = hours.get(employee_id, 0)
        utilization = round((assigned / capacity) * 100, 2) if capacity else 0
        metrics.append(
            {
                "employee_id": employee_id,
                "name": employee["name"],
                "role": employee["role"],
                "assigned_hours": assigned,
                "capacity_hours": capacity,
                "utilization": utilization,
                "availability": employee["availability"],
                "indicator": utilization_indicator(utilization),
            }
        )
    return sorted(metrics, key=lambda item: item["utilization"], reverse=True)


def utilization_indicator(utilization):
    if utilization >= 95:
        return "Red"
    if utilization >= 75:
        return "Yellow"
    return "Green"


def generate_workload_alerts(metrics):
    alerts = []
    overloaded = [metric for metric in metrics if metric["indicator"] == "Red"]
    available = [metric for metric in metrics if metric["indicator"] == "Green"]
    for metric in overloaded:
        suggestion = "Split tasks or move lower-priority work."
        if available:
            suggestion = f"Consider moving work to {available[-1]['name']}."
        alerts.append(
            {
                "employee": metric["name"],
                "indicator": metric["indicator"],
                "message": f"{metric['name']} is at {metric['utilization']}% utilization.",
                "suggestion": suggestion,
            }
        )
    return alerts


def calculate_analytics(projects, tasks, employees, risks):
    completed = [task for task in tasks if task["status"] == "Completed"]
    open_tasks = [task for task in tasks if task["status"] != "Completed"]
    overdue = [
        task
        for task in open_tasks
        if parse_iso(task.get("due_date")) and parse_iso(task.get("due_date")) < date.today()
    ]
    total_points = sum(int(task.get("story_points") or 0) for task in completed)
    velocity = round(total_points / max(len(projects), 1), 2)
    utilization = workload_by_employee(tasks, employees)
    completion_rate = round((len(completed) / len(tasks)) * 100, 2) if tasks else 0
    delay_rate = round((len(overdue) / len(tasks)) * 100, 2) if tasks else 0

    employee_metrics = []
    for metric in utilization:
        assigned = [task for task in tasks if task.get("assignee_employee_id") == metric["employee_id"]]
        done = [task for task in assigned if task["status"] == "Completed"]
        employee_metrics.append(
            {
                **metric,
                "productivity": sum(int(task.get("story_points") or 0) for task in done),
                "completion_rate": round((len(done) / len(assigned)) * 100, 2) if assigned else 0,
                "avg_completion_time": "N/A",
            }
        )

    health_scores = []
    for project in projects:
        project_tasks = [task for task in tasks if task["project_id"] == project["id"]]
        project_risks = [risk for risk in risks if risk["project_id"] == project["id"]]
        health_scores.append(calculate_team_health(project, project_tasks, employees, project_risks)["score"])

    forecast = build_forecast(projects[0], tasks, employees, risks) if projects else {}
    return {
        "employee_metrics": employee_metrics,
        "project_metrics": {
            "total_projects": len(projects),
            "active_projects": len(
                [
                    project
                    for project in projects
                    if project.get("status") not in ("Completed", "Cancelled")
                ]
            ),
            "velocity": velocity,
            "delay_rate": delay_rate,
            "team_health": round(sum(health_scores) / len(health_scores), 2) if health_scores else 0,
            "completion_forecast": forecast.get("completion_date", "N/A"),
            "completion_rate": completion_rate,
            "open_tasks": len(open_tasks),
        },
    }


def build_forecast(project, tasks, employees, risks):
    completed = sum(1 for task in tasks if task["status"] == "Completed")
    remaining = max(len(tasks) - completed, 0)
    velocity = max(completed, 1)
    weeks = max(round(remaining / velocity), 1) if remaining else 0
    completion_date = date.today() + timedelta(days=weeks * 7)
    shortages = [
        metric["name"]
        for metric in workload_by_employee(tasks, employees)
        if metric["indicator"] == "Red"
    ]
    delay_probability = min(
        95,
        round((remaining * 6) + (len(risks) * 12) + (len(shortages) * 15), 2),
    )
    return {
        "completion_date": completion_date.isoformat(),
        "delay_probability": delay_probability,
        "resource_shortages": shortages,
        "velocity_trend": "Improving" if completed > remaining else "Stable",
        "recommendations": forecast_recommendations(delay_probability, shortages),
    }


def forecast_recommendations(delay_probability, shortages):
    recommendations = []
    if delay_probability > 60:
        recommendations.append("Reduce scope or add sprint capacity before the next checkpoint.")
    if shortages:
        recommendations.append("Rebalance high-utilization employees before assigning new tasks.")
    if not recommendations:
        recommendations.append("Maintain current cadence and review risk signals weekly.")
    return recommendations


def detect_risks(project, tasks, employees):
    risks = []
    metrics = workload_by_employee(tasks, employees)
    overdue = [
        task
        for task in tasks
        if parse_iso(task.get("due_date")) and parse_iso(task.get("due_date")) < date.today() and task["status"] != "Completed"
    ]
    blocked = [task for task in tasks if task["status"] == "Blocked"]
    busy_members = [employee for employee in employees if employee.get("availability") == "Busy"]

    if any(metric["indicator"] == "Red" for metric in metrics):
        risks.append(
            {
                "risk": "Burnout risk from high utilization",
                "probability": "High",
                "impact": "High",
                "mitigation": "Move lower-priority tasks away from overloaded team members.",
            }
        )
    if overdue:
        risks.append(
            {
                "risk": "Timeline slippage from overdue tasks",
                "probability": "High",
                "impact": "High",
                "mitigation": "Review overdue tasks and reset delivery commitments.",
            }
        )
    if blocked:
        risks.append(
            {
                "risk": "Dependency issue blocking execution",
                "probability": "Medium",
                "impact": "High",
                "mitigation": "Resolve blocked tasks before starting adjacent work.",
            }
        )
    if busy_members:
        risks.append(
            {
                "risk": "Resource conflict from busy team members",
                "probability": "Medium",
                "impact": "Medium",
                "mitigation": "Confirm availability or assign backup owners.",
            }
        )
    if not tasks:
        risks.append(
            {
                "risk": "Planning gap: no execution tasks",
                "probability": "Medium",
                "impact": "Medium",
                "mitigation": "Break requirements into actionable tasks before kickoff.",
            }
        )
    return risks


def ai_task_breakdown(requirements, employees):
    schema = {
        "tasks": [
            {
                "title": "string",
                "description": "string",
                "story_points": 3,
                "suggested_owner": "employee name or role",
            }
        ]
    }
    prompt = {
        "requirements": requirements,
        "employees": employees[:20],
        "instruction": "Return implementation tasks only. Do not assign final owners; suggest owners for PM approval.",
        "schema": schema,
    }
    fallback = fallback_task_breakdown(requirements, employees)
    return ask_groq_json(prompt, fallback)


def fallback_task_breakdown(requirements, employees):
    owners = [employee.get("name") for employee in employees] or ["Unassigned"]
    base = requirements.strip() or "Project requirement"
    return {
        "source": "fallback",
        "tasks": [
            {
                "title": f"Define scope for {base}",
                "description": "Clarify user journeys, acceptance criteria, and delivery constraints.",
                "story_points": 3,
                "suggested_owner": owners[0],
            },
            {
                "title": f"Build core workflow for {base}",
                "description": "Implement the primary user-facing and backend execution flow.",
                "story_points": 5,
                "suggested_owner": owners[min(1, len(owners) - 1)],
            },
            {
                "title": f"Validate and release {base}",
                "description": "Test edge cases, fix defects, and prepare rollout notes.",
                "story_points": 3,
                "suggested_owner": owners[-1],
            },
        ],
    }


def ai_sprint_plan(project, tasks, employees, capacity_hours):
    fallback = fallback_sprint_plan(tasks, employees, capacity_hours)
    return ask_groq_json(
        {
            "project": project,
            "open_tasks": tasks,
            "team": employees,
            "capacity_hours": capacity_hours,
            "schema": {
                "sprint_tasks": [
                    {"title": "string", "story_points": 3, "owner": "string", "due_date": "YYYY-MM-DD"}
                ],
                "summary": "string",
            },
        },
        fallback,
    )


def fallback_sprint_plan(tasks, employees, capacity_hours):
    employee_names = [employee["name"] for employee in employees] or ["Unassigned"]
    sprint_tasks = []
    today = date.today()
    used_hours = 0
    for index, task in enumerate(tasks):
        if task["status"] == "Completed":
            continue
        hours = float(task.get("estimated_hours") or 0)
        if capacity_hours and used_hours + hours > capacity_hours and sprint_tasks:
            break
        used_hours += hours
        sprint_tasks.append(
            {
                "title": task["title"],
                "story_points": int(task.get("story_points") or 1),
                "owner": employee_names[index % len(employee_names)],
                "due_date": (today + timedelta(days=3 + index * 2)).isoformat(),
            }
        )
    return {
        "source": "fallback",
        "summary": f"Planned {len(sprint_tasks)} tasks using {used_hours} of {capacity_hours or 'available'} hours.",
        "sprint_tasks": sprint_tasks,
    }


def ai_assistant_answer(question, context):
    fallback = {
        "source": "fallback",
        "answer": build_context_answer(question, context),
        "recommendations": context.get("forecast", {}).get("recommendations", []),
    }
    return ask_groq_json(
        {
            "question": question,
            "project_context": context,
            "answer_topics": [
                "delayed tasks",
                "overloaded employees",
                "progress summaries",
                "risk explanations",
                "reassignment suggestions",
            ],
            "schema": {"answer": "string", "recommendations": ["string"]},
        },
        fallback,
    )


def build_context_answer(question, context):
    metrics = context.get("analytics", {}).get("project_metrics", {})
    risks = context.get("risks", [])
    overloaded = [
        item["name"]
        for item in context.get("workload", [])
        if item.get("indicator") == "Red"
    ]
    parts = [
        f"Progress is {metrics.get('completion_rate', 0)}% with {metrics.get('open_tasks', 0)} open tasks.",
    ]
    if overloaded:
        parts.append(f"Overloaded employees: {', '.join(overloaded)}.")
    if risks:
        parts.append(f"Top risk: {risks[0]['risk']} with {risks[0]['impact']} impact.")
    return " ".join(parts)
