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
- ablations.tex from results/ablations/ablations.csv (scripts/ablation_table.py): each ablation on ablation_50;
- efficiency.tex from results/e6/canonical_200/efficiency.json (scripts/efficiency.py --sample): E6 per model and
  system;
- preregistered.tex from results/preregistered/{h1,h3,h3c} (#103): H1, H3 and H3c per model and held-out sample;
- gap_resolution.tex from the same files: one row per hypothesis with its main-analysis result and verdict.

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
          wide: bool = False, tight: bool = False) -> str:
    """A booktabs table; tight halves the space between columns, for a table with many of them."""
    env = "table*" if wide else "table"
    lines = [
        f"% Written by scripts/make_paper_tables.py from {', '.join(sources)}. Do not edit by hand.",
        f"\\begin{{{env}}}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\footnotesize",
        *(["\\setlength{\\tabcolsep}{3pt}"] if tight else []),
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


SYSTEMS = (("baseline_r0", "B0"), ("baseline_r1", "B1"), ("pipeline_p3", "Pipeline"), ("b2_r1", "B2"))
# Readable names for the Bedrock model IDs, the same names as in the pre-registered table.
MODEL_NAMES = {
    "openai.gpt-oss-120b-1:0": "gpt-oss-120b", "openai.gpt-oss-20b-1:0": "gpt-oss-20b",
    "deepseek.v3.2": "DeepSeek V3.2", "qwen.qwen3-next-80b-a3b": "Qwen3 Next 80B",
    "mistral.mistral-large-3-675b-instruct": "Mistral Large 3", "moonshotai.kimi-k2.5": "Kimi K2.5",
    "zai.glm-4.7": "GLM 4.7",
}


def efficiency(results: Path) -> tuple[str, list[str]] | None:
    """E6 on canonical_200: cost, latency, calls and reliability per model and system, mean over the repeats (only
    gpt-oss-120b's pipeline has more than one). Rows follow the model order of the file, then B0, B1, pipeline, B2."""
    source = "results/e6/canonical_200/efficiency.json"
    data = read(results / "e6" / "canonical_200" / "efficiency.json")
    if data is None:
        return None
    by_model: dict[str, dict[str, dict]] = {}
    for group in data["configurations"]:
        system, model = [part.strip() for part in group["configuration"].split("|")[:2]]
        by_model.setdefault(model, {})[system] = group
    rows, unpriced = [], False
    for model, groups in by_model.items():
        first = True  # the model name only on its first row
        for system, label in SYSTEMS:
            group = groups.get(system)
            if group is None:
                continue
            metric = lambda name: group["metrics"][name]["mean"]  # noqa: E731
            cost = metric("mean_cost_usd")
            unpriced |= cost is None
            tokens = metric("mean_input_tokens") + metric("mean_output_tokens")
            rows.append([tex(MODEL_NAMES.get(model, model)) if first else "", label,
                         str(len(group["runs"])), f"{tokens:,.0f}", f"{metric('mean_llm_calls'):.1f}",
                         f"{metric('mean_solver_calls'):.1f}", f"{metric('mean_latency_s'):.0f}",
                         DASH if cost is None else f"{1000 * cost:.2f}", percent(metric("failed_run_rate")),
                         percent(metric("solver_error_rate")), percent(metric("repair_success_rate"))])
            first = False
    with_b0 = [tex(MODEL_NAMES.get(model, model)) for model, groups in by_model.items() if "baseline_r0" in groups]
    dates = sorted({price["date"] for price in data["prices_usd_per_million_tokens"].values()})
    header = ["Model", "System", "Rep.", "Tokens", "LLM", "Solver", "Time (s)", "US\\$/1k", "Failed", "Sol.\\ err.",
              "Repair"]
    caption = ("Efficiency and reliability on \\texttt{canonical\\_200} per problem, mean over the repeats: tokens, "
               "LLM and solver calls, latency, cost in US\\$ per 1,000 problems (" + tex(data["price_source"])
               + " prices read on " + ", ".join(dates) + "), and the failed-run, solver-error and repair-success "
               "rates (\\%)" + ("; -- where the model has no listed price" if unpriced else "")
               + (f". B0 was run for {', '.join(with_b0)} only" if with_b0 else "")
               + ". B2 is shown as run, with a budget of 1.25 times the pipeline's mean tokens for the models "
               "added in \\#103; the H3 tests hold it to the pipeline's tokens")
    return table(caption, "tab:efficiency", "llrrrrrrrrr", header, rows, [source], wide=True), [source]


# (folder in results/preregistered/{h1,h3,h3c}, data label, model label); rows appear in this order when they exist.
PREREGISTERED = (
    # The first tests of #103: H3c on the 387 new problems (primary) and H3 on all of canonical_587 (secondary).
    ("canonical_587_rest_387", "387 new", "gpt-oss-120b"),  # explained in the caption
    ("canonical_587", r"\texttt{canonical\_587}", "gpt-oss-120b"),
    ("canonical_200_deepseek", r"\texttt{canonical\_200}", "DeepSeek V3.2"),
    ("canonical_200_qwen", r"\texttt{canonical\_200}", "Qwen3 Next 80B"),
    ("canonical_200_mistral", r"\texttt{canonical\_200}", "Mistral Large 3"),
    ("canonical_200_kimi", r"\texttt{canonical\_200}", "Kimi K2.5"),
    ("canonical_200_glm", r"\texttt{canonical\_200}", "GLM 4.7"),
    ("canonical_200_gpt-oss-20b", r"\texttt{canonical\_200}", "gpt-oss-20b"),
    ("canonical_unused", r"\texttt{canonical\_unused}", "gpt-oss-120b"),
    ("held_out_1457", "all held out", "gpt-oss-120b"),
)
SHORT_VERDICT = {"supported": "yes", "partly supported": "partly", "not supported": "no"}  # for a narrow column
H3C_COMPARISON = "pipeline k=1 + B2 minus B2"  # the primary test of docs/preregistration_combination.md


def interval(low_high: list[float]) -> str:
    low, high = low_high
    return f"[{100 * low:+.1f}, {100 * high:+.1f}]"


def sensitivity_changes(base: Path) -> list[str]:
    """The verdicts that change in the sensitivity analysis of Addendum 3 (without Pollution and the reference_wrong
    problem): h3/<folder>_sensitivity, and for H3c the _sensitivity folder or, where no reference_wrong problem is in
    the sample, the _without_pollution one."""
    changes = []
    for folder, data_label, model in PREREGISTERED:
        main, sens = read(base / "h3" / folder / "e3.json"), read(base / "h3" / f"{folder}_sensitivity" / "e3.json")
        if main and sens and main["h3"]["supported"] != sens["h3"]["supported"]:
            changes.append(f"H3 for {model} on {data_label}, now " + interval(sens["h3"]["wrong_accept_difference_ci"]))
        main = read(base / "h3c" / folder / "combination.json")
        sens = read(base / "h3c" / f"{folder}_sensitivity" / "combination.json") or read(
            base / "h3c" / f"{folder}_without_pollution" / "combination.json")
        if main and sens and (main["paired"][H3C_COMPARISON]["0.5"][1] < 0) != (sens["paired"][H3C_COMPARISON]["0.5"][1] < 0):
            changes.append(f"H3c for {model} on {data_label}, now " + interval(sens["paired"][H3C_COMPARISON]["0.5"]))
    return changes


def preregistered(results: Path) -> tuple[str, list[str]] | None:
    """The pre-registered tests of #103 (main analysis, not the sensitivity folders): H1 per model, H3 (pipeline
    against B2 at k = 3) and H3c (the pipeline combined with B2, against B2). H3c is supported only when the upper end
    of its paired interval at 50% coverage is below 0, the rule fixed in docs/preregistration_combination.md."""
    rows, sources = [], []
    for folder, data_label, model in PREREGISTERED:
        base = results / "preregistered"
        h1, h3 = read(base / "h1" / folder / "gap1.json"), read(base / "h3" / folder / "e3.json")
        h3c = read(base / "h3c" / folder / "combination.json")
        if h1 is None and h3 is None and h3c is None:
            continue
        problems = (h3 or h3c or {}).get("problems")
        cells = [data_label, model, DASH if problems is None else f"{problems:,}"]
        if h1:
            summary = h1["summary"]
            # three digits: the H1 rule is a gain of 0.10, and gpt-oss-20b's 0.075 would round to 0.07 or 0.08
            cells += [number(summary["auroc"]["combined"]["mean"], digits=3),
                      number(summary["gain"]["mean"], digits=3, sign=True), SHORT_VERDICT[verdict(summary["h1"])]]
            sources.append(f"results/preregistered/h1/{folder}/gap1.json")
        else:
            cells += [DASH] * 3
        if h3:
            level = next(level for level in h3["levels"] if level["k"] == h3["h3"]["k"])
            cells += [f"{percent(level['pipeline']['accuracy'])} / {percent(level['b2']['accuracy'])}",
                      f"{percent(level['pipeline']['wrong_accept_rate'])} / {percent(level['b2']['wrong_accept_rate'])}",
                      interval(h3["h3"]["wrong_accept_difference_ci"]),
                      "yes" if h3["h3"]["supported"] else "no"]
            sources.append(f"results/preregistered/h3/{folder}/e3.json")
        else:
            cells += [DASH] * 4
        if h3c:
            ci = h3c["paired"][H3C_COMPARISON]["0.5"]
            cells += [interval(ci), "yes" if ci[1] < 0 else "no"]
            sources.append(f"results/preregistered/h3c/{folder}/combination.json")
        else:
            cells += [DASH] * 2
        rows.append(cells)
    if not rows:
        return None
    changes = sensitivity_changes(results / "preregistered")
    header = ["Data", "Model", "Prob.", "AUROC", "Gain", "H1", "Acc., pipe.\\ / B2", "WAR, pipe.\\ / B2",
              "H3 interval", "H3", "H3c interval", "H3c"]
    caption = ("Pre-registered tests (\\#103) on problems and models not used to design the system: H1 (AUROC of the "
               "combined score and its gain over feasibility), H3 (pipeline against B2 at an equal budget, $k=3$) and "
               "H3c (the pipeline at $k=1$ combined with B2, against B2). Accuracy and WAR in \\%; WAR and the "
               "intervals (points, paired 95\\% bootstrap, first minus B2) at 50\\% coverage. Verdicts: yes "
               "(supported), partly (partly supported), no (not supported). 387 new: the problems of "
               "\\texttt{canonical\\_587} outside \\texttt{canonical\\_200}. Main analysis; in the sensitivity "
               "analysis (without Pollution and the one reference\\_wrong problem) "
               + (("the only verdicts that change are " + "; ".join(changes)) if changes else "no verdict changes"))
    return table(caption, "tab:preregistered", "llrrrlrrrlrl", header, rows, sources, wide=True, tight=True), sources


def gap_resolution(results: Path) -> tuple[str, list[str]] | None:
    """One row per hypothesis: what was tested and the verdict, from the same files as the gap tables and the
    pre-registered table (main analysis only). Each test counts the held-out runs that support it."""
    g1 = read(results / "gap1" / "canonical_200" / "gap1.json")
    g2 = {name: read(results / path / "gap2.json") for name, path in (
        ("canonical_200", "gap2/canonical_200"), ("canonical_587", "gap2/canonical_587"),
        ("canonical_unused", "preregistered/h2/canonical_unused"))}
    g3 = read(results / "gap3" / "canonical_200" / "e3.json")
    base = results / "preregistered"
    h1 = [d for folder, _, _ in PREREGISTERED if (d := read(base / "h1" / folder / "gap1.json"))]
    h3 = [d for folder, _, _ in PREREGISTERED if (d := read(base / "h3" / folder / "e3.json"))]
    h3c = [d for folder, _, _ in PREREGISTERED if (d := read(base / "h3c" / folder / "combination.json"))]
    if g1 is None or g3 is None or None in g2.values() or not (h1 and h3 and h3c):
        return None

    def count(items: list[bool]) -> str:
        return f"{sum(items)} of {len(items)}"

    s1 = g1["summary"]
    h1_partly = [verdict(d["summary"]["h1"]) != "not supported" for d in h1]
    alphas = sorted({run["alpha_scan"]["smallest_alpha_meeting_h2_rule"] for d in g2.values() for run in d["runs"]
                     if run.get("alpha_scan")})
    h2_any = [verdict(d["summary"]["h2"]) == "supported" for d in g2.values()]
    low, high = g3["h3"]["wrong_accept_difference_ci"]
    rows = [
        ["1", "H1: AUROC gain $\\ge$ 0.10 over feasibility",
         f"{number(s1['auroc']['feasibility']['mean'], digits=2)} to {number(s1['auroc']['combined']['mean'], digits=2)}; "
         f"partly in {count(h1_partly)} pre-registered runs",
         verdict(s1["h1"])],
        ["2", "H2: WAR $\\le$ 10\\% on unseen classes, half answered",
         f"met in {count(h2_any)} samples; smallest $\\alpha$ met: {100 * alphas[0]:.0f}--{100 * alphas[-1]:.0f}\\%",
         "not supported" if not any(h2_any) else "supported"],
        ["3", "H3: lower WAR than B2 at an equal budget",
         f"[{100 * low:+.1f}, {100 * high:+.1f}] on \\texttt{{canonical\\_200}}; supported in "
         f"{count([d['h3']['supported'] for d in h3])} pre-registered runs",
         "not supported" if not any(d["h3"]["supported"] for d in h3) and not g3["h3"]["supported"] else "partly"],
        ["3", "H3c: the pipeline with B2 beats B2",
         f"supported in {count([d['paired'][H3C_COMPARISON]['0.5'][1] < 0 for d in h3c])} pre-registered runs",
         "not supported" if not any(d["paired"][H3C_COMPARISON]["0.5"][1] < 0 for d in h3c) else "partly"],
    ]
    sources = ["results/gap1/canonical_200/gap1.json", "results/gap2", "results/gap3/canonical_200/e3.json",
               "results/preregistered"]
    caption = ("Gap resolution: each hypothesis, its main-analysis result and verdict (sensitivity results in "
               "Table~\\ref{tab:preregistered})")
    ragged = r">{\raggedright\arraybackslash}p"  # array package: no stretched spaces in narrow columns
    return table(caption, "tab:gap_resolution", f"l{ragged}{{2.55cm}}{ragged}{{3.75cm}}{ragged}{{1.35cm}}",
                 ["Gap", "Hypothesis", "Main-analysis result", "Verdict"], rows, sources, tight=True), sources


BUILDERS = {"baselines.tex": baselines, "gap1.tex": gap1, "gap2.tex": gap2, "gap3.tex": gap3,
            "ablations.tex": ablations, "efficiency.tex": efficiency, "preregistered.tex": preregistered,
            "gap_resolution.tex": gap_resolution}


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
