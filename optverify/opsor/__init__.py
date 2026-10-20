"""OpsOR-Bench: Operations Research benchmark problem generators and loaders."""

from .base import OpsORInstance, assert_question_contains_numbers, extract_numbers_from_text
from .gate_assignment import (
    GateAssignmentScenario,
    build_gate_assignment_question,
    build_gate_reference_model,
    create_gate_assignment_instance,
    generate_gate_scenario,
    solve_gate_assignment,
)

__all__ = [
    "OpsORInstance",
    "assert_question_contains_numbers",
    "extract_numbers_from_text",
    "GateAssignmentScenario",
    "build_gate_assignment_question",
    "build_gate_reference_model",
    "create_gate_assignment_instance",
    "generate_gate_scenario",
    "solve_gate_assignment",
]
