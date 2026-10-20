"""Ground-Crew Rostering problem generator and question text builder."""

from __future__ import annotations

from dataclasses import dataclass
import random


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
        "An airport ground handling service must roster personnel across daily operating shifts to minimize total staffing costs.",
        f"Under labor safety regulations, no worker may be scheduled to work more than {scenario.max_consecutive} consecutive shifts without a rest period.",
        "",
        "Operational Shifts and Required Headcounts:",
    ]
    for shift in scenario.shifts:
        lines.append(f"- {shift.shift_id}: requires at least {shift.required_crew} workers.")

    lines.append("")
    lines.append("Worker Roster and Availability:")
    for worker in scenario.workers:
        avail_str = ", ".join(worker.available_shifts)
        lines.append(
            f"- {worker.worker_id}: compensation is {worker.shift_cost} per shift, maximum of {worker.max_shifts} total shifts, available for: {avail_str}."
        )

    lines.append("")
    lines.append("Constraints and Rules:")
    lines.append("1. Shift staffing demand must be met for each shift.")
    lines.append("2. Each worker cannot exceed their designated maximum total shifts.")
    lines.append(f"3. Consecutive shifts limit: no worker can work more than {scenario.max_consecutive} consecutive shifts.")
    lines.append("4. A worker can only be assigned to shifts for which they are available.")
    lines.append("")
    lines.append("Objective:")
    lines.append("Determine the valid crew schedule that minimizes total labor cost (the sum of shift costs for all scheduled shifts across all workers).")
    lines.append("What is the minimum total staffing cost in dollars?")

    return "\n".join(lines)
