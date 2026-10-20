"""Airport Gate Assignment problem generator and question text builder."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class Gate:
    gate_id: str
    gate_type: str  # "narrowbody" or "widebody"
    walking_distance: int  # passenger walking distance in meters


@dataclass(frozen=True)
class Flight:
    flight_id: str
    arrival_minute: int
    departure_minute: int
    passengers: int
    aircraft_type: str  # "narrowbody" or "widebody"


@dataclass
class GateAssignmentScenario:
    flights: list[Flight]
    gates: list[Gate]
    buffer_minutes: int

    def all_numbers(self) -> list[float | int]:
        """Return all numerical constants that must appear in the question text."""
        numbers: list[float | int] = [self.buffer_minutes]
        for gate in self.gates:
            numbers.append(gate.walking_distance)
        for flight in self.flights:
            numbers.extend([flight.arrival_minute, flight.departure_minute, flight.passengers])
        return numbers


def generate_gate_scenario(num_flights: int, num_gates: int, seed: int) -> GateAssignmentScenario:
    """Deterministically generate a feasible airport gate assignment scenario."""
    rng = random.Random(seed)

    # Distribute gates: 1 or 2 widebody gates, rest narrowbody
    num_widebody = max(1, num_gates // 3)
    gates: list[Gate] = []
    for g_idx in range(num_gates):
        g_id = f"Gate_{g_idx + 1}"
        g_type = "widebody" if g_idx < num_widebody else "narrowbody"
        # Walking distance between 50m and 450m
        distance = 50 + g_idx * 40 + rng.randint(0, 20)
        gates.append(Gate(gate_id=g_id, gate_type=g_type, walking_distance=distance))

    buffer_minutes = 20

    # To guarantee feasibility, assign each flight to a preliminary feasible gate slot
    # then assign arrival and departure intervals without conflict
    gate_free_time: dict[str, int] = {g.gate_id: 0 for g in gates}
    flights: list[Flight] = []

    # Interleave assignments across gates to balance schedule
    for f_idx in range(num_flights):
        assigned_gate = gates[f_idx % num_gates]
        # Aircraft type must match gate capability
        if assigned_gate.gate_type == "widebody":
            ac_type = "widebody" if rng.random() < 0.6 else "narrowbody"
        else:
            ac_type = "narrowbody"

        current_free = gate_free_time[assigned_gate.gate_id]
        # Flight arrives at or after current free time
        gap = rng.randint(5, 25)
        arrival = current_free + gap
        duration = rng.randint(35, 75)
        departure = arrival + duration
        gate_free_time[assigned_gate.gate_id] = departure + buffer_minutes

        passengers = rng.randint(80, 260)
        flights.append(
            Flight(
                flight_id=f"Flight_{f_idx + 1:02d}",
                arrival_minute=arrival,
                departure_minute=departure,
                passengers=passengers,
                aircraft_type=ac_type,
            )
        )

    # Sort flights chronologically by arrival time for clarity
    flights = sorted(flights, key=lambda f: (f.arrival_minute, f.flight_id))

    return GateAssignmentScenario(flights=flights, gates=gates, buffer_minutes=buffer_minutes)


def build_gate_assignment_question(scenario: GateAssignmentScenario) -> str:
    """Build natural-language question text stating all parameters."""
    lines = [
        "An airport terminal must assign scheduled flights to terminal gates to minimize total passenger walking distance.",
        f"A separation buffer of at least {scenario.buffer_minutes} minutes is required between consecutive flights assigned to the same gate.",
        "",
        "Available Gates:",
    ]
    for gate in scenario.gates:
        cap_note = "widebody and narrowbody aircraft" if gate.gate_type == "widebody" else "narrowbody aircraft only"
        lines.append(
            f"- {gate.gate_id}: accepts {cap_note}, walking distance to exit is {gate.walking_distance} meters."
        )

    lines.append("")
    lines.append("Scheduled Flights:")
    for flight in scenario.flights:
        lines.append(
            f"- {flight.flight_id}: {flight.aircraft_type} aircraft, {flight.passengers} passengers, arrives at minute {flight.arrival_minute}, departs at minute {flight.departure_minute}."
        )

    lines.append("")
    lines.append("Constraints and Rules:")
    lines.append("1. Each flight must be assigned to exactly one gate.")
    lines.append("2. Widebody aircraft can only be assigned to gates that accept widebody aircraft. Narrowbody aircraft can use any gate.")
    lines.append(f"3. Two flights assigned to the same gate cannot overlap in time: if flight A departs at minute D and flight B arrives at minute A' at the same gate with A' >= D, then A' must be at least D + {scenario.buffer_minutes} minutes.")
    lines.append("")
    lines.append("Objective:")
    lines.append("Determine the valid gate assignment that minimizes the total passenger walking distance (the sum of passenger counts multiplied by the assigned gate walking distance for each flight).")
    lines.append("What is the minimum total passenger walking distance in meters?")

    return "\n".join(lines)


def build_gate_reference_model(scenario: GateAssignmentScenario) -> pulp.LpProblem:
    """Construct the exact PuLP mixed-integer reference model for gate assignment."""
    import pulp

    model = pulp.LpProblem("Airport_Gate_Assignment", pulp.LpMinimize)

    # Decision variables: x[f, g] = 1 if flight f is assigned to gate g
    x: dict[tuple[str, str], pulp.LpVariable] = {}
    for flight in scenario.flights:
        for gate in scenario.gates:
            x[(flight.flight_id, gate.gate_id)] = pulp.LpVariable(
                f"assign_{flight.flight_id}_{gate.gate_id}", cat=pulp.LpBinary
            )

    # Objective: Minimize total passenger walking distance
    model += pulp.lpSum(
        flight.passengers * gate.walking_distance * x[(flight.flight_id, gate.gate_id)]
        for flight in scenario.flights
        for gate in scenario.gates
    )

    # Constraint 1: Every flight must be assigned to exactly one gate
    for flight in scenario.flights:
        model += (
            pulp.lpSum(x[(flight.flight_id, gate.gate_id)] for gate in scenario.gates) == 1,
            f"assign_once_{flight.flight_id}",
        )

    # Constraint 2: Aircraft type compatibility
    for flight in scenario.flights:
        if flight.aircraft_type == "widebody":
            for gate in scenario.gates:
                if gate.gate_type != "widebody":
                    model += (
                        x[(flight.flight_id, gate.gate_id)] == 0,
                        f"incompatible_{flight.flight_id}_{gate.gate_id}",
                    )

    # Constraint 3: Non-overlapping gate occupancies (with separation buffer)
    buffer = scenario.buffer_minutes
    for i, f1 in enumerate(scenario.flights):
        for f2 in scenario.flights[i + 1 :]:
            # Conflict if time windows overlap including the required buffer
            overlap = max(f1.arrival_minute, f2.arrival_minute) < min(
                f1.departure_minute + buffer, f2.departure_minute + buffer
            )
            if overlap:
                for gate in scenario.gates:
                    model += (
                        x[(f1.flight_id, gate.gate_id)] + x[(f2.flight_id, gate.gate_id)] <= 1,
                        f"no_overlap_{f1.flight_id}_{f2.flight_id}_{gate.gate_id}",
                    )

    return model


def solve_gate_assignment(scenario: GateAssignmentScenario) -> float:
    """Solve the gate assignment reference model with HiGHS and return the exact optimal value."""
    import pulp

    model = build_gate_reference_model(scenario)
    solver = pulp.HiGHS(msg=False)
    status = model.solve(solver)
    status_str = pulp.LpStatus[status]
    if status_str != "Optimal":
        raise ValueError(f"Gate assignment scenario did not solve to Optimal: status={status_str}")
    return round(float(pulp.value(model.objective)), 2)


def create_gate_assignment_instance(size: int, seed: int) -> OpsORInstance:
    """Create a complete OpsORInstance for gate assignment at a given size and seed."""
    from .base import OpsORInstance, assert_question_contains_numbers

    # Map instance size (number of flights) to proportional gate capacity
    num_flights = size
    if size <= 5:
        num_gates = 3
    elif size <= 8:
        num_gates = 4
    else:
        num_gates = 5

    scenario = generate_gate_scenario(num_flights=num_flights, num_gates=num_gates, seed=seed)
    question = build_gate_assignment_question(scenario)
    answer = solve_gate_assignment(scenario)

    # Verify that all numbers used by the model are in the question text
    assert_question_contains_numbers(question, scenario.all_numbers())

    params = {
        "num_flights": num_flights,
        "num_gates": num_gates,
        "buffer_minutes": scenario.buffer_minutes,
        "gates": [
            {"gate_id": g.gate_id, "gate_type": g.gate_type, "walking_distance": g.walking_distance}
            for g in scenario.gates
        ],
        "flights": [
            {
                "flight_id": f.flight_id,
                "arrival_minute": f.arrival_minute,
                "departure_minute": f.departure_minute,
                "passengers": f.passengers,
                "aircraft_type": f.aircraft_type,
            }
            for f in scenario.flights
        ],
    }

    return OpsORInstance(
        family="GateAssignment",
        size=size,
        seed=seed,
        question=question,
        answer=answer,
        params=params,
    )
