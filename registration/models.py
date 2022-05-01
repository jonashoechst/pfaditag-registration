import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Land(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    groups = db.relationship('Group', backref='land', lazy=True)

    def __repr__(self):
        return f'<Land {self.id} ({self.name})>'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64))
    street = db.Column(db.String(64))
    zip = db.Column(db.String(5))
    city = db.Column(db.String(64))
    website = db.Column(db.String(64))

    land_id = db.Column(db.Integer, db.ForeignKey('land.id'))
    groups = db.relationship('Event', backref='group', lazy=True)

    def __repr__(self):
        return f'<Group {self.id} ({self.name})>'


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(64), index=True)
    email = db.Column(db.String(64))
    tel = db.Column(db.String(32))

    lat = db.Column(db.Numeric(8, 6))
    lon = db.Column(db.Numeric(9, 6))

    date = db.Column(db.Date, index=True, default=datetime.date(2022, 9, 24))
    time = db.Column(db.Time, index=True, default=datetime.time(00, 00))
    description = db.Column(db.String(2000))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __repr__(self):
        return f'<Event {self.id} ({self.title})>'


class User(UserMixin, db.Model):
    id = db.Column(db.String(40), unique=True, primary_key=True)
    password = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=False)

    manage_land_id = db.Column(db.Integer, db.ForeignKey('land.id'), nullable=True)
    manage_group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)

    # permissions
    is_superuser = db.Column(db.Boolean, default=False)
    is_manager_land = db.Column(db.Boolean, default=False)
    is_manager_group = db.Column(db.Boolean, default=False)

    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.id} ({self.name})>'
