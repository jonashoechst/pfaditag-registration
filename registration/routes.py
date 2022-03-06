from datetime import date
import flask
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, TelField, SelectField, DateField, TimeField
from wtforms.validators import DataRequired


import registration


class LandForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])


class GroupForm(FlaskForm):
    name = StringField('Stammesname', validators=[DataRequired()])
    street = StringField('Straße, Nr.', validators=[DataRequired()])
    zip = StringField('PLZ', validators=[DataRequired()])
    city = StringField('Ort', validators=[DataRequired()])
    website = StringField('Website')
    land_id = SelectField('VCP Land', coerce=int)


class EventForm(FlaskForm):
    title = StringField('Aktionstitel', validators=[DataRequired()])
    email = EmailField('E-Mail Adresse')
    tel = TelField('Telefonnummer')

    date = DateField('Aktionstag')
    time = TimeField('Startzeit')
    description = TextAreaField('Beschreibung')
    group_id = SelectField('Gruppe', coerce=int)


@registration.app.route('/')
@registration.app.route('/index')
def index():
    return flask.render_template('index.html', title='PfadiTag 2022')


@registration.app.route('/admin/groups')
def groups():
    _groups = registration.models.Group.query.all()

    return flask.render_template('groups.html', groups=_groups)


@registration.app.route('/admin/groups/edit/<_id>', methods=['GET', 'POST'])
def groups_edit(_id):
    form = GroupForm()

    # create new group if keyword is given
    if _id == "new":
        model = registration.models.Group()
        registration.db.session.add(model)
    else:
        model = registration.models.Group.query.get(_id)
        if model is None:
            return flask.redirect(flask.url_for('groups_edit', _id="new"))

    form.land_id.choices = [(g.id, g.name) for g in registration.models.Land.query.all()]

    # validate post data
    if form.validate_on_submit():
        # update fields in model
        for field_id, field in form._fields.items():
            setattr(model, field_id, field.data)

        registration.db.session.commit()
        flask.flash(f"Gruppe {model.name} wurde gespeichert.")

        return flask.redirect(flask.url_for('groups'))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in model.__dict__:
            field.data = model.__dict__[field_id]

    return flask.render_template('groups_edit.html', form=form, _id=_id)


@registration.app.route('/admin/events')
def events():
    _events = registration.models.Event.query.all()

    return flask.render_template('events.html', events=_events)


@registration.app.route('/admin/events/edit/<_id>', methods=['GET', 'POST'])
def events_edit(_id):
    form = EventForm()

    # create new group if keyword is given
    if _id == "new":
        event = registration.models.Event()
        registration.db.session.add(event)
    else:
        event = registration.models.Event.query.get(_id)
        if event is None:
            return flask.redirect(flask.url_for('events_edit', _id="new"))

    form.group_id.choices = [(g.id, g.name) for g in registration.models.Group.query.all()]

    # validate post data
    if form.validate_on_submit():
        # update fields in model
        for field_id, field in form._fields.items():
            setattr(event, field_id, field.data)

        registration.db.session.commit()
        flask.flash(f"Aktion {event.title} wurde gespeichert.")

        return flask.redirect(flask.url_for('events'))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in event.__dict__:
            field.data = event.__dict__[field_id]

    return flask.render_template('events_edit.html', form=form, _id=_id)
