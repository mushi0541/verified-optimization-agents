"""List the parser's subtour rule for every TSP problem of the given pipeline runs (devlog entry 14, #91). No API calls.

    python scripts/tsp_parser_rules.py --records results/<run>/records.jsonl [...] --out results/failures/tsp_parser/parser_rules.csv

For each TSP record: the run, the final solver status, whether the answer is correct, the parser's requirements that
mention the subtour constraint, and a label for the rule they state:
- "keeps the start city": a Miller-Tucker-Zemlin formula for all i != j, with no exception for the start city;
- "leaves the start city out": the formula is limited to the other cities (for example i, j in {2, ..., N});
- "no formula": the requirement names subtour elimination or MTZ but gives no formula.
The label comes from the wording, so every row keeps the requirement text for a reader to check by hand.
"""

import argparse
import csv
import json
import re
from pathlib import Path

SUBTOUR = re.compile(r"mtz|miller|subtour|sub-tour|u_i|u\[i\]|u_\{?i", re.I)
FORMULA = re.compile(r"u_?\[?i\]?\s*-\s*u_?\[?j\]?|u_i\s*-\s*u_j", re.I)
LEAVES_OUT = re.compile(
    r"(i|j)\s*(≠|!=|<>|\\neq)\s*(1|0|start|depot|origin|base|home|hq|headquarters)\b"
    r"|\{\s*2\s*,|2\s*(≤|<=)\s*i|i\s*,\s*j\s*(≥|>=)\s*2|i\s*,\s*j\s*∈\s*\{2"
    r"|excluding|except|other than|non-?depot|not the (start|depot)|i,\s*j\s*≠\s*\w+"
    r"|(?-i:\b(i|j)\s*≠\s*[A-Z]\w*)",  # a named start city, such as i ≠ Alpha (case-sensitive, so i ≠ j does not match)
    re.I,
)


def formula_clause(rule: str) -> str:
    """The clause that holds the MTZ formula: a rule often states the bounds of u (for all i != start) in another
    clause, and only the formula's own range decides whether the start city is kept."""
    clauses = re.split(r"\s\|\s|;|,?\s+and\s+(?=for|u)", rule)
    return next((c for c in clauses if FORMULA.search(c)), "")


def label(rule: str) -> str:
    if not rule:
        return "no subtour requirement"
    clause = formula_clause(rule)
    if not clause:
        return "no formula"
    return "leaves the start city out" if LEAVES_OUT.search(clause) else "keeps the start city"


def rows(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line) if line.strip() else None
        if not record or record.get("problem_class") != "TSP":
            continue
        requirements = (record.get("spec") or {}).get("requirements") or {}
        rule = " | ".join(str(text) for text in requirements.values() if SUBTOUR.search(str(text)))
        status = record["attempts"][-1]["solve"]["status"] if record.get("attempts") else "no attempt"
        out.append({"run": path.parent.name, "problem_id": record["problem_id"], "final_status": status,
                    "correct": record["correct"], "rule": label(rule), "requirement_text": rule})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    table = [row for path in args.records for row in rows(path)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    print(f"{len(table)} TSP records written to {args.out.as_posix()}")


if __name__ == "__main__":
    main()
