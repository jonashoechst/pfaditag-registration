import datetime
from typing import List

import flask
import icalendar
from flask_login import current_user

from .models import Event, Group, User, UserPermission

public_bp = flask.Blueprint("public", __name__, url_prefix="", static_folder="static")


@public_bp.route("/index")
@public_bp.route("/")
def index():
    _events: List[Event] = Event.query.all()
    if not current_user.is_authenticated:
        _events = [e for e in _events if e.is_current]
    return flask.render_template(
        "index.j2",
        events=_events,
    )


@public_bp.route("/impressum")
def impressum():
    editors: list[User] = list(User.query.filter(User.is_superuser))
    # get tree roots
    for root in Group.query.filter(None == Group.parent_id):
        root: Group
        for perm in root.permissions:
            perm: UserPermission
            if perm.granted and perm.user not in editors:
                editors.append(perm.user)

    return flask.render_template(
        "impressum.j2",
        editors=editors,
    )


@public_bp.route("/datenschutz")
def datenschutz():
    return flask.render_template(
        "datenschutz.j2",
    )


@public_bp.route("/faq")
def faq():
    return flask.render_template(
        "faq.j2",
    )


@public_bp.route("/faq_intern")
def faq_intern():
    return flask.render_template(
        "faq_intern.j2",
    )


@public_bp.route("/events")
def events():
    if current_user.is_authenticated:
        _events = current_user.query_events()
    else:
        _events = [e for e in Event.query.all() if e.is_current]

    return flask.render_template(
        "admin/events.j2",
        events=_events,
    )


@public_bp.route("/event/<int:event_id>")
def event(event_id):
    _event = Event.query.get(event_id)
    if not _event:
        flask.flash("Aktion konnte nicht gefunden werden.", "warning")
        return flask.redirect(flask.url_for("public.index"))

    return flask.render_template(
        "event.j2",
        title=_event.title,
        event=_event,
    )


@public_bp.route("/event/<int:event_id>.ics")
def event_ics(event_id):
    _event = Event.query.get(event_id)
    if not _event:
        flask.flash("Aktion konnte nicht gefunden werden.", "warning")
        return flask.redirect(flask.url_for("public.index"))

    cal_event = icalendar.Event()

    cal_event.add("summary", _event.title)
    cal_event.add("dtstart", datetime.datetime.combine(_event.date, _event.time))
    cal_event.add("dtend", datetime.datetime.combine(_event.date_end, _event.time_end))
    cal_event.add("dtstamp", datetime.datetime.now())
    cal_event["description"] = _event.description + "\n"

    if _event.email:
        cal_event["description"] += "\nE-Mail: " + _event.email
    if _event.tel:
        cal_event["description"] += "\nTelefon: " + _event.tel
    if _event.group.website:
        cal_event["description"] += "\nWebsite: " + _event.group.website

    cal_event["organizer"] = icalendar.vCalAddress(f"mailto:{_event.email}")
    cal_event["organizer"].params["cn"] = icalendar.vText(f"{_event.group}")

    cal_event["location"] = icalendar.vText(_event.group.city)
    cal_event["geo"] = f"{_event.lat},{_event.lon}"

    cal_event["url"] = icalendar.vUri(flask.url_for("public.event", event_id=_event.id, _external=True))

    cal = icalendar.Calendar()
    cal.add_component(cal_event)

    response = flask.Response(cal.to_ical(), mimetype="text/calendar")
    response.headers["Content-Disposition"] = f"attachment; filename={_event.title}.ics"

    return response
