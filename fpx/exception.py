"""Application errors and error handling logic.
"""
from __future__ import annotations

from sanic import response
from webargs_sanic.sanicparser import HandleValidationError

from fpx.types import App, Request


class FpxError(Exception):
    _status = 500

    def __init__(self, details, *args):
        super().__init__(*args)
        self._details = details


class NotFoundError(FpxError):
    _status = 404


class NotAuthorizedError(FpxError):
    _status = 403


class NotAuthenticatedError(FpxError):
    _status = 401


class JwtError(FpxError):
    _status = 422


class RequestError(FpxError):
    _status = 400


class ConfigError(FpxError):
    pass


class TransportError(FpxError):
    pass

class UrlNotAvailableError(TransportError):
    pass


async def handle_validation_error(request: Request, err: HandleValidationError):
    """Convert validation error into JSON response."""
    exc = err.exc
    if exc:
        return response.json({"errors": exc.messages}, status=422)
    return None


async def handle_fpx_error(request: Request, err: NotFoundError):
    """Convert arbitrary FPX error into JSON response."""
    return response.json({"errors": err._details}, status=err._status)


def add_handlers(app: App):
    app.exception(HandleValidationError)(handle_validation_error)
    app.exception(FpxError)(handle_fpx_error)
