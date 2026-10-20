from optverify.llm import OpenAICompatibleLLM, with_temperature


def test_temperature_copy_shares_request_pacing(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:1/v1")
    monkeypatch.setenv("LLM_MAX_RPM", "2")
    llm = OpenAICompatibleLLM("some-model")
    sampler = with_temperature(llm, 0.7)
    assert sampler.temperature == 0.7 and llm.temperature == 0.0
    assert sampler._pacer is llm._pacer
