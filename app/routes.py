from flask import render_template, redirect, flash, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, TextAreaField, TelField
from wtforms.validators import DataRequired

from app import app


class LocalEvent(FlaskForm):
    title = StringField('title', validators=[DataRequired()])
    email = EmailField('email')  # , validators=[DataRequired()])
    tel = TelField('tel')
    description = TextAreaField('description')  # , validators=[DataRequired()])


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='PfadiTag 2022')


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    event = LocalEvent()
    if event.validate_on_submit():
        flash(f"Creating new event {event.title.data}")
        return redirect(url_for('edit'))

    return render_template('edit.html', form=event)
