from __future__ import annotations

from typing import TYPE_CHECKING

from sanic import HTTPResponse
from sanic import Request as SanicRequest
from sanic import Sanic
from sqlalchemy.orm import Session
from typing_extensions import TypeAlias

if TYPE_CHECKING:
    from fpx.config import FpxConfig
    from fpx.context import Context

App: TypeAlias = "Sanic[FpxConfig, Context]"
Request: TypeAlias = "SanicRequest[App, Context]"
Response: TypeAlias = HTTPResponse
AlchemySession: TypeAlias = Session
