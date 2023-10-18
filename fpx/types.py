from __future__ import annotations

from sanic import HTTPResponse
from sanic import Request as SanicRequest
from sanic import Sanic
from sqlalchemy.orm import Session
from typing_extensions import TypeAlias

from fpx.config import FpxConfig
from fpx.context import Context

App: TypeAlias = Sanic[FpxConfig, Context]
Request: TypeAlias = SanicRequest[App, Context]
Response: TypeAlias = HTTPResponse
AlchemySession: TypeAlias = Session
