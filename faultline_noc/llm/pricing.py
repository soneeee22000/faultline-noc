"""Per-model token prices and a hard spend cap for recorded runs."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

TOKENS_PER_PRICE_UNIT = 1_000_000
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.1


@dataclass(frozen=True)
class ModelPrice:
    """USD per million input tokens and per million output tokens."""

    input_usd: float
    output_usd: float


PRICES: dict[str, ModelPrice] = {
    "claude-haiku-4-5": ModelPrice(input_usd=1.0, output_usd=5.0),
    "claude-sonnet-5": ModelPrice(input_usd=2.0, output_usd=10.0),
}


class BudgetExceededError(RuntimeError):
    """Raised before a request would be sent once the spend cap is reached."""


def _tokens(usage: Mapping[str, Any], key: str) -> int:
    """Return a token count from a usage block, treating a missing or null field as zero."""
    return int(usage.get(key) or 0)


def usage_cost_usd(model: str, usage: Mapping[str, Any]) -> float:
    """Return the USD cost of one response from its usage block."""
    price = PRICES[model]
    input_units = (
        _tokens(usage, "input_tokens")
        + _tokens(usage, "cache_creation_input_tokens") * CACHE_WRITE_MULTIPLIER
        + _tokens(usage, "cache_read_input_tokens") * CACHE_READ_MULTIPLIER
    )
    output_units = _tokens(usage, "output_tokens")
    return (input_units * price.input_usd + output_units * price.output_usd) / TOKENS_PER_PRICE_UNIT


@dataclass
class SpendTracker:
    """Accumulates spend and tokens per model and enforces a hard cap."""

    budget_usd: float
    spent_usd: dict[str, float] = field(default_factory=dict)
    tokens: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def total_usd(self) -> float:
        """Return spend across every model."""
        return sum(self.spent_usd.values())

    def record(self, model: str, usage: Mapping[str, Any]) -> None:
        """Add one response's cost and token counts."""
        self.spent_usd[model] = self.spent_usd.get(model, 0.0) + usage_cost_usd(model, usage)
        counts = self.tokens.setdefault(model, {"input": 0, "output": 0})
        counts["input"] += (
            _tokens(usage, "input_tokens")
            + _tokens(usage, "cache_creation_input_tokens")
            + _tokens(usage, "cache_read_input_tokens")
        )
        counts["output"] += _tokens(usage, "output_tokens")

    def check(self) -> None:
        """Raise BudgetExceededError when the cap has been reached."""
        if self.total_usd >= self.budget_usd:
            raise BudgetExceededError(
                f"spend ${self.total_usd:.4f} reached the ${self.budget_usd:.2f} cap"
            )
