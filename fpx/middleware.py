from sanic import Sanic
from collections import deque


def db_session(request):
    request.ctx.db = request.app.DbSession()


def db_session_close(request, response):
    try:
        request.ctx.db.close()
    except AttributeError:
        # DB session is not set. Probably it's non-existing route
        pass


def create_download_queue(app, loop):
    app.download_queue = deque()
    app.active_downloads = list()


def add_middlewares(app: Sanic):
    app.middleware(db_session)
    app.middleware("response")(db_session_close)

    app.listener("after_server_start")(create_download_queue)
