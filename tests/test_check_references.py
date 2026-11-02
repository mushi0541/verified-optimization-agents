"""Tests for scripts/check_references.py on small hand-made questions (no LLM calls)."""

import pytest

from optverify.contracts import Problem
from scripts.check_references import capacity_wording, check, parse_inventory, parse_pollution, solve_inventory, solve_pollution

POLLUTION = """A district must lower its waste.
* For Line A, waste coefficient is 1, output volume is 10.
* For Line B, waste coefficient is 1, output volume is 10.
Techniques:
* By adopting Technique X, material loss will be decreased by 50%
* By adopting Technique Y, material loss will be decreased by 100%
| Line \\ Technique | Technique X | Technique Y |
|--|-|-|
| Line A | 1 | 3 |
| Line B | 2 | 1 |
The objective is to cut waste by at least a fraction P = 0.5 of the baseline while minimizing cost."""

INVENTORY = """A center plans stock over two days.
The initial stock level at the start of the first day is 8 units.
On each day the supplier permits a shipment whose volume must be between 0 and 10 units.
* Day 1: 9 units
* Day 2: 1 units
Unmet demand is lost. The total stock held at any moment must not exceed the storage capacity of 10 units.
The aggregate cost comprises three elements: a procurement cost of 1 per unit ordered; a storage cost of 1 per unit
kept overnight; and a shortage penalty of 100 per unit of unmet demand."""


def test_pollution_is_read_and_solved():
    data = parse_pollution(POLLUTION)
    assert data == {"sources": [(1.0, 10.0), (1.0, 10.0)], "rates": [0.5, 1.0], "cost": [[1.0, 3.0], [2.0, 1.0]], "P": 0.5}
    # Removing 10 of the baseline 20 is cheapest with Technique Y on all of Line B: removal 10 at cost 1 * 10.
    assert solve_pollution(data) == pytest.approx(10.0)


def test_inventory_is_read_and_the_two_capacity_readings_differ():
    data = parse_inventory(INVENTORY)
    assert (data["initial"], data["low"], data["high"], data["capacity"], data["lead"]) == (8.0, 0.0, 10.0, 10.0, 0)
    assert data["demand"] == [9.0, 1.0] and (data["order_cost"], data["hold_cost"], data["short_cost"]) == (1.0, 1.0, 100.0)
    # End of day: order 1 on day 1 (stock 0), then 1 on day 2: cost 2. After arrival: day 1 may hold at most 10, so
    # 8 + 2 is allowed and the same plan works: cost 2. Both readings agree when the capacity does not bind.
    assert solve_inventory(data, False) == pytest.approx(2.0)
    assert solve_inventory(data, True) == pytest.approx(2.0)
    tight = dict(data, demand=[12.0, 1.0])
    # Day 1 needs 12 with 8 in stock. End of day: order 4 (stock 0), then 1: cost 5. After arrival: at most 8 + 2 may
    # be on hand, so 2 units are lost at 100 each: cost 2 + 200 + 1 = 203.
    assert solve_inventory(tight, False) == pytest.approx(5.0)
    assert solve_inventory(tight, True) == pytest.approx(203.0)


def test_lead_times_are_read_or_the_question_is_not_checked():
    # canonical-0622's wording: words between the time unit and "transit".
    transit = INVENTORY.replace("Unmet demand is lost.", "Each requested shipment will require 4 week(s) for transit. Unmet demand is lost.")
    assert parse_inventory(transit)["lead"] == 4
    assert parse_inventory(INVENTORY.replace("Unmet demand is lost.", "There is a 2-hour transmission delay. Unmet demand is lost."))["lead"] == 2
    assert parse_inventory(INVENTORY.replace("Unmet demand is lost.", "Shipments are delivered instantly. Unmet demand is lost."))["lead"] == 0
    for sentence, lead in (("There is a lag of 2 days.", 2), ("Each order requires 3 days to travel.", 3),
                           ("The transit time of 3 legs applies.", 3), ("Orders take a lead time of 2 port calls.", 2),
                           ("An order becomes available for use in the subsequent week.", 1)):
        assert parse_inventory(INVENTORY.replace("Unmet demand is lost.", sentence + " Unmet demand is lost."))["lead"] == lead
    # A delay the parser cannot read must not be solved as lead 0.
    assert parse_inventory(INVENTORY.replace("Unmet demand is lost.", "Shipments arrive after a short transit. Unmet demand is lost.")) is None


def test_capacity_wording():
    assert capacity_wording("The stock at the end of any day must not exceed the capacity of 5.") == "end of period"
    assert capacity_wording(INVENTORY) == "any moment"


