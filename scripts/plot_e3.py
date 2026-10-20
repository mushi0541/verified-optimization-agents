"""E3 plots (Gap 3) from saved results only: the accuracy-cost curve and the risk-coverage curve at k = 3.

- Accuracy-cost: reads accuracy_cost.csv written by `analyze_e3.py --out`. Mean tokens per problem against accuracy,
  with one line for the pipeline at k = 1, 2, 3, one for B2 at the same budgets, and B0 and B1 as single points.
- Risk-coverage at k = 3: reads the same record files as analyze_e3.py and, on the problems both systems share,
  plots the wrong-accept rate when the top share of problems by score is answered (exact mean over tie-breaks),
  with a dashed line at the 50% coverage used for H3.

Each figure is saved as PDF (for the LaTeX report) and PNG (for the README). No titles are drawn; captions go in the report.

Example:
    python scripts/plot_e3.py --curve results/e3/accuracy_cost.csv --pipeline results/pipeline_.../records.jsonl \\
        --b2 results/b2_.../records.jsonl --out results/e3
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no screen needed (the CI check runs on Linux)
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.analyze_e3 import LEVELS, b2_at, load_records, pipeline_at, wrong_accept_at_coverage  # noqa: E402

COVERAGES = [round(0.05 * step, 2) for step in range(1, 21)]
H3_COVERAGE = 0.5
LINE_STYLES = {"pipeline": ("Pipeline", "o", "tab:blue"), "b2": ("B2 (single agent)", "s", "tab:orange")}
LABEL_OFFSETS = {"pipeline": (4, 6), "b2": (4, -12)}  # k labels above the pipeline line, below the B2 line
POINT_STYLES = {"B0": ("B0", "^", "tab:gray"), "B1": ("B1", "v", "black")}


def main() -> None:
    parser = argparse.ArgumentParser(description="E3 plots: accuracy-cost and risk-coverage curves (no API calls).")
    parser.add_argument("--curve", required=True, help="accuracy_cost.csv written by analyze_e3.py --out")
    parser.add_argument("--pipeline", nargs="+", required=True, help="records.jsonl of pipeline runs with k = 3")
    parser.add_argument("--b2", nargs="+", required=True, help="records.jsonl of B2 runs")
    parser.add_argument("--out", required=True, help="folder for the PDF and PNG files")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = plot_accuracy_cost(read_curve(Path(args.curve)), out_dir)
    curves = risk_coverage_curves(load_records(args.pipeline), load_records(args.b2))
    written += plot_risk_coverage(curves, out_dir)[1]
    for path in written:
        print(path)


def read_curve(path: Path) -> list[dict]:
    """Rows of accuracy_cost.csv; B0 and B1 have no k, and missing costs stay None."""
    with path.open(encoding="utf-8", newline="") as file:
        return [
            {
                "system": row["system"],
                "k": int(row["k"]) if row["k"] else None,
                "mean_tokens": float(row["mean_tokens"]) if row["mean_tokens"] else None,
                "accuracy": float(row["accuracy"]),
            }
            for row in csv.DictReader(file)
        ]


def risk_coverage_curves(pipeline: dict[str, dict], b2: dict[str, dict], k: int = LEVELS[-1]) -> dict[str, list]:
    """Wrong-accept rate at each coverage for both systems at level k, on the problems they share.

    The B2 budget is the pipeline's mean tokens at k, the same rule as analyze_e3.analyze().
    """
    ids = sorted(set(pipeline) & set(b2))
    if not ids:
        raise ValueError("the pipeline and B2 records share no problems")
    pipe = [pipeline_at(pipeline[i], k) for i in ids]
    budget = sum(outcome["tokens"] for outcome in pipe) / len(pipe)
    single = [b2_at(b2[i], budget) for i in ids]
    return {
        name: [wrong_accept_at_coverage(outcomes, coverage, draws=0, rng=None)["wrong_accept_rate"] for coverage in COVERAGES]
        for name, outcomes in (("pipeline", pipe), ("b2", single))
    }


def plot_accuracy_cost(rows: list[dict], out_dir: Path) -> list[Path]:
    figure, axes = plt.subplots(figsize=(5, 3.5))
    for system, (label, marker, color) in LINE_STYLES.items():
        points = sorted((row for row in rows if row["system"] == system), key=lambda row: row["k"])
        if not points:
            continue
        x, y = [row["mean_tokens"] for row in points], [row["accuracy"] for row in points]
        axes.plot(x, y, marker=marker, color=color, label=label)
        levels_at: dict[tuple, list] = {}  # levels that land on the same point share one label
        for row in points:
            levels_at.setdefault((row["mean_tokens"], row["accuracy"]), []).append(str(row["k"]))
        for point, levels in levels_at.items():
            axes.annotate(
                "k = " + ", ".join(levels), point, textcoords="offset points",
                xytext=LABEL_OFFSETS[system], fontsize=8, color=color,
            )
    for row in rows:
        if row["system"] in POINT_STYLES and row["mean_tokens"] is not None:
            label, marker, color = POINT_STYLES[row["system"]]
            axes.scatter(row["mean_tokens"], row["accuracy"], marker=marker, color=color, label=label, zorder=3)
    axes.set_xlabel("Mean tokens per problem (input + output)")
    axes.set_ylabel("Accuracy (share of problems correct)")
    axes.set_ylim(0, 1.02)
    axes.grid(alpha=0.3)
    axes.legend(fontsize=8)
    return _save(figure, out_dir, "accuracy_cost")


def plot_risk_coverage(curves: dict[str, list], out_dir: Path, k: int = LEVELS[-1]):
    """Returns the figure (so tests can read the plotted values) and the files written."""
    figure, axes = plt.subplots(figsize=(5, 3.5))
    for system, (label, marker, color) in LINE_STYLES.items():
        rates = [float("nan") if rate is None else rate for rate in curves[system]]
        axes.plot(COVERAGES, rates, marker=marker, markersize=3, color=color, label=f"{label}, k = {k}")
    axes.axvline(H3_COVERAGE, linestyle="--", color="gray", linewidth=1, label="50% coverage (H3)")
    axes.set_xlabel("Coverage (share of all problems answered)")
    axes.set_ylabel("Wrong-accept rate (share)")
    axes.set_xlim(0, 1.02)
    axes.set_ylim(bottom=0)
    axes.grid(alpha=0.3)
    axes.legend(fontsize=8)
    return figure, _save(figure, out_dir, f"risk_coverage_k{k}")


def _save(figure, out_dir: Path, name: str) -> list[Path]:
    figure.tight_layout()
    paths = [out_dir / f"{name}.pdf", out_dir / f"{name}.png"]
    for path in paths:
        figure.savefig(path, dpi=200)
    plt.close(figure)
    return paths


if __name__ == "__main__":
    main()
