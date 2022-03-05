from registration import app, db

app.config.update({
    "SECRET_KEY": "SomethingNotEntirelySecret",
})


@app.shell_context_processor
def make_shell_context():
    return {'db': db}
