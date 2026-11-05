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


def test_the_gap3_table_has_each_level_and_the_reference_points(tmp_path):
    results = tmp_path / "results"
    level = {"k": 3, "pipeline": {"mean_tokens": 20783.2, "accuracy": 0.78, "wrong_accept_rate": 0.06},
             "b2": {"mean_tokens": 20881.48, "accuracy": 0.805, "wrong_accept_rate": 0.06398},
             "paired": {"mcnemar_p": 0.3017, "wrong_accept_difference_ci": [-0.0502, 0.0430]}}
    _write(results / "gap3" / "canonical_200" / "e3.json", {
        "problems": 200, "settings": {"coverage": 0.5}, "levels": [level],
        "h3": {"k": 3, "supported": False},
        "reference_points": {"B0": {"mean_tokens": 2555.13, "accuracy": 0.77}}})
    make_tables(results, tmp_path / "tables")
    text = (tmp_path / "tables" / "gap3.tex").read_text(encoding="utf-8")
    assert "$k=3$ & 20,783 / 20,881 & 78.0 / 80.5 & 0.30 & 6.0 / 6.4 & [-5.0, +4.3] \\\\" in text
    assert "B0 & 2,555 & 77.0 & -- & -- & -- \\\\" in text
    assert "H3 at $k=3$: not supported" in text


def test_an_ablation_rate_from_fewer_than_two_repeats_is_marked(tmp_path):
    path = tmp_path / "results" / "ablations" / "ablations.csv"
    path.parent.mkdir(parents=True)
    columns = ["accuracy", "coverage", "wrong_accept_rate", "auroc", "mean_tokens", "mean_calls"]
    header = ["ablation", *columns, "repeats", *(f"{c}_std" for c in columns)]
    rows = [["(vi) Calibrated", "0.82", "0.0333", "0.2", "0.9126", "21381.4", "8.2", "3",
             "0.02", "0.0577", "", "0.07", "593.7", "0.15"],
            ["(iv) Without the parser", "0.82", "0.84", "0.0476", "0.9336", "16594.1", "7.5", "1", "", "", "", "", "", ""]]
    path.write_text("\n".join(",".join(row) for row in [header, *rows]) + "\n", encoding="utf-8")
    make_tables(tmp_path / "results", tmp_path / "tables")
    text = (tmp_path / "tables" / "ablations.tex").read_text(encoding="utf-8")
    assert r"(vi) Calibrated & 3 & 82.0 $\pm$ 2.0 & 3.3 $\pm$ 5.8 & 20.0$^\dagger$ & 0.91 $\pm$ 0.07" in text
    assert "(iv) Without the parser & 1 & 82.0 & 84.0 & 4.8 & 0.93 & 16,594 \\\\" in text  # one repeat: no sd, no mark
    assert r"$^\dagger$ from fewer than two of the repeats" in text


def test_the_efficiency_table_has_a_row_per_model_and_system(tmp_path):
    def group(system, model, runs, tokens, cost):
        metrics = {name: _stat(value) for name, value in {
            "mean_input_tokens": tokens / 2, "mean_output_tokens": tokens / 2, "mean_llm_calls": 8.25,
            "mean_solver_calls": 4.2, "mean_latency_s": 91.7, "mean_cost_usd": cost, "failed_run_rate": 0.0,
            "solver_error_rate": 0.038, "repair_success_rate": None}.items()}
        return {"configuration": f"{system} | {model} | bedrock us-east-1 | canonical_200 | 200 problems [abc123]",
                "runs": ["run"] * runs, "metrics": metrics}

    _write(tmp_path / "results" / "e6" / "canonical_200" / "efficiency.json", {
        "price_source": "Amazon Bedrock on-demand, us-east-1",
        "prices_usd_per_million_tokens": {"openai.gpt-oss-120b-1:0": {"date": "2026-10-20"}},
        "configurations": [group("pipeline_p3", "openai.gpt-oss-120b-1:0", 3, 21274.0, 0.00877),
                           group("baseline_r1", "openai.gpt-oss-120b-1:0", 1, 2664.0, 0.00119),
                           group("baseline_r1", "openai.gpt-oss-20b-1:0", 1, 4271.0, None)]})
    make_tables(tmp_path / "results", tmp_path / "tables")
    lines = [line for line in (tmp_path / "tables" / "efficiency.tex").read_text(encoding="utf-8").splitlines()
             if " & " in line and not line.startswith("Model")]
    assert lines[0].startswith("gpt-oss-120b & B1 & 1 & 2,664 &")  # B1 before the pipeline; readable model names
    assert lines[1].startswith(" & Pipeline & 3 & 21,274 & 8.2 & 4.2 & 92 & 8.77 & 0.0 & 3.8 & -- ")
    assert lines[2].startswith("gpt-oss-20b & B1 & 1 & 4,271 &") and " & -- & 0.0 & " in lines[2]
    text = (tmp_path / "tables" / "efficiency.tex").read_text(encoding="utf-8")
    assert "-- where the model has no listed price" in text
    assert "B0 was run for" not in text  # no model has a B0 run here


def test_the_preregistered_table_applies_the_h3c_rule(tmp_path):
    base = tmp_path / "results" / "preregistered"
    level = {"k": 3, "pipeline": {"accuracy": 0.685, "wrong_accept_rate": 0.03},
             "b2": {"accuracy": 0.805, "wrong_accept_rate": 0.0333}}
    _write(base / "h1" / "canonical_200_qwen" / "gap1.json", {"summary": {
        "auroc": {"combined": _stat(0.928)}, "gain": _stat(0.0751), "h1": "not supported (the gain is below 0.10)"}})
    _write(base / "h3" / "canonical_200_qwen" / "e3.json", {
        "problems": 200, "levels": [level], "h3": {"k": 3, "wrong_accept_difference_ci": [-0.0325, 0.034], "supported": False}})
    _write(base / "h3c" / "canonical_200_qwen" / "combination.json", {
        "problems": 200, "paired": {"pipeline k=1 + B2 minus B2": {"0.5": [-0.04, -0.001]}}})
    _write(base / "h3" / "held_out_1457" / "e3.json", {
        "problems": 1457, "levels": [level], "h3": {"k": 3, "wrong_accept_difference_ci": [0.016, 0.044], "supported": False}})
    make_tables(tmp_path / "results", tmp_path / "tables")
    rows = [line for line in (tmp_path / "tables" / "preregistered.tex").read_text(encoding="utf-8").splitlines()
            if line.startswith(("\\texttt", "all held out"))]
    # three digits for the gain, and H3c is "yes" because the upper end of its interval is below 0
    assert rows[0] == ("\\texttt{canonical\\_200} & Qwen3 Next 80B & 200 & 0.928 & +0.075 & no & 68.5 / 80.5 & "
                       "3.0 / 3.3 & [-3.2, +3.4] & no & [-4.0, -0.1] & yes \\\\")
    assert rows[1] == "all held out & gpt-oss-120b & 1,457 & -- & -- & -- & 68.5 / 80.5 & 3.0 / 3.3 & [+1.6, +4.4] & no & -- & -- \\\\"
