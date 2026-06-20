import re


RELATED_ROLES = {
    "Frontend Developer": {"Full Stack Developer", "UI/UX Designer"},
    "Backend Developer": {"Full Stack Developer", "Python Developer", "Java Developer"},
    "Full Stack Developer": {"Frontend Developer", "Backend Developer"},
    "Python Developer": {"Backend Developer", "Data Scientist", "ML Engineer", "AI Engineer"},
    "Java Developer": {"Backend Developer", "Full Stack Developer"},
    "DevOps Engineer": {"Cloud Engineer", "Backend Developer"},
    "Cloud Engineer": {"DevOps Engineer", "Backend Developer"},
    "Data Analyst": {"Data Scientist", "ML Engineer"},
    "Data Scientist": {"Data Analyst", "ML Engineer", "AI Engineer"},
    "ML Engineer": {"Data Scientist", "AI Engineer", "Python Developer"},
    "AI Engineer": {"ML Engineer", "Data Scientist", "Python Developer"},
    "QA Engineer": {"Project Manager"},
    "UI/UX Designer": {"Frontend Developer"},
    "Project Manager": {"QA Engineer"},
}


def normalize_tokens(value):
    return [
        token.strip().lower()
        for token in re.split(r"[,;/|\n]+", value or "")
        if token.strip()
    ]


def extract_project_skills(project):
    tech_skills = normalize_tokens(project.get("technology_preferences", ""))
    if tech_skills:
        return tech_skills

    description = project.get("description", "")
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]{1,}", description)
    stop_words = {
        "and",
        "the",
        "for",
        "with",
        "from",
        "that",
        "this",
        "project",
        "application",
        "system",
    }
    return sorted({word.lower() for word in words if word.lower() not in stop_words})[:20]


def role_match_score(employee_role, preferred_roles):
    if not preferred_roles:
        return 100
    if employee_role in preferred_roles:
        return 100
    related = RELATED_ROLES.get(employee_role, set())
    if any(role in related or employee_role in RELATED_ROLES.get(role, set()) for role in preferred_roles):
        return 50
    return 0


def skills_match_score(employee_skills, project_skills):
    if not project_skills:
        return 100
    employee_tokens = set(normalize_tokens(employee_skills))
    found = 0
    for skill in project_skills:
        skill_l = skill.lower()
        if skill_l in employee_tokens or any(skill_l in token or token in skill_l for token in employee_tokens):
            found += 1
    return round((found / len(project_skills)) * 100, 2)


def experience_score(experience, max_experience):
    if max_experience <= 0:
        return 0
    return round(min((float(experience) / max_experience) * 100, 100), 2)


def score_employee(employee, project, max_experience):
    project_skills = extract_project_skills(project)
    preferred_roles = project.get("preferred_roles", [])

    skills_score = skills_match_score(employee["skills"], project_skills)
    role_score = role_match_score(employee["role"], preferred_roles)
    performance_score = float(employee["performance_score"])
    exp_score = experience_score(employee["experience"], max_experience)
    availability_score = 100 if employee["availability"] == "Available" else 0

    final_score = round(
        (skills_score * 0.40)
        + (role_score * 0.25)
        + (performance_score * 0.20)
        + (exp_score * 0.10)
        + (availability_score * 0.05),
        2,
    )

    return {
        "employee_id": employee["employee_id"],
        "name": employee["name"],
        "assigned_role": employee["role"],
        "skills": employee["skills"],
        "availability": employee["availability"],
        "final_score": final_score,
        "skills_match": skills_score,
        "role_match": role_score,
        "performance_score": performance_score,
        "experience": float(employee["experience"]),
        "experience_score": exp_score,
        "availability_score": availability_score,
        "reason": build_reason(skills_score, role_score, performance_score, exp_score, availability_score),
        "weakness": build_weakness(skills_score, role_score, availability_score),
    }


def build_reason(skills_score, role_score, performance_score, exp_score, availability_score):
    reasons = []
    if skills_score >= 70:
        reasons.append("strong skill alignment")
    if role_score >= 100:
        reasons.append("exact role fit")
    elif role_score == 50:
        reasons.append("related role fit")
    if performance_score >= 80:
        reasons.append("high performance history")
    if exp_score >= 70:
        reasons.append("solid experience depth")
    if availability_score == 100:
        reasons.append("currently available")
    return ", ".join(reasons) if reasons else "balanced candidate with moderate fit"


def build_weakness(skills_score, role_score, availability_score):
    if availability_score == 0:
        return "Currently busy, which may affect immediate staffing."
    if skills_score < 50:
        return "Skill overlap with the requested technology set is limited."
    if role_score == 0:
        return "Role does not directly match the preferred roles."
    return "No major weakness detected from the available data."


def generate_assignment(employees, project):
    if not employees:
        return {"project_skills": [], "ranked_candidates": [], "selected_team": [], "candidate_pool": []}

    max_experience = max(float(employee["experience"]) for employee in employees)
    ranked = [
        score_employee(employee, project, max_experience)
        for employee in employees
        if employee["employee_id"] and employee["name"]
    ]
    ranked.sort(key=lambda item: item["final_score"], reverse=True)

    try:
        team_size = int(project.get("team_size") or 5)
    except ValueError:
        team_size = 5
    team_size = max(1, team_size)

    candidate_limit = min(team_size * 3, 20)
    selected_team = ranked[:team_size]
    candidate_pool = ranked[:candidate_limit]

    return {
        "project_skills": extract_project_skills(project),
        "ranked_candidates": ranked,
        "selected_team": selected_team,
        "candidate_pool": candidate_pool,
    }

