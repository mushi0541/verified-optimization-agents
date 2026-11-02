"""Check the benchmark's reference answers for Pollution and Inventory against the models their questions state.

    python scripts/check_references.py --out results/reference_check [--records results/<run>/records.jsonl ...]

Part of the hand-check of doubtful references (#40). For each problem the script reads the data from the question
text and solves the model the text describes with HiGHS. No LLM is used.

- Pollution: x[i, j] is the share of source i's volume treated by technique j; each source's shares add up to at
  most 1 ("a part may stay untreated"); the cost is cost[i, j] * volume[i] * x[i, j]; the removed amount
  (coefficient * volume * reduction * x) must reach P times the baseline (the sum of coefficient * volume).
- Inventory (lost sales): an order every period between the stated bounds, arriving after the stated lead time;
  holding cost on the stock at the end of each period, a penalty on unmet demand, which is lost. The text leaves
  open when the capacity applies, so both readings are solved: at the end of each period, and also right after a
  delivery arrives.

A reference counts as reproduced when one stated reading gives it within the grading tolerance (0.2%). With
--records, the pipeline's answer on each problem is compared too, so a "wrong" answer that equals the stated model
is visible. Problems whose text the parser cannot read are listed as not checked, never guessed.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import pulp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optverify.data import load_split  # noqa: E402
from optverify.grading import is_correct  # noqa: E402

NUMBER = r"([0-9]+(?:\.[0-9]+)?)"


def parse_pollution(question: str) -> dict | None:
    """Sources (coefficient, volume), reduction rates, the cost matrix and P, read by the structure of the text:
    bullets with two numbers and no percent sign are sources, bullets with a percent sign are techniques, numeric
    table rows are costs."""
    sources, rates, cost = [], [], []
    for line in question.splitlines():
        text = line.strip()
        numbers = re.findall(r"(?<![A-Za-z])[0-9]+(?:\.[0-9]+)?", text)
        if text.startswith("*") and "%" in text:
            rates.append(float(re.search(NUMBER + r"\s*%", text).group(1)) / 100)
        elif text.startswith("*") and len(numbers) >= 2:
            sources.append((float(numbers[-2]), float(numbers[-1])))
        elif text.startswith("|"):
            cells = [c.strip() for c in text.strip("|").split("|")]
            if len(cells) > 1 and all(re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", c) for c in cells[1:]):
                cost.append([float(c) for c in cells[1:]])
    target = re.search(rf"P = {NUMBER}", question)
    if not (sources and rates and target and len(cost) == len(sources) and all(len(row) == len(rates) for row in cost)):
        return None
    return {"sources": sources, "rates": rates, "cost": cost, "P": float(target.group(1))}


def solve_pollution(data: dict) -> float | None:
    model = pulp.LpProblem("pollution", pulp.LpMinimize)
    n, k = len(data["sources"]), len(data["rates"])
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", 0, 1) for i in range(n) for j in range(k)}
    model += pulp.lpSum(data["cost"][i][j] * data["sources"][i][1] * x[i, j] for i, j in x)
    baseline = sum(coefficient * volume for coefficient, volume in data["sources"])
    removed = pulp.lpSum(data["sources"][i][0] * data["sources"][i][1] * data["rates"][j] * x[i, j] for i, j in x)
    model += removed >= data["P"] * baseline
    for i in range(n):
        model += pulp.lpSum(x[i, j] for j in range(k)) <= 1
    model.solve(pulp.HiGHS(msg=False))
    return pulp.value(model.objective) if model.status == 1 else None


def parse_inventory(question: str) -> dict | None:
    """Initial stock, order bounds, capacity, lead time, demand per period and the three costs (order, holding,
    shortage, in the order the text gives them)."""
    text = question.replace("\u2011", "-").replace("\u2013", "-")
    initial = (re.search(rf"(?:initial|starting|opening|beginning)[^.]*?(?:is|of|:|stands at|amounts to|totals)\s*(?:precisely\s*)?{NUMBER}", text, re.I)
               or re.search(rf"(?:initial|starting|opening|beginning)[^.]*?(?:is|of|:|stands at|amounts to|totals)\s*(?:precisely\s*)?zero\b", text, re.I)
               or re.search(rf"(?:initial|starting|opening|beginning)\s+stock[^.]*?\bzero\b", text, re.I)
               or re.search(rf"(?:initial|starting)[^.]*?\bzero\b", text, re.I)
               or re.search(rf"(?:initial|starting|opening|beginning)[^.]*?\b([0-9]+)\b[^.]*?(?:kiloliters|gallons|liters|barrels|units|doses|cases|boxes|vials|megaliters)", text, re.I))
    bounds = (re.search(rf"between {NUMBER} and {NUMBER}", text)
              or re.search(rf"(?:no less than|at least|minimum of) {NUMBER}[^.]*?(?:no more than|at most|maximum of) {NUMBER}", text)
              or re.search(rf"from {NUMBER} to {NUMBER}", text)
              or re.search(rf"(?:bounded between|fall between|constrained to be between|constrained to fall between|must fall between|size must be between|volume must be between|amount requested must be between|order must be between)\s+{NUMBER}\s+(?:and|to)\s+{NUMBER}", text, re.I)
              or re.search(rf"(?:within a range of|within the range of|in the range of)\s+{NUMBER}\s+to\s+{NUMBER}", text, re.I)
              or re.search(rf"(?:no less than|at least|minimum of|no fewer than)\s+{NUMBER}[^.]*?(?:no more than|at most|maximum of|no greater than)\s+{NUMBER}", text, re.I))
    capacity = (re.search(rf"capacity[^.0-9]{{0,40}}?{NUMBER}", text, re.I)
                or re.search(rf"(?:must not exceed|cannot exceed|may not exceed|must not surpass|cannot surpass)[^.0-9]{{0,40}}?{NUMBER}", text)
                or re.search(rf"capacity[^.0-9]{{0,60}}?{NUMBER}", text, re.I)
                or re.search(rf"(?:must not exceed|cannot exceed|may not exceed|must not surpass|cannot surpass|must remain within)[^.0-9]{{0,70}}?{NUMBER}", text, re.I)
                or re.search(rf"(?:can hold at most|can accommodate at most|hold at most|accommodate at most)\s*{NUMBER}", text, re.I)
                or re.search(rf"(?:storage limit|depot limit|facility limit|maximum storage|capacity limit)[^.0-9]{{0,60}}?{NUMBER}", text, re.I))
    units = r"(?:day|week|month|period|hour|leg|shift|quarter|port call|cycle)"
    lead = (re.search(rf"(?:lead time of|lag of|transit time of|delay of|requires(?: an?)?|require(?: an?)?|takes|needs) "
                      rf"{NUMBER}[- ]{units}", text, re.I)
            or re.search(rf"{NUMBER}[- ]{units}s?(?:\(s\))?(?:\s+\w+){{0,3}}?\s+(?:transit|lead|deliver|arriv|ship|delay|transmission)",
                         text, re.I)
            or re.search(rf"(?:lead time of|lag of|transit time of|delay of|requires(?: an?)?|require(?: an?)?|takes|needs?|fixed lead time of|delivery lag of|shipping delay of)\s*{NUMBER}\s*(?:full\s*)?{units}", text, re.I)
            or re.search(rf"(?:transit period of|transit time of|transit delay of|transit duration of|conveyance delay of|pipeline transit period of)\s*{NUMBER}\s*(?:full\s*)?{units}", text, re.I)
            or re.search(rf"{NUMBER}-(?:full\s*)?{units}\s*(?:lead time|lag|transit|delay|delivery|transit time|transit period|transit delay|conveyance delay|pipeline transit period)", text, re.I)
            or re.search(rf"{NUMBER}\s*(?:full\s*)?{units}\s*(?:lead time|lag|transit|delay|delivery|transit time|transit period|of lead time|transit delay|conveyance delay|pipeline transit period)", text, re.I)
            or re.search(rf"requires\s+{NUMBER}\s+{units}\s+to\s+be\s+delivered", text, re.I))
    next_period = re.search(rf"(?:available|arriv\w*|deliver\w*)[^.]*\b(?:subsequent|following|next) {units}\b", text, re.I)
    if lead:
        lead_time = int(float(lead.group(1)))
    elif next_period:
        lead_time = 1  # "available in the subsequent week"
    elif re.search(r"instant|immediately|same (?:day|period)|without delay|no delay|no lead time|no lag", text, re.I):
        lead_time = 0
    elif re.search(r"transit|arriv|lead time|delay|shipping time|deliver(?:ed|y)? after", text, re.I):
        return None  # the text names a delay that could not be read: not checked, never guessed as 0
    else:
        lead_time = 0
    demand = [float(n) for n in re.findall(rf"^\s*[-*] [A-Za-z]+ \d+:[^0-9]*{NUMBER}", text, re.M)]
    if not demand:
        bracket = re.search(rf"demand[^.]*?:?\s*\[([0-9, ]+)\]", text, re.I)
        if bracket:
            demand = [float(x.strip()) for x in bracket.group(1).split(",") if x.strip()]
        else:
            day_items = re.findall(rf"^\s*[-*]? *(?:Day|Week|Interval|Period|Shift|Port Call)\s*\d+\s*:[^0-9\n]*{NUMBER}", text, re.M | re.I)
            if day_items and len(day_items) >= 2:
                demand = [float(x) for x in day_items]
    cost_text = text[text.lower().find("three"):] if "three" in text.lower() else text
    costs = [float(n) for n in re.findall(rf"{NUMBER}\s*(?:[A-Za-z$]+\s+){{0,2}}per", cost_text)][:3]
    if len(costs) < 3:
        cost_matches = re.findall(rf"(?:cost|expense|penalty|levied|assessed|calculated|charged|set|imposed|amounting to)[^.,;\n]{{0,50}}?(?:at|of|to|is)\s*(\$?\s*{NUMBER})\s*(?:monetary units\s*)?(?:per|\/|for each\b)", text, re.I)
        if len(cost_matches) < 3:
            cost_matches = re.findall(rf"(?:at|of|to)\s*(\$?\s*{NUMBER})\s*(?:monetary units\s*)?(?:per|\/|for each\b)", text, re.I)
        if len(cost_matches) < 3:
            cost_matches = re.findall(rf"(\$?\s*{NUMBER})\s*(?:monetary units\s*)?(?:per|\/|for each\b)\s*([A-Za-z]+)", text, re.I)
        if len(cost_matches) >= 3:
            costs = [float(re.search(NUMBER, c[0] if isinstance(c, tuple) else c).group(1)) for c in cost_matches[:3]]
    if not (initial and bounds and capacity and demand and len(costs) == 3):
        return None
    init_val = 0.0 if "zero" in initial.group(0).lower() else float(re.search(NUMBER, initial.group(0)).group(1))
    cap_m = re.search(NUMBER, capacity.group(0))
    cap_val = float(cap_m.group(1)) if cap_m else float(capacity.group(1))
    return {"initial": init_val, "low": float(bounds.group(1)), "high": float(bounds.group(2)),
            "capacity": cap_val, "lead": lead_time, "demand": demand,
            "order_cost": costs[0], "hold_cost": costs[1], "short_cost": costs[2]}


def solve_inventory(data: dict, capacity_after_arrival: bool) -> float | None:
    periods, lead = len(data["demand"]), data["lead"]
    model = pulp.LpProblem("inventory", pulp.LpMinimize)
    order = [pulp.LpVariable(f"q{t}", data["low"], data["high"]) for t in range(periods)]
    stock = [pulp.LpVariable(f"i{t}", 0, data["capacity"]) for t in range(periods)]
    lost = [pulp.LpVariable(f"s{t}", 0, data["demand"][t]) for t in range(periods)]
    model += pulp.lpSum(data["order_cost"] * order[t] + data["hold_cost"] * stock[t] + data["short_cost"] * lost[t]
                        for t in range(periods))
    for t in range(periods):
        before = data["initial"] if t == 0 else stock[t - 1]
        arrival = order[t - lead] if t >= lead else 0
        model += stock[t] == before + arrival - data["demand"][t] + lost[t]
        if capacity_after_arrival:
            model += before + arrival <= data["capacity"]
    model.solve(pulp.HiGHS(msg=False, timeLimit=60))
    return pulp.value(model.objective) if model.status == 1 else None


def capacity_wording(question: str) -> str:
    """How an Inventory question words its capacity rule: "end of period", "any moment" or "other"."""
    sentence = re.search(r"[^.]*capacit[^.]*\.", question.lower())
    words = sentence.group(0) if sentence else ""
    if re.search(r"end of (any|each|every|the)", words):
        return "end of period"
    return "any moment" if re.search(r"any (moment|time|point)", words) else "other"


def check(problems, answers: dict[str, float]) -> list[dict]:
    rows = []
    for problem in problems:
        row = {"problem_id": problem.problem_id, "problem_class": problem.problem_class, "reference": problem.answer,
               "capacity_wording": capacity_wording(problem.question) if problem.problem_class == "Inventory" else ""}
        if problem.problem_class == "Pollution":
            data = parse_pollution(problem.question)
            readings = {"stated model": solve_pollution(data)} if data else None
        else:
            data = parse_inventory(problem.question)
            readings = ({"capacity at end of period": solve_inventory(data, False),
                         "capacity also after arrival": solve_inventory(data, True)} if data else None)
        if readings is None:
            row.update(checked=False, reproduced_by="", stated_optima="", pipeline="", pipeline_equals="")
            rows.append(row)
            continue
        matching = [name for name, value in readings.items() if value is not None and is_correct(value, problem.answer)]
        row.update(checked=True, reproduced_by=" | ".join(matching) or "none",
                   stated_optima=" | ".join(f"{name}: {'infeasible' if v is None else round(v, 3)}" for name, v in readings.items()))
        predicted = answers.get(problem.problem_id)
        row["pipeline"] = "" if predicted is None else predicted
        if predicted is None:
            row["pipeline_equals"] = ""
        else:
            equal = [name for name, value in readings.items() if value is not None and is_correct(predicted, value)]
            row["pipeline_equals"] = ("reference" if is_correct(predicted, problem.answer) else "") or " | ".join(equal) or "neither"
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for problem_class in ("Pollution", "Inventory"):
        members = [r for r in rows if r["problem_class"] == problem_class]
        checked = [r for r in members if r["checked"]]
        with_pipeline = [r for r in checked if r["pipeline"] != ""]
        summary[problem_class] = {
            "problems": len(members),
            "checked": len(checked),
            "reproduced": sum(r["reproduced_by"] != "none" for r in checked),
            "by_reading": {name: sum(name in r["reproduced_by"] for r in checked)
                           for name in (("stated model",) if problem_class == "Pollution"  # a tuple: a fixed key order
                                        else ("capacity at end of period", "capacity also after arrival"))},
            "pipeline_answers": len(with_pipeline),
            "pipeline_equals_reference": sum(r["pipeline_equals"] == "reference" for r in with_pipeline),
            "pipeline_equals_a_stated_reading_only": sum(r["pipeline_equals"] not in ("reference", "neither") for r in with_pipeline),
        }
    return summary


def markdown(summary: dict) -> str:
    classes = summary["classes"]
    lines = [
        "# Reference check (Pollution and Inventory)", "",
        "Each question's data is read from its text and the model the text states is solved with HiGHS. A reference",
        "counts as reproduced within the grading tolerance (0.2%). Made by `scripts/check_references.py`.", "",
        "| Class | Problems | Checked | Reference reproduced | Pipeline answers | Pipeline = reference | Pipeline = a stated reading only |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, c in classes.items():
        lines.append(f"| {name} | {c['problems']} | {c['checked']} | {c['reproduced']} | {c['pipeline_answers']} | "
                     f"{c['pipeline_equals_reference']} | {c['pipeline_equals_a_stated_reading_only']} |")
    readings = ", ".join(f"{name}: {count}" for name, count in classes["Inventory"]["by_reading"].items())
    lines += ["", f"Inventory references reproduced by each capacity reading: {readings}.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="folder for the CSV and summary files")
    parser.add_argument("--records", type=Path, nargs="*", default=[], help="pipeline runs whose answers to compare")
    args = parser.parse_args()

    problems = [p for p in load_split("canonical") if p.problem_class in ("Pollution", "Inventory")]
    answers = {}
    for path in args.records:
        for line in path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line) if line.strip() else {}
            if record.get("predicted") is not None:
                answers.setdefault(record["problem_id"], record["predicted"])
    rows = check(problems, answers)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "references.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"records": [p.as_posix() for p in args.records], "classes": summarize(rows)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (args.out / "summary.md").write_text(markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
