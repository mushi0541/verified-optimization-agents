"""Grading and summary metrics."""

from collections import defaultdict

# Same rule as the base paper's evaluation script (OPT-Engine): |pred - true| <= 0.002 * |true|.
RELATIVE_TOLERANCE = 0.002


def is_correct(predicted: float | None, reference: float | None, rel_tol: float = RELATIVE_TOLERANCE) -> bool:
    if predicted is None or reference is None:
        return False
    return abs(predicted - reference) <= rel_tol * abs(reference) + 1e-9


def same_optimum(a: float | None, b: float | None, rel_tol: float = RELATIVE_TOLERANCE) -> bool:
    """Used by the verifier to compare two of our own answers (no reference involved)."""
    if a is None or b is None:
        return False
    return abs(a - b) <= rel_tol * max(abs(a), abs(b)) + 1e-9


def summarize(records: list[dict]) -> dict:
    """Headline numbers for a run. Records are RunRecord.to_json() dictionaries."""
    total = len(records)
    if total == 0:
        return {"problems": 0}

    final_status = [record["attempts"][-1]["solve"]["status"] if record["attempts"] else "no_code" for record in records]
    summary = {
        "problems": total,
        "accuracy": _share(record["correct"] for record in records),
        "solved_rate": _share(status == "optimal" for status in final_status),
        "status_counts": _count(final_status),
        "mean_input_tokens": sum(r["usage"]["input_tokens"] for r in records) / total,
        "mean_output_tokens": sum(r["usage"]["output_tokens"] for r in records) / total,
        "mean_llm_calls": sum(r["usage"]["calls"] for r in records) / total,
        "mean_latency_s": sum(r["latency_s"] for r in records) / total,
        "accuracy_by_class": _accuracy_by(records, "problem_class"),
    }

    decided = [record for record in records if record.get("decision")]
    if decided:
        answered = [r for r in decided if r["decision"]["action"] == "answer"]
        summary["decision_counts"] = _count(r["decision"]["action"] for r in decided)
        summary["coverage"] = len(answered) / len(decided)
        summary["selective_accuracy"] = _share(r["correct"] for r in answered) if answered else None
        summary["wrong_accept_rate"] = _share(not r["correct"] for r in answered) if answered else None
    return summary


def _accuracy_by(records: list[dict], key: str) -> dict:
    groups = defaultdict(list)
    for record in records:
        groups[record[key]].append(record["correct"])
    return {name: sum(values) / len(values) for name, values in sorted(groups.items())}


def _share(flags) -> float:
    flags = list(flags)
    return sum(flags) / len(flags) if flags else 0.0


def _count(values) -> dict:
    counts: dict = defaultdict(int)
    for value in values:
        counts[value] += 1
    return dict(sorted(counts.items()))
