from __future__ import annotations

from typing import Any

from sanic.config import Config
from sqlalchemy import create_engine

from . import model


def _defaults() -> dict[str, Any]:
    return dict(
        DEBUG=False,
        HOST="0.0.0.0",
        PORT=8000,
        KEEP_ALIVE=False,
        CORS_ORIGINS="*",
        DB_URL="sqlite:////tmp/fpx.db",
        DB_EXTRAS={
            # "echo": True,
        },
        SIMULTANEOURS_DOWNLOADS_LIMIT=2,
        FALLBACK_ERROR_FORMAT="json",
        JWT_ALGORITHM="HS256",
    )


class FpxConfig(Config):
    def __init__(self):
        super().__init__()
        self.update_config(_defaults())
        self.load_environment_vars(prefix="FPX_")
        self.update_config("${FPX_CONFIG}")

        engine = create_engine(self.DB_URL, **self.DB_EXTRAS)
        model.Session.remove()
        model.Session.configure(bind=engine)
