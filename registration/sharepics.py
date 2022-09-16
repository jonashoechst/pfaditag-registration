from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import flask

from . import models

sharepics_bp = flask.Blueprint('sharepics', __name__, url_prefix='/sharepics', static_folder='static')


@sharepics_bp.route('/sharepic_<int:event_id>_photo.png')
def sharepic_photo(event_id: int, color="#7876aa"):
    event: models.Event = models.Event.query.get(event_id)
    if not event.photo:
        return flask.abort(404)

    # create PIL image / draw object
    img = Image.new("RGBA", (2000, 2000), color="#ffffff")

    # draw event image
    photo = Image.open(io.BytesIO(event.photo))
    thumb = ImageOps.fit(photo, (2000, 1500), Image.ANTIALIAS)
    img.paste(thumb, (0, 0))

    # PfadiTag transparent overlay
    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.text((1000, 1500), "PfadiTag", font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=515), anchor="ms", fill=(255, 255, 255, 150))
    img = Image.alpha_composite(img, overlay)

    # Draw texts
    draw = ImageDraw.Draw(img)
    draw.text((1950, 1950), "pfaditag.de", font=ImageFont.truetype("etc/Roboto/Roboto-Regular.ttf", size=80), anchor="rb", fill=color)

    # compile a contact line
    if event.email and event.tel:
        contact = f"{event.email} - {event.tel}"
    elif event.tel:
        contact = event.tel
    elif event.email:
        contact = event.email
    elif event.group.website:
        contact = event.group.website
    else:
        contact = f"{event.group.zip} {event.group.city}"
    draw.text((50, 1950), contact, font=ImageFont.truetype("etc/Roboto/Roboto-Light.ttf", size=60), anchor="lb", fill=color)

    draw.text((50, 1550), event.title, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=100), fill=color)
    draw.text((50, 1670), event.group.short_name, font=ImageFont.truetype("etc/Roboto/Roboto-Regular.ttf", size=100), fill=color)

    if event.date == event.date_end:
        date_str = f'{event.date.strftime("%A, %d. %B %Y")} von {event.time.strftime("%H:%M")} bis {event.time_end.strftime("%H:%M")} Uhr'
    else:
        date_str = f'von {event.dt.strftime("%A, %d.%m.%Y, %H:%M")} bis {event.dt_end.strftime("%A, %d.%m.%Y, %H:%M")} Uhr'
    draw.text((50, 1790), date_str, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=50), fill=color)

    # create BytesIO as virtual output file
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')

    # send output
    response = flask.make_response(img_bytes.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response
