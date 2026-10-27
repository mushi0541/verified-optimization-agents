"""Per-step trace writer for observability and debugging."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import TokenUsage


def _sensitive_env_values() -> set[str]:
    """Collect secret values from environment variables that look like keys, passwords or tokens."""
    secrets = set()
    sensitive_substrings = ("KEY", "SECRET", "TOKEN", "PASSWORD")
    for name, value in os.environ.items():
        if any(sub in name.upper() for sub in sensitive_substrings):
            val_str = str(value).strip()
            if len(val_str) >= 4:
                secrets.add(val_str)
    return secrets


def _redact(text: str, secrets: set[str]) -> str:
    """Replace sensitive strings with [REDACTED]."""
    for secret in secrets:
        if secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


class TraceWriter:
    """Appends JSON lines for every step of an optimization problem run."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else None

    def record(
        self,
        role: str,
        input_info: Any,
        output_info: Any,
        tokens: TokenUsage | dict | None = None,
        latency_s: float = 0.0,
    ) -> None:
        if self.path is None:
            return

        if tokens is None:
            token_dict = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
        elif isinstance(tokens, TokenUsage):
            token_dict = {
                "input_tokens": tokens.input_tokens,
                "output_tokens": tokens.output_tokens,
                "calls": tokens.calls,
            }
        elif isinstance(tokens, dict):
            token_dict = {
                "input_tokens": int(tokens.get("input_tokens", 0)),
                "output_tokens": int(tokens.get("output_tokens", 0)),
                "calls": int(tokens.get("calls", 0)),
            }
        else:
            token_dict = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "input": input_info,
            "output": output_info,
            "tokens": token_dict,
            "latency_s": round(float(latency_s), 4),
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw_json = json.dumps(entry)
        sanitized = _redact(raw_json, _sensitive_env_values())

        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(sanitized + "\n")
