import flask
from flask_wtf import FlaskForm
from wtforms import *
from wtforms.validators import DataRequired

from . import models
from .models import db

admin_bp = flask.Blueprint('admin', __name__, url_prefix='/admin', static_folder='static')


class LandForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])


class GroupForm(FlaskForm):
    name = StringField('Stammesname', validators=[DataRequired()])
    street = StringField('Straße, Nr.', validators=[DataRequired()])
    zip = StringField('PLZ', validators=[DataRequired()])
    city = StringField('Ort', validators=[DataRequired()])
    website = StringField('Website')
    land_id = SelectField('VCP Land', coerce=int)

    submit = SubmitField('Speichern')
    abort = SubmitField('Abbrechen')
    delete = SubmitField('Löschen')


class EventForm(FlaskForm):
    title = StringField('Aktionstitel', validators=[DataRequired()])
    email = EmailField('E-Mail Adresse')
    tel = TelField('Telefonnummer')

    date = DateField('Aktionstag')
    time = TimeField('Startzeit')
    description = TextAreaField('Beschreibung')
    group_id = SelectField('Gruppe', coerce=int)

    lat = HiddenField()
    lon = HiddenField()

    submit = SubmitField('Speichern')
    abort = SubmitField('Abbrechen')
    delete = SubmitField('Löschen')


@admin_bp.route('/groups')
def groups():
    _groups = models.Group.query.all()

    return flask.render_template('groups.html', groups=_groups)


@admin_bp.route('/groups/edit/<_id>', methods=['GET', 'POST'])
def groups_edit(_id):
    form = GroupForm()

    # create new group if keyword is given
    if _id == "new":
        group = models.Group()
        db.session.add(group)
    else:
        group = models.Group.query.get(_id)
        if group is None:
            return flask.redirect(flask.url_for('admin.groups_edit', _id="new"))

    form.land_id.choices = [(g.id, g.name) for g in models.Land.query.all()]

    if form.abort.data:
        return flask.redirect(flask.url_for('admin.groups'))

    if form.delete.data:
        db.session.delete(group)
        db.session.commit()
        flask.flash(f"Gruppe '{group.name}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for('admin.groups'))

    if form.submit.data:
        # validate post data
        if form.validate_on_submit():
            # update fields in model
            for field_id, field in form._fields.items():
                setattr(group, field_id, field.data)

            db.session.commit()
            flask.flash(f"Gruppe '{group.name}' wurde gespeichert.", "success")

            return flask.redirect(flask.url_for('admin.groups'))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in group.__dict__:
            field.data = group.__dict__[field_id]

    return flask.render_template('groups_edit.html', form=form, _id=_id)


@admin_bp.route('/events')
def events():
    _events = models.Event.query.all()

    return flask.render_template('events.html', events=_events)


@admin_bp.route('/events/edit/<_id>', methods=['GET', 'POST'])
def events_edit(_id):
    form = EventForm()

    # create new group if keyword is given
    if _id == "new":
        event = models.Event()
        db.session.add(event)
    else:
        event = models.Event.query.get(_id)
        if event is None:
            return flask.redirect(flask.url_for('admin.events_edit', _id="new"))

    form.group_id.choices = [(g.id, g.name) for g in models.Group.query.all()]

    if form.abort.data:
        return flask.redirect(flask.url_for('admin.events'))

    if form.delete.data:
        db.session.delete(event)
        db.session.commit()
        flask.flash(f"Aktion '{event.title}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for('admin.events'))

    if form.submit.data:
        # validate post data
        if form.validate_on_submit():
            # update fields in model
            for field_id, field in form._fields.items():
                setattr(event, field_id, field.data)

            db.session.commit()
            flask.flash(f"Aktion '{event.title}' erfolgreich gespeichert.", "success")

            return flask.redirect(flask.url_for('admin.events'))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in event.__dict__:
            field.data = event.__dict__[field_id]

    return flask.render_template('events_edit.html', form=form, _id=_id)
