import datetime
import flask
import secrets
from flask_login import login_required, current_user, login_user, logout_user
from flask_mail import Message
from flask import current_app, render_template

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    SelectField,
    BooleanField,
    Field,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
)


from . import login_manager, mail
from .models import (
    db,
    User,
    Group,
    Land,
)

# Blueprint Configuration
auth_bp = flask.Blueprint('auth', __name__, url_prefix='/auth', static_folder='static')
current_user: User


class ProfileForm(FlaskForm):
    id = StringField('E-Mail Adresse', validators=[
        Length(min=6),
        Email(message='Bitte gib eine valide E-Mail Adresse an.'),
        DataRequired(),
    ])
    name = StringField(
        'Name',
        description="Bitte Vor- und Nachname angeben, damit wir euch zuordnen können.",
        validators=[DataRequired()],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=8, message='Das Passwort muss mindestens 8 Zeichen haben.')],
    )
    confirm = PasswordField(
        'Password (wiederholen)',
        validators=[DataRequired(),
                    EqualTo('password', message='Die Passwörter stimmen nicht überein.')],
    )
    is_superuser = BooleanField(
        'Superuser',
        description="Superuser-Rechte erlauben es, auf alle Inhalte zuzugreifen.",
    )

    manage_group_id = SelectField(
        'Stammeskoodinator*in',
        coerce=int,
        description="Wähle einen Stamm aus, für die du Aktionen verwalten möchtest. Der Zugriff muss noch bestätigt werden.",
    )
    is_manager_group = BooleanField(
        'Freigabe Stamm',
        description="Stammeskoodinator-Rechte erlauben es, auf den Stamm zuzugreifen.",
    )
    manage_land_id = SelectField(
        'Landeskoodinator*in',
        coerce=int,
        description="Wähle ein Land aus, für das du die Rechte haben möchtest. Der Zugriff muss noch bestätigt werden.",
    )
    is_manager_land = BooleanField(
        'Freigabe Land',
        description="Landeskoodinator*in-Rechte erlauben es, auf das Land zuzugreifen.",
    )

    submit = SubmitField('Speichern')
    delete = SubmitField('Löschen')


class LoginForm(FlaskForm):
    id = StringField(
        'E-Mail Adresse',
        validators=[DataRequired(), Email(message='Bitte gib eine valide E-Mail Adresse an.')],
    )
    password = PasswordField(
        'Password', validators=[],
    )
    submit = SubmitField('Login')
    reset = SubmitField("Passwort vergessen?")


class PasswordResetForm(FlaskForm):
    id = StringField(
        'E-Mail Adresse',
        validators=[DataRequired(), Email(message='Bitte gib die E-Mail Adresse deines Accounts an.')],
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=8, message='Das Passwort muss mindestens 8 Zeichen haben.')]
    )
    confirm = PasswordField(
        'Password (wiederholen)',
        validators=[DataRequired(), EqualTo('password', message='Die Passwörter stimmen nicht überein.')],
    )
    submit = SubmitField('Passwort zurücksetzen')


def disable_field(field: Field, disabled=True):
    if not field.render_kw:
        field.render_kw = {}
    if disabled:
        field.render_kw.update({'disabled': ""})
    else:
        field.render_kw.pop('disabled', None)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    next_page = flask.request.args.get('next') or flask.url_for('public.index')

    # Bypass if user is logged in
    if current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", 'alert')
        return flask.redirect(next_page)

    form = LoginForm()

    # if reset password
    if form.reset.data and form.validate_on_submit():
        user = User.query.filter_by(id=form.id.data).first()
        if user:
            return flask.redirect(flask.url_for('auth.reset', username=form.id.data))

        flask.flash("Es existiert kein Benutzer mit dieser E-Mail Adresse.", 'alert')
        return flask.redirect(flask.url_for('auth.login'))

    # if submit: validate login attempt
    if form.submit.data and form.validate_on_submit():
        user = User.query.filter_by(id=form.id.data).first()
        if user and user.check_password(password=form.password.data):
            login_user(user)
            user.last_login = datetime.datetime.now()
            db.session.commit()

            flask.flash(f"Login erfolgreich. Willkommen, {current_user.name}!", 'success')
            return flask.redirect(next_page)

        flask.flash('Login fehlgeschlagen.', 'danger')
        return flask.redirect(flask.url_for('auth.login'))

    return flask.render_template(
        'generic_form.html',
        form=form,
        title='Login',
    )


