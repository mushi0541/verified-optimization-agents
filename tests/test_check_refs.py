"""Tests for scripts/check_refs.py reference validation."""

import pytest
from scripts.check_refs import (
    check_entries,
    cross_reference,
    extract_citations,
    parse_bibtex,
    validate_references,
)

SAMPLE_BIB = """
@article{vaswani2017attention,
  author    = {Vaswani, Ashish and others},
  title     = {Attention is All You Need},
  journal   = {Adv. Neural Inf. Process. Syst.},
  volume    = {30},
  year      = {2017},
  doi       = {10.5555/3295222.3295349},
  url       = {https://arxiv.org/abs/1706.03762}
}

@inproceedings{wang2023selfconsistency,
  author    = {Wang, Xuezhi and others},
  title     = {Self-Consistency Improves Chain of Thought Reasoning in Language Models},
  booktitle = {Proc. 11th Int. Conf. Learn. Represent. (ICLR)},
  year      = {2023},
  url       = {https://arxiv.org/abs/2203.11171}
}
"""

SAMPLE_TEX = r"""
\documentclass{article}
\begin{document}
Transformer architecture \cite{vaswani2017attention} enables self-consistency \cite{wang2023selfconsistency}.
\end{document}
"""


def test_parse_bibtex_extracts_fields():
    entries = parse_bibtex(SAMPLE_BIB)
    assert len(entries) == 2
    assert "vaswani2017attention" in entries
    assert "wang2023selfconsistency" in entries
    v = entries["vaswani2017attention"]
    assert v["_type"] == "article"
    assert v["year"] == "2017"
    assert v["doi"] == "10.5555/3295222.3295349"
    assert v["url"] == "https://arxiv.org/abs/1706.03762"


def test_extract_citations_from_latex():
    tex = r"We use \cite{refA} and multiple \cite{refB, refC} and \citep{refD}."
    cites = extract_citations(tex)
    assert cites == {"refA", "refB", "refC", "refD"}


def test_check_entries_detects_missing_links_and_fields():
    bad_bib = """
@misc{nolink2024,
  author = {Smith, John},
  title  = {A Paper Without A Link},
  year   = {2024}
}

@misc{notitle2024,
  author = {Doe, Jane},
  year   = {2024},
  url    = {https://example.com}
}
"""
    entries = parse_bibtex(bad_bib)
    errors = check_entries(entries, min_entries=2)
    assert any("neither DOI nor URL" in e and "nolink2024" in e for e in errors)
    assert any("missing required field 'title'" in e and "notitle2024" in e for e in errors)


def test_cross_reference_detects_mismatches():
    bib_keys = {"alpha", "beta", "gamma"}
    tex_cites = {"beta", "delta"}
    uncited, missing = cross_reference(bib_keys, tex_cites)
    assert uncited == {"alpha", "gamma"}
    assert missing == {"delta"}


def test_validate_references_end_to_end(tmp_path):
    bib_file = tmp_path / "refs.bib"
    tex_file = tmp_path / "main.tex"

    bib_file.write_text(SAMPLE_BIB, encoding="utf-8")
    tex_file.write_text(SAMPLE_TEX, encoding="utf-8")

    valid, messages = validate_references(bib_file, tex_file, min_entries=2)
    assert valid is True
    assert any("verified and cited" in m for m in messages)

    # Fail when min_entries is higher than available
    valid_high, msgs_high = validate_references(bib_file, tex_file, min_entries=10)
    assert valid_high is False
    assert any("at least 10 are required" in m for m in msgs_high)

    # Fail when a citation is uncited in LaTeX
    tex_file.write_text(r"\cite{vaswani2017attention}", encoding="utf-8")
    valid_uncited, msgs_uncited = validate_references(bib_file, tex_file, min_entries=2)
    assert valid_uncited is False
    assert any("not cited in LaTeX" in m for m in msgs_uncited)
