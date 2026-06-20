from datetime import datetime
from app.database import get_db


def insert_employee(employee):
    db = get_db()
    db.execute(
        """
        INSERT INTO employees
            (employee_id, name, skills, experience, role, availability, performance_score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            employee["employee_id"],
            employee["name"],
            employee["skills"],
            employee["experience"],
            employee["role"],
            employee["availability"],
            employee["performance_score"],
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    db.commit()


def employee_exists(employee_id):
    return (
        get_db()
        .execute("SELECT 1 FROM employees WHERE employee_id = ?", (employee_id,))
        .fetchone()
        is not None
    )


def list_employees(search="", role="", availability="", sort="performance_desc"):
    query = "SELECT * FROM employees WHERE 1=1"
    params = []
    if search:
        query += " AND LOWER(name) LIKE ?"
        params.append(f"%{search.lower()}%")
    if role:
        query += " AND role = ?"
        params.append(role)
    if availability:
        query += " AND availability = ?"
        params.append(availability)
    sort_map = {
        "experience_desc": "experience DESC, performance_score DESC",
        "experience_asc": "experience ASC, performance_score DESC",
        "performance_desc": "performance_score DESC, experience DESC",
        "performance_asc": "performance_score ASC, experience DESC",
        "name_asc": "name ASC",
    }
    query += f" ORDER BY {sort_map.get(sort, sort_map['performance_desc'])}"
    return get_db().execute(query, params).fetchall()


def all_employees():
    return get_db().execute("SELECT * FROM employees").fetchall()


def distinct_roles():
    rows = get_db().execute(
        "SELECT DISTINCT role FROM employees ORDER BY role ASC"
    ).fetchall()
    return [row["role"] for row in rows]
