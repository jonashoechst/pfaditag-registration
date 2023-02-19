from __future__ import annotations
import csv
import datetime
import logging
import secrets

import flask
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped
from sqlalchemy.exc import OperationalError, ProgrammingError
from . import db
db: SQLAlchemy


class Land(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(64), index=True)
    groups: Mapped[list[Group]] = db.relationship('Group', back_populates='land')
    regions: Mapped[list[Region]] = db.relationship('Region', back_populates='land')
    users: Mapped[list[User]] = db.relationship('User', back_populates='manage_land')

    def __repr__(self) -> str:
        return f'<Land {self.id} ({self.name})>'

    def query_managers(self) -> list[User]:
        return User.query.filter(
            (User.is_superuser) |
            (User.is_manager_land & (User.manage_land_id == self.id))
        )


class Region(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(db.String(64), index=True)

    land_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('land.id'))
    land: Mapped[Land] = db.relationship("Land", back_populates="regions")

    groups: Mapped[list[Group]] = db.relationship('Group', back_populates='region')
    users: Mapped[list[User]] = db.relationship('User', back_populates='manage_region')

    def __repr__(self) -> str:
        return f'<Region {self.id} ({self.name})>'

    @property
    def display_name(self) -> str:
        return f'{self.land.name}, {self.name} ({self.id})'

    def query_managers(self) -> list[User]:
        return User.query.filter(
            (User.is_superuser) |
            (User.is_manager_land & (User.manage_land_id == self.land_id))
            (User.is_manager_region & (User.manage_region_id == self.id))
        )


class Group(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    name: Mapped[str] = db.Column(db.String(64))
    street: Mapped[str] = db.Column(db.String(64))
    zip: Mapped[str] = db.Column(db.String(5))
    city: Mapped[str] = db.Column(db.String(64))
    website: Mapped[str] = db.Column(db.String(64))
    instagram: Mapped[str] = db.Column(db.String(64))
    facebook: Mapped[str] = db.Column(db.String(64))

    land_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('land.id'))
    land: Mapped[Land] = db.relationship("Land", back_populates="groups")

    region_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('region.id'))
    region: Mapped[Region] = db.relationship("Region", back_populates="groups")

    events: Mapped[list[Event]] = db.relationship('Event', back_populates='group')
    users: Mapped[list[User]] = db.relationship('User', back_populates='manage_group')

    def __repr__(self) -> str:
        return f'<Group {self.id} ({self.name})>'

    @property
    def display_name(self) -> str:
        return f'{self.land.name}, Stamm {self.name}, {self.city} ({self.id})'

    @property
    def short_name(self) -> str:
        return f'{self.name}, {self.city}'

    def query_managers(self) -> list[User]:
        return User.query.filter(
            (User.is_superuser) |
            (User.is_manager_land & (User.manage_land_id == self.land_id)) |
            (User.is_manager_group & (User.manage_group_id == self.id))
        )


class Event(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    title: Mapped[str] = db.Column(db.String(64), index=True)
    email: Mapped[str] = db.Column(db.String(64))
    tel: Mapped[str] = db.Column(db.String(32))

    lat: Mapped[float] = db.Column(db.Numeric(8, 6))
    lon: Mapped[float] = db.Column(db.Numeric(9, 6))

    date: Mapped[datetime.date] = db.Column(db.Date, index=True, default=datetime.date(2023, 9, 23))
    time: Mapped[datetime.date] = db.Column(db.Time, index=True, default=datetime.time(00, 00))
    date_end: Mapped[datetime.date] = db.Column(db.Date, index=True, default=datetime.date(2023, 9, 23))
    time_end: Mapped[datetime.date] = db.Column(db.Time, index=True, default=datetime.time(00, 00))

    description: Mapped[str] = db.Column(db.String(2000))
    photo = db.Column(db.LargeBinary(16*1024**2))

    group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('group.id'))
    group: Mapped[Group] = db.relationship("Group", back_populates="events")

    def __repr__(self) -> str:
        return f'<Event {self.id} ({self.title})>'

    @property
    def dt(self) -> datetime.datetime:
        return datetime.datetime.combine(self.date, self.time)

    @property
    def dt_end(self) -> datetime.datetime:
        return datetime.datetime.combine(self.date_end, self.time_end)

    @property
    def date_string(self) -> str:
        if self.date == self.date_end:
            return f'{self.date.strftime("%A, %d. %B %Y")} von {self.time.strftime("%H:%M")} bis {self.time_end.strftime("%H:%M")} Uhr'

        return f'von {self.dt.strftime("%A, %d.%m.%Y, %H:%M")} bis {self.dt_end.strftime("%A, %d.%m.%Y, %H:%M")} Uhr'

    @property
    def contact_string(self) -> str:
        if self.email and self.tel:
            return f"{self.email} - {self.tel}"
        elif self.tel:
            return self.tel
        elif self.email:
            return self.email
        elif self.group.website:
            return self.group.website
        else:
            return f"{self.group.zip} {self.group.city}"


