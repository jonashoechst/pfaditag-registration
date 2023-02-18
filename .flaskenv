# values are parsed with json.loads(), hence boolean values need to be lowercase or 0/1
FLASK_APP = "registration.py"
FLASK_DEBUG = 1
FLASK_SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
FLASK_SECRET_KEY = "5f352379324c22463451387a0aec5d2f"
FLASK_SQLALCHEMY_TRACK_MODIFICATIONS = False


FLASK_MAIL_SERVER = "harrington.uberspace.de"
FLASK_MAIL_USERNAME = "pfaditag@jonashoechst.de"
FLASK_MAIL_PASSWORD = ""
FLASK_MAIL_PORT = 587
FLASK_MAIL_USE_TLS = 1
FLASK_MAIL_USE_SSL = 0
