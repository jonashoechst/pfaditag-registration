# fmt: off

import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.update({
    "SECRET_KEY": "SomethingNotEntirelySecret",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///test.db",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
})

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes
