import json
from pathlib import Path

import pytest

from vastu_analyzer import PlanValidationError, load_plan, plan_from_dict
from vastu_analyzer.geometry import area
from vastu_analyzer.loader import plan_to_dict

MINIMAL = {
    "footprint": [[0, 0], [10, 0], [10, 10], [0, 10]],
    "rooms": [{"name": "A", "type": "living", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}],
}


def test_minimal_plan_defaults() -> None:
    plan = plan_from_dict(MINIMAL)
    assert plan.north.angle_deg == 0.0
    assert plan.location is None
    assert plan.entrances == []


def test_units_are_converted_to_metres() -> None:
    plan = plan_from_dict({**MINIMAL, "units": "ft"})
    assert area(plan.footprint) == pytest.approx(100 * 0.3048**2)


def test_first_entrance_becomes_main() -> None:
    plan = plan_from_dict({**MINIMAL, "entrances": [{"position": [5, 0]}, {"position": [0, 5]}]})
    assert plan.entrances[0].main
    assert not plan.entrances[1].main


def test_numeric_north_shorthand_and_clockwise_input() -> None:
    data = {**MINIMAL, "north": 15}
    data["rooms"] = [{"name": "A", "type": "x", "polygon": [[0, 0], [0, 10], [10, 10], [10, 0]]}]
    plan = plan_from_dict(data)
    assert plan.north.angle_deg == 15
    # clockwise input is re-oriented to counter-clockwise
    from vastu_analyzer.geometry import signed_area

    assert signed_area(plan.rooms[0].polygon) > 0


def test_all_errors_are_collected() -> None:
    bad = {
        "schema_version": "9",
        "units": "furlong",
        "north": {"reference": "grid"},
        "footprint": [[0, 0], [1, 1]],
        "rooms": [{"name": "X", "polygon": [[0, 0], [1, 0], [2, 0]]}],
        "entrances": [{"position": "door"}],
        "location": {"latitude": 99, "longitude": 0},
    }
    with pytest.raises(PlanValidationError) as exc:
        plan_from_dict(bad)
    msgs = " | ".join(exc.value.errors)
    for needle in ("schema_version", "units", "north.reference", "footprint", "zero area",
                   "missing 'type'", "position", "latitude"):  # fmt: skip
        assert needle in msgs


def test_room_outside_footprint_is_rejected() -> None:
    data = {**MINIMAL, "rooms": [{"name": "Far", "type": "living",
                                  "polygon": [[20, 20], [21, 20], [21, 21]]}]}  # fmt: skip
    with pytest.raises(PlanValidationError, match="outside the footprint"):
        plan_from_dict(data)


def test_empty_rooms_rejected() -> None:
    with pytest.raises(PlanValidationError, match="at least one room"):
        plan_from_dict({"footprint": MINIMAL["footprint"], "rooms": []})


def test_invalid_json_file(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(PlanValidationError, match="invalid JSON"):
        load_plan(p)
    p.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(PlanValidationError, match="object"):
        load_plan(p)


def test_round_trip(sample_path: Path, tmp_path: Path) -> None:
    plan = load_plan(sample_path)
    out = tmp_path / "rt.json"
    out.write_text(json.dumps(plan_to_dict(plan)), encoding="utf-8")
    again = load_plan(out)
    assert [r.name for r in again.rooms] == [r.name for r in plan.rooms]
    assert again.location == plan.location
    assert again.north == plan.north
