import json

import pytest

from scripts.analyze_e3 import analyze, b2_at, load_records, pipeline_at, wrong_accept_at_coverage, write_curve
from scripts.plot_e3 import COVERAGES, plot_accuracy_cost, plot_risk_coverage, read_curve, risk_coverage_curves
from tests.test_analyze_e3 import _synthetic_runs


def _write_records(path, records: dict) -> str:
    path.write_text("\n".join(json.dumps(record) for record in records.values()), encoding="utf-8")
    return str(path)


def test_plots_are_written_and_show_the_analysis_values(tmp_path):
    pipeline, b2 = _synthetic_runs()
    pipeline = load_records([_write_records(tmp_path / "pipeline.jsonl", pipeline)])
    b2 = load_records([_write_records(tmp_path / "b2.jsonl", b2)])
    write_curve(analyze(pipeline, b2, bootstrap=20), tmp_path / "accuracy_cost.csv")

    written = plot_accuracy_cost(read_curve(tmp_path / "accuracy_cost.csv"), tmp_path)
    figure, risk_files = plot_risk_coverage(risk_coverage_curves(pipeline, b2), tmp_path)
    names = sorted(path.name for path in written + risk_files)
    assert names == ["accuracy_cost.pdf", "accuracy_cost.png", "risk_coverage_k3.pdf", "risk_coverage_k3.png"]
    assert all(path.stat().st_size > 0 for path in written + risk_files)

    # The plotted value at 50% coverage is the exact tie mean used by the analysis.
    ids = sorted(pipeline)
    pipe = [pipeline_at(pipeline[i], 3) for i in ids]
    single = [b2_at(b2[i], sum(o["tokens"] for o in pipe) / len(pipe)) for i in ids]
    at_half = COVERAGES.index(0.5)
    plotted = {line.get_label(): list(line.get_ydata()) for line in figure.axes[0].lines}
    assert plotted["Pipeline, k = 3"][at_half] == wrong_accept_at_coverage(pipe, 0.5, draws=0, rng=None)["wrong_accept_rate"]
    assert plotted["B2 (single agent), k = 3"][at_half] == pytest.approx(
        wrong_accept_at_coverage(single, 0.5, draws=0, rng=None)["wrong_accept_rate"]
    )


def test_read_curve_keeps_reference_points_without_k(tmp_path):
    path = tmp_path / "accuracy_cost.csv"
    path.write_text(
        "system,k,mean_tokens,mean_calls,accuracy,wrong_accept_rate_at_coverage\n"
        "B0,,2600.0,1.0,0.6,\nB1,,,,0.7,\npipeline,3,17000.0,7.0,0.8,0.05\n",
        encoding="utf-8",
    )
    rows = read_curve(path)
    assert rows[0] == {"system": "B0", "k": None, "mean_tokens": 2600.0, "accuracy": 0.6}
    assert rows[1]["mean_tokens"] is None  # unknown cost: not drawn
    assert rows[2]["k"] == 3
    assert len(plot_accuracy_cost(rows, tmp_path)) == 2


def test_risk_coverage_needs_shared_problems():
    pipeline, b2 = _synthetic_runs()
    with pytest.raises(ValueError, match="share no problems"):
        risk_coverage_curves(pipeline, {"other": b2["q00"]})
