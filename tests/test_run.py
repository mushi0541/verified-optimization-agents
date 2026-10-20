from pathlib import Path

import pytest

from optverify.data import load_sample_file
from optverify.run import _endpoint, parse_args


def test_default_arguments_without_sample_file():
    args = parse_args(["baseline", "--model", "dummy"])
    assert args.sample_file is None
    assert args.per_class == 5
    assert args.seed == 0
    assert args.split == "canonical"


def test_custom_per_class_and_seed_without_sample_file():
    args = parse_args(["baseline", "--model", "dummy", "--per-class", "10", "--seed", "42"])
    assert args.sample_file is None
    assert args.per_class == 10
    assert args.seed == 42


def test_sample_file_accepted_without_per_class_or_seed():
    args = parse_args(["baseline", "--model", "dummy", "--sample-file", "samples/canonical_100.json"])
    assert args.sample_file == Path("samples/canonical_100.json")
    assert args.per_class is None
    assert args.seed is None


def test_sample_file_combined_with_per_class_fails(capsys):
    with pytest.raises(SystemExit):
        parse_args(["baseline", "--model", "dummy", "--sample-file", "samples/canonical_100.json", "--per-class", "5"])
    captured = capsys.readouterr()
    assert "--sample-file cannot be combined with --per-class or --seed" in captured.err


def test_sample_file_combined_with_seed_fails(capsys):
    with pytest.raises(SystemExit):
        parse_args(["baseline", "--model", "dummy", "--sample-file", "samples/canonical_100.json", "--seed", "0"])
    captured = capsys.readouterr()
    assert "--sample-file cannot be combined with --per-class or --seed" in captured.err


def test_sample_file_loads_problems_and_pairs():
    # Canonical sample file loads 100 problems
    canonical_args = parse_args(["baseline", "--model", "dummy", "--sample-file", "samples/canonical_100.json"])
    canonical_probs = load_sample_file(canonical_args.sample_file)
    assert len(canonical_probs) == 100

    # Constraint pairs sample file loads both original and augmented problems (30 pairs -> 60 problems)
    pairs_args = parse_args(["baseline", "--model", "dummy", "--sample-file", "samples/constraint_pairs_30.json"])
    pairs_probs = load_sample_file(pairs_args.sample_file)
    assert len(pairs_probs) == 60


def test_endpoint_records_the_provider_host_only(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://user:secret@api.cerebras.ai/v1")
    assert _endpoint("openai:gpt-oss-120b") == "api.cerebras.ai"  # never the credentials in the URL
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    assert _endpoint("bedrock:openai.gpt-oss-120b-1:0") == "bedrock us-east-1"
