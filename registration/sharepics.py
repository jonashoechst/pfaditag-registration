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
    overlay_draw.text((-38, 1030), "PfadiTag", font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=505), fill=(255, 255, 255, 150))
    img = Image.alpha_composite(img, overlay)

    # Draw texts
    draw = ImageDraw.Draw(img)
    draw.text((1550, 1880), "pfaditag.de", font=ImageFont.truetype("etc/Roboto/Roboto-Regular.ttf", size=80), fill=color)

    draw.text((50, 1900), event.contact_string, font=ImageFont.truetype("etc/Roboto/Roboto-Light.ttf", size=60), fill=color)
    draw.text((50, 1550), event.title, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=100), fill=color)
    draw.text((50, 1670), f"Stamm {event.group.short_name}", font=ImageFont.truetype("etc/Roboto/Roboto-Regular.ttf", size=100), fill=color)
    draw.text((50, 1790), event.date_string, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=50), fill=color)

    # create BytesIO as virtual output file
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')

    # send output
    response = flask.make_response(img_bytes.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers["Content-Disposition"] = f"attachment"
    return response


@sharepics_bp.route('/sharepic_<int:event_id>_story_<int:story_id>.png')
def sharepic_story(event_id: int, story_id: int, color="#7876aa"):
    event: models.Event = models.Event.query.get(event_id)

    # create PIL image / draw object
    img = Image.open(f"etc/sharepics/story_{story_id}.png")
    img = img.resize((1080, 1920))
    draw = ImageDraw.Draw(img)

    # Overlay text
    draw.text((20, 1540), event.title, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=60), fill=color)
    draw.text((20, 1600), f"Stamm {event.group.short_name}", font=ImageFont.truetype("etc/Roboto/Roboto-Regular.ttf", size=60), fill=color)
    draw.text((20, 1670), event.date_string, font=ImageFont.truetype("etc/Roboto/Roboto-Bold.ttf", size=30), fill=color)

    draw.text((20, 1740), event.contact_string, font=ImageFont.truetype("etc/Roboto/Roboto-Light.ttf", size=40), fill=color)

    # create BytesIO as virtual output file
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')

    # send output
    response = flask.make_response(img_bytes.getvalue())
    response.headers['Content-Type'] = 'image/png'
    response.headers["Content-Disposition"] = f"attachment"

    return response
