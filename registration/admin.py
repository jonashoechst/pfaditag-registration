import datetime
from typing import Any

import flask
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileSize
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    SelectField,
    StringField,
    SubmitField,
    TelField,
    TextAreaField,
    TimeField,
)
from wtforms.validators import (
    URL,
    DataRequired,
    Email,
    Length,
    Optional,
)

from . import models
from .models import db

admin_bp = flask.Blueprint("admin", __name__, url_prefix="/admin", static_folder="static")


class GroupForm(FlaskForm):
    group_type = SelectField(
        "Ebene",
        validators=[
            Length(max=64),
        ],
        choices=[
            ("", ""),
            ("Land", "Land"),
            ("Landesverband", "Landesverband"),
            ("Region", "Region"),
            ("Gau", "Gau"),
            ("Bezirk", "Bezirk"),
            ("Stamm", "Stamm"),
            ("Siedlung", "Siedlung"),
            ("Neuanfang", "Neuanfang"),
            ("Aufbaugruppe", "Aufbaugruppe"),
        ],
    )
    name = StringField(
        "Name",
        validators=[
            DataRequired(),
            Length(max=255),
        ],
        description="Name der Gliederung, je nach Nutzung in der Gruppierung auch mit Ortsname.",
    )
    street = StringField(
        "Straße, Nr.",
        validators=[
            Optional(),
            Length(max=64),
        ],
    )
    zip = StringField(
        "PLZ",
        validators=[
            Optional(),
            Length(max=5),
        ],
    )
    city = StringField(
        "Ort",
        validators=[
            Optional(),
            Length(max=64),
        ],
    )
    website = StringField(
        "Website",
        validators=[
            Optional(),
            URL(False),
            Length(max=64),
        ],
    )
    instagram = StringField(
        "Instagram",
        validators=[
            Optional(),
            URL(False),
            Length(max=64),
        ],
        render_kw={"placeholder": "https://instagram.com/"},
    )
    facebook = StringField(
        "Facebook",
        validators=[
            Optional(),
            URL(False),
            Length(max=64),
        ],
        render_kw={"placeholder": "https://www.facebook.com/"},
    )

    submit = SubmitField("Speichern")


class EventForm(FlaskForm):
    group_id = SelectField(
        "Gliederung",
        validators=[DataRequired()],
    )
    title = StringField(
        "Aktionstitel",
        validators=[
            DataRequired(),
            Length(max=64),
        ],
    )
    email = EmailField(
        "E-Mail Adresse",
        validators=[
            Optional(),
            Email(),
            Length(max=64),
        ],
        description="Die E-Mail Adresse und Telefonnummer werden öffentlich angezeigt.",
    )
    tel = TelField(
        "Telefonnummer",
        validators=[
            Optional(),
            Length(max=32),
        ],
    )

    date = DateField("Aktionstag", validators=[DataRequired()])
    time = TimeField("Startzeit", validators=[DataRequired()])
    date_end = DateField("Aktionstag (Ende)")
    time_end = TimeField("Endzeit", validators=[DataRequired()])
    description = TextAreaField(
        "Beschreibung",
        validators=[
            Optional(),
            Length(max=2000),
        ],
        render_kw={"rows": "12"},
        description="Versuche einen kurzen Text zu schreiben, der die Aktion beschreibt und auch nicht-Pfadfindern gut erklärt, was ihr macht.",
    )
    photo = FileField(
        "Aktionsfoto",
        description="Für jede Aktion kann ein Foto hochgeladen werden, ein Neues ersetzt das Alte.",
        validators=[
            FileAllowed(
                ["jpg", "JPG", "png", "PNG", "jpeg", "JPEG", "gif", "GIF"],
                "Hier können nur Bilder hochgeladen werden (jpg, png, gif).",
            ),
            FileSize(16 * 1024**2, 0, "Hochgeladene Fotos dürfen 16 MB nicht überschreiten."),
        ],
    )

    lat = StringField(
        "Treffpunkt (Latitude)",
        description="Die Koordinaten des Treffpunktes kannst du durch klicken auf die Karte eingeben.",
        validators=[DataRequired()],
    )
    lon = StringField(
        "Treffpunkt (Longitude)",
        validators=[DataRequired()],
    )

    submit = SubmitField("Speichern")
    delete = SubmitField("Löschen")


