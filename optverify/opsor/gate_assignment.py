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
