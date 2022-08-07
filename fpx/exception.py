class FpxError(Exception):
    _status = 500

    def __init__(self, details, *args):
        super().__init__(*args)
        self._details = details


class NotFound(FpxError):
    _status = 404


class NotAuthorized(FpxError):
    _status = 403


class JwtError(FpxError):
    _status = 422

class RequestError(FpxError):
    _status = 400
