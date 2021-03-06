import datetime
import flask
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from flask_login import current_user, login_required
from wtforms import (
    StringField,
    EmailField,
    TelField,
    SubmitField,
    TextAreaField,
    SelectField,
    DateField,
    TimeField,
)
from wtforms.validators import (
    DataRequired,
    URL,
    Optional,
    Email,
)

from . import models
from .models import db

current_user: models.User

admin_bp = flask.Blueprint('admin', __name__, url_prefix='/admin', static_folder='static')


class LandForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])


class GroupForm(FlaskForm):
    name = StringField('Stammesname', validators=[DataRequired()])
    street = StringField('Straße, Nr.', validators=[Optional()])
    zip = StringField('PLZ', validators=[Optional()])
    city = StringField('Ort', validators=[DataRequired()])
    website = StringField('Website', validators=[Optional(), URL(False)])
    land_id = SelectField('VCP Land', validators=[DataRequired()], coerce=int)

    submit = SubmitField('Speichern')
    delete = SubmitField('Löschen')


class EventForm(FlaskForm):
    group_id = SelectField('Stamm', validators=[DataRequired()], coerce=int)
    title = StringField('Aktionstitel', validators=[DataRequired()])
    email = EmailField(
        'E-Mail Adresse',
        validators=[Optional(), Email()],
        description="Die E-Mail Adresse und Telefonnummer werden öffentlich angezeigt."
    )
    tel = TelField(
        'Telefonnummer',
        validators=[Optional()],
    )

    date = DateField('Aktionstag', validators=[DataRequired()])
    time = TimeField('Startzeit', validators=[DataRequired()])
    date_end = DateField('Aktionstag (Ende)')
    time_end = TimeField('Endzeit', validators=[DataRequired()])
    description = TextAreaField(
        'Beschreibung',
        validators=[Optional()],
        render_kw={'rows': '12'},
        description="Versuche einen kurzen Text zu schreiben, der die Aktion beschreibt und auch nicht-Pfadfindern gut erklärt, was ihr macht."
    )
    photo = FileField("Aktionsfoto",
                      description="Für jede Aktion kann ein Foto hochgeladen werden, ein Neues ersetzt das Alte.",
                      validators=[
                          FileAllowed(['jpg', "JPG", 'png', 'PNG', 'jpeg', "JPEG", "gif", "GIF"], 'Hier können nur Bilder hochgeladen werden (jpg, png, gif).'),
                          FileSize(16*1024**2, 0, "Hochgeladene Fotos dürfen 16 MB nicht überschreiten.")
                      ],
                      )

    lat = StringField(
        "Treffpunkt (Latitude)",
        description="Die Koordinaten des Treffpunktes kannst du durch klicken auf die Karte eingeben.",
    )
    lon = StringField(
        "Treffpunkt (Longitude)",
    )

    submit = SubmitField('Speichern')
    delete = SubmitField('Löschen')


@admin_bp.route('/groups')
@login_required
def groups():
    if not current_user.has_permissions:
        flask.flash("Du hast noch keine Berechtigungen erteilt bekommen.")

    return flask.render_template('admin/groups.html')


@admin_bp.route('/groups/edit/<_id>', methods=['GET', 'POST'])
@login_required
def groups_edit(_id):
    form = GroupForm()

    # create new group if keyword is given
    if _id == "new":
        if current_user.is_superuser:
            group = models.Group()
            db.session.add(group)
        elif current_user.is_manager_land and current_user.manage_land:
            group = models.Group(land_id=current_user.manage_land.id)
            db.session.add(group)
        else:
            flask.flash('Du bist nicht berechtigt, einen neuen Stamm anzulegen.', 'danger')
            return flask.redirect(flask.request.referrer or flask.url_for('admin.groups'))
    else:
        group = models.Group.query.get(_id)

        # check if user is allows to edit event
        if group not in current_user.query_groups():
            flask.flash("Du bist nicht berechtigt, diese Gruppe zu bearbeiten.", "danger")
            return flask.redirect(flask.request.referrer or flask.url_for('admin.groups'))

    # form.land_id.choices = models.Land.query.all()
    form.land_id.choices = [(l.id, l.name) for l in current_user.query_lands()]
    if group.land and group.land not in current_user.query_lands():
        form.land_id.choices.append((group.land_id, group.land.name))

    # POST: delete group
    if form.delete.data:
        for event in group.events:
            db.session.delete(event)
        db.session.delete(group)
        db.session.commit()
        flask.flash(f"Stamm '{group.name}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for('admin.groups'))

    # POST: save group
    if form.submit.data:
        if form.validate_on_submit():
            for field_id, field in form._fields.items():
                setattr(group, field_id, field.data)

            db.session.commit()
            flask.flash(f"Stamm '{group.name}' wurde gespeichert.", "success")

            return flask.redirect(flask.url_for('admin.groups'))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in group.__dict__:
            field.data = group.__dict__[field_id]

    _title = f"Stamm {group.name} bearbeiten" if _id != "new" else "Neuen Stamm anlegen"

    return flask.render_template('generic_form.html', form=form, _id=_id, title=_title)


@admin_bp.route('/events/edit/<_id>', methods=['GET', 'POST'])
@login_required
def events_edit(_id):
    form = EventForm()

    # create new group if keyword is given
    if _id == "new":
        event = models.Event()
        db.session.add(event)
    else:
        event = models.Event.query.get(_id)

        # check if user is allows to edit event
        if event not in current_user.query_events():
            flask.flash("Du bist nicht berechtigt, diese Aktion zu bearbeiten.", "danger")
            return flask.redirect(flask.request.referrer or flask.url_for('public.events'))

    form.group_id.choices = [(g.id, g.display_name) for g in current_user.query_groups()]

    # POST: delete
    if form.delete.data:
        db.session.delete(event)
        db.session.commit()
        flask.flash(f"Aktion '{event.title}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for('public.events'))

    # POST: submit
    if form.submit.data:
        if form.validate_on_submit():
            # check if event ends after start
            dt_start = datetime.datetime.combine(form.date.data, form.time.data)
            dt_end = datetime.datetime.combine(form.date_end.data, form.time_end.data)
            if dt_end <= dt_start:
                flask.flash("Das Ende der Aktion liegt vor deren Beginn. Die Aktion konnte nicht gespeichert werden.", "danger")
                return flask.render_template('admin/events_edit.html', form=form, _id=_id)

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

            db.session.commit()
            flask.flash(f"Aktion '{event.title}' wurde gespeichert.", "success")

            return flask.redirect(flask.url_for('admin.events_edit', _id=event.id))

    # GET: initialize form values
    for field_id, field in form._fields.items():
        if field_id in event.__dict__:
            field.data = event.__dict__[field_id]

    return flask.render_template('admin/events_edit.html', form=form, _id=_id)
