from optverify.run import _endpoint


def test_endpoint_records_the_provider_host_only(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://user:secret@api.cerebras.ai/v1")
    assert _endpoint("openai:gpt-oss-120b") == "api.cerebras.ai"  # never the credentials in the URL
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    assert _endpoint("bedrock:openai.gpt-oss-120b-1:0") == "bedrock us-east-1"
