import re

VALID_AVAILABILITY = {"Available", "Busy"}
PREFERRED_ROLES = [
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Python Developer",
    "Java Developer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Data Analyst",
    "Data Scientist",
    "ML Engineer",
    "AI Engineer",
    "QA Engineer",
    "UI/UX Designer",
    "Project Manager",
]


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or "") is not None


def validate_signup(name, email, password, role):
    errors = []
    if not name or len(name.strip()) < 2:
        errors.append("Name must be at least 2 characters.")
    if not is_valid_email(email):
        errors.append("A valid email address is required.")
    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    if role not in {"Admin", "Project Manager", "Viewer"}:
        errors.append("Role is invalid.")
    return errors


def validate_employee(row):
    errors = []
    required = [
        "employee_id", "name", "skills", "experience",
        "role", "availability", "performance_score",
    ]
    for field in required:
        if not str(row.get(field, "")).strip():
            errors.append(f"{field} is required.")
    try:
        experience = float(row.get("experience", ""))
        if experience < 0:
            errors.append("experience must be >= 0.")
    except (TypeError, ValueError):
        errors.append("experience must be a number.")
    try:
        performance = float(row.get("performance_score", ""))
        if performance < 0 or performance > 100:
            errors.append("performance_score must be between 0 and 100.")
    except (TypeError, ValueError):
        errors.append("performance_score must be a number.")
    availability = str(row.get("availability", "")).strip()
    if availability not in VALID_AVAILABILITY:
        errors.append("availability must be Available or Busy.")
    return errors


def normalize_employee(row):
    return {
        "employee_id": str(row["employee_id"]).strip(),
        "name": str(row["name"]).strip(),
        "skills": str(row["skills"]).strip(),
        "experience": float(row["experience"]),
        "role": str(row["role"]).strip(),
        "availability": str(row["availability"]).strip(),
        "performance_score": float(row["performance_score"]),
    }
