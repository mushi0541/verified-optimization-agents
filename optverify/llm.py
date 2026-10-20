"""Model clients.

Both clients return the same LLMReply, so the rest of the code does not depend on the provider.
Model spec format: "openai:<model name>" (any OpenAI-compatible endpoint, the default route for the
free tiers listed in .env.example) or "bedrock:<model id>" (paid, optional).
"""

import copy
import os
import re
import threading
import time
from typing import Protocol

from .contracts import LLMReply, TokenUsage

# Free plans count the prompt plus max_tokens against a tokens-per-minute limit and reject larger requests
# with a message such as "... tokens per minute (TPM): Limit 8000, Requested 9259 ...".
_TPM_LIMIT_ERROR = re.compile(r"Limit (\d+), Requested (\d+)")
MIN_ANSWER_TOKENS = 512


def fitted_output_cap(error_message: str, max_tokens: int, margin: int = 100) -> int | None:
    """Output cap that fits the per-minute limit, read from a "request too large" error message.

    The prompt size is Requested - max_tokens, so the cap is Limit - prompt size - margin.
    Returns None when the message has no such numbers or too little room is left for an answer.
    """
    match = _TPM_LIMIT_ERROR.search(error_message)
    if match is None:
        return None
    limit, requested = int(match[1]), int(match[2])
    cap = limit - (requested - max_tokens) - margin
    return cap if cap >= MIN_ANSWER_TOKENS else None


class LLM(Protocol):
    name: str

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply: ...


class _Pacer:
    """Spaces out requests so that at most one starts every min_interval_s seconds."""

    def __init__(self, min_interval_s: float):
        self.min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def wait_for_turn(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_s = self._next_request_at - now
            self._next_request_at = max(now, self._next_request_at) + self.min_interval_s
        if wait_s > 0:
            time.sleep(wait_s)


class BedrockLLM:
    """Amazon Bedrock Converse API. Uses AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_REGION."""

    def __init__(self, model_id: str, temperature: float = 0.0):
        import boto3
        from botocore.config import Config

        self.name = model_id
        self.temperature = temperature
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            config=Config(read_timeout=300, retries={"max_attempts": 8, "mode": "adaptive"}),
        )

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply:
        start = time.perf_counter()
        response = self.client.converse(
            modelId=self.name,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": self.temperature},
        )
        # Reasoning models also return reasoning blocks; only the text blocks are the answer.
        text = "".join(block.get("text", "") for block in response["output"]["message"]["content"])
        usage = response["usage"]
        return LLMReply(
            text=text,
            usage=TokenUsage(usage["inputTokens"], usage["outputTokens"], 1),
            latency_s=time.perf_counter() - start,
        )


class OpenAICompatibleLLM:
    """Free-tier friendly client for any OpenAI-compatible endpoint (Groq, OpenRouter, Google AI Studio,
    a local Ollama server, ...). Uses LLM_BASE_URL, LLM_API_KEY and optionally LLM_MAX_RPM, which spaces
    out requests so free-tier rate limits are not hit."""

    def __init__(self, model: str, temperature: float = 0.0):
        from openai import OpenAI

        self.name = model
        self.temperature = temperature
        self.client = OpenAI(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.getenv("LLM_API_KEY", "not-needed-for-local-servers"),
            max_retries=8,
            timeout=300,
        )
        max_rpm = float(os.getenv("LLM_MAX_RPM", "0") or 0)
        self._pacer = _Pacer(60.0 / max_rpm if max_rpm > 0 else 0.0)

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply:
        from openai import APIStatusError

        try:
            return self._request(prompt, max_tokens)
        except APIStatusError as error:
            fitted = fitted_output_cap(str(error), max_tokens)
            if error.status_code != 413 or fitted is None:
                raise
            return self._request(prompt, fitted)

    def _request(self, prompt: str, max_tokens: int) -> LLMReply:
        self._pacer.wait_for_turn()
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=max_tokens,
        )
        usage = response.usage
        return LLMReply(
            text=response.choices[0].message.content or "",
            usage=TokenUsage(usage.prompt_tokens, usage.completion_tokens, 1),
            latency_s=time.perf_counter() - start,
        )


def make_llm(spec: str, temperature: float = 0.0) -> LLM:
    provider, _, model = spec.partition(":")
    if provider == "bedrock":
        return BedrockLLM(model, temperature)
    if provider == "openai":
        return OpenAICompatibleLLM(model, temperature)
    raise ValueError(f"Unknown provider in '{spec}'. Use 'bedrock:<model id>' or 'openai:<model>'.")


def with_temperature(llm: LLM, temperature: float) -> LLM:
    """A copy of a client that samples at another temperature. The copy shares the connection and the
    request pacing of the original, so both together still respect LLM_MAX_RPM."""
    other = copy.copy(llm)
    other.temperature = temperature
    return other
