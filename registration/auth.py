import datetime
import json
import flask
from flask_login import login_required, current_user, login_user, logout_user
from flask_mail import Message
from flask import current_app, render_template

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    BooleanField,
    Field,
    HiddenField,
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
    UserPermission,
    Group,
)

# Blueprint Configuration
auth_bp = flask.Blueprint("auth", __name__, url_prefix="/auth", static_folder="static")
current_user: User


class ProfileForm(FlaskForm):
    id = StringField(
        "E-Mail Adresse",
        validators=[
            Length(min=6, max=100),
            Email(message="Bitte gib eine valide E-Mail Adresse an.", allow_smtputf8=False),
            DataRequired(),
        ],
    )
    name = StringField(
        "Name",
        description="Bitte Vor- und Nachname angeben, damit wir dich zuordnen können.",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=200, message="Das Passwort muss zwischen 8 und 200 Zeichen haben."),
        ],
    )
    confirm = PasswordField(
        "Password (wiederholen)",
        validators=[DataRequired(), EqualTo("password", message="Die Passwörter stimmen nicht überein.")],
    )
    is_superuser = BooleanField(
        "Superuser",
        description="Superuser-Rechte erlauben es, auf alle Inhalte zuzugreifen.",
    )

    submit = SubmitField("Speichern")
    delete = SubmitField("Löschen")


def disable_field(field: Field, disabled=True):
    if not field.render_kw:
        field.render_kw = {}
    if disabled:
        field.render_kw.update({"disabled": ""})
    else:
        field.render_kw.pop("disabled", None)


class LoginForm(FlaskForm):
    id = ProfileForm.id
    password = ProfileForm.password
    submit = SubmitField("Login")
    reset = SubmitField("Passwort vergessen?")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_page = flask.request.args.get("next") or flask.url_for("public.index")

    # Bypass if user is logged in
    if current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", "alert")
        return flask.redirect(next_page)

    form = LoginForm()

    # if reset password
    if form.reset.data and form.validate_on_submit():
        _user = User.query.filter_by(id=form.id.data).first()
        if _user:
            return flask.redirect(flask.url_for("auth.reset", username=form.id.data))

        flask.flash("Es existiert keine Nutzer*in mit dieser E-Mail Adresse.", "alert")
        return flask.redirect(flask.url_for("auth.login"))

    # if submit: validate login attempt
    if form.submit.data and form.validate_on_submit():
        _user = User.query.filter_by(id=form.id.data).first()
        if _user and _user.check_password(password=form.password.data):
            login_user(_user)
            _user.last_login = datetime.datetime.now()
            db.session.commit()

            flask.flash(f"Login erfolgreich. Willkommen, {current_user.name}!", "success")
            return flask.redirect(next_page)

        flask.flash("Login fehlgeschlagen.", "danger")
        return flask.redirect(flask.url_for("auth.login"))

    return flask.render_template(
        "generic_form.j2",
        form=form,
        title="Login",
    )


class PasswordResetForm(FlaskForm):
    id = ProfileForm.id
    password = ProfileForm.password
    confirm = ProfileForm.confirm
    submit = SubmitField("Passwort zurücksetzen")


@auth_bp.route("/reset/<username>", methods=["GET", "POST"])
def reset(username):
    # Bypass if user is logged in
    if current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", "alert")
        return flask.redirect(flask.url_for("public.index"))

    # Get user object and token
    _user = User.query.filter_by(id=username).first()
    token = flask.request.args.get("token")

    # Validate reset attempt
    if not _user:
        flask.flash("Nutzer*in nicht gefunden.", "danger")
        return flask.redirect(flask.url_for("auth.login"))

    form = PasswordResetForm()
    form.id.data = username

    # if token exits and is valid: allow reset
    if token and _user.verify_token(token):
        # if form is valid / posted
        if form.validate_on_submit():
            _user.set_password(form.password.data)
            db.session.commit()
            flask.flash("Passwort erfolgreich geändert.", "success")
            return flask.redirect(flask.url_for("auth.login"))

        # return passwort enter form
        return flask.render_template(
            "generic_form.j2",
            form=form,
            title="Passwort zurücksetzen",
        )

    form._fields.pop("password")
    form._fields.pop("confirm")

    # Validate reset attempt
    if form.validate_on_submit():
        if _user:
            _user.set_token()
            db.session.commit()

            msg = Message(
                subject=f"[{current_app.config['APP_TITLE']}] Passwort zurücksetzen",
                sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                recipients=[_user.id],
            )
            msg.body = render_template("mail/reset.txt", user=_user)
            mail.send(msg)

            flask.flash("E-Mail zum Zurücksetzen des Passwortes wurde gesendet.", "success")
            return flask.redirect(flask.url_for("auth.reset", username=username))

        flask.flash("Passwort konnte nicht zurückgesetzt werden.", "danger")
        return flask.redirect(flask.url_for("auth.reset", username=username))

    return flask.render_template(
        "generic_form.j2",
        form=form,
        title="Passwort zurücksetzen",
    )


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flask.flash("Logout erfolgreich.", "success")
    return flask.redirect(flask.url_for("auth.login"))


