# fmt: off

import logging
import locale

from flask import Flask
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
logging.basicConfig(level=logging.DEBUG)

migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()

    Bootstrap5(app)

    from registration.models import db
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    with app.app_context():
        from registration.admin import admin_bp
        app.register_blueprint(admin_bp)

        from registration.public import public_bp
        app.register_blueprint(public_bp)

        from registration.auth import auth_bp
        app.register_blueprint(auth_bp)

        return app
