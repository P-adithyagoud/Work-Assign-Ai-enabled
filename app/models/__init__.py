from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db

VALID_ROLES = ("Admin", "Project Manager", "Viewer")


def create_user(name, email, password, role, username=None):
    db = get_db()
    if not username:
        username = email.split('@')[0]
    cursor = db.execute(
        """
        INSERT INTO users (name, username, email, password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            username.strip().lower(),
            email.strip().lower(),
            generate_password_hash(password),
            role if role in VALID_ROLES else "Project Manager",
            datetime.utcnow().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    return cursor.lastrowid


def get_user_by_email(email):
    return get_db().execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()


def get_user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def get_user_by_username(username):
    return get_db().execute(
        "SELECT * FROM users WHERE username = ?", (username.strip().lower(),)
    ).fetchone()


def verify_user(login_id, password):
    """Verify user by email or username."""
    user = get_user_by_email(login_id)
    if not user:
        user = get_user_by_username(login_id)
    if not user or not check_password_hash(user["password_hash"], password):
        return None
    return user
