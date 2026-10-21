"""Offline tests for the interactive web server and helper."""

import json
import threading
import urllib.error
import urllib.request

import pytest

from optverify.interactive import MAX_QUESTION_LENGTH, solve_interactive_problem
from optverify.web import INDEX_FILE, make_server
from tests.fake_llm import TOY_QUESTION, FakeLLM


def test_solve_interactive_problem_rejects_empty_and_whitespace():
    with pytest.raises(ValueError, match="empty or whitespace"):
        solve_interactive_problem("", FakeLLM())
    with pytest.raises(ValueError, match="empty or whitespace"):
        solve_interactive_problem("   \n\t  ", FakeLLM())


def test_solve_interactive_problem_rejects_overlong_question():
    too_long = "x" * (MAX_QUESTION_LENGTH + 1)
    with pytest.raises(ValueError, match="exceeds maximum length"):
        solve_interactive_problem(too_long, FakeLLM())


def test_solve_interactive_problem_succeeds_with_fake_llm():
    record = solve_interactive_problem(TOY_QUESTION, FakeLLM(), paraphrases=1)
    assert record.problem_id == "interactive"
    assert record.predicted is not None
    assert record.decision is not None
    assert record.decision.action in ("answer", "escalate", "abstain")


def test_server_binds_to_127_0_0_1():
    server = make_server("127.0.0.1", 0, FakeLLM())
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_server_rejects_other_hosts():
    with pytest.raises(ValueError, match="127.0.0.1 only"):
        make_server("0.0.0.0", 0, FakeLLM())


@pytest.fixture
def running_server():
    server = make_server("127.0.0.1", 0, FakeLLM())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_get_root_serves_html(running_server):
    req = urllib.request.Request(f"{running_server}/")
    with urllib.request.urlopen(req) as response:
        assert response.status == 200
        assert "text/html" in response.headers.get("Content-Type", "")
        content = response.read().decode("utf-8")
        assert "Verified Optimization Agents" in content


def test_unknown_path_returns_404(running_server):
    req = urllib.request.Request(f"{running_server}/unknown_route")
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 404


def test_post_bad_json_returns_400(running_server):
    req = urllib.request.Request(
        f"{running_server}/api/solve",
        data=b"not valid json",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
    assert "application/json" in exc_info.value.headers.get("Content-Type", "")
    data = json.loads(exc_info.value.read().decode("utf-8"))
    assert "error" in data


def test_post_missing_question_returns_400(running_server):
    req = urllib.request.Request(
        f"{running_server}/api/solve",
        data=json.dumps({"threshold": 0.8}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 400
    assert "application/json" in exc_info.value.headers.get("Content-Type", "")
    data = json.loads(exc_info.value.read().decode("utf-8"))
    assert "error" in data


def test_post_invalid_threshold_returns_400(running_server):
    for bad_threshold in (-0.1, 1.5, "invalid"):
        req = urllib.request.Request(
            f"{running_server}/api/solve",
            data=json.dumps({"question": TOY_QUESTION, "threshold": bad_threshold}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400
        assert "application/json" in exc_info.value.headers.get("Content-Type", "")
        data = json.loads(exc_info.value.read().decode("utf-8"))
        assert "error" in data


def test_post_oversized_body_returns_413(running_server):
    large_data = {"question": "x" * 25000}
    req = urllib.request.Request(
        f"{running_server}/api/solve",
        data=json.dumps(large_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req)
    assert exc_info.value.code == 413
    assert "application/json" in exc_info.value.headers.get("Content-Type", "")
    data = json.loads(exc_info.value.read().decode("utf-8"))
    assert "error" in data


def test_post_solve_returns_expected_keys(running_server):
    req = urllib.request.Request(
        f"{running_server}/api/solve",
        data=json.dumps({"question": TOY_QUESTION, "threshold": 0.8}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))

    expected_keys = {
        "action",
        "predicted",
        "reasons",
        "score",
        "number_coverage",
        "missing_numbers",
        "paraphrase_agreement",
        "paraphrase_objectives",
        "explanation",
        "variables",
        "code",
        "status",
        "stdout",
        "error",
        "usage",
        "latency_s",
        "threshold",
    }
    assert expected_keys.issubset(data.keys())
    assert data["action"] in ("answer", "escalate", "abstain")
    assert data["threshold"] == 0.8


def test_html_contains_no_forbidden_dom_methods():
    html_text = INDEX_FILE.read_text(encoding="utf-8")
    assert "innerHTML" not in html_text
    assert "insertAdjacentHTML" not in html_text
    assert "document.write" not in html_text


class RaisingLLM(FakeLLM):
    def complete(self, prompt: str, max_tokens: int = 4096):
        raise RuntimeError("boom\nline two é")


def test_pipeline_error_with_unicode_and_newline_returns_json_500():
    server = make_server("127.0.0.1", 0, RaisingLLM())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    try:
        req = urllib.request.Request(
            f"{url}/api/solve",
            data=json.dumps({"question": TOY_QUESTION, "threshold": 0.8}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 500
        assert "application/json" in exc_info.value.headers.get("Content-Type", "")
        data = json.loads(exc_info.value.read().decode("utf-8"))
        assert "error" in data
        assert "Pipeline error: boom\nline two é" in data["error"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
