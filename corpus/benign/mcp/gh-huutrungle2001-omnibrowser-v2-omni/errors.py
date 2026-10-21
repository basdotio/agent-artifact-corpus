class OmniError(Exception):
    def __init__(self, code, message, exit_code):
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def invalid(message):
    return OmniError("INVALID_ARGUMENT", message, 2)


def stale():
    return OmniError("STALE_REF", "Run --observe again before acting.", 4)
