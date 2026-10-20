"""Airport Ground Equipment Dispatch problem generator and question text builder."""

from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class EquipmentUnit:
    unit_id: str
    unit_type: str  # "loader" or "tug"
    fixed_cost: int  # activation / turnout cost
    max_hours: int  # maximum operational capacity in hours


@dataclass(frozen=True)
class ServiceRequest:
    request_id: str
    stand_id: str
    required_type: str  # "loader" or "tug"
    required_hours: int


@dataclass
class EquipmentDispatchScenario:
    units: list[EquipmentUnit]
    requests: list[ServiceRequest]
    transit_costs: dict[tuple[str, str], int]  # (unit_id, request_id) -> cost

    def all_numbers(self) -> list[float | int]:
        """Return all numerical constants that must appear in the question text."""
        numbers: list[float | int] = []
        for unit in self.units:
            numbers.extend([unit.fixed_cost, unit.max_hours])
        for req in self.requests:
            numbers.append(req.required_hours)
        for cost in self.transit_costs.values():
            numbers.append(cost)
        return numbers


def generate_equipment_scenario(num_requests: int, num_units: int, seed: int) -> EquipmentDispatchScenario:
    """Deterministically generate a feasible equipment dispatch scenario."""
    rng = random.Random(seed)

    # Distribute units between loaders and tugs
    units: list[EquipmentUnit] = []
    for k in range(num_units):
        u_id = f"Unit_{k + 1:02d}"
        u_type = "loader" if k % 2 == 0 else "tug"
        fixed_cost = 180 + k * 35 + rng.randint(0, 30)
        # Capacity in operating hours (10 to 18 hours)
        max_hours = 12 + rng.randint(0, 6)
        units.append(EquipmentUnit(unit_id=u_id, unit_type=u_type, fixed_cost=fixed_cost, max_hours=max_hours))

    # Generate requests matching available unit types
    requests: list[ServiceRequest] = []
    for r in range(num_requests):
        r_id = f"Req_{r + 1:02d}"
        stand_id = f"Stand_{r + 1}"
        r_type = "loader" if r % 2 == 0 else "tug"
        hours = rng.randint(2, 4)
        requests.append(ServiceRequest(request_id=r_id, stand_id=stand_id, required_type=r_type, required_hours=hours))

    # Generate transit cost matrix between unit depots and aircraft stands
    transit_costs: dict[tuple[str, str], int] = {}
    for unit in units:
        for req in requests:
            base_dist = rng.randint(15, 65)
            transit_costs[(unit.unit_id, req.request_id)] = base_dist

    # Feasibility check: ensure capacity per type is strictly sufficient
    for eq_type in ["loader", "tug"]:
        type_reqs = [r for r in requests if r.required_type == eq_type]
        type_units = [u for u in units if u.unit_type == eq_type]
        total_demanded_hours = sum(r.required_hours for r in type_reqs)
        total_capacity_hours = sum(u.max_hours for u in type_units)
        if total_capacity_hours < total_demanded_hours:
            # Increase unit capacities to ensure feasibility
            extra = (total_demanded_hours - total_capacity_hours + len(type_units)) // len(type_units) + 2
            for idx, u in enumerate(units):
                if u.unit_type == eq_type:
                    units[idx] = EquipmentUnit(
                        unit_id=u.unit_id,
                        unit_type=u.unit_type,
                        fixed_cost=u.fixed_cost,
                        max_hours=u.max_hours + extra,
                    )

    return EquipmentDispatchScenario(units=units, requests=requests, transit_costs=transit_costs)


def build_equipment_dispatch_question(scenario: EquipmentDispatchScenario) -> str:
    """Build natural-language question text stating all parameters."""
    lines = [
        "An airport operations manager must dispatch ground support equipment to service aircraft stands, minimizing the total cost.",
        "The total cost is the sum of fixed activation costs for deployed units plus transit costs between units and stands.",
        "",
        "Available Ground Equipment Units:",
    ]
    for unit in scenario.units:
        lines.append(
            f"- {unit.unit_id}: {unit.unit_type}, fixed activation cost is {unit.fixed_cost}, maximum capacity is {unit.max_hours} operating hours."
        )

    lines.append("")
    lines.append("Aircraft Stand Service Requests:")
    for req in scenario.requests:
        lines.append(
            f"- {req.request_id} (at {req.stand_id}): requires {unit_type_label(req.required_type)}, duration is {req.required_hours} hours."
        )

    lines.append("")
    lines.append("Transit Costs between Units and Requests:")
    for unit in scenario.units:
        unit_costs = [
            f"{req.request_id}: {scenario.transit_costs[(unit.unit_id, req.request_id)]}"
            for req in scenario.requests
        ]
        lines.append(f"- {unit.unit_id} -> {', '.join(unit_costs)}")

    lines.append("")
    lines.append("Constraints and Rules:")
    lines.append("1. Each aircraft service request must be fulfilled by exactly one equipment unit.")
    lines.append("2. An equipment unit can only service requests that require its specific equipment type (a loader cannot service a tug request, and vice versa).")
    lines.append("3. If an equipment unit is assigned to one or more requests, its fixed activation cost is incurred.")
    lines.append("4. Total service hours assigned to an active unit cannot exceed its maximum operating hours capacity.")
    lines.append("")
    lines.append("Objective:")
    lines.append("Determine the valid dispatch assignment that minimizes total cost (sum of activation costs for active units plus transit costs for assigned requests).")
    lines.append("What is the minimum total dispatch cost in dollars?")

    return "\n".join(lines)