def test_check_marks_reproduced_references_and_pipeline_answers():
    problems = [
        Problem("canonical-9001", POLLUTION, 10.0, "Pollution", 2, "canonical"),
        Problem("canonical-9002", POLLUTION, 25.0, "Pollution", 2, "canonical"),
        Problem("canonical-9003", "no data here", 1.0, "Pollution", 2, "canonical"),
    ]
    rows = {row["problem_id"]: row for row in check(problems, {"canonical-9001": 10.0, "canonical-9002": 10.0})}
    assert rows["canonical-9001"]["reproduced_by"] == "stated model" and rows["canonical-9001"]["pipeline_equals"] == "reference"
    # A reference the stated model cannot give, and a pipeline answer that equals the stated model instead.
    assert rows["canonical-9002"]["reproduced_by"] == "none" and rows["canonical-9002"]["pipeline_equals"] == "stated model"
    assert rows["canonical-9003"]["checked"] is False  # an unreadable question is not checked, never guessed

def test_extended_inventory_patterns():
    # Phrasing variations: zero stock, range bounds, storage facility capacity, transit period with full day, dash bullets, monetary unit costs
    text_dash = """A regional facility manages stock over 3 days.
The initial stockpile at the outset is precisely 0 units.
On each day the shipment must fall within the range of 5 to 25 units.
The storage facility capacity of 40 units must not be surpassed.
Every shipment will require a transit period of 1 full day before delivery.
Daily requirements are:
- Day 1: 10 units
- Day 2: 15 units
- Day 3: 20 units
Unmet demand is lost.
Costs comprise: procurement cost of 2 monetary units per unit ordered, storage cost of 1 monetary unit per unit held overnight, and a stockout penalty assessed at 50 monetary units per unit of unmet requirement."""
    data = parse_inventory(text_dash)
    assert data == {
        "initial": 0.0, "low": 5.0, "high": 25.0, "capacity": 40.0, "lead": 1,
        "demand": [10.0, 15.0, 20.0], "order_cost": 2.0, "hold_cost": 1.0, "short_cost": 50.0,
    }
    assert solve_inventory(data, False) == pytest.approx(580.0)
    assert solve_inventory(data, True) == pytest.approx(580.0)

    # Bracketed demand and zero lead time
    text_bracket = """A depot manages inventory.
The starting stock is zero units.
Each order size must be between 0 and 50.
Storage limit of 100 units.
Shipments arrive with no lead time.
The projected demand is [10, 20, 30].
Unmet demand is lost.
The costs are 3 per unit ordered, 2 per unit held, and 20 per unit short."""
    data_b = parse_inventory(text_bracket)
    assert data_b["initial"] == 0.0
    assert data_b["demand"] == [10.0, 20.0, 30.0]
    assert data_b["lead"] == 0

    # Lead time with full days phrasing
    text_full = """A plant plans storage.
The beginning stock stands at 15 kiloliters.
Orders from 10 to 30 kiloliters.
The tank can hold at most 50 kiloliters.
Each order will require 2 full days to reach the reservoir.
* Period 1: 15 kiloliters
* Period 2: 25 kiloliters
Unmet demand is lost.
Procurement cost of 2 per kiloliter, holding cost of 1 per kiloliter, shortage penalty of 10 per kiloliter."""
    data_f = parse_inventory(text_full)
    assert data_f["lead"] == 2
    assert data_f["initial"] == 15.0
    assert data_f["capacity"] == 50.0



def test_the_initial_stock_is_the_number_the_pattern_captures():
    # Another number before it in the same sentence (here the horizon) must not be read as the initial stock.
    text = ("A depot manages stock. The initial stock for the 3-day horizon is 20 units. Each order must be between 0 "
            "and 50 units. Storage capacity is 100 units. Orders arrive with no delay.\n* Day 1: 10 units\n"
            "* Day 2: 20 units\n* Day 3: 30 units\nThe three costs are 3 per unit ordered, 2 per unit held and 20 per "
            "unit short.")
    assert parse_inventory(text)["initial"] == 20.0


def test_hand_labels_schema_and_values():
    import csv
    from pathlib import Path
    from optverify.data import load_split

    path = Path(__file__).resolve().parent.parent / 'results' / 'reference_check' / 'hand_labels.csv'
    assert path.exists(), 'hand_labels.csv must exist'
    rows = list(csv.DictReader(path.open(encoding='utf-8')))
    assert len(rows) >= 10, 'hand_labels.csv must contain hand check rows'

    expected_fields = {'problem_id', 'problem_class', 'reference', 'hand_optimum', 'reading', 'label', 'note'}
    assert set(rows[0].keys()) == expected_fields

    canonical_problems = {p.problem_id: p for p in load_split('canonical')}
    valid_labels = {'reference_correct', 'reference_wrong', 'text_ambiguous', 'not_checked'}

    for r in rows:
        pid = r['problem_id']
        assert pid in canonical_problems, f'Unknown problem_id: {pid}'
        assert r['problem_class'] in {'Inventory', 'Pollution'}
        assert r['label'] in valid_labels
        assert float(r['reference']) == pytest.approx(canonical_problems[pid].answer, rel=1e-3)

    by_id = {r['problem_id']: r for r in rows}
    assert by_id['canonical-0648']['label'] == 'reference_wrong'
    assert by_id['canonical-0644']['label'] == 'text_ambiguous'
    assert by_id['canonical-0667']['label'] == 'text_ambiguous'
    assert by_id['canonical-1578']['label'] == 'reference_wrong'
