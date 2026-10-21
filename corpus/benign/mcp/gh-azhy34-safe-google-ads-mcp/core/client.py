import os
import time
import random
import grpc
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from google.api_core import protobuf_helpers
from .config import LOGIN_CUSTOMER_ID
from shield.telemetry import record_api_call, redact_secrets

REQUEST_ID_KEY = "request-id"
# Google (best-practices/understand-api-errors, error-types): retry only transient server errors, with exponential
# backoff and jitter. RESOURCE_EXHAUSTED (quota) is left out on purpose: its wait is long, an agent should see it at once.
TRANSIENT_STATUSES = frozenset({"UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "UNKNOWN", "ABORTED"})
TRANSIENT_ADS_CODES = frozenset({"internal_error.TRANSIENT_ERROR", "internal_error.INTERNAL_ERROR"})
# Reads only: repeating a mutate could apply a change twice
RETRYABLE_METHODS = frozenset({"Search", "GenerateKeywordIdeas", "ListAccessibleCustomers"})
RETRY_DELAYS_S = (1.0, 2.0)
RETRY_JITTER_S = 0.5
MAX_LOGGED_REQUEST_CHARS = 2000

def _short_method(method) -> str:
    """'/google.ads.googleads.v24.services.GoogleAdsService/Search' -> 'GoogleAdsService/Search'."""
    if isinstance(method, bytes):
        method = method.decode()
    service, _, name = str(method).lstrip("/").rpartition("/")
    return f"{service.rsplit('.', 1)[-1]}/{name}"

def _request_text(request) -> str:
    """The failed request as Google's logging guide asks (the GAQL query, the operations), one line, masked, cut."""
    text = redact_secrets(" ".join(str(request).split()))
    return text if len(text) <= MAX_LOGGED_REQUEST_CHARS else text[:MAX_LOGGED_REQUEST_CHARS] + "..."

def _metadata_request_id(call) -> str | None:
    try:
        for key, value in call.trailing_metadata() or ():
            if key == REQUEST_ID_KEY:
                return value.decode() if isinstance(value, bytes) else str(value)
    except Exception:
        pass
    return None

def failure_status(exc) -> str:
    """'query_error.BAD_NUMBER' for a Google Ads failure, 'grpc.UNAVAILABLE' for a bare gRPC error."""
    if isinstance(exc, GoogleAdsException):
        from shield.error_shield import _error_code_name
        try:
            errors = list(exc.failure.errors) if exc.failure else []
            if errors:
                return _error_code_name(errors[0])
        except Exception:
            pass
        try:
            return f"grpc.{exc.error.code().name}"
        except Exception:
            return "GOOGLE_ADS_ERROR"
    try:
        return f"grpc.{exc.code().name}"
    except Exception:
        return type(exc).__name__

def _is_transient(exc) -> bool:
    status = failure_status(exc)
    if status in TRANSIENT_ADS_CODES:
        return True
    if not status.startswith("grpc.") or status[5:] not in TRANSIENT_STATUSES:
        return False
    # A dead refresh token surfaces as a gRPC error from the auth plugin: repeating it only wastes seconds
    details = ""
    try:
        details = exc.details() or ""
    except Exception:
        pass
    return "metadata from plugin" not in details and "invalid_grant" not in details

class GoogleAdsCallInterceptor(grpc.UnaryUnaryClientInterceptor):
    """
    Google's logging guide (developers.google.com/google-ads/api/docs/productionize/logging, Option 4: a custom gRPC
    interceptor) asks for the request-id of every call and the full request of a failed one; its monitoring guide asks
    for request time at subsystem granularity. This interceptor records each API call of the running tool call
    (shield.telemetry.record_api_call): method, time, status, request-id, attempt, and the request when it failed.
    It also retries transient errors of read methods (Google's retry guidance: exponential backoff with jitter).
    In this chain a failure is returned, not raised (grpc wraps the library's GoogleAdsException in the returned
    outcome), so the outcome is inspected with .exception(). Streaming calls are not covered: no tool uses search_stream.
    """
    def intercept_unary_unary(self, continuation, client_call_details, request):
        method = _short_method(getattr(client_call_details, "method", ""))
        retryable = method.rsplit("/", 1)[-1] in RETRYABLE_METHODS
        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            response = continuation(client_call_details, request)
            ms = (time.perf_counter() - started) * 1000
            try:
                exc = response.exception()
            except Exception:
                exc = None
            try:
                if exc is None:
                    record_api_call(method, ms, "OK", _metadata_request_id(response), attempt)
                else:
                    request_id = getattr(exc, "request_id", None) or _metadata_request_id(exc)
                    record_api_call(method, ms, failure_status(exc), request_id, attempt, _request_text(request))
            except Exception:
                pass  # the journal never breaks an API call
            if exc is not None and retryable and attempt <= len(RETRY_DELAYS_S) and _is_transient(exc):
                time.sleep(RETRY_DELAYS_S[attempt - 1] + random.uniform(0, RETRY_JITTER_S))
                continue
            return response

_API_CALL_INTERCEPTOR = GoogleAdsCallInterceptor()

def get_ads_client(login_id: str = None) -> GoogleAdsClient:
    """
    Initializes and returns an official GoogleAdsClient using credentials from environment.
    Uses use_proto_plus=True for high-performance protobuf access.
    Every service client it hands out carries the GoogleAdsCallInterceptor, so the 57 get_service() calls in tools/ need no change.
    """
    credentials = {
        'developer_token': os.environ.get('GOOGLE_ADS_DEVELOPER_TOKEN'),
        'refresh_token': os.environ.get('GOOGLE_ADS_REFRESH_TOKEN'),
        'client_id': os.environ.get('GOOGLE_ADS_CLIENT_ID'),
        'client_secret': os.environ.get('GOOGLE_ADS_CLIENT_SECRET'),
        'login_customer_id': login_id or os.environ.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID') or LOGIN_CUSTOMER_ID,
        'use_proto_plus': True
    }
    client = GoogleAdsClient.load_from_dict(credentials)
    original_get_service = client.get_service

    def get_service(name, *args, interceptors=None, **kwargs):
        return original_get_service(name, *args, interceptors=[*(interceptors or []), _API_CALL_INTERCEPTOR], **kwargs)

    client.get_service = get_service
    return client

def eur_to_micros(amount_eur: float) -> int:
    """
    Converts EUR to micros rounded to whole cents.
    int(4.10 * 1_000_000) == 4099999, which the API rejects as not a multiple of 0.01 EUR.
    """
    return int(round(amount_eur * 100)) * 10_000

def build_update_mask(original_obj, mutated_obj):
    """
    Generates a protobuf FieldMask for sparse updates.
    Prevents the notorious Google Ads API bug where missing masks reset fields to defaults (e.g. 0.01 € bid).
    """
    return protobuf_helpers.field_mask(original_obj, mutated_obj)
