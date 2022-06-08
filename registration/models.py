import csv
import datetime
import secrets
from typing import List

from flask_sqlalchemy import event
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class Land(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    groups = db.relationship('Group', back_populates='land')
    regions = db.relationship('Region', back_populates='land')
    users = db.relationship('User', back_populates='manage_land')

    def __repr__(self):
        return f'<Land {self.id} ({self.name})>'

    def query_managers(self):
        return User.query.filter(
            (User.is_superuser) |
            (User.is_manager_land & (User.manage_land_id == self.id))
        )


class Region(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)

    land_id = db.Column(db.Integer, db.ForeignKey('land.id'))
    land = db.relationship("Land", back_populates="regions")

    groups = db.relationship('Group', back_populates='region')

    def __repr__(self):
        return f'<Region {self.id} ({self.name})>'


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(64))
    street = db.Column(db.String(64))
    zip = db.Column(db.String(5))
    city = db.Column(db.String(64))
    website = db.Column(db.String(64))

    land_id = db.Column(db.Integer, db.ForeignKey('land.id'))
    land = db.relationship("Land", back_populates="groups")

    region_id = db.Column(db.Integer, db.ForeignKey('region.id'))
    region = db.relationship("Region", back_populates="groups")

    events = db.relationship('Event', back_populates='group')

    def __repr__(self):
        return f'<Group {self.id} ({self.name})>'

    @property
    def display_name(self):
        return f'{self.land.name}, Stamm {self.name}, {self.city} ({self.id})'

    @property
    def short_name(self):
        return f'Stamm {self.name}, {self.city}'

    def query_managers(self):
        return User.query.filter(
            (User.is_superuser) |
            (User.is_manager_land & (User.manage_land_id == self.land_id))
        )


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
    group = db.relationship("Group", back_populates="events")

    def __repr__(self):
        return f'<Event {self.id} ({self.title})>'


class User(UserMixin, db.Model):
    id = db.Column(db.String(40), unique=True, primary_key=True)
    password = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=False)

    manage_land_id = db.Column(db.Integer, db.ForeignKey('land.id'), nullable=True)
    manage_land = db.relationship('Land')
    manage_group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    manage_group = db.relationship('Group')

    # permissions
    is_superuser = db.Column(db.Boolean, default=False)
    is_manager_land = db.Column(db.Boolean, default=False)
    is_manager_group = db.Column(db.Boolean, default=False)

    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    token = db.Column(db.String(32), unique=False, nullable=True)
    token_expiration = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def set_password(self, password):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password):
        if not password:
            return False
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.id} ({self.name})>'

    def query_groups(self) -> List[Group]:
        '''Returns a list of groups the user can manage'''
        groups = []

        if self.is_manager_group and self.manage_group_id:
            groups.append(self.manage_group)
        if self.is_manager_land and self.manage_land_id:
            for group in self.manage_land.groups:
                if group not in groups:
                    groups.append(group)
        if self.is_superuser:
            for group in Group.query.all():
                if group not in groups:
                    groups.append(group)

        return groups

    def query_events(self) -> List[Event]:
        '''Returns a list of events that the user is allowed to manage'''
        events = []

        if self.is_manager_group and self.manage_group_id:
            events += self.manage_group.events
        if self.is_manager_land and self.manage_land_id:
            for group in self.manage_land.groups:
                for event in group.events:
                    if event not in events:
                        events.append(event)
        if self.is_superuser:
            for event in Event.query.all():
                if event not in events:
                    events.append(event)

        return events

    def query_lands(self) -> List[Land]:
        '''Returns a list of lands the user can manage'''
        lands = []

        if self.is_manager_land and self.manage_land_id:
            lands.append(self.manage_land)
        if self.is_superuser:
            for land in Land.query.all():
                if land not in lands:
                    lands.append(land)

        return lands

    def query_users(self) -> List:
        '''Returns as list of users this user can manage'''
        users = [self]

        if self.is_manager_land and self.manage_land_id:
            for user in self.manage_land.users:
                if user not in users:
                    users.append(user)
        if self.is_superuser:
            for user in User.query.all():
                if user not in users:
                    users.append(user)

        return users

    def query_managers(self) -> List:
        '''Returns a list of users that can manage this user'''
        return User.query.filter(
            # all managers of the same land
            (User.is_manager_land & (User.manage_land_id == self.manage_land_id)) |
            # all managers of the group's land
            (User.is_manager_land & (User.manage_land_id == self.manage_group.land_id))
        )

    def set_token(self, validity: datetime.timedelta = datetime.timedelta(days=1)) -> str:
        self.token = secrets.token_urlsafe(32)
        self.token_expiration = datetime.datetime.now() + validity

        return self.token

    def reset_token(self):
        self.set_token(validity=datetime.timedelta(0))

    def verify_token(self, token) -> bool:
        if self.token and self.token_expiration:
            if self.token == token and self.token_expiration > datetime.datetime.now():
                return True

        return False

    @ property
    def has_permissions(self) -> bool:
        return (self.is_superuser or self.is_manager_land or self.is_manager_group)


@ event.listens_for(Group.__table__, 'after_create')
def create_departments(*args, **kwargs):
    with open("etc/group_list.csv") as group_list:
        group_reader = csv.reader(group_list, dialect='excel', delimiter=';')
        next(group_reader)
        for _id, _land, _region, _name, _ort, *_ in group_reader:
            try:
                _name = _name.removeprefix("VCP ")
                _name = _name.removeprefix("Stamm ")
                _name = _name.strip()

                group = Group(
                    id=int(_id),
                    name=_name.strip(),
                    zip=_ort[:5],
                    city=_ort[6:],
                    land_id=int(_id[:2]),
                    region_id=int(_id[:4]),
                )
                db.session.add(group)

                if Land.query.filter_by(id=group.land_id).count() == 0:
                    land = Land(
                        id=group.land_id,
                        name=_land.strip(),
                    )
                    db.session.add(land)

                if Region.query.filter_by(id=group.region_id).count() == 0:
                    region = Region(
                        id=group.region_id,
                        name=_region.strip(),
                        land_id=group.land_id,
                    )
                    db.session.add(region)

                db.session.commit()

            except ValueError:
                pass

    db.session.commit()
