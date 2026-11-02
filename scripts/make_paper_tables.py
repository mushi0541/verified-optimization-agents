"""#44: write the paper's result tables (docs/paper/tables/*.tex) from the analysis files in results/ (no API calls).

    python scripts/make_paper_tables.py [--results results] [--out docs/paper/tables]

Each table is built only from files that the analysis scripts wrote, so no number in it is typed by hand:
- baselines.tex from results/e1_e2/e1_e2.json (scripts/compare_baselines.py): B0 and B1 per class, mean and sample
  standard deviation over the repeats, next to the base paper's reported SIR accuracy;
- gap1.tex from results/gap1/<sample>/gap1.json (scripts/analyze_gap1.py): AUROC of each signal and of the combined
  score, the gain over feasibility and the H1 verdict, per sample;
- gap2.tex from results/gap2/<sample>/gap2.json (scripts/analyze_gap2.py): coverage and wrong-accept rate at the H2
  alpha and at the fixed threshold, the smallest alpha the data supports and the H2 verdict, per sample;
- gap3.tex from results/gap3/canonical_200/e3.json (scripts/analyze_e3.py): the pipeline against B2 at an equal
  token budget for each k, with the paired interval and the H3 verdict, and B0 and B1 as reference points;
- ablations.tex from results/ablations/ablations.csv (scripts/ablation_table.py): each ablation on ablation_50.

A table whose input files are missing is not written, so main.tex shows its \\generated note instead; the script says
which tables it wrote and which it skipped. Rows follow fixed lists of samples, so the output does not depend on the
order of files on disk.
"""

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# (folder in results/gap1 or results/gap2, label in the table); rows appear in this order when their folder exists.
GAP1_SAMPLES = (
    ("canonical_200", r"\texttt{canonical\_200}"),
    ("canonical_587", r"\texttt{canonical\_587}"),
    ("constraint_pairs_60", r"Constraint pairs"),
    ("linguistic_60", r"Linguistic"),
)
GAP2_SAMPLES = (
    ("canonical_200", r"\texttt{canonical\_200}", "all"),
    ("canonical_200_without_pollution", r"\texttt{canonical\_200}", "no Pollution"),
    ("canonical_587", r"\texttt{canonical\_587}", "all"),
    ("canonical_587_without_pollution", r"\texttt{canonical\_587}", "no Pollution"),
)
SIGNALS = ("feasibility", "number", "requirement", "paraphrase", "combined")
DASH = "--"


def percent(value: float | None, sd: float | None = None) -> str:
    """A rate as a percentage with one decimal, with its standard deviation when there is one."""
    if value is None:
        return DASH
    return f"{100 * value:.1f}" + (f" $\\pm$ {100 * sd:.1f}" if sd is not None else "")


def mean_cell(stat: dict, repeats: int) -> str:
    """A rate's mean over the repeats (with its sd when two or more have a value), marked "(k/n)" when only k of the n
    repeats have a value, for example a wrong-accept rate when a repeat answered nothing."""
    with_value = stat["repeats_with_value"]
    text = percent(stat["mean"], stat["sd"] if with_value > 1 else None)
    return text if with_value in (0, repeats) else f"{text} ({with_value}/{repeats})"


def number(value: float | None, sd: float | None = None, digits: int = 3, sign: bool = False) -> str:
    if value is None:
        return DASH
    text = f"{value:+.{digits}f}" if sign else f"{value:.{digits}f}"
    return text + (f" $\\pm$ {sd:.{digits}f}" if sd is not None else "")


def tex(text: str) -> str:
    """Text safe for LaTeX (model names and the like)."""
    for char in "\\&%$#_{}":
        text = text.replace(char, "\\" + char)
    return text


def verdict(text: str) -> str:
    """The short form of an H1 or H2 verdict: the words before any explanation in brackets."""
    return text.split(" (")[0]


def table(caption: str, label: str, columns: str, header: list[str], rows: list[list[str]], sources: list[str],
          wide: bool = False) -> str:
    env = "table*" if wide else "table"
    lines = [
        f"% Written by scripts/make_paper_tables.py from {', '.join(sources)}. Do not edit by hand.",
        f"\\begin{{{env}}}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\footnotesize",
        f"\\begin{{tabular}}{{@{{}}{columns}@{{}}}}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
        *(" & ".join(row) + " \\\\" for row in rows),
        "\\bottomrule",
        "\\end{tabular}",
        f"\\end{{{env}}}",
    ]
    return "\n".join(lines) + "\n"


