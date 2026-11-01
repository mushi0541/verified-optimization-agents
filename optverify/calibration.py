"""Gap 2: a decision threshold calibrated to a target wrong-accept rate alpha, and its leave-one-class-out test.

A threshold is accepted only if the one-sided exact (Clopper-Pearson) upper bound on its wrong-accept rate
stays at or below alpha. Thresholds are scanned from strict to lenient and the scan stops before the first
one that fails, so this fixed order keeps the bound valid across thresholds. Only feasible answers can be
accepted: the decision layer abstains on everything else, whatever the threshold.
"""

from math import comb

MIN_ACCEPTED = 29  # with fewer accepted problems, even 0 wrong cannot give a 95% bound below 10%


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p).

    In floats comb(n, i) overflows near n = 1,030; our calibrations accept at most a few hundred problems.
    """
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def upper_bound(wrong: int, accepted: int, confidence: float = 0.95) -> float:
    """One-sided exact upper bound on the wrong-accept rate: the p where P(X <= wrong) = 1 - confidence."""
    if wrong >= accepted:
        return 1.0
    low, high = wrong / accepted, 1.0
    for _ in range(100):  # bisection; 100 halvings is far below float precision
        middle = (low + high) / 2
        if binomial_cdf(wrong, accepted, middle) > 1 - confidence:
            low = middle
        else:
            high = middle
    return high


def exact_interval(wrong: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Two-sided exact (Clopper-Pearson) interval for a rate of wrong / total."""
    if total == 0:
        return 0.0, 1.0
    tail = (1 + confidence) / 2
    upper = upper_bound(wrong, total, tail)
    lower = 0.0 if wrong == 0 else 1 - upper_bound(total - wrong, total, tail)
    return lower, upper


def calibrate_threshold(scored: list[tuple[float, bool]], alpha: float, confidence: float = 0.95) -> float | None:
    """The most lenient threshold whose wrong-accept bound stays at or below alpha, or None to answer nothing.

    `scored` holds (score, correct) for the feasible answers of the calibration problems.
    """
    chosen = None
    for threshold in sorted({score for score, _ in scored if score > 0}, reverse=True):
        accepted = [correct for score, correct in scored if score >= threshold]
        if len(accepted) < MIN_ACCEPTED:
            continue
        if upper_bound(accepted.count(False), len(accepted), confidence) > alpha:
            break
        chosen = threshold
    return chosen


def record_score(record: dict) -> float | None:
    """The score the decision layer used, or None when nothing could be answered.

    The pipeline uses its verifier score; B2 stores no verifier report and uses its sample agreement rate.
    """
    if record.get("verifier"):
        return record["verifier"]["score"] if record["verifier"]["feasible"] else None
    if record.get("samples"):
        return record["sample_agreement"] if record["decision"]["action"] != "abstain" else None
    return None


def scored_answers(records: list[dict]) -> list[tuple[float, bool]]:
    """(score, correct) of every answer that could be accepted, in saved pipeline or B2 records."""
    return [(score, bool(r["correct"])) for r in records if (score := record_score(r)) is not None]


def record_system(records: list[dict]) -> str:
    """The system the records come from (for example pipeline_p3 or b2_r1); a calibration is valid only for it."""
    systems = {r["system"] for r in records if "failed" not in r}
    if len(systems) != 1:
        raise ValueError(f"the records must come from one system, found {sorted(systems) or 'none'}")
    return systems.pop()


def check_system(calibration: dict, system: str) -> None:
    """Refuse a calibration file made for another system: pipeline scores and B2 agreement rates differ."""
    made_for = calibration.get("system", "")
    if made_for.split("_")[0] != system:
        raise ValueError(
            f"the calibration file was made from {made_for or 'unknown'} records, not {system}; "
            f"run scripts/calibrate.py on {system} records"
        )


def leave_one_class_out(records: list[dict], alpha: float, confidence: float = 0.95) -> dict:
    """Calibrate on nine classes, test on the tenth, for every class; pool the held-out results."""
    finished = [r for r in records if "failed" not in r]
    folds = []
    for held_out in sorted({r["problem_class"] for r in finished}):
        calibration = [r for r in finished if r["problem_class"] != held_out]
        test = [r for r in finished if r["problem_class"] == held_out]
        threshold = calibrate_threshold(scored_answers(calibration), alpha, confidence)
        answered = [score_ok for score_ok in scored_answers(test) if threshold is not None and score_ok[0] >= threshold]
        folds.append({
            "held_out_class": held_out,
            "threshold": threshold,
            "problems": len(test),
            "answered": len(answered),
            "wrong_accepted": sum(not correct for _, correct in answered),
        })

    answered = sum(f["answered"] for f in folds)
    wrong = sum(f["wrong_accepted"] for f in folds)
    return {
        "alpha": alpha,
        "confidence": confidence,
        "problems": len(finished),
        "failed_problems": len(records) - len(finished),
        "pooled": rates(answered, wrong, len(finished), confidence),
        "folds": folds,
        # The threshold for the application and for shift tests (OpsOR-Bench): calibrated on every class.
        "threshold": calibrate_threshold(scored_answers(finished), alpha, confidence),
    }


def rates(answered: int, wrong: int, problems: int, confidence: float = 0.95) -> dict:
    """Coverage and wrong-accept rate with its exact interval."""
    return {
        "answered": answered,
        "wrong_accepted": wrong,
        "coverage": answered / problems if problems else 0.0,
        "wrong_accept_rate": wrong / answered if answered else None,
        "exact_interval": list(exact_interval(wrong, answered, confidence)),
    }


def fixed_threshold(records: list[dict], threshold: float, confidence: float = 0.95) -> dict:
    """The same pooled numbers for one fixed threshold on every class (ablation vi)."""
    finished = [r for r in records if "failed" not in r]
    answered = [correct for score, correct in scored_answers(finished) if score >= threshold]
    return {"threshold": threshold, **rates(len(answered), answered.count(False), len(finished), confidence)}


def threshold_from_file(calibration: dict) -> float:
    """The decision threshold a calibration file sets; no passing threshold means answer nothing."""
    return calibration["threshold"] if calibration["threshold"] is not None else float("inf")