@admin_bp.route("/groups")
@login_required
def groups():
    group_id = flask.request.args.get("group_id")
    group = db.session.get(models.Group, group_id)
    if group_id and not group:
        flask.flash("Gliederung konnte nicht gefunden werden.", "warning")

    if group:
        if not current_user.has_group_permission(group.id):
            flask.flash(f"Du hast keine Berechtigung die Gliederung von {group} anzuzeigen.", "warning")
        else:
            return flask.render_template("admin/groups.j2", groups=group.subtree, title=f"Gliederungen {group}")

    return flask.render_template("admin/groups.j2", groups=current_user.query_groups())


@admin_bp.route("/groups/edit/<group_id>", methods=["GET", "POST"])
@login_required
def group_edit(group_id):
    form = GroupForm()

    if not current_user.has_group_permission(group_id):
        flask.flash("Du bist nicht berechtigt, diese Gruppe zu bearbeiten.", "danger")
        return flask.redirect(flask.request.referrer or flask.url_for("auth.edit_user", user_id=current_user.id))

    group = models.Group.query.get(group_id)

    # POST: save group
    if form.submit.data:
        if form.validate_on_submit():
            for field_id, field in form._fields.items():
                setattr(group, field_id, field.data)

            db.session.commit()
            flask.flash(f"Gliederung '{group}' wurde gespeichert.", "success")

            return flask.redirect(flask.url_for("admin.groups"))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in group.__dict__:
            field.data = group.__dict__[field_id]

    return flask.render_template("admin/group_edit.j2", form=form, group=group)


@admin_bp.route("/events/edit/<_id>", methods=["GET", "POST"])
@login_required
def events_edit(_id):
    form = EventForm()

    # create new group if keyword is given
    if _id == "new":
        event = models.Event()
        group_id = flask.request.args.get("group_id")
        group = models.Group.query.get(group_id)
        if group:
            form.group_id.data = group.id
    else:
        event: Any | None = models.Event.query.get(_id)

        # check if user is allows to edit event
        if not event or event not in current_user.query_events():
            flask.flash("Du bist nicht berechtigt, diese Aktion zu bearbeiten.", "danger")
            return flask.redirect(flask.request.referrer or flask.url_for("public.events"))

    form.group_id.choices = [(g.id, g.name) for g in current_user.query_groups()]

    # POST: delete
    if form.delete.data:
        db.session.delete(event)
        db.session.commit()
        flask.flash("Aktion wurde erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for("public.events"))

    # POST: submit
    if form.submit.data:
        if form.validate_on_submit():
            # check if event ends after start
            dt_start = datetime.datetime.combine(form.date.data, form.time.data)
            dt_end = datetime.datetime.combine(form.date_end.data, form.time_end.data)
            if dt_end < dt_start:
                flask.flash(
                    "Das Ende der Aktion liegt vor dem Beginn. Die Aktion konnte nicht gespeichert werden.", "danger"
                )
                return flask.render_template("admin/events_edit.j2", form=form, _id=_id)

            # update fields in model
            for field_id, field in form._fields.items():
                if field_id in ["lat", "lon"]:
                    try:
                        setattr(event, field_id, float(field.data))
                    except ValueError:
                        setattr(event, field_id, None)
                if field_id == "photo":
                    if field.data:
                        blob = field.data.stream.read()
                        setattr(event, field_id, blob)
                else:
                    setattr(event, field_id, field.data)

            db.session.add(event)
            db.session.commit()
            flask.flash(f"Aktion '{event.title}' wurde gespeichert.", "success")

            return flask.redirect(flask.url_for("admin.events_edit", _id=event.id))

    # GET: initialize form values
    for field_id, field in form._fields.items():
        if field_id in event.__dict__:
            field.data = event.__dict__[field_id]

    return flask.render_template("admin/events_edit.j2", form=form, _id=_id)


class MailForm(FlaskForm):
    recv_users = BooleanField(
        "Koordinator*innen",
        description="Sende an alle Koordinator*innen, die auf deiner Ebene oder darunter sind (z.B. Stämme deines Landes).",
    )
    recv_event_mails = BooleanField(
        "Kontaktadressen Aktionen",
        description="Sende an alle Aktionen, die du in deiner Rolle verwalten kannst (z.B. Aktionen deines Landes).",
    )
    subject = StringField(
        "Betreff",
        validators=[
            DataRequired(),
            Length(max=400),
        ],
    )
    text = TextAreaField(
        "Text",
        validators=[
            Length(max=10000),
        ],
        render_kw={"rows": "12"},
    )

    submit = SubmitField("Senden")