def read(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def baselines(results: Path) -> tuple[str, list[str]] | None:
    """The main model's B0 and B1 (the block with a repair round) and, when there is one, a B0-only reference model
    (the base paper's DeepSeek-V3.2), next to the paper's reported SIR accuracy."""
    data = read(results / "e1_e2" / "e1_e2.json")
    main = next((b for b in data["models"] if b["with_repair"]), None) if data else None
    if main is None:
        return None
    reference = next((b for b in data["models"] if not b["with_repair"]), None)

    def accuracy(entry: dict | None, system: str) -> str:
        stat = (entry or {}).get(system, {}).get("accuracy", {})
        return percent(stat.get("mean"), stat.get("sd"))

    header = ["Class", "B0", "B1"] + ([f"B0, {tex(reference['model'])}"] if reference else []) + ["SIR, reported"]
    rows = []
    for name, entry in main["classes"].items():
        other = [accuracy(reference["classes"].get(name), "B0")] if reference else []
        rows.append([name, accuracy(entry, "B0"), accuracy(entry, "B1"), *other,
                     percent(entry.get("reported", {}).get("accuracy"))])
    other = [accuracy(reference["overall"], "B0")] if reference else []
    rows.append(["All classes", accuracy(main["overall"], "B0"), accuracy(main["overall"], "B1"), *other, DASH])
    repeats = f"{main['repeats']} repeat" + ("s" if main["repeats"] != 1 else "")
    caption = (f"Accuracy (\\%, 0.2\\% rule) of the baselines ({tex(main['model'])}) on \\texttt{{canonical\\_200}}, "
               f"{repeats}, mean $\\pm$ sd where there are two or more")
    sources = ["results/e1_e2/e1_e2.json"]
    return table(caption, "tab:baselines", "l" + "r" * (len(header) - 1), header, rows, sources), sources


def gap1(results: Path) -> tuple[str, list[str]] | None:
    rows, sources = [], []
    for folder, label in GAP1_SAMPLES:
        data = read(results / "gap1" / folder / "gap1.json")
        if data is None:
            continue
        summary, repeats = data["summary"], len(data["runs"])
        sd = (lambda stat: stat["sd"]) if repeats > 1 else (lambda stat: None)
        aurocs = [number(summary["auroc"][s]["mean"], sd(summary["auroc"][s]), 2) for s in SIGNALS]
        gain = summary["gain"]
        rows.append([label, str(repeats), *aurocs, number(gain["mean"], sd(gain), 2, sign=True), verdict(summary["h1"])])
        sources.append(f"results/gap1/{folder}/gap1.json")
    if not rows:
        return None
    header = ["Sample", "Rep.", "Feas.", "Number", "Req.", "Para.", "Combined", "Gain", "H1"]
    caption = ("AUROC of each signal and of the combined score for separating correct from wrong answers, "
               "mean $\\pm$ sd over the repeats")
    return table(caption, "tab:gap1", "lr" + "r" * 6 + "l", header, rows, sources, wide=True), sources


def smallest_alpha(runs: list[dict], key: str) -> str:
    values = [run["alpha_scan"][key] for run in runs if run.get("alpha_scan")]
    if not values:
        return DASH
    if any(v is None for v in values):
        return "none" if all(v is None for v in values) else "some none"
    low, high = min(values), max(values)
    return f"{100 * low:.0f}" if low == high else f"{100 * low:.0f}--{100 * high:.0f}"


def gap2(results: Path) -> tuple[str, list[str]] | None:
    rows, sources, alphas = [], [], set()
    for folder, label, classes in GAP2_SAMPLES:
        data = read(results / "gap2" / folder / "gap2.json")
        if data is None:
            continue
        runs, summary = data["runs"], data["summary"]
        h2_alpha = data["settings"]["h2_alpha"]
        alphas.add(h2_alpha)
        at_alpha = summary["by_alpha"][f"{h2_alpha:g}"]
        fixed = summary["fixed"]
        rows.append([
            label, classes, str(len(runs)),
            mean_cell(at_alpha["coverage"], len(runs)),
            mean_cell(at_alpha["wrong_accept_rate"], len(runs)),
            mean_cell(fixed["coverage"], len(runs)),
            mean_cell(fixed["wrong_accept_rate"], len(runs)),
            smallest_alpha(runs, "smallest_alpha_meeting_h2_rule"),
            smallest_alpha(runs, "smallest_alpha_meeting_the_bound_too"),
            verdict(summary["h2"]) if classes == "all" else "(sensitivity)",
        ])
        sources.append(f"results/gap2/{folder}/gap2.json")
    if not rows:
        return None
    if len(alphas) != 1:
        raise SystemExit(f"the Gap 2 files use different H2 alphas: {sorted(alphas)}")
    alpha = f"{100 * alphas.pop():g}"
    header = ["Sample", "Classes", "Rep.", f"Cov. ($\\alpha$={alpha}\\%)", "WAR", "Cov. (0.8)", "WAR",
              "Min.\\ $\\alpha$", "+ bound", "H2"]
    caption = ("Calibrated abstention tested leave-one-class-out: coverage and wrong-accept rate (WAR, \\%) at the H2 "
               "alpha and at the fixed threshold 0.8, and the smallest alpha (\\%) that meets H2's rule, without and "
               "with the one-sided bound; ``no Pollution'' is the sensitivity analysis, not the H2 result")
    return table(caption, "tab:gap2", "llr" + "r" * 6 + "l", header, rows, sources, wide=True), sources


def gap3(results: Path) -> tuple[str, list[str]] | None:
    """The pipeline against B2 at each paraphrase level k (B2 held to the pipeline's tokens at that k), with B0 and
    B1 as cheap reference points."""
    source = "results/gap3/canonical_200/e3.json"
    data = read(results / "gap3" / "canonical_200" / "e3.json")
    if data is None:
        return None
    coverage = f"{100 * data['settings']['coverage']:g}"
    rows = []
    for level in data["levels"]:
        pipe, single, paired = level["pipeline"], level["b2"], level["paired"]
        low, high = paired["wrong_accept_difference_ci"]
        rows.append([f"$k={level['k']}$", f"{pipe['mean_tokens']:,.0f} / {single['mean_tokens']:,.0f}",
                     f"{percent(pipe['accuracy'])} / {percent(single['accuracy'])}", f"{paired['mcnemar_p']:.2f}",
                     f"{percent(pipe['wrong_accept_rate'])} / {percent(single['wrong_accept_rate'])}",
                     f"[{100 * low:+.1f}, {100 * high:+.1f}]"])
    for name, point in data["reference_points"].items():
        rows.append([name, f"{point['mean_tokens']:,.0f}", percent(point["accuracy"]), DASH, DASH, DASH])
    h3 = data["h3"]
    header = ["", "Tokens, pipeline / B2", "Accuracy", "McNemar $p$", f"WAR at {coverage}\\% cov.",
              "WAR difference, 95\\% CI"]
    caption = (f"The pipeline against B2 at an equal token budget on \\texttt{{canonical\\_200}} ({data['problems']} "
               f"problems): accuracy, and wrong-accept rate (WAR, \\%) when each answers {coverage}\\% of the problems, "
               f"with the paired interval of pipeline minus B2 (points); B0 and B1 are reference points. "
               f"H3 at $k={h3['k']}$: {'supported' if h3['supported'] else 'not supported'}")
    return table(caption, "tab:gap3", "lrrrrr", header, rows, [source], wide=True), [source]


def ablations(results: Path) -> tuple[str, list[str]] | None:
    """Each ablation on ablation_50 at the fixed threshold. A rate with no sd although there are several repeats had a
    value in fewer than two of them, and is marked with a dagger."""
    source = "results/ablations/ablations.csv"
    path = results / "ablations" / "ablations.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8", newline="") as handle:
        entries = list(csv.DictReader(handle))
    marked = False

    def cell(entry: dict, key: str, show) -> str:
        nonlocal marked
        if entry[key] == "":
            return DASH
        repeats, sd = int(entry["repeats"]), entry[f"{key}_std"]
        text = show(float(entry[key]), float(sd) if sd and repeats > 1 else None)
        if repeats > 1 and not sd:
            marked = True
            text += "$^\\dagger$"
        return text

    rows = [[tex(entry["ablation"]), entry["repeats"], cell(entry, "accuracy", percent),
             cell(entry, "coverage", percent), cell(entry, "wrong_accept_rate", percent),
             cell(entry, "auroc", lambda v, sd: number(v, sd, 2)),  # two digits, as in gap1.tex
             cell(entry, "mean_tokens", lambda v, sd: f"{v:,.0f}" + (f" $\\pm$ {sd:,.0f}" if sd is not None else ""))]
            for entry in entries]
    header = ["Ablation", "Rep.", "Accuracy", "Coverage", "WAR", "AUROC", "Tokens"]
    caption = ("Ablations on \\texttt{ablation\\_50} at the fixed threshold (\\%, mean $\\pm$ sd over the repeats)"
               + ("; $^\\dagger$ from fewer than two of the repeats" if marked else ""))
    return table(caption, "tab:ablations", "p{5.2cm}rrrrrr", header, rows, [source], wide=True), [source]


BUILDERS = {"baselines.tex": baselines, "gap1.tex": gap1, "gap2.tex": gap2, "gap3.tex": gap3,
            "ablations.tex": ablations}


def make_tables(results: Path, out: Path) -> dict[str, list[str] | None]:
    """Write every table whose inputs exist; returns {file name: its input files, or None when skipped}."""
    written = {}
    for name, builder in BUILDERS.items():
        built = builder(results)
        if built is None:
            written[name] = None
            continue
        text, sources = built
        out.mkdir(parents=True, exist_ok=True)
        (out / name).write_text(text, encoding="utf-8")
        written[name] = sources
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "results")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs" / "paper" / "tables")
    args = parser.parse_args()
    for name, sources in make_tables(args.results, args.out).items():
        print(f"{name}: " + ("skipped, its input files are not in results/" if sources is None
                             else "written from " + ", ".join(sources)))


if __name__ == "__main__":
    sys.exit(main())