def unit_type_label(u_type: str) -> str:
    return "a loader" if u_type == "loader" else "a tug"


def build_equipment_reference_model(scenario: EquipmentDispatchScenario) -> pulp.LpProblem:
    """Construct the exact PuLP mixed-integer reference model for equipment dispatch."""
    import pulp

    model = pulp.LpProblem("Airport_Equipment_Dispatch", pulp.LpMinimize)

    # Decision variables
    # u[k] = 1 if equipment unit k is activated
    u: dict[str, pulp.LpVariable] = {
        unit.unit_id: pulp.LpVariable(f"activate_{unit.unit_id}", cat=pulp.LpBinary)
        for unit in scenario.units
    }
    # z[k, r] = 1 if unit k services request r
    z: dict[tuple[str, str], pulp.LpVariable] = {
        (unit.unit_id, req.request_id): pulp.LpVariable(
            f"dispatch_{unit.unit_id}_{req.request_id}", cat=pulp.LpBinary
        )
        for unit in scenario.units
        for req in scenario.requests
    }

    # Objective: Minimize total fixed activation costs plus transit costs
    model += pulp.lpSum(unit.fixed_cost * u[unit.unit_id] for unit in scenario.units) + pulp.lpSum(
        scenario.transit_costs[(unit.unit_id, req.request_id)] * z[(unit.unit_id, req.request_id)]
        for unit in scenario.units
        for req in scenario.requests
    )

    # Constraint 1: Fulfillment of every service request
    for req in scenario.requests:
        model += (
            pulp.lpSum(
                z[(unit.unit_id, req.request_id)]
                for unit in scenario.units
                if unit.unit_type == req.required_type
            )
            == 1,
            f"fulfill_{req.request_id}",
        )

    # Constraint 2: Type compatibility restriction
    for unit in scenario.units:
        for req in scenario.requests:
            if unit.unit_type != req.required_type:
                model += (
                    z[(unit.unit_id, req.request_id)] == 0,
                    f"incompatible_{unit.unit_id}_{req.request_id}",
                )

    # Constraint 3: Activation linking and operational hour capacity
    for unit in scenario.units:
        for req in scenario.requests:
            model += (
                z[(unit.unit_id, req.request_id)] <= u[unit.unit_id],
                f"link_{unit.unit_id}_{req.request_id}",
            )
        model += (
            pulp.lpSum(
                req.required_hours * z[(unit.unit_id, req.request_id)]
                for req in scenario.requests
            )
            <= unit.max_hours * u[unit.unit_id],
            f"capacity_{unit.unit_id}",
        )

    return model


def solve_equipment_dispatch(scenario: EquipmentDispatchScenario) -> float:
    """Solve the equipment dispatch reference model with HiGHS and return the exact optimal value."""
    import pulp

    model = build_equipment_reference_model(scenario)
    solver = pulp.HiGHS(msg=False)
    status = model.solve(solver)
    status_str = pulp.LpStatus[status]
    if status_str != "Optimal":
        raise ValueError(f"Equipment dispatch scenario did not solve to Optimal: status={status_str}")
    return round(float(pulp.value(model.objective)), 2)


def create_equipment_dispatch_instance(size: int, seed: int) -> OpsORInstance:
    """Create a complete OpsORInstance for equipment dispatch at a given size and seed."""
    from .base import OpsORInstance, assert_question_contains_numbers

    num_requests = size
    if size <= 5:
        num_units = 3
    elif size <= 8:
        num_units = 4
    else:
        num_units = 6

    scenario = generate_equipment_scenario(num_requests=num_requests, num_units=num_units, seed=seed)
    question = build_equipment_dispatch_question(scenario)
    answer = solve_equipment_dispatch(scenario)

    # Verify that all numbers used by the model are in the question text
    assert_question_contains_numbers(question, scenario.all_numbers())

    params = {
        "num_requests": num_requests,
        "num_units": num_units,
        "units": [
            {
                "unit_id": u.unit_id,
                "unit_type": u.unit_type,
                "fixed_cost": u.fixed_cost,
                "max_hours": u.max_hours,
            }
            for u in scenario.units
        ],
        "requests": [
            {
                "request_id": r.request_id,
                "stand_id": r.stand_id,
                "required_type": r.required_type,
                "required_hours": r.required_hours,
            }
            for r in scenario.requests
        ],
        "transit_costs": {
            f"{u_id}->{r_id}": cost for (u_id, r_id), cost in scenario.transit_costs.items()
        },
    }

    return OpsORInstance(
        family="EquipmentDispatch",
        size=size,
        seed=seed,
        question=question,
        answer=answer,
        params=params,
    )
