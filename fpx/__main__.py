from sanic import Sanic

from fpx.app import loader

app = loader.load()
app.prepare(
    host=app.config.HOST,
    port=app.config.PORT,
    dev=app.config.DEBUG,
)

Sanic.serve(app, app_loader=loader)
