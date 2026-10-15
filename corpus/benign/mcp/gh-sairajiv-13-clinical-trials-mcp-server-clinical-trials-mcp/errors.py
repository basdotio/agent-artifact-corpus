"""Error types for the ClinicalTrials.gov client.

The client raises these instead of raw ``httpx`` exceptions so the MCP tool
layer can turn them into short, actionable tool errors. Messages are written
for the calling model: they say what failed and what to try next, and they
never carry stack traces or response bodies from the upstream API.
"""


class TrialsError(Exception):
    """Base class for all errors raised by this package."""


class StudyNotFoundError(TrialsError):
    """The requested NCT number does not exist in ClinicalTrials.gov."""

    def __init__(self, nct_id: str) -> None:
        self.nct_id = nct_id
        super().__init__(
            f"No study found for NCT number {nct_id}. "
            "Check the number and try again; NCT numbers look like NCT01234567."
        )


class UpstreamError(TrialsError):
    """ClinicalTrials.gov returned an error response we cannot retry away."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(
            f"ClinicalTrials.gov rejected the request (HTTP {status_code}). "
            "The query parameters may be invalid; simplify the query and try again."
        )


class UpstreamUnavailableError(TrialsError):
    """ClinicalTrials.gov could not be reached after retries (5xx or network)."""

    def __init__(self, attempts: int) -> None:
        self.attempts = attempts
        super().__init__(
            "ClinicalTrials.gov is not responding right now "
            f"(tried {attempts} times). Wait a moment and try again."
        )


class UpstreamDataError(TrialsError):
    """ClinicalTrials.gov responded with a body that is not valid study data."""

    def __init__(self) -> None:
        super().__init__(
            "ClinicalTrials.gov returned data in an unexpected format. "
            "Try the request again; if it keeps failing, narrow the query."
        )
