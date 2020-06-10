import logging

DEBUG = False

HOST = "0.0.0.0"
PORT = 8000

KEEP_ALIVE = False

DB_URL = "sqlite:////tmp/fpx.db"
SIMULTANEOURS_DOWNLOADS_LIMIT = 2

LOGGING = {
    "version": 1,
    "formatters": {
        "generic": {
            "format": "%(asctime)s %(levelname)-5.5s [%(name)s] %(message)s",
        },
        "access": {
            "format": (
                "%(asctime)s %(levelname)-5.5s [%(name)s] [%(host)s]: "
                "%(request)s %(message)s %(status)d %(byte)d"
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": logging.NOTSET,
            "formatter": "generic",
        },
        "access": {
            "class": "logging.StreamHandler",
            "level": logging.NOTSET,
            "formatter": "access",
        },
    },
    "loggers": {
        "root": {"handlers": ["console"], "level": logging.WARNING,},
        "sanic": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": 0,
        },
        "sanic.access": {
            "handlers": ["access"],
            "level": logging.INFO,
            "propagate": 0,
        },
        "fpx": {
            "handlers": ["console"],
            "level": logging.INFO,
            "propagate": 0,
        },
    },
}
