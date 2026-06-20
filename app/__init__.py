import os
from flask import Flask, jsonify, redirect, url_for
from dotenv import load_dotenv

from config import Config
from app.database import close_db, init_db


def create_app(test_config=None):
    """Create and configure the Flask application."""
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config is not None:
        app.config.from_mapping(test_config)

    # Ensure the instance folder and uploads folder exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"])
    except OSError:
        pass

    # Initialize Database
    app.teardown_appcontext(close_db)
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            app.logger.error(f"Database initialization failed: {e}")

    # Register custom template filters
    @app.template_filter("percentage")
    def percentage_filter(value):
        if value is None:
            return "0%"
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter("score_color")
    def score_color_filter(score):
        """Returns a class name for the score based on its value."""
        try:
            score = float(score)
            if score >= 80:
                return "text-success bg-success-light"
            elif score >= 50:
                return "text-warning bg-warning-light"
            else:
                return "text-danger bg-danger-light"
        except (ValueError, TypeError):
            return "text-muted"

    # Register Blueprints from app.routes
    from app.routes.auth import auth_bp
    from app.routes.employee import employee_bp
    from app.routes.project import project_bp
    from app.routes.execution import execution_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(execution_bp)

    # Global Redirect from Root to Dashboard
    @app.route("/")
    def index():
        return redirect(url_for("project.dashboard"))

    @app.route("/health")
    def health():
        from app.database import get_db
        import os
        try:
            db = get_db()
            db.execute("SELECT 1")
            db_type = "postgresql" if "postgresql" in app.config["DATABASE"] or "postgres" in app.config["DATABASE"] else "sqlite"
            return jsonify({"ok": True, "db": db_type, "DATABASE_URL_SET": bool(os.getenv("DATABASE_URL"))}), 200
        except Exception as e:
            return jsonify({"ok": False, "error": str(e), "DATABASE_URL_SET": bool(os.getenv("DATABASE_URL"))}), 500

    # Global JSON error handler so API fetch calls never receive HTML on crash
    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f"Internal server error: {e}")
        return jsonify({"ok": False, "error": "Internal server error. Please try again."}), 500

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "Not found."}), 404

    return app
