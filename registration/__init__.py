# fmt: off

import logging
import locale

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap

locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
Bootstrap(app)
app.config.update({
    "SECRET_KEY": "SomethingNotEntirelySecret",
    "SQLALCHEMY_DATABASE_URI": "sqlite:///test.db",
    "SQLALCHEMY_TRACK_MODIFICATIONS": False,
})

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from registration import routes, models
