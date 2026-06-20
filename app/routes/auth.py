try:
    import psycopg2
    _IntegrityError = (psycopg2.IntegrityError,)
except ImportError:
    _IntegrityError = ()
try:
    import sqlite3
    _IntegrityError = _IntegrityError + (sqlite3.IntegrityError,)
except ImportError:
    pass
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for

from app.models import create_user, get_user_by_id, verify_user
from app.utils import validate_signup


auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return view(**kwargs)

    return wrapped_view


def current_user():
    user_id = session.get("user_id")
    return get_user_by_id(user_id) if user_id else None


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("auth.login_page"))
            if user["role"] not in roles:
                return {"ok": False, "error": "You do not have permission for this action."}, 403
            return view(**kwargs)

        return wrapped_view

    return decorator


@auth_bp.get("/signup")
def signup_page():
    return render_template("signup.html", roles=["Admin", "Project Manager", "Viewer"])


@auth_bp.post("/signup")
def signup():
    data = request.form if request.form else request.get_json(silent=True) or {}
    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    role = data.get("role", "Viewer")

    errors = validate_signup(name, email, password, role)
    if errors:
        return {"ok": False, "errors": errors}, 400

    try:
        user_id = create_user(name, email, password, role)
    except Exception as e:
        err_str = str(e).lower()
        if "unique" in err_str or "duplicate" in err_str or "already exists" in err_str:
            return {"ok": False, "errors": ["An account with this email already exists."]}, 409
        return {"ok": False, "errors": ["An unexpected error occurred. Please try again."]}, 500

    session.clear()
    session["user_id"] = user_id
    return {"ok": True, "redirect": url_for("project.dashboard")}


@auth_bp.get("/login")
def login_page():
    return render_template("login.html")


@auth_bp.post("/login")
def login():
    data = request.form if request.form else request.get_json(silent=True) or {}
    user = verify_user(data.get("email", ""), data.get("password", ""))
    if not user:
        return {"ok": False, "errors": ["Invalid email or password."]}, 401
    session.clear()
    session["user_id"] = user["id"]
    return {"ok": True, "redirect": url_for("project.dashboard")}


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
