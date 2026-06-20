import os
from flask import Flask, redirect, url_for
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
        init_db()

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

    return app
