from garage61.models import Garage61Error


class Garage61ClientError(Exception):
    """Base class for all structured Garage61 client errors."""

    error_code: str = "api_error"
    recoverable: bool = False

    def to_model(self) -> Garage61Error:
        return Garage61Error(
            error=self.error_code,
            message=str(self),
            recoverable=self.recoverable,
        )


class LapNotFoundError(Garage61ClientError):
    """Raised when GET /laps/{id} returns 404."""

    error_code = "lap_not_found"
    recoverable = False


class TelemetryUnavailableError(Garage61ClientError):
    """Raised when a lap exists but has no telemetry CSV."""

    error_code = "telemetry_unavailable"
    recoverable = False


class TelemetryParseError(Garage61ClientError):
    """Raised when the telemetry CSV is missing expected columns."""

    error_code = "telemetry_parse_error"
    recoverable = False


class APIError(Garage61ClientError):
    """Raised for any non-2xx response not otherwise handled."""

    error_code = "api_error"
    recoverable = False


class NoLapsFoundError(Garage61ClientError):
    """Raised when a lap search returns zero results."""

    error_code = "no_laps_found"
    recoverable = True