class User(UserMixin, db.Model):
    id: Mapped[int] = db.Column(db.String(100), unique=True, primary_key=True)
    password: Mapped[str] = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    name: Mapped[str] = db.Column(db.String(100), nullable=False, unique=False)

    manage_land_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('land.id'), nullable=True)
    manage_land: Mapped[Land] = db.relationship('Land')
    manage_region_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=True)
    manage_region: Mapped[Region] = db.relationship('Region')
    manage_group_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)
    manage_group: Mapped[Group] = db.relationship('Group')

    # permissions
    is_superuser: Mapped[bool] = db.Column(db.Boolean, default=False)
    is_manager_land: Mapped[bool] = db.Column(db.Boolean, default=False)
    is_manager_region: Mapped[bool] = db.Column(db.Boolean, default=False)
    is_manager_group: Mapped[bool] = db.Column(db.Boolean, default=False)

    created_on: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    token: Mapped[str] = db.Column(db.String(32), unique=False, nullable=True)
    token_expiration: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def set_password(self, password: str):
        self.password = generate_password_hash(password, method='sha256')

    def check_password(self, password: str) -> bool:
        if not password:
            return False
        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f'<User {self.id} ({self.name})>'

    def query_groups(self) -> list[Group]:
        '''Returns a list of groups the user can manage'''
        flask.current_app.logger.debug("%s.query_groups()", self)
        groups = []

        if self.is_manager_group and self.manage_group_id:
            groups.append(self.manage_group)
        if self.is_manager_region and self.manage_region_id:
            for group in self.manage_region.groups:
                if group not in groups:
                    groups.append(group)
        if self.is_manager_land and self.manage_land_id:
            for group in self.manage_land.groups:
                if group not in groups:
                    groups.append(group)
        if self.is_superuser:
            for group in Group.query.all():
                if group not in groups:
                    groups.append(group)

        return groups

    def query_events(self) -> list[Event]:
        '''Returns a list of events that the user is allowed to manage'''
        flask.current_app.logger.debug("%s.query_events()", self)
        events = []

        if self.is_manager_group and self.manage_group_id:
            events += self.manage_group.events
        if self.is_manager_region and self.manage_region_id:
            for group in self.manage_region.groups:
                for event in group.events:
                    if event not in events:
                        events.append(event)
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

    def query_regions(self) -> list[Region]:
        '''Returns a list of regions the user can manage'''
        flask.current_app.logger.debug("%s.query_regions()", self)
        regions: list[Region] = []

        if self.is_manager_region and self.manage_region_id:
            regions.append(self.manage_region)
        if self.is_manager_land and self.manage_land_id:
            for region in self.manage_land.regions:
                if region not in regions:
                    regions.append(region)
        if self.is_superuser:
            for region in Region.query.all():
                if region not in region:
                    regions.append(region)

        return regions

    def query_lands(self) -> list[Land]:
        '''Returns a list of lands the user can manage'''
        flask.current_app.logger.debug("%s.query_lands()", self)
        lands: list[Land] = []

        if self.is_manager_land and self.manage_land_id:
            lands.append(self.manage_land)
        if self.is_superuser:
            for land in Land.query.all():
                if land not in lands:
                    lands.append(land)

        return lands

    def query_users(self) -> list[User]:
        '''Returns as list of users this user can manage'''
        flask.current_app.logger.debug("%s.query_users()", self)
        users: list[User] = [self]

        if self.is_manager_group and self.manage_group_id:
            for user in self.manage_group.users:
                if user not in users:
                    users.append(user)

        if self.is_manager_region and self.manage_region_id:
            # add all region managers
            for user in self.manage_region.users:
                if user not in users:
                    users.append(user)
            # add all managers of groups belonging to the land
            for group in self.manage_region.groups:
                for user in group.users:
                    if user not in users:
                        users.append(user)

        if self.is_manager_land and self.manage_land_id:
            # add all land managers
            for user in self.manage_land.users:
                if user not in users:
                    users.append(user)
            # add all managers of regions belonging to the land
            for region in self.manage_land.regions:
                for user in region.users:
                    if user not in users:
                        users.append(user)
            # add all managers of groups belonging to the land
            for group in self.manage_land.groups:
                for user in group.users:
                    if user not in users:
                        users.append(user)

        if self.is_superuser:
            # add all remaining users
            for user in User.query.all():
                if user not in users:
                    users.append(user)

        return users

    def query_managers(self) -> list[User]:
        '''Returns a list of users that can manage this user'''
        flask.current_app.logger.debug("%s.query_managers()", self)

        managers: list[User] = []

        # the group managers can be managed by
        if self.manage_group_id:
            for user in User.query.filter(
                # all managers of the group
                (User.is_manager_group & (User.manage_group_id == self.manage_group_id)) |
                # all managers of the group' region
                (User.is_manager_region & (User.manage_region_id == self.manage_group.region_id)) |
                # all managers of the group's land
                (User.is_manager_land & (User.manage_land_id == self.manage_group.land_id))
            ):
                if user not in managers:
                    managers.append(user)

        # the region managers can be managed by
        if self.manage_region_id:
            for user in User.query.filter(
                # all managers of the region
                (User.is_manager_region & (User.manage_region_id == self.manage_region_id)) |
                # all managers of the regions's land
                (User.is_manager_land & (User.manage_land_id == self.manage_region.land_id))
            ):
                if user not in managers:
                    managers.append(user)

        # the land managers can be managed by
        if self.manage_land_id:
            for user in User.query.filter(
                # all managers of the land
                (User.is_manager_land & (User.manage_land_id == self.manage_land_id))
            ):
                if user not in managers:
                    managers.append(user)

        return managers

    def set_token(self, validity: datetime.timedelta = datetime.timedelta(days=1)) -> str:
        self.token = secrets.token_urlsafe(24)
        self.token_expiration = datetime.datetime.now() + validity

        return self.token

    def reset_token(self):
        self.set_token(validity=datetime.timedelta(0))

    def verify_token(self, token) -> bool:
        if self.token and self.token_expiration:
            if self.token == token and self.token_expiration > datetime.datetime.now():
                return True

        return False

    @property
    def has_permissions(self) -> bool:
        return (self.is_superuser or self.is_manager_region or self.is_manager_land or self.is_manager_group)

    def has_group_permission(self, group: Group) -> bool:
        '''Returns a boolean indicating the user has permissions to access the group'''
        if self.is_superuser:
            return True
        if self.is_manager_land and self.manage_land_id == group.land_id:
            return True
        if self.is_manager_region and self.manage_region_id == group.region_id:
            return True
        if self.is_manager_group and self.manage_group_id == group.id:
            return True

        return False

    def has_event_permission(self, event: Event) -> bool:
        '''Returns a boolean indicating the user has permissions to access the group'''
        if self.is_superuser:
            return True
        if self.is_manager_land and self.manage_land == event.group.land_id:
            return True
        if self.is_manager_region and self.manage_region == event.group.region_id:
            return True
        if self.is_manager_group and self.manage_group_id == event.group_id:
            return True

        return False


