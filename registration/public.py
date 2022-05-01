import flask
from . import models
from flask import current_app


public_bp = flask.Blueprint('public', __name__, url_prefix='', static_folder='static')


@public_bp.route('/')
@public_bp.route('/index')
def index():
    _events = models.Event.query.all()
    _groups = models.Group.query.all()
    return flask.render_template('index.html', title=current_app.config["APP_TITLE"], events=_events, groups=_groups)
