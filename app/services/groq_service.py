import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"


def generate_ai_plan(project, selected_team, candidate_pool):
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        return fallback_plan(project, selected_team, "GROQ_API_KEY is not configured.")

    payload = {
        "model": current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a project staffing assistant. The employee selection is already "
                    "decided by a deterministic scoring engine. Do not change or replace the "
                    "selected team. Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "project": project,
                        "selected_team": selected_team,
                        "candidate_pool_for_context_only": candidate_pool,
                        "required_schema": {
                            "team_explanations": [
                                {"name": "string", "explanation": "string", "recommendation": "string"}
                            ],
                            "team_structure": [{"role": "string", "responsibility": "string"}],
                            "technology_stack": ["string"],
                            "timeline": [{"phase": "string", "duration": "string", "notes": "string"}],
                            "risks": [{"risk": "string", "mitigation": "string"}],
                            "final_recommendations": ["string"],
                        },
                    }
                ),
            },
        ],
    }

    request = Request(
        GROQ_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return normalize_ai_plan(json.loads(extract_json(content)), project, selected_team)
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
        return fallback_plan(project, selected_team, f"Groq response unavailable: {exc}")


def ask_groq_json(prompt_payload, fallback):
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        return fallback

    payload = {
        "model": current_app.config.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are AssignIQ's project execution assistant. Return only valid JSON. "
                    "Do not override deterministic staffing decisions; provide planning, risk, "
                    "task, sprint, and recommendation support only."
                ),
            },
            {"role": "user", "content": json.dumps(prompt_payload)},
        ],
    }
    request = Request(
        GROQ_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(extract_json(content))
            parsed.setdefault("source", "groq")
            return parsed
    except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError, ValueError) as exc:
        fallback = dict(fallback)
        fallback["source"] = "fallback"
        fallback["note"] = f"Groq response unavailable: {exc}"
        return fallback


def extract_json(content):
    content = content.strip()
    if content.startswith("{"):
        return content
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Groq response.")
    return match.group(0)


def normalize_ai_plan(plan, project, selected_team):
    fallback = fallback_plan(project, selected_team)
    normalized = {}
    for key, value in fallback.items():
        normalized[key] = plan.get(key, value)
    normalized["source"] = "groq"
    return normalized


def fallback_plan(project, selected_team, note=None):
    roles = [member["assigned_role"] for member in selected_team]
    stack = [
        item.strip()
        for item in (project.get("technology_preferences") or "Python, Flask, SQLite").split(",")
        if item.strip()
    ]

    plan = {
        "team_explanations": [
            {
                "name": member["name"],
                "explanation": (
                    f"{member['name']} was selected by the deterministic scoring engine with "
                    f"a final score of {member['final_score']}."
                ),
                "recommendation": "Use this candidate in the listed assigned role and monitor delivery capacity.",
            }
            for member in selected_team
        ],
        "team_structure": [
            {"role": role, "responsibility": default_responsibility(role)} for role in roles
        ],
        "technology_stack": stack,
        "timeline": [
            {"phase": "Discovery and planning", "duration": "1 week", "notes": "Finalize scope, risks, and success criteria."},
            {"phase": "Implementation", "duration": project.get("duration") or "2-4 weeks", "notes": "Build prioritized features with weekly reviews."},
            {"phase": "Testing and release", "duration": "1 week", "notes": "Validate quality, performance, and handoff readiness."},
        ],
        "risks": [
            {"risk": "Availability constraints", "mitigation": "Confirm allocation before kickoff and keep backup candidates ready."},
            {"risk": "Skill gaps", "mitigation": "Pair specialists with related-role candidates where scores show weaker skill coverage."},
        ],
        "final_recommendations": [
            "Use deterministic scores for staffing decisions.",
            "Review candidates marked Busy before committing the final schedule.",
            "Re-run the plan when project scope or required technologies change.",
        ],
        "source": "fallback",
    }
    if note:
        plan["note"] = note
    return plan


def default_responsibility(role):
    mapping = {
        "Frontend Developer": "Build and polish user-facing screens.",
        "Backend Developer": "Own APIs, database flows, and business logic.",
        "Full Stack Developer": "Bridge frontend and backend implementation work.",
        "Python Developer": "Implement Python services, integrations, and automation.",
        "Java Developer": "Own Java services and platform integrations.",
        "DevOps Engineer": "Manage deployment, CI/CD, and operational reliability.",
        "Cloud Engineer": "Design cloud infrastructure and runtime environments.",
        "Data Analyst": "Translate data into reports and decision support.",
        "Data Scientist": "Develop analytical models and evaluate data quality.",
        "ML Engineer": "Build model pipelines and production ML workflows.",
        "AI Engineer": "Design AI integrations, prompts, and evaluation loops.",
        "QA Engineer": "Plan and execute functional and regression testing.",
        "UI/UX Designer": "Design usable flows, layouts, and interaction patterns.",
        "Project Manager": "Coordinate scope, timeline, communication, and delivery risks.",
    }
    return mapping.get(role, "Contribute within assigned project responsibilities.")
