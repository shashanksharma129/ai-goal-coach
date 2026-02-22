# ABOUTME: ADK execution telemetry: structured JSON log and cost calculation.
# ABOUTME: Gemini 2.5 Flash pricing: $0.075/1M input, $0.30/1M output.

import json
from dataclasses import dataclass
from datetime import datetime, timezone


# Gemini 2.5 Flash pricing per 1M tokens (USD)
INPUT_COST_PER_1M = 0.075
OUTPUT_COST_PER_1M = 0.30


def estimate_cost_usd(prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate cost in USD for Gemini 2.5 Flash."""
    return (prompt_tokens / 1_000_000) * INPUT_COST_PER_1M + (
        completion_tokens / 1_000_000
    ) * OUTPUT_COST_PER_1M


@dataclass
class TelemetryLogEntry:
    """Structured telemetry entry for one agent run."""

    timestamp: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: float
    confidence_score: float | None
    success: bool

    def to_json(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "latency_ms": round(self.latency_ms, 2),
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "estimated_cost_usd": f"{self.estimated_cost_usd:.6f}",
                "confidence_score": self.confidence_score,
                "success": self.success,
            }
        )


def log_run(
    *,
    latency_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
    confidence_score: float | None,
    success: bool,
) -> None:
    """Print a structured JSON log line to stdout for one agent run."""
    entry = TelemetryLogEntry(
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost_usd=estimate_cost_usd(prompt_tokens, completion_tokens),
        confidence_score=confidence_score,
        success=success,
    )
    print(entry.to_json(), flush=True)
