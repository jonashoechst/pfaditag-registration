import flask
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, TelField, SelectField
from wtforms.validators import DataRequired

import registration
from pprint import pprint


class LocalEvent(FlaskForm):
    title = StringField('title', validators=[DataRequired()])
    email = EmailField('email')  # , validators=[DataRequired()])
    tel = TelField('tel')
    description = TextAreaField('description')  # , validators=[DataRequired()])


class group(FlaskForm):
    _label = "Gruppe"

    name = StringField('Stammesname', validators=[DataRequired()])
    street = StringField('Straße, Nr.', validators=[DataRequired()])
    zip = StringField('PLZ', validators=[DataRequired()])
    city = StringField('Ort', validators=[DataRequired()])
    website = StringField('Website')
    land = SelectField('VCP Land', coerce=int)


class land(FlaskForm):
    _label = "VCP Land"

    name = StringField('Name', validators=[DataRequired()])


@registration.app.route('/')
@registration.app.route('/index')
def index():
    return flask.render_template('index.html', title='PfadiTag 2022')


@registration.app.route('/admin/<model_name>', methods=['GET', 'POST'])
def list(model_name):
    form = globals()[model_name]()
    Model = getattr(registration.models, model_name)
    data = Model.query.all()

    return flask.render_template('list.html', form=form, data=data)


@registration.app.route('/admin/<model_name>/edit/<_id>', methods=['GET', 'POST'])
def edit(model_name, _id):
    form = globals()[model_name]()
    Model = getattr(registration.models, model_name)

    # create new group if keyword is given
    if _id == "new":
        model = Model()
        registration.db.session.add(model)
    else:
        model = Model.query.get(_id)
        if model is None:
            return flask.redirect(flask.url_for('edit', model_name=model_name, _id="new"))

    # initialize choices for select fields
    for field_id, field in form._fields.items():
        if isinstance(field, SelectField):
            key = [key for key in Model.__table__.foreign_keys if key.parent.key.startswith(field_id)][0]
            SelectModel = getattr(registration.models, key.column.table.name)
            field.choices = [(str(x.id), x.name) for x in SelectModel.query.all()]

    # validate post data
    if form.validate_on_submit():
        # update fields in model
        for field_id, field in form._fields.items():
            # if field_id in model.__dict__:
            setattr(model, field_id, field.data)

        registration.db.session.commit()
        flask.flash(f"{form._label} wurde gespeichert.")

        return flask.redirect(flask.url_for('edit', model_name=model_name, _id=model.id))

    # initialize form values
    for field_id, field in form._fields.items():
        if field_id in model.__dict__:
            field.data = model.__dict__[field_id]

    return flask.render_template('edit.html', form=form)
