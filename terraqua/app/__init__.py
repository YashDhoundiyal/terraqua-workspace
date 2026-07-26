import os

from flask import Flask, render_template, redirect, url_for
from flask_login import current_user

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.manager.routes import manager_bp
    from app.employee.routes import employee_bp
    from app.api.routes import api_bp
    from app.reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for(f"{current_user.role}.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(401)
    def unauthorized(e):
        return redirect(url_for("auth.login"))

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.context_processor
    def inject_globals():
        from app.utils import utcnow
        return {"current_year": utcnow().year}

    from app.seed import seed_cli, run_seed
    app.cli.add_command(seed_cli)

    with app.app_context():
       from app.models import User

if User.query.count() == 0:
    run_seed()

 from app.seed ...
app.cli.add_command(...)

with app.app_context():
    ...

return app
