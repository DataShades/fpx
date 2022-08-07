from __future__ import annotations

import base64
import json
from threading import main_thread

from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class Base64Json(fields.Field):
    """Converts JSON-cmpatible structure into base64-encoded json string."""

    default_error_messages = {
        "string": "Not a string.",
        "base64": "Not a valid base64-encoded value",
        "json": "Not a valid JSON",
        "unallowed": "Unexpected value type after deserialization: {type}",
    }

    def _fpx_is_allowed(self, v):
        allowed = self.metadata.get("fpx_allow")
        if not allowed:
            allowed = self.metadata.get("fpx_expect", object)

        return isinstance(v, allowed)

    def _fpx_is_expected(self, v):
        expected = self.metadata.get("fpx_expect")
        if expected:
            return isinstance(v, expected)
        return False

    def _serialize(self, value, attr, obj, **kwargs):
        return base64.encodebytes(json.dumps(value).encode("utf8"))

    def _deserialize(self, value, attr, data, **kwargs):
        if self._fpx_is_expected(value):
            return value

        if not isinstance(value, (str, bytes)):
            raise self.make_error("string")

        if isinstance(value, str):
            value = value.encode("utf8")

        try:
            value = base64.decodebytes(value)
        except ValueError as err:
            raise self.make_error("base64") from err

        try:
            value = json.loads(value)
        except ValueError as err:
            raise self.make_error("json") from err

        if not self._fpx_is_allowed(value):
            raise self.make_error("unallowed", type=type(value))

        return value


class StreamUrl(Schema):
    client = fields.Str(required=True)


class TicketIndex(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(1))


class TicketGenerate(Schema):
    type = fields.Str(required=True)
    items = Base64Json(required=True, metadata={"fpx_expect": list})
    options = Base64Json(
        required=False, load_default=dict, metadata={"fpx_expect": dict}
    )

    @validates_schema
    def validate_ticket_type(self, data, **kwargs):
        if data["type"] == "stream" and len(data["items"]) != 1:
            raise ValidationError({"type": ["Ticket with the type `stream` allows only one item"]})
