"""Tests for scripts/make_paper_tables.py: the paper's tables come from the analysis files in results/ (#44)."""

import json
from pathlib import Path

from scripts.make_paper_tables import BUILDERS, make_tables, tex

REPO_RESULTS = Path(__file__).resolve().parent.parent / "results"


def _stat(mean, sd=None, with_value=1):
    return {"mean": mean, "sd": sd, "repeats_with_value": with_value}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _baseline_block(model, with_repair, b0, b1=None, sd=None):
    entry = {"B0": {"accuracy": _stat(b0, sd)}, "B1": {"accuracy": _stat(b1, sd)}}
    return {"model": model, "with_repair": with_repair, "repeats": 3,
            "overall": entry, "classes": {"TSP": dict(entry, reported={"accuracy": 0.859})}}


def _gap2(runs_scan, coverage, war, h2="not supported"):
    runs = [{"alpha_scan": {"smallest_alpha_meeting_h2_rule": rule, "smallest_alpha_meeting_the_bound_too": bound}}
            for rule, bound in runs_scan]
    return {"settings": {"h2_alpha": 0.1}, "runs": runs,
            "summary": {"by_alpha": {"0.1": {"coverage": coverage, "wrong_accept_rate": war}},
                        "fixed": {"coverage": _stat(0.83, 0.015, len(runs)),
                                  "wrong_accept_rate": _stat(0.084, 0.005, len(runs))},
                        "h2": h2}}


def test_tables_are_built_from_the_analysis_files(tmp_path):
    results = tmp_path / "results"
    _write(results / "e1_e2" / "e1_e2.json", {"models": [
        _baseline_block("openai.gpt-oss-120b-1:0", True, 0.77, 0.78, sd=0.01),
        _baseline_block("deepseek.v3.2", False, 0.80),
    ]})
    _write(results / "gap1" / "canonical_200" / "gap1.json", {
        "runs": [{}, {}, {}],
        "summary": {"auroc": {s: _stat(0.5 + i / 10, 0.02, 3) for i, s in
                              enumerate(("feasibility", "number", "requirement", "paraphrase", "combined"))},
                    "gain": _stat(0.33, 0.05, 3),
                    "h1": "partly supported (the gain holds, but not every signal is needed)"}})
    _write(results / "gap2" / "canonical_200" / "gap2.json",
           _gap2([(0.18, 0.24), (0.12, 0.26), (0.18, 0.21)], _stat(0.103, 0.154, 3), _stat(0.375, 0.177, 2)))

    written = make_tables(results, tmp_path / "tables")
    assert written["baselines.tex"] == ["results/e1_e2/e1_e2.json"]
    baselines = (tmp_path / "tables" / "baselines.tex").read_text(encoding="utf-8")
    assert "TSP & 77.0 $\\pm$ 1.0 & 78.0 $\\pm$ 1.0 & 80.0 & 85.9 \\\\" in baselines
    assert "All classes & 77.0 $\\pm$ 1.0 & 78.0 $\\pm$ 1.0 & 80.0 & -- \\\\" in baselines
    assert baselines.startswith("% Written by scripts/make_paper_tables.py")

    gap1 = (tmp_path / "tables" / "gap1.tex").read_text(encoding="utf-8")
    assert "\\texttt{canonical\\_200} & 3 & 0.50 $\\pm$ 0.02" in gap1
    assert "+0.33 $\\pm$ 0.05 & partly supported \\\\" in gap1  # the verdict without its explanation

    gap2 = (tmp_path / "tables" / "gap2.tex").read_text(encoding="utf-8")
    # A rate that only some repeats have says so, and the smallest alpha is the range over the repeats.
    assert "& 3 & 10.3 $\\pm$ 15.4 & 37.5 $\\pm$ 17.7 (2/3) & 83.0 $\\pm$ 1.5 & 8.4 $\\pm$ 0.5 & 12--18 & 21--26 & not supported" in gap2


def test_a_table_without_its_files_is_skipped(tmp_path):
    written = make_tables(tmp_path / "results", tmp_path / "tables")
    assert written == {name: None for name in BUILDERS}
    assert not (tmp_path / "tables").exists()  # main.tex then shows its \generated note


def test_a_sensitivity_row_is_never_given_an_h2_verdict(tmp_path):
    results = tmp_path / "results"
    _write(results / "gap2" / "canonical_587_without_pollution" / "gap2.json",
           _gap2([(0.08, 0.16)], _stat(0.939), _stat(0.107), h2="supported"))
    make_tables(results, tmp_path / "tables")
    row = [line for line in (tmp_path / "tables" / "gap2.tex").read_text(encoding="utf-8").splitlines()
           if line.startswith("\\texttt")][0]
    assert row.endswith("& no Pollution & 1 & 93.9 & 10.7 & 83.0 & 8.4 & 8 & 16 & (sensitivity) \\\\")  # no sd for one repeat


def test_the_scripts_run_on_the_committed_results(tmp_path):
    for name, sources in make_tables(REPO_RESULTS, tmp_path).items():
        if sources is not None:
            text = (tmp_path / name).read_text(encoding="utf-8")
            assert "\\begin{table" in text and "\\end{tabular}" in text


def test_text_is_escaped_for_latex():
    assert tex("canonical_200 & 10%") == "canonical\\_200 \\& 10\\%"
