import datetime
import json

import flask
from flask import current_app, render_template
from flask_login import current_user, login_required, login_user, logout_user
from flask_mail import Message
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    Field,
    HiddenField,
    PasswordField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
)

from . import login_manager, mail
from .models import (
    Group,
    User,
    UserPermission,
    db,
)

# Blueprint Configuration
auth_bp = flask.Blueprint("auth", __name__, url_prefix="/auth", static_folder="static")


class ProfileForm(FlaskForm):
    id = StringField(
        "E-Mail Adresse",
        validators=[
            Length(min=6, max=100),
            Email(message="Bitte gib eine valide E-Mail Adresse an.", allow_smtputf8=False),
            DataRequired(),
        ],
        render_kw={"autocomplete": "email"},
    )
    name = StringField(
        "Name",
        description="Bitte Vor- und Nachname angeben, damit wir dich zuordnen können.",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
        render_kw={"autocomplete": "name"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=200, message="Das Passwort muss zwischen 8 und 200 Zeichen haben."),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    confirm = PasswordField(
        "Password (wiederholen)",
        validators=[DataRequired(), EqualTo("password", message="Die Passwörter stimmen nicht überein.")],
        render_kw={"autocomplete": "new-password"},
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
    id = StringField(
        "E-Mail Adresse",
        validators=[
            Length(min=6, max=100),
            Email(message="Bitte gib eine valide E-Mail Adresse an.", allow_smtputf8=False),
            DataRequired(),
        ],
        render_kw={"autocomplete": "email"},
    )
    password = PasswordField(
        "Password",
        render_kw={"autocomplete": "current-password"},
    )
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

    # Pre-fill email if provided (e.g., after password reset)
    prefill_email = flask.request.args.get("prefill_email")
    if prefill_email and not form.id.data:
        form.id.data = prefill_email

    # if reset password
    if form.reset.data and form.validate_on_submit():
        _user = User.query.filter_by(id=form.id.data).first()
        if _user:
            # Generate token and send reset email immediately
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
            return flask.redirect(flask.url_for("auth.login"))

        flask.flash("Es existiert keine Nutzer*in mit dieser E-Mail Adresse.", "alert")
        return flask.redirect(flask.url_for("auth.login"))

    # if submit: validate login attempt
    if form.submit.data and form.validate_on_submit():
        _user = User.query.filter_by(id=form.id.data).first()
        if _user and _user.check_password(password=form.password.data):
            login_user(_user, remember=True)
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
    id = StringField(
        "E-Mail Adresse",
        validators=[
            Length(min=6, max=100),
            Email(message="Bitte gib eine valide E-Mail Adresse an.", allow_smtputf8=False),
            DataRequired(),
        ],
        render_kw={"autocomplete": "email"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=200, message="Das Passwort muss zwischen 8 und 200 Zeichen haben."),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    confirm = PasswordField(
        "Password (wiederholen)",
        validators=[DataRequired(), EqualTo("password", message="Die Passwörter stimmen nicht überein.")],
        render_kw={"autocomplete": "new-password"},
    )
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

    # Token is required - if not present or invalid, redirect to login
    if not token or not _user.verify_token(token):
        flask.flash("Ungültiger oder abgelaufener Reset-Link. Bitte fordere einen neuen an.", "warning")
        return flask.redirect(flask.url_for("auth.login"))

    # Token is valid - allow password reset
    if form.validate_on_submit():
        _user.set_password(form.password.data)
        db.session.commit()
        flask.flash("Passwort erfolgreich geändert. Du kannst dich jetzt mit deinem neuen Passwort anmelden.", "success")
        return flask.redirect(flask.url_for("auth.login", prefill_email=username))

    # Show password reset form
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

    _user: User | None = db.session.get(User, user_id)

    if not _user:
        flask.flash("Du hast keine Berechtigung, diesen Account zu bearbeiten.", "alert")
        return flask.redirect(flask.url_for("auth.users"))
    if _user.id == current_user.id:
        pass
    elif current_user.is_superuser:
        pass
    else:
        flask.flash("Du hast keine Berechtigung, diesen Account zu bearbeiten.", "alert")
        return flask.redirect(flask.url_for("auth.users"))

    # disable editing the email adress
    form._fields.pop("id")

    # adjust password rules to accept empty passwords for existing users
    form.password.flags = None
    form.password.validators = [Optional(), Length(min=8, message="Das Passwort muss mindestens 8 Zeichen haben.")]

    form.confirm.flags = None
    form.confirm.validators = [EqualTo("password", message="Die Passwörter stimmen nicht überein.")]

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
    id = StringField(
        "E-Mail Adresse",
        validators=[
            Length(min=6, max=100),
            Email(message="Bitte gib eine valide E-Mail Adresse an.", allow_smtputf8=False),
            DataRequired(),
        ],
        render_kw={"autocomplete": "email"},
    )
    name = StringField(
        "Name",
        description="Bitte Vor- und Nachname angeben, damit wir dich zuordnen können.",
        validators=[
            DataRequired(),
            Length(max=100),
        ],
        render_kw={"autocomplete": "name"},
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=200, message="Das Passwort muss zwischen 8 und 200 Zeichen haben."),
        ],
        render_kw={"autocomplete": "new-password"},
    )
    confirm = PasswordField(
        "Password (wiederholen)",
        validators=[DataRequired(), EqualTo("password", message="Die Passwörter stimmen nicht überein.")],
        render_kw={"autocomplete": "new-password"},
    )
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
            perm: UserPermission | None = None
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

    return flask.render_template("auth/new_user.j2", form=form, tree_data=get_group_tree_json())


@auth_bp.route("/users")
@login_required
def users():
    if not current_user.is_superuser:
        flask.flash("Nur Superuser können die Nutzerübersicht aufrufen.", "info")
        return flask.redirect(flask.url_for("auth.edit_user", user_id=current_user.id))

    _users = User.query.all()
    return flask.render_template("auth/users.j2", users=_users)


@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    flask.flash("Du musst angemeldet sein, um diese Seite aufrufen zu können.", "info")
    return flask.redirect(flask.url_for("auth.login", next=flask.request.url))


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
    """Legacy recursive function - consider using build_group_tree_optimized() instead."""
    return dict(
        id=group.id,
        text=group.display_name,
        children=[group_tree(sgroup) for sgroup in group.children],
    )


def build_group_tree_optimized(max_depth: int = 20) -> list[dict]:
    """
    Build group tree with fetch-once strategy to avoid N+1 queries.
    
    Fetches all groups in a single query and builds the tree structure in memory.
    This is much more efficient than the recursive approach with lazy loading.
    
    Includes safeguards:
    - Depth limiting to prevent excessive nesting
    - Cycle detection to prevent infinite recursion from circular references
    
    Args:
        max_depth: Maximum depth of tree to build (default: 20)
    
    Returns:
        List of root-level group nodes with nested children.
    """
    # Single query to fetch all groups
    all_groups = db.session.query(Group).all()
    
    # Build lookup dictionary: parent_id -> list of children
    groups_by_parent = {}
    for group in all_groups:
        parent_id = group.parent_id or 'root'
        groups_by_parent.setdefault(parent_id, []).append(group)
    
    def build_node(group: Group, depth: int = 0, visited: set = None) -> dict:
        """
        Recursively build tree node with children.
        
        Args:
            group: The group to build node for
            depth: Current depth in the tree
            visited: Set of visited group IDs for cycle detection
        
        Returns:
            Dictionary representing the tree node
        """
        if visited is None:
            visited = set()
        
        # Cycle detection: check if we've already visited this group in current path
        if group.id in visited:
            return {
                'id': group.id,
                'text': group.display_name + ' ⚠️ (circular reference)',
                'children': []
            }
        
        # Depth limit: prevent excessive nesting
        if depth >= max_depth:
            children = groups_by_parent.get(group.id, [])
            text = group.display_name
            if children:
                text += f' ⚠️ (+{len(children)} more, depth limit reached)'
            return {
                'id': group.id,
                'text': text,
                'children': []
            }
        
        # Add current group to visited set for this path
        visited_copy = visited.copy()
        visited_copy.add(group.id)
        
        # Recursively build children
        return {
            'id': group.id,
            'text': group.display_name,
            'children': [
                build_node(child, depth + 1, visited_copy) 
                for child in groups_by_parent.get(group.id, [])
            ]
        }
    
    # Build tree starting from root nodes (those without parent)
    return [build_node(group) for group in groups_by_parent.get('root', [])]


def get_group_tree_json() -> str:
    """
    Get group tree as JSON string for use in templates.
    
    Returns:
        JSON-serialized group tree structure.
    """
    tree_data = build_group_tree_optimized()
    return json.dumps(tree_data)


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

    return flask.render_template("auth/edit_permission.j2", form=form, title=_title, tree_data=get_group_tree_json())