@auth_bp.route('/reset/<username>', methods=['GET', 'POST'])
def reset(username):
    # Bypass if user is logged in
    if current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", 'alert')
        return flask.redirect(flask.url_for('public.index'))

    # Get user object and token
    user = User.query.filter_by(id=username).first()
    token = flask.request.args.get('token')

    # Validate reset attempt
    if not user:
        flask.flash('Benutzer nicht gefunden.', 'danger')
        return flask.redirect(flask.url_for('auth.login'))

    form = PasswordResetForm()
    form.id.data = username

    # if token exits and is valid: allow reset
    if token and user.verify_token(token):
        # if form is valid / posted
        if form.validate_on_submit():
            user.set_password(form.password.data)
            db.session.commit()
            flask.flash('Passwort erfolgreich geändert.', 'success')
            return flask.redirect(flask.url_for('auth.login'))

        # return passwort enter form
        return flask.render_template(
            'generic_form.html',
            form=form,
            title='Passwort zurücksetzen',
        )

    form._fields.pop("password")
    form._fields.pop("confirm")

    # Validate reset attempt
    if form.validate_on_submit():
        if user:
            user.set_token()
            db.session.commit()

            msg = Message(
                subject=f"[{current_app.config['APP_TITLE']}] Passwort zurücksetzen",
                sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                recipients=[user.id],
            )
            msg.body = render_template("mail/reset.txt", user=user)
            mail.send(msg)

            flask.flash('E-Mail zum Zurücksetzen des Passwortes wurde gesendet.', 'success')
            return flask.redirect(flask.url_for('auth.reset', username=username))

        flask.flash('Passwort konnte nicht zurückgesetzt werden.', 'danger')
        return flask.redirect(flask.url_for('auth.reset', username=username))

    return flask.render_template(
        'generic_form.html',
        form=form,
        title='Passwort zurücksetzen',
    )


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flask.flash("Logout erfolgreich.", 'success')
    return flask.redirect(flask.url_for('auth.login'))