def update_groups(csv_path="etc/group_list.csv"):
    try:
        group_list = open(csv_path, encoding="utf-8")
        group_reader = csv.reader(group_list, dialect='excel', delimiter=';')

        # skip csv header
        next(group_reader)

        for _id, _land, _region, _name, _ort, *_ in group_reader:
            # skip empty lines
            if _id == "":
                continue

            try:
                _name = _name[4:] if _name.startswith("VCP ") else _name
                _name = _name[6:] if _name.startswith("Stamm ") else _name
                _name = _name.strip()

                _land_id = int(_id[:2])
                land = Land.query.get(_land_id)
                if land is None:
                    land = Land(
                        id=_land_id,
                        name=_land.strip(),
                    )
                    db.session.add(land)
                    flask.current_app.logger.info("Created %s", land)

                _region_id = int(_id[:4])
                region = Region.query.get(_region_id)
                if region is None:
                    region = Region(
                        id=_region_id,
                        name=_region.strip(),
                        land_id=_land_id,
                    )
                    db.session.add(region)
                    flask.current_app.logger.info("Created %s", region)

                _group_id = int(_id)
                group = Group.query.get(_group_id)
                if group is None:
                    group = Group(
                        id=_group_id,
                        name=_name.strip(),
                        zip=_ort[:5],
                        city=_ort[6:],
                        land_id=_land_id,
                        region_id=_region_id,
                    )
                    db.session.add(group)
                    flask.current_app.logger.info("Created %s", group)

                db.session.commit()

            except ValueError as e:
                flask.current_app.logger.warning("Error parsing group '%s': %s", _id, e)

        db.session.commit()
    except (OperationalError, ProgrammingError) as e:
        flask.current_app.logger.warning("Couldn't update groups: %s", e)
    finally:
        group_list.close()
