# fmt: off

import locale

from flask import Flask
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from sqlalchemy import MetaData

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

metadata = MetaData(
    naming_convention={
        "ix": 'ix_%(column_0_label)s',
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()


def create_app():
    app = Flask(__name__)
    app.config['APP_TITLE'] = "PfadiTag 2024"
    app.config.from_prefixed_env()

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

        from registration.models import update_groups
        update_groups()

        return app
