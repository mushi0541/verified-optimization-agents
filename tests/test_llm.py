from optverify.llm import MIN_ANSWER_TOKENS, OpenAICompatibleLLM, fitted_output_cap, with_temperature

# The message Groq returned for the TSP problem of the Phase 1 pipeline run.
GROQ_TOO_LARGE = (
    "Error code: 413 - {'error': {'message': 'Request too large for model `openai/gpt-oss-120b` in organization "
    "`org` service tier `on_demand` on tokens per minute (TPM): Limit 8000, Requested 9259, please reduce your "
    "message size and try again.', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}"
)


def test_temperature_copy_shares_request_pacing(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1/v1")
    monkeypatch.setenv("LLM_MAX_RPM", "2")
    llm = OpenAICompatibleLLM("some-model")
    sampler = with_temperature(llm, 0.7)
    assert sampler.temperature == 0.7 and llm.temperature == 0.0
    assert sampler._pacer is llm._pacer


def test_fitted_output_cap_leaves_room_for_the_prompt():
    prompt_tokens = 9259 - 4096
    assert fitted_output_cap(GROQ_TOO_LARGE, max_tokens=4096) == 8000 - prompt_tokens - 100


def test_fitted_output_cap_gives_up_without_numbers_or_room():
    assert fitted_output_cap("Error code: 500 - server error", max_tokens=4096) is None
    almost_full = "Limit 8000, Requested 11800"  # the prompt alone uses 7,704 tokens
    assert fitted_output_cap(almost_full, max_tokens=4096) is None
    assert 8000 - (11800 - 4096) - 100 < MIN_ANSWER_TOKENS
