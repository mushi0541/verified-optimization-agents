"""Model clients.

Both clients return the same LLMReply, so the rest of the code does not depend on the provider.
Model spec format: "openai:<model name>" (any OpenAI-compatible endpoint, the default route for the
free tiers listed in .env.example) or "bedrock:<model id>" (paid, optional).
"""

import os
import threading
import time
from typing import Protocol

from .contracts import LLMReply, TokenUsage


class LLM(Protocol):
    name: str

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply: ...


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
        self.min_interval_s = 60.0 / max_rpm if max_rpm > 0 else 0.0
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def _wait_for_turn(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_s = self._next_request_at - now
            self._next_request_at = max(now, self._next_request_at) + self.min_interval_s
        if wait_s > 0:
            time.sleep(wait_s)

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply:
        self._wait_for_turn()
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
