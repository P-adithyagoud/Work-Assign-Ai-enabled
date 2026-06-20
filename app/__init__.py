import os
from flask import Flask, redirect, url_for
from dotenv import load_dotenv

def create_app(test_config=None):
    """Create and configure the Flask application."""
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__, instance_relative_config=True)
    
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-placeholder'),
        DATABASE=os.path.join(app.instance_path, 'projectassign.db'),
    )

    if test_config is not None:
        # Load test config if passed in
        app.config.from_mapping(test_config)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize Database
    from . import database
    database.init_app(app)
    
    # Register custom template filters
    @app.template_filter('percentage')
    def percentage_filter(value):
        if value is None:
            return "0%"
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return str(value)

    @app.template_filter('score_color')
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

    # Register Blueprints
    from .auth.routes import bp as auth_bp
    app.register_blueprint(auth_bp)

    from .dashboard.routes import bp as dashboard_bp
    app.register_blueprint(dashboard_bp)

    from .employees.routes import bp as employees_bp
    app.register_blueprint(employees_bp)

    from .projects.routes import bp as projects_bp
    app.register_blueprint(projects_bp)

    # Register API Blueprints
    from .api_routes.projects import bp as api_projects_bp
    app.register_blueprint(api_projects_bp)
    
    from .api_routes.tasks import bp as api_tasks_bp
    app.register_blueprint(api_tasks_bp)
    
    from .api_routes.insights import bp as api_insights_bp
    app.register_blueprint(api_insights_bp)

    # Global Redirect from Root to Dashboard
    @app.route('/')
    def index():
        return redirect(url_for('dashboard.index'))

    return app
