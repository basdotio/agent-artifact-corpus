class AuOpenDataError(Exception):
    """Base for every domain error. Carries a remedy so a caller is never stuck."""

    def __init__(self, message: str, *, remedy_url: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.remedy_url = remedy_url


class ResourceNotFound(AuOpenDataError): ...


class ResourceNotQueryable(AuOpenDataError): ...


class ResourceTooLarge(AuOpenDataError): ...


class SqlRejected(AuOpenDataError): ...


class QueryTimeout(AuOpenDataError):
    """A query passed validation but ran too long and was aborted by the sandbox watchdog.

    Deliberately distinct from SqlRejected: a timeout is a runtime abort, not a validation
    rejection, and the message a model reads should say so -- "your SQL is invalid" and
    "your SQL ran too long" call for different retries.
    """


class UpstreamUnavailable(AuOpenDataError): ...


class DownloadFailed(AuOpenDataError): ...
