# fmt: off

import logging
import logging.config
import locale

from flask import Flask
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config['APP_TITLE'] = "PfadiTag 2022"
    app.config.from_prefixed_env()

    logging.getLogger("flask_wtf").handlers = app.logger.handlers
    logging.getLogger("flask_wtf.csrf").handlers = app.logger.handlers

    Bootstrap5(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)


    with app.app_context():
        from registration.admin import admin_bp
        app.register_blueprint(admin_bp)

        from registration.public import public_bp
        app.register_blueprint(public_bp)

        from registration.auth import auth_bp
        app.register_blueprint(auth_bp)

        from registration.sharepics import sharepics_bp
        app.register_blueprint(sharepics_bp)

        with db.session.no_autoflush:
            db.create_all()
        return app