@auth_bp.route('/user/<_id>', methods=['GET', 'POST'])
def user(_id):
    form = ProfileForm()

    if not current_user and _id != "new":
        flask.flash("Du bist nicht eingeloggt.", 'alert')
        return flask.redirect(flask.url_for('auth.login'))

    # create new profile if keyword is given
    if _id == "new":
        user = User()

        form._fields.pop("is_manager_group")
        form._fields.pop("is_manager_land")
        form._fields.pop("is_superuser")
        form.submit.label.text = "Registrieren"
    else:
        if not isinstance(current_user, User):
            flask.flash("Du bist nicht eingeloggt.", 'alert')
            return flask.redirect(flask.url_for('auth.login'))

        user = User.query.filter_by(id=_id).first()

        # disable editing the email adress
        form._fields.pop("id")

        # adjust password rules to accept empty passwords for existing users
        form.password.flags = None
        form.password.validators = [Optional(), Length(min=8, message='Das Passwort muss mindestens 8 Zeichen haben.')]

        form.confirm.flags = None
        form.confirm.validators = [EqualTo('password', message='Die Passwörter stimmen nicht überein.')]

        if user not in current_user.query_users():
            flask.flash(f"Du hast keine Berechtigung, diesen Account zu bearbeiten. {current_user.query_users()}", 'alert')
            return flask.redirect(flask.url_for('admin.accounts'))

    form.manage_group_id.choices = [(0, "")] + [(g.id, g.display_name) for g in Group.query.all()]
    form.manage_land_id.choices = [(0, "")] + [(l.id, l.name) for l in Land.query.all()]

    # POST: delete user
    if form.delete.data:
        db.session.delete(user)
        db.session.commit()
        flask.flash(f"Account '{user.id}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for("public.index"))

    # POST: save user
    if form.submit.data:
        if form.validate_on_submit():
            form.manage_group_id.data = form.manage_group_id.data if form.manage_group_id.data else None
            form.manage_land_id.data = form.manage_land_id.data if form.manage_land_id.data else None

            user.name = form.name.data
            if form.password.data:
                user.set_password(form.password.data)

            # if the current user is logged in, check permissions
            if current_user.is_authenticated:
                permissions_altered = False

                # superuser privilege can only be altered by other superusers
                if form.is_superuser.data != user.is_superuser:
                    if current_user == user:
                        flask.flash("Du kannst deine eigenen Rechte nur bearbeiten, wenn du weitergehende Rechte hast.", 'warning')
                    elif current_user.is_superuser:
                        permissions_altered = True
                        user.is_superuser = form.is_superuser.data
                    else:
                        flask.flash("Du hast keine Berechtigung, dem Account Superuser-Rechte zu erteilen oder zu entziehen.", 'warning')

                # land manager privilege can be altered by superusers
                if form.is_manager_land.data != user.is_manager_land:
                    if current_user.is_superuser:
                        flask.flash("Landeskoodinator*in-Rechte mit Hilfe der Superuser-Rechte bearbeitet.")
                        permissions_altered = True
                        user.is_manager_land = form.is_manager_land.data
                    elif current_user == user:
                        flask.flash("Du kannst deine eigenen Rechte nur bearbeiten, wenn du weitergehende Rechte hast.", 'warning')
                    elif current_user.is_manager_land and current_user.manage_land == user.manage_land:
                        flask.flash("Landeskoodinator*in-Rechte mit Hilfe der Landeskoodinator*in-Rechte bearbeitet.")
                        permissions_altered = True
                        user.is_manager_land = form.is_manager_land.data
                    else:
                        flask.flash(f"Du hast keine Berechtigung, Rechte für das Land {user.manage_land.name} zu vergeben.", 'warning')

                # updated managed land
                if form.manage_land_id.data != user.manage_land_id:
                    user.manage_land_id = form.manage_land_id.data
                    permissions_altered = True

                    # reset permission if land changed
                    if current_user.is_superuser:
                        pass
                    elif not user.is_manager_land:
                        pass
                    else:
                        flask.flash("Durch die Änderung des Landes wurde die Freigabe entzogen.", 'warning')
                        user.is_manager_land = False

                # group manager privilege can be altered by superusers or land managers
                if form.is_manager_group.data != user.is_manager_group:
                    # Allow if current user has permission for the same group
                    # Allow if current user has permission for the groups land

                    # Allow for superusers
                    if current_user.is_superuser:
                        flask.flash("Stammeskoodinator*in-Rechte mit Hilfe der Superuser-Rechte bearbeitet.")
                        permissions_altered = True
                        user.is_manager_group = form.is_manager_group.data
                    elif current_user.is_manager_land and current_user.manage_land == user.manage_group.land:
                        flask.flash("Stammeskoodinator*in-Rechte mit Hilfe der Landeskoodinator*in-Rechte bearbeitet.")
                        permissions_altered = True
                        user.is_manager_group = form.is_manager_group.data
                    elif current_user == user:
                        flask.flash("Du kannst deine eigenen Rechte nur bearbeiten, wenn du weitergehende Rechte hast.", 'warning')
                    elif current_user.is_manager_group and current_user.manage_group == user.manage_group:
                        flask.flash("Stammeskoodinator*in-Rechte mit Hilfe der Stammeskoodinator*in-Rechte bearbeitet.")
                        permissions_altered = True
                        user.is_manager_group = form.is_manager_group.data
                    else:
                        flask.flash(f"Du hast keine Berechtigung, Rechte für die Gruppe {user.manage_group.name} zu vergeben.", 'warning')

                # updated managed group
                if form.manage_group_id.data != user.manage_group_id:
                    permissions_altered = True
                    user.manage_group_id = form.manage_group_id.data

                    # remove permission, if group changed
                    if current_user.is_superuser:
                        pass
                    elif current_user.is_manager_land and current_user.manage_land == user.manage_land:
                        pass
                    elif not user.is_manager_group:
                        pass
                    else:
                        flask.flash("Durch die Änderung der Gruppe wurde die Freigabe entzogen.", 'warning')
                        user.is_manager_group = False

                if permissions_altered:
                    msg = Message(
                        subject=f"[{current_app.config['APP_TITLE']}] Rechte angepasst",
                        sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                        recipients=[user.id],
                        cc=[u.id for u in user.query_managers()],
                        bcc=[u.id for u in User.query.filter(User.is_superuser)],
                    )
                    msg.body = render_template("mail/permissions_altered.txt", user=user)
                    mail.send(msg)

            # create new user
            if _id == "new":
                if User.query.get(form.id.data):
                    flask.flash(f"Der Account {form.id.data} existiert bereits.", 'warning')
                    return flask.redirect(flask.url_for('auth.user', _id="new"))

                if User.query.count() == 0:
                    user.is_superuser = True

                user.id = form.id.data
                user.manage_group_id = form.manage_group_id.data
                user.manage_land_id = form.manage_land_id.data

                db.session.add(user)
                db.session.commit()

                msg = Message(
                    subject=f"[{current_app.config['APP_TITLE']}] Neuer Account",
                    sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                    recipients=[user.id],
                    cc=[u.id for u in user.query_managers()],
                    bcc=[u.id for u in User.query.filter(User.is_superuser)],
                )
                msg.body = render_template("mail/hello.txt", user=user)
                mail.send(msg)

                flask.flash(f"Account {user.id} wurde angelegt.", "success")
                return flask.redirect(flask.url_for('auth.login', _id=user.id))

            # save account
            db.session.commit()
            flask.flash(f"Account {user.id} wurde gespeichert.", "success")
            return flask.redirect(flask.url_for('auth.user', _id=user.id))

    # initialize form values
    for field_id, field in dict(form._fields).items():
        # set data from existing user
        if field_id in user.__dict__:
            field.data = user.__dict__[field_id]

    _title = f"Account {user.id} bearbeiten" if _id != "new" else "Account anlegen"

    return flask.render_template('generic_form.html', form=form, _id=_id, title=_title)


@auth_bp.route('/users')
@login_required
def users():
    return flask.render_template("auth/users.html")


@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    flask.flash('Du musst angemeldet sein, um diese Seite aufrufen zu können.', 'info')
    return flask.redirect(flask.url_for('auth.login'))
