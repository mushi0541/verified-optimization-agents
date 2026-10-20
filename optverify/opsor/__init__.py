"""OpsOR-Bench: Operations Research benchmark problem generators and loaders."""

from .base import OpsORInstance, assert_question_contains_numbers, extract_numbers_from_text
from .crew_rostering import (
    CrewRosteringScenario,
    build_crew_reference_model,
    build_crew_rostering_question,
    create_crew_rostering_instance,
    generate_crew_scenario,
    solve_crew_rostering,
)
from .equipment_dispatch import (
    EquipmentDispatchScenario,
    build_equipment_dispatch_question,
    build_equipment_reference_model,
    create_equipment_dispatch_instance,
    generate_equipment_scenario,
    solve_equipment_dispatch,
)
from .gate_assignment import (
    GateAssignmentScenario,
    build_gate_assignment_question,
    build_gate_reference_model,
    create_gate_assignment_instance,
    generate_gate_scenario,
    solve_gate_assignment,
)
from .registry import DEFAULT_OPSOR_PATH, generate_opsor_dataset, save_opsor_jsonl

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
    "CrewRosteringScenario",
    "build_crew_reference_model",
    "build_crew_rostering_question",
    "create_crew_rostering_instance",
    "generate_crew_scenario",
    "solve_crew_rostering",
    "EquipmentDispatchScenario",
    "build_equipment_dispatch_question",
    "build_equipment_reference_model",
    "create_equipment_dispatch_instance",
    "generate_equipment_scenario",
    "solve_equipment_dispatch",
    "DEFAULT_OPSOR_PATH",
    "generate_opsor_dataset",
    "save_opsor_jsonl",
]
