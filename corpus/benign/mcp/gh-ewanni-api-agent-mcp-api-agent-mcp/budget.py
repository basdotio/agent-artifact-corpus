from dataclasses import dataclass


class BudgetExhaustedError(RuntimeError):
    """Raised when no more generated-token budget can be reserved."""


@dataclass
class TokenBudget:
    """Tracks generated tokens and reserves output capacity before concurrent calls."""

    max_tokens: int
    used_tokens: int = 0
    reserved_tokens: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens - self.reserved_tokens)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0

    def reserve(self, requested: int) -> int:
        if requested < 1:
            raise ValueError("requested token reservation must be positive")
        allowance = min(requested, self.remaining)
        if allowance == 0:
            raise BudgetExhaustedError("discussion output-token budget is exhausted")
        self.reserved_tokens += allowance
        return allowance

    def settle(self, reservation: int, actual: int | None) -> None:
        if reservation < 0 or reservation > self.reserved_tokens:
            raise ValueError("invalid token reservation")
        self.reserved_tokens -= reservation
        self.used_tokens += reservation if actual is None else max(0, actual)

    def charge(self, tokens: int) -> None:
        if tokens < 0:
            raise ValueError("token usage cannot be negative")
        self.used_tokens += tokens
