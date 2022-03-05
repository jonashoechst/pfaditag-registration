from datetime import datetime

from registration import db


class land(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    groups = db.relationship('group', backref='land', lazy=True)

    def __repr__(self):
        return f'<Land {self.id} ({self.name})>'


class group(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64))
    street = db.Column(db.String(64))
    zip = db.Column(db.String(5))
    city = db.Column(db.String(64))
    website = db.Column(db.String(64))

    land_id = db.Column(db.Integer, db.ForeignKey('land.id'))

    def __repr__(self):
        return f'<Group {self.id} ({self.name})>'


class event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), index=True)

    email = db.Column(db.String(64))
    tel = db.Column(db.String(32))

    start = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    description = db.Column(db.String(2000))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __repr__(self):
        return f'<Event {self.id} ({self.title})>'
