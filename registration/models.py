import datetime

from registration import db


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

    date = db.Column(db.Date, index=True, default=datetime.date(2022, 9, 24))
    time = db.Column(db.Time, index=True)
    description = db.Column(db.String(2000))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __repr__(self):
        return f'<Event {self.id} ({self.title})>'
