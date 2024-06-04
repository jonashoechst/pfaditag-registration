from __future__ import annotations

import datetime
import hmac
import secrets

import flask
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped
from werkzeug.security import check_password_hash, generate_password_hash

from . import db

db: SQLAlchemy


class Group(db.Model):
    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    parent_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("group.id"), nullable=True)
    parent: Mapped[Group] = db.relationship("Group", back_populates="children", remote_side=[id])
    children: Mapped[list[Group]] = db.relationship("Group", back_populates="parent")
    attributes: Mapped[dict] = db.Column(db.JSON, default={})
    group_type: Mapped[str] = db.Column(db.String(255), nullable=False, default="")

    name: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    street: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    zip: Mapped[str] = db.Column(db.String(5), nullable=False, default="")
    city: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    website: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    instagram: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    facebook: Mapped[str] = db.Column(db.String(64), nullable=False, default="")

    display: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)

    events: Mapped[list[Event]] = db.relationship("Event", back_populates="group")
    # users: Mapped[list[User]] = db.relationship('User', secondary="user_permission", back_populates="groups")
    permissions: Mapped[list[UserPermission]] = db.relationship("UserPermission")

    @property
    def users(self) -> list[User]:
        return [p.user for p in self.permissions if p.granted]

    def __repr__(self) -> str:
        return f"<Group {self.id} ({self.name})>"

    def __str__(self) -> str:
        if self.group_type:
            return self.group_type + " " + self.name
        return self.name

    @property
    def display_name(self) -> str:
        return str(self)

    @property
    def subtree(self) -> list[Group]:
        return [self] + [gc for c in self.children for gc in c.subtree]

    @property
    def root(self) -> Group:
        if not self.parent_id:
            return self
        return self.parent.root

    @property
    def path(self) -> list[Group]:
        if not self.parent_id:
            return [self]
        return self.parent.path + [self]

    @property
    def depth(self) -> int:
        if not self.parent_id:
            return 0
        return self.parent.depth + 1


class Event(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)

    title: Mapped[str] = db.Column(db.String(64), index=True)
    email: Mapped[str] = db.Column(db.String(64), nullable=False, default="")
    tel: Mapped[str] = db.Column(db.String(32), nullable=False, default="")

    lat: Mapped[float] = db.Column(db.Numeric(8, 6), nullable=False)
    lon: Mapped[float] = db.Column(db.Numeric(9, 6), nullable=False)

    date: Mapped[datetime.date] = db.Column(db.Date, nullable=False, index=True, default=datetime.date(2024, 9, 20))
    time: Mapped[datetime.date] = db.Column(db.Time, nullable=False, index=True, default=datetime.time(00, 00))
    date_end: Mapped[datetime.date] = db.Column(db.Date, nullable=False, index=True, default=datetime.date(2024, 9, 22))
    time_end: Mapped[datetime.date] = db.Column(db.Time, nullable=False, index=True, default=datetime.time(00, 00))

    description: Mapped[str] = db.Column(db.String(2000), nullable=False)

    group_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey("group.id"))
    group: Mapped[Group] = db.relationship("Group", back_populates="events")

    def __repr__(self) -> str:
        return f"<Event {self.id} ({self.title})>"

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

    @property
    def is_current(self) -> bool:
        return self.date.year == datetime.date.today().year


class User(UserMixin, db.Model):
    id: Mapped[int] = db.Column(db.String(100), unique=True, primary_key=True)
    password: Mapped[str] = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)
    name: Mapped[str] = db.Column(db.String(100), nullable=False, unique=False)
    # groups: Mapped[list[Group]] = db.relationship('Group', secondary="user_permission", back_populates="users")

    # permissions
    is_superuser: Mapped[bool] = db.Column(db.Boolean, default=False)
    permissions: Mapped[list[UserPermission]] = db.relationship("UserPermission")

    created_on: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    token: Mapped[str] = db.Column(db.String(32), unique=False, nullable=True)
    token_expiration: Mapped[datetime.datetime] = db.Column(db.DateTime, index=False, unique=False, nullable=True)

    def set_password(self, password: str):
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not password:
            return False

        method, salt, hashval = self.password.split("$", 2)
        if method == "sha256":
            flask.flash(
                "Du hast dein Passwort schon länger nicht geändert. "
                + 'Du kannst es in <a href="'
                + flask.url_for("auth.edit_user", user_id=self.id)
                + '">deinen Accounteinstellungen</a> neu setzen.',
                "warning",
            )

            usalt = salt.encode("utf-8")
            upass = password.encode("utf-8")
            return hmac.compare_digest(hmac.new(usalt, upass, "sha256").hexdigest(), hashval)

        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f"<User {self.id} ({self.name})>"

    @property
    def groups(self) -> list[Group]:
        return [p.group for p in self.permissions if p.granted]

    def query_groups(self) -> list[Group]:
        """Returns a list of groups the user can manage"""
        flask.current_app.logger.debug("%s.query_groups()", self)
        groups = []

        # add all direct groups
        for group in self.groups:
            if group not in groups:
                groups.append(group)

        # add all subtree groups
        for group in self.groups:
            for pgroup in group.subtree:
                if pgroup not in groups:
                    groups.append(pgroup)

        # add all groups
        if self.is_superuser:
            for group in Group.query.all():
                if group not in groups:
                    groups.append(group)

        return groups

    def query_events(self) -> list[Event]:
        """Returns a list of events that the user is allowed to manage"""
        flask.current_app.logger.debug("%s.query_events()", self)
        events = []

        for group in self.query_groups():
            for event in group.events:
                if event not in events:
                    events.append(event)

        if self.is_superuser:
            for event in Event.query.all():
                if event not in events:
                    events.append(event)

        return events

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

    def has_group_permission(self, group_id: str) -> bool:
        """Returns a boolean indicating the user has permissions to access the group"""
        if self.is_superuser:
            return True

        for group in self.groups:
            for subgroup in group.subtree:
                if group_id == subgroup.id:
                    return True

        return False

    def has_event_permission(self, event: Event) -> bool:
        """Returns a boolean indicating the user has permissions to access the group"""
        return self.has_group_permission(event.group)


class UserPermission(db.Model):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[str] = db.Column(db.String(100), db.ForeignKey(User.id))
    group_id: Mapped[str] = db.Column(db.String(64), db.ForeignKey(Group.id))

    granted: Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)

    user: Mapped[User] = db.relationship("User", back_populates="permissions")
    group: Mapped[Group] = db.relationship("Group", back_populates="permissions")

    def query_grantable_users(self) -> list[User]:
        "Returns a list of users that are allowed to grant this permission"
        users = []
        for pgroup in self.group.path:
            for perm in pgroup.permissions:
                if perm.granted and perm.user not in users:
                    users.append(perm.user)

        return users
