import datetime
import flask
import icalendar
from . import models
from flask import current_app
from flask_login import current_user

public_bp = flask.Blueprint('public', __name__, url_prefix='', static_folder='static')


@public_bp.route('/index')
@public_bp.route('/')
def index():
    _events = models.Event.query.all()
    return flask.render_template(
        'index.html',
        events=_events,
    )


@public_bp.route('/impressum')
def impressum():
    return flask.render_template(
        'impressum.html',
        title="Impressum",
    )


@public_bp.route('/datenschutz')
def datenschutz():
    return flask.render_template(
        'datenschutz.html',
        title="Datenschutzerklärung",
    )


@public_bp.route('/events')
def events():
    if current_user.is_authenticated:
        _events = current_user.query_events()
    else:
        _events = models.Event.query.all()

    return flask.render_template(
        'admin/events.html',
        title="Aktionen",
        events=_events,
    )


@public_bp.route('/event/<int:event_id>')
def event(event_id):
    event = models.Event.query.get(event_id)
    return flask.render_template(
        'event.html',
        title=event.title,
        event=event,
    )


@public_bp.route('/event/<int:event_id>.ics')
def event_ics(event_id):
    event = models.Event.query.get(event_id)

    cal_event = icalendar.Event()

    cal_event.add('summary', event.title)
    cal_event.add('dtstart',  datetime.datetime.combine(event.date, event.time))
    cal_event.add('dtend', datetime.datetime.combine(event.date_end, event.time_end))
    cal_event.add('dtstamp', datetime.datetime.now())
    cal_event['description'] = event.description + "\n"

    if event.email:
        cal_event['description'] += "\nE-Mail: " + event.email
    if event.tel:
        cal_event['description'] += "\nTelefon: " + event.tel
    if event.group.website:
        cal_event['description'] += "\nWebsite: " + event.group.website

    cal_event['organizer'] = icalendar.vCalAddress(f"mailto:{event.email}")
    cal_event['organizer'].params['cn'] = icalendar.vText(f"Stamm {event.group.short_name}")

    cal_event['location'] = icalendar.vText(event.group.city)
    cal_event['geo'] = f"{event.lat},{event.lon}"

    cal_event['url'] = icalendar.vUri(flask.url_for('public.event', event_id=event.id, _external=True))

    cal = icalendar.Calendar()
    cal.add_component(cal_event)

    response = flask.Response(cal.to_ical(), mimetype='text/calendar')
    response.headers["Content-Disposition"] = f"attachment; filename={event.title}.ics"

    return response
