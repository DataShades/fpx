from marshmallow import Schema, fields, validate


class Index(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(1))
