from sanic import Sanic

def db_session(request):
    request.ctx.db = request.app.ctx.db_session()


def db_session_close(request, response):
    try:
        request.ctx.db.close()
    except AttributeError:
        # DB session is not set. Probably it's non-existing route
        pass

def add_middlewares(app: Sanic):
    app.middleware(db_session)
    app.middleware("response")(db_session_close)
