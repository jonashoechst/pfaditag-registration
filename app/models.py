from datetime import datetime

from app import db


class Land(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)

    def __repr__(self):
        return f'<Land {self.id} ({self.name})>'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))

    street = db.Column(db.String(64))
    number = db.Column(db.String(32))
    zip = db.Column(db.Integer)
    city = db.Column(db.String(64))

    website = db.Column(db.String(64))
    land_id = db.Column(db.Integer, db.ForeignKey('land.id'))

    def __repr__(self):
        return f'<Group {self.id} ({self.name})>'


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), index=True)

    email = db.Column(db.String(64))
    tel = db.Column(db.String(32))

    start = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    description = db.Column(db.String(2000))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __repr__(self):
        return f'<Event {self.id} ({self.title})>'
