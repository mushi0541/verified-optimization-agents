"""Ground-Crew Rostering problem generator and question text builder."""

from __future__ import annotations

from dataclasses import dataclass
import random

import pulp


@dataclass(frozen=True)
class Shift:
    shift_id: str
    shift_index: int
    required_crew: int


@dataclass(frozen=True)
class Worker:
    worker_id: str
    shift_cost: int
    max_shifts: int
    available_shifts: tuple[str, ...]


@dataclass
class CrewRosteringScenario:
    shifts: list[Shift]
    workers: list[Worker]
    max_consecutive: int = 2

    def all_numbers(self) -> list[float | int]:
        """Return all numerical constants that must appear in the question text."""
        numbers: list[float | int] = [self.max_consecutive]
        for shift in self.shifts:
            numbers.append(shift.required_crew)
        for worker in self.workers:
            numbers.extend([worker.shift_cost, worker.max_shifts])
        return numbers


def generate_crew_scenario(num_shifts: int, num_workers: int, seed: int) -> CrewRosteringScenario:
    """Deterministically generate a feasible ground-crew rostering scenario."""
    rng = random.Random(seed)

    # Generate shifts with required staffing demand (2 to 4 workers per shift)
    shifts: list[Shift] = []
    for t in range(num_shifts):
        demand = rng.randint(2, 3) if num_workers <= 6 else rng.randint(2, 4)
        shifts.append(Shift(shift_id=f"Shift_{t + 1}", shift_index=t, required_crew=demand))

    # Generate workers with individual shift costs and shift caps
    shift_ids = [s.shift_id for s in shifts]
    workers: list[Worker] = []
    for w in range(num_workers):
        w_id = f"Worker_{w + 1:02d}"
        shift_cost = rng.randint(120, 260)
        # Shift cap
        max_shifts = min(num_shifts, max(2, (num_shifts + 1) // 2 + rng.randint(0, 1)))

        # Availability: worker is available for most shifts to guarantee feasibility
        available = [s_id for s_id in shift_ids if rng.random() > 0.15]
        if len(available) < max_shifts:
            available = list(shift_ids[:max_shifts + 1])

        workers.append(
            Worker(
                worker_id=w_id,
                shift_cost=shift_cost,
                max_shifts=max_shifts,
                available_shifts=tuple(sorted(available)),
            )
        )

    # Feasibility check: ensure each shift has enough available workers
    for shift in shifts:
        available_count = sum(1 for w in workers if shift.shift_id in w.available_shifts)
        if available_count < shift.required_crew:
            # Add availability for workers who lack it
            for w_idx, w in enumerate(workers):
                if shift.shift_id not in w.available_shifts:
                    new_avail = tuple(sorted(list(w.available_shifts) + [shift.shift_id]))
                    workers[w_idx] = Worker(
                        worker_id=w.worker_id,
                        shift_cost=w.shift_cost,
                        max_shifts=w.max_shifts,
                        available_shifts=new_avail,
                    )
                    available_count += 1
                    if available_count >= shift.required_crew + 1:
                        break

    return CrewRosteringScenario(shifts=shifts, workers=workers, max_consecutive=2)


def build_crew_rostering_question(scenario: CrewRosteringScenario) -> str:
    """Build natural-language question text stating all parameters."""
    lines = [
        "An airport ground handling service must roster personnel across operating shifts to minimize total staffing costs.",
        f"Under labor safety regulations, shifts run in the order Shift_1, Shift_2, ..., Shift_n, with no wrap-around from the last shift to the first. No worker may work more than {scenario.max_consecutive} shifts in a row in this order; a shift the worker does not work breaks the run.",
        "",
        "Operational Shifts and Required Headcounts:",
    ]
    for shift in scenario.shifts:
        lines.append(f"- {shift.shift_id}: requires at least {shift.required_crew} workers.")

    lines.append("")
    lines.append("Worker Roster and Availability:")
    shift_order = {s.shift_id: i for i, s in enumerate(scenario.shifts)}
    for worker in scenario.workers:
        avail_shifts = sorted(worker.available_shifts, key=lambda s_id: shift_order.get(s_id, 0))
        avail_str = ", ".join(avail_shifts)
        lines.append(
            f"- {worker.worker_id}: compensation is {worker.shift_cost} per shift, maximum of {worker.max_shifts} total shifts, available for: {avail_str}."
        )

    lines.append("")
    lines.append("Constraints and Rules:")
    lines.append("1. Each shift needs at least its required number of workers.")
    lines.append("2. Each worker cannot exceed their designated maximum total shifts.")
    lines.append(f"3. No worker may work more than {scenario.max_consecutive} shifts in a row in this order.")
    lines.append("4. A worker can only be assigned to shifts for which they are available.")
    lines.append("")
    lines.append("Objective:")
    lines.append("Determine the valid crew schedule that minimizes total labor cost (the sum of shift costs for all scheduled shifts across all workers).")
    lines.append("What is the minimum total staffing cost in dollars?")

    return "\n".join(lines)


def build_crew_reference_model(scenario: CrewRosteringScenario) -> pulp.LpProblem:
    """Construct the exact PuLP mixed-integer reference model for ground-crew rostering."""
    model = pulp.LpProblem("Ground_Crew_Rostering", pulp.LpMinimize)

    # Decision variables: y[w, s] = 1 if worker w is assigned to shift s
    y: dict[tuple[str, str], pulp.LpVariable] = {}
    for worker in scenario.workers:
        for shift in scenario.shifts:
            y[(worker.worker_id, shift.shift_id)] = pulp.LpVariable(
                f"assign_{worker.worker_id}_{shift.shift_id}", cat=pulp.LpBinary
            )

    # Objective: Minimize total labor cost
    model += pulp.lpSum(
        worker.shift_cost * y[(worker.worker_id, shift.shift_id)]
        for worker in scenario.workers
        for shift in scenario.shifts
    )

    # Constraint 1: Staffing demand coverage per shift
    for shift in scenario.shifts:
        model += (
            pulp.lpSum(
                y[(worker.worker_id, shift.shift_id)]
                for worker in scenario.workers
                if shift.shift_id in worker.available_shifts
            )
            >= shift.required_crew,
            f"demand_{shift.shift_id}",
        )

    # Constraint 2: Maximum shifts per worker
    for worker in scenario.workers:
        model += (
            pulp.lpSum(y[(worker.worker_id, shift.shift_id)] for shift in scenario.shifts)
            <= worker.max_shifts,
            f"max_shifts_{worker.worker_id}",
        )

    # Constraint 3: Availability restriction
    for worker in scenario.workers:
        for shift in scenario.shifts:
            if shift.shift_id not in worker.available_shifts:
                model += (
                    y[(worker.worker_id, shift.shift_id)] == 0,
                    f"unavailable_{worker.worker_id}_{shift.shift_id}",
                )

    # Constraint 4: Maximum consecutive shifts limit
    for worker in scenario.workers:
        for t in range(len(scenario.shifts) - scenario.max_consecutive):
            window = [scenario.shifts[t + offset].shift_id for offset in range(scenario.max_consecutive + 1)]
            model += (
                pulp.lpSum(y[(worker.worker_id, s_id)] for s_id in window) <= scenario.max_consecutive,
                f"consecutive_{worker.worker_id}_from_{window[0]}",
            )

    return model


def solve_crew_rostering(scenario: CrewRosteringScenario) -> float:
    """Solve the crew rostering reference model with HiGHS and return the exact optimal value."""
    model = build_crew_reference_model(scenario)
    solver = pulp.HiGHS(msg=False)
    status = model.solve(solver)
    status_str = pulp.LpStatus[status]
    if status_str != "Optimal":
        raise ValueError(f"Crew rostering scenario did not solve to Optimal: status={status_str}")
    return round(float(pulp.value(model.objective)), 2)


def create_crew_rostering_instance(size: int, seed: int) -> OpsORInstance:
    """Create a complete OpsORInstance for ground-crew rostering at a given size and seed."""
    from .base import OpsORInstance, assert_question_contains_numbers

    num_shifts = size
    if size <= 5:
        num_workers = size + 2
    elif size <= 8:
        num_workers = size + 3
    else:
        num_workers = size + 4

    scenario = generate_crew_scenario(num_shifts=num_shifts, num_workers=num_workers, seed=seed)
    question = build_crew_rostering_question(scenario)
    answer = solve_crew_rostering(scenario)

    # Verify that all numbers used by the model are in the question text
    assert_question_contains_numbers(question, scenario.all_numbers())

    params = {
        "num_shifts": num_shifts,
        "num_workers": num_workers,
        "max_consecutive": scenario.max_consecutive,
        "shifts": [{"shift_id": s.shift_id, "required_crew": s.required_crew} for s in scenario.shifts],
        "workers": [
            {
                "worker_id": w.worker_id,
                "shift_cost": w.shift_cost,
                "max_shifts": w.max_shifts,
                "available_shifts": list(w.available_shifts),
            }
            for w in scenario.workers
        ],
    }

    return OpsORInstance(
        family="CrewRostering",
        size=size,
        seed=seed,
        question=question,
        answer=answer,
        params=params,
    )