@auth_bp.route("/user/edit/<user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    form = ProfileForm()

    if not isinstance(current_user, User):
        flask.flash("Du bist nicht eingeloggt.", "alert")
        return flask.redirect(flask.url_for("auth.login"))

    _user = User.query.filter_by(id=user_id).first()

    # disable editing the email adress
    form._fields.pop("id")

    # adjust password rules to accept empty passwords for existing users
    form.password.flags = None
    form.password.validators = [Optional(), Length(min=8, message="Das Passwort muss mindestens 8 Zeichen haben.")]

    form.confirm.flags = None
    form.confirm.validators = [EqualTo("password", message="Die Passwörter stimmen nicht überein.")]

    if _user.id == current_user.id:
        pass
    elif current_user.is_superuser:
        pass
    else:
        flask.flash("Du hast keine Berechtigung, diesen Account zu bearbeiten.", "alert")
        return flask.redirect(flask.url_for("auth.users"))

    # POST: delete user
    if form.delete.data:
        db.session.delete(_user)
        db.session.commit()
        flask.flash(f"Account '{_user.id}' erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for("public.index"))

    # POST: save user
    if form.submit.data:
        if form.validate_on_submit():
            _user.name = form.name.data
            if form.password.data:
                _user.set_password(form.password.data)

            # if the current user is logged in, check permissions
            if current_user.is_authenticated:
                # superuser privilege can only be altered by other superusers
                if form.is_superuser.data != _user.is_superuser:
                    if current_user == _user:
                        flask.flash("Du kannst deine eigenen Rechte nicht bearbeiten.", "warning")
                    elif current_user.is_superuser:
                        _user.is_superuser = form.is_superuser.data
                    else:
                        flask.flash(
                            "Du hast keine Berechtigung, dem Account Superuser-Rechte zu erteilen oder zu entziehen.",
                            "warning",
                        )

            # save account
            db.session.commit()
            flask.flash(f"Account {_user.id} wurde gespeichert.", "success")
            return flask.redirect(flask.url_for("auth.edit_user", user_id=_user.id))

    # initialize form values
    for field_id, field in dict(form._fields).items():
        # set data from existing user
        if field_id in _user.__dict__:
            field.data = _user.__dict__[field_id]

    return flask.render_template("auth/edit_user.j2", form=form, user=_user, permissions=_user.permissions)


class RegisterForm(FlaskForm):
    id = ProfileForm.id
    name = ProfileForm.name
    password = ProfileForm.password
    confirm = ProfileForm.confirm
    group_id = HiddenField(
        "Gliederung", description="Wahle eine Gruppe aus, für die du eine Berechtigung beantragen möchtest."
    )

    submit = SubmitField("Registrieren")


@auth_bp.route("/user/new", methods=["GET", "POST"])
def new_user():
    if isinstance(current_user, User) and current_user.is_authenticated:
        flask.flash("Du bist bereits eingeloggt.", "alert")
        return flask.redirect(flask.url_for("auth.edit_user", user_id=current_user.id))

    form = RegisterForm()

    # POST: save user
    if form.submit.data:
        if form.validate_on_submit():
            if User.query.get(form.id.data):
                flask.flash(f"Der Account {form.id.data} existiert bereits.", "warning")
                return flask.redirect(flask.url_for("auth.new_user"))

            # create new user
            _user = User()
            _user.id = form.id.data
            _user.name = form.name.data
            if form.password.data:
                _user.set_password(form.password.data)

            # create initial user as superuser
            if User.query.count() == 0:
                _user.is_superuser = True
            db.session.add(_user)

            # create initial group permission
            perm: UserPermission
            if form.group_id.data:
                perm = UserPermission()
                perm.user_id = _user.id
                perm.group_id = form.group_id.data
                perm.granted = False
                db.session.add(perm)

            db.session.commit()

            # send hello message
            msg = Message(
                subject=f"[{current_app.config['APP_TITLE']}] Neuer Account",
                sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                recipients=[_user.id],
                bcc=[u.id for u in User.query.filter(User.is_superuser)],
            )
            msg.body = render_template("mail/hello.txt", user=_user)
            mail.send(msg)

            # send permission request request
            if perm:
                perm_msg = Message(
                    subject=f"[{current_app.config['APP_TITLE']}] Berechtigung freigeben",
                    sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                    recipients=[u.id for u in perm.query_grantable_users()],
                )
                perm_msg.body = render_template("mail/perm_request.txt", perm=perm)
                mail.send(perm_msg)

            flask.flash(f"Account {_user.id} wurde angelegt.", "success")
            return flask.redirect(flask.url_for("auth.login", _id=_user.id))

    roots = db.session.query(Group).filter(None == Group.parent_id).all()
    tree_data = [group_tree(group) for group in roots]

    return flask.render_template("auth/new_user.j2", form=form, tree_data=json.dumps(tree_data))


@auth_bp.route("/users")
@login_required
def users():
    if not current_user.is_superuser:
        flask.flash("Nur Superuser können die Nutzerübersicht aufrufen.", "info")
        return flask.redirect(flask.url_for("auth.edit_user", user_id=current_user.id))

    _users = User.query.all()
    return flask.render_template("auth/users.j2", users=_users, title="Übersicht Accounts")


@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    flask.flash("Du musst angemeldet sein, um diese Seite aufrufen zu können.", "info")
    return flask.redirect(flask.url_for("auth.login"))


class PermissionForm(FlaskForm):
    user_id = StringField(
        "Nutzer*in",
        description="E-Mail Adresse der Nutzer*in.",
    )
    group_id = HiddenField(
        "Gliederung",
    )
    granted = BooleanField(
        "Bestätigt",
        description="Die Berechtigung muss bestätigt werden.",
    )

    submit = SubmitField("Speichern")
    delete = SubmitField("Löschen")


def group_tree(group: Group) -> dict:
    return dict(
        id=group.id,
        text=group.display_name,
        children=[group_tree(sgroup) for sgroup in group.children],
    )


@auth_bp.route("/auth/permission/<permission_id>", methods=["GET", "POST"])
@login_required
def edit_permission(permission_id: str):
    form = PermissionForm()

    # create new profile if keyword is given
    if permission_id == "new":
        _perm = UserPermission()
        user_id = flask.request.args.get("user_id")
        if user_id:
            form.user_id.data = user_id
        group_id = flask.request.args.get("group_id")
        if group_id:
            form.group_id.data = group_id
        form.submit.label.text = "Erstellen"
    else:
        _perm = UserPermission.query.filter_by(id=int(permission_id)).first()
        if not _perm:
            flask.flash("Berechtigung existiert nicht.", "warning")
            return flask.redirect(flask.url_for("public.index"))

        # disable editing group
        form.group_id.render_kw = {"disabled": True}
        form.user_id.render_kw = {"disabled": True}

    # POST: delete permission
    if form.delete.data:
        db.session.delete(_perm)
        db.session.commit()
        flask.flash("Berechtigung erfolgreich gelöscht.", "success")
        return flask.redirect(flask.url_for("auth.edit_user", user_id=_perm.user_id))

    # POST: save permission
    if form.submit.data:
        if form.validate_on_submit():
            if permission_id == "new":
                _perm.user_id = form.user_id.data
                _perm.group_id = form.group_id.data

            # if permissions should be altered, check user permissions
            if _perm.granted != form.granted.data:
                if current_user.has_group_permission(_perm.group_id):
                    _perm.granted = form.granted.data
                else:
                    flask.flash("Du hast keine Berechtigung, diese Berechtigung zu bearbeiten.", "warning")
                    return flask.redirect(flask.url_for("auth.edit_user", user_id=_perm.user_id))

                if _perm.granted and permission_id != "new":
                    perm_msg = Message(
                        subject=f"[{current_app.config['APP_TITLE']}] Berechtigung erteilt",
                        sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                        recipients=[_perm.user_id],
                    )
                    perm_msg.body = render_template("mail/perm_granted.txt", perm=_perm)
                    mail.send(perm_msg)

            # create new permission
            if permission_id == "new":
                db.session.add(_perm)
                db.session.commit()

                grantable_users = [u.id for u in _perm.query_grantable_users()]
                # send to superusers if not grantables exist
                bcc = [] if grantable_users else [u.id for u in User.query.filter(User.is_superuser)]

                if not _perm.granted:
                    perm_msg = Message(
                        subject=f"[{current_app.config['APP_TITLE']}] Berechtigung angefragt",
                        sender=f"{current_app.config['APP_TITLE']} <{current_app.config['MAIL_USERNAME']}>",
                        recipients=grantable_users,
                        bcc=bcc,
                    )
                    perm_msg.body = render_template("mail/perm_request.txt", perm=_perm)
                    mail.send(perm_msg)

                flask.flash("Berechtigung wurde angelegt.", "success")
                return flask.redirect(flask.url_for("auth.edit_user", user_id=_perm.user_id))

            # save account
            db.session.commit()
            flask.flash("Berechtigung wurde gespeichert.", "success")
            return flask.redirect(flask.url_for("auth.edit_user", user_id=_perm.user_id))

    # initialize form values
    for field_id, field in dict(form._fields).items():
        # set data from existing user
        if field_id in _perm.__dict__:
            field.data = _perm.__dict__[field_id]

    _title = "Berechtigung bearbeiten" if permission_id != "new" else "Berechtigung anlegen"

    roots = db.session.query(Group).filter(None == Group.parent_id).all()
    tree_data = [group_tree(group) for group in roots]

    return flask.render_template("auth/edit_permission.j2", form=form, title=_title, tree_data=json.dumps(tree_data))
