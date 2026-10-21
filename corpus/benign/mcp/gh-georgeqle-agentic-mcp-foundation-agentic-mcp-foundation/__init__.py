"""Tool-independent lifecycle primitives. Domain operations stay in adapters."""

PROTOCOL_VERSION = 1


class LifecycleError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code, self.retryable = code, retryable

    def report(self):
        return {"code": self.code, "message": str(self), "retryable": self.retryable}
