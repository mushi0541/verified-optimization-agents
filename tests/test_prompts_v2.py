"""Tests for the v2 prompts (#95): they change three templates, and v1 stays exactly as it was."""

import pytest

from optverify import prompts


@pytest.fixture(autouse=True)
def back_to_v1():
    yield
    prompts.use_version("v1")


def test_v2_changes_three_templates_and_v1_comes_back():
    v1 = {name: getattr(prompts, name) for name in ("PARSE", "FORMALIZE_FROM_SPEC", "REPAIR", "PARAPHRASE")}
    prompts.use_version("v2")
    assert "plain words" in prompts.PARSE and "except the start city" in prompts.PARSE
    assert "follow the problem text" in prompts.FORMALIZE_FROM_SPEC
    assert "infeasible" in prompts.REPAIR and "{note}" in prompts.REPAIR
    assert prompts.PARAPHRASE == v1["PARAPHRASE"]  # the paraphraser is not part of v2
    prompts.use_version("v1")
    assert {name: getattr(prompts, name) for name in v1} == v1


def test_v2_templates_format_like_v1():
    prompts.use_version("v2")  # the same placeholders as v1, so formatting works the same way
    assert "Q" in prompts.PARSE.format(question="Q")
    prompts.FORMALIZE_FROM_SPEC.format(question="Q", spec="{}")
    prompts.REPAIR.format(question="Q", code="c", error="infeasible", note="")


def test_an_unknown_version_is_refused():
    with pytest.raises(ValueError, match="unknown prompt version"):
        prompts.use_version("v3")
