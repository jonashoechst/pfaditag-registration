import datetime
import flask
import flask_login

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    SelectField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
)


from . import login_manager
from .models import (
    db,
    User,
    Group,
    Land,
)

# Blueprint Configuration
auth_bp = flask.Blueprint('auth', __name__, static_folder='static')


class SignupForm(FlaskForm):
    email = StringField('E-Mail Adresse', validators=[
        Length(min=6),
        Email(message='Bitte gib eine valide E-Mail Adresse an.'),
        DataRequired(),
    ])
    name = StringField('Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8, message='Das Passwort muss mindestens 8 Zeichen haben.')])
    confirm = PasswordField('Password (wiederholen)', validators=[DataRequired(), EqualTo('password', message='Die Passwörter stimmen nicht überein.')])

    group_id = SelectField('Manager für Stamm', coerce=int, description="Wähle einen Stamm aus, für die du Aktionen verwalten möchtest. Der Zugriff muss noch bestätigt werden.")
    land_id = SelectField('Länderkoodinator:in', coerce=int, description="Wähle ein Land aus, für das du die Koodinator-Rechte haben möchtest. Der Zugriff muss noch bestätigt werden.")

    submit = SubmitField('Registrieren')


class LoginForm(FlaskForm):
    email = StringField('E-Mail Adresse', validators=[DataRequired(), Email(message='Bitte gib eine valide E-Mail Adresse an.')])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_page = flask.request.args.get('next') or flask.url_for('public.index')

    # Bypass if user is logged in
    if flask_login.current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", 'alert')
        return flask.redirect(next_page)

    form = LoginForm()
    # Validate login attempt
    if form.validate_on_submit():
        user = User.query.filter_by(id=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            flask_login.login_user(user)
            user.last_login = datetime.datetime.now()
            db.session.commit()

            flask.flash(f"Login erfolgreich. Willkommen, {flask_login.current_user.name}!", 'success')
            return flask.redirect(next_page)

        flask.flash('E-Mail Adresse / Passwort Kombination stimmt nicht überein.', 'danger')
        return flask.redirect(flask.url_for('auth.login'))

    return flask.render_template(
        'generic_form.html',
        form=form,
        title='Login',
    )


@ auth_bp.route("/logout")
def logout():
    flask_login.logout_user()
    flask.flash("Logout erfolgreich.", 'success')
    return flask.redirect(flask.url_for('auth.login'))


@ auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()

    form.group_id.choices = [(0, "")] + [(g.id, g.name) for g in Group.query.all()]
    form.land_id.choices = [(0, "")] + [(l.id, l.name) for l in Land.query.all()]

    if form.validate_on_submit():
        existing_user = User.query.filter_by(id=form.email.data).first()
        if existing_user is None:
            user = User(
                id=form.email.data,
                name=form.name.data,
            )
            user.set_password(form.password.data)
            user.last_login = datetime.datetime.now()
            user.created_on = datetime.datetime.now()
            db.session.add(user)
            db.session.commit()

            flask_login.login_user(user)
            return flask.redirect(flask.url_for('auth.login'))

        flask.flash('Es existiert bereits ein:e Nutzer:in mit dieser E-Mail Adresse.', 'error')

    return flask.render_template(
        'generic_form.html',
        title='Neuen Account erstellen',
        form=form,
    )


@ login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@ login_manager.unauthorized_handler
def unauthorized():
    flask.flash('Du musst angemeldet sein, um diese Seite aufrufen zu können.', 'info')
    return flask.redirect(flask.url_for('auth.login'))
