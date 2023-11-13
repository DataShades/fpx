"""Application config logic.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from sanic.config import Config
from sanic.exceptions import LoadFileException
from sqlalchemy import create_engine

from . import model

log = logging.getLogger(__name__)


def _defaults() -> dict[str, Any]:
    """Default values for all config options."""
    return {
        "DEBUG": False,
        "HOST": "0.0.0.0",
        "PORT": 8000,
        "KEEP_ALIVE": False,
        "CORS_ORIGINS": "*",
        "DB_URL": "sqlite:////tmp/fpx.db",
        "DB_EXTRAS": {
            # "echo": True,
        },
        "SIMULTANEOURS_DOWNLOADS_LIMIT": 2,
        "FALLBACK_ERROR_FORMAT": "json",
        "JWT_ALGORITHM": "HS256",
        "FPX_LOG_LEVEL": "INFO",
        "FPX_NO_QUEUE": True,
        "FPX_TRANSPORT": "aiohttp",
        "FPX_PIPE_SILLY_STREAM": True,
    }


class FpxConfig(Config):
    """Configuration for Sanic app object."""

    FPX_TRANSPORT: Literal["aiohttp", "httpx"]

    def __init__(self):
        super().__init__()

        self.update_config(_defaults())

        # load all FPX_-prefixed envvars. This if required to locate config
        # file specified by FPX_CONFIG.
        self.load_environment_vars(prefix="FPX_")

        try:
            self.update_config("${FPX_CONFIG}")
        except LoadFileException:
            log.debug("Cannot locate config file($FPX_CONFIG)")

        engine = create_engine(self.DB_URL, **self.DB_EXTRAS)
        model.Session.remove()
        model.Session.configure(bind=engine)
