import copy

import pytest

from vastu_analyzer import analyze, load_rules
from vastu_analyzer.geometry import rotate
from vastu_analyzer.models import Entrance, FloorPlan, North, Room


def _by_name(result, name):  # type: ignore[no-untyped-def]
    return next(r for r in result.rooms if r.name == name)


def test_compliant_plan_scores_high(compliant_plan: FloorPlan) -> None:
    res = analyze(compliant_plan)
    assert res.vci > 85
    assert not [f for f in res.findings if f.severity == "critical"]
    assert res.components["entrance"] == pytest.approx(100.0)


def test_defective_plan_flags_classic_doshas(sample_plan: FloorPlan) -> None:
    res = analyze(sample_plan)
    assert 40 < res.vci < 75
    critical = {f.subject for f in res.findings if f.severity == "critical"}
    assert {"Kitchen", "Toilet 1"} <= critical
    assert _by_name(res, "Kitchen").score == pytest.approx(0.0)
    assert _by_name(res, "Master Bedroom").zone == "SW"


def test_optimiser_moves_kitchen_to_south_east(sample_plan: FloorPlan) -> None:
    res = analyze(sample_plan)
    assert res.swaps, "expected at least one improving exchange"
    first = res.swaps[0]
    assert {first.room_a, first.room_b} == {"Kitchen", "Bedroom 3"}
    assert res.optimised_vci is not None
    assert res.optimised_vci > res.vci + 10
    gains = [s.gain for s in res.swaps]
    assert all(g >= 0.5 for g in gains)
    # immovable rooms are never exchanged
    assert all("Staircase" not in (s.room_a, s.room_b) for s in res.swaps)


def test_no_optimise_flag(sample_plan: FloorPlan) -> None:
    res = analyze(sample_plan, optimise=False)
    assert res.swaps == []
    assert res.optimised_vci is None


def test_rotation_invariance_of_zoning(compliant_plan: FloorPlan) -> None:
    """Rotating the drawing together with its north arrow must not change the result."""
    base = analyze(compliant_plan, optimise=False)
    plan = copy.deepcopy(compliant_plan)
    plan.footprint = rotate(plan.footprint, 90.0)
    for r in plan.rooms:
        r.polygon = rotate(r.polygon, 90.0)
    plan.entrances = [
        Entrance(e.name, rotate([e.position], 90.0)[0], e.main) for e in plan.entrances
    ]
    plan.north = North(angle_deg=-90.0)  # arrow now points to the drawing's left
    rot = analyze(plan, optimise=False)
    assert rot.vci == pytest.approx(base.vci, abs=1e-6)
    for a, b in zip(base.rooms, rot.rooms, strict=True):
        assert a.zone == b.zone


def test_flipping_north_ruins_compliance(compliant_plan: FloorPlan) -> None:
    flipped = copy.deepcopy(compliant_plan)
    flipped.north = North(angle_deg=180.0)
    assert analyze(flipped).vci < analyze(compliant_plan).vci - 25


def test_magnetic_declination_shifts_true_north(compliant_plan: FloorPlan) -> None:
    plan = copy.deepcopy(compliant_plan)
    plan.north = North(angle_deg=10.0, reference="magnetic", declination_deg=1.3)
    assert plan.north.true_angle_deg == pytest.approx(8.7)
    res = analyze(plan)
    assert res.site.orientation_skew == pytest.approx(8.7)


def test_exterior_walls_and_physics(sample_plan: FloorPlan) -> None:
    res = analyze(sample_plan)
    master = _by_name(res, "Master Bedroom")
    sectors = sorted(w.sector for w in master.walls)
    assert len(master.walls) == 2
    assert "S" in sectors
    assert master.solar["peak_sol_air"] > 55
    assert _by_name(res, "Pooja").walls == []  # interior room
    subjects = {(f.category, f.subject) for f in res.findings}
    assert ("physics", "Kitchen") in subjects  # no morning sun
    assert res.solar_summary["overhang_depth_ratio"] == pytest.approx(0.55, abs=0.03)


def test_corner_cut_and_brahmasthana_detection() -> None:
    # 9 x 9 square with the NE 3 x 3 removed, and a toilet in the centre.
    fp = [(0, 0), (9, 0), (9, 6), (6, 6), (6, 9), (0, 9)]
    rooms = [
        Room("Hall", "living", [(0, 0), (9, 0), (9, 6), (6, 6), (6, 3), (3, 3), (3, 6), (0, 6)]),
        Room("WC", "toilet", [(3, 3), (6, 3), (6, 6), (3, 6)]),
        Room("Top", "bedroom", [(0, 6), (6, 6), (6, 9), (0, 9)]),
    ]
    plan = FloorPlan("cut", fp, rooms, [Entrance("door", (4.5, 0.0), True)])
    res = analyze(plan)
    assert res.site.corner_fill["NE"] == pytest.approx(0.0)
    assert res.site.brahmasthana_blocked == pytest.approx(1.0)
    subjects = {f.subject: f.severity for f in res.findings}
    assert subjects["NE corner"] == "critical"
    assert "Brahmasthana" in subjects
    assert res.solar_summary == {}  # no location given


def test_custom_rules_are_respected(sample_plan: FloorPlan) -> None:
    rb = load_rules()
    rb.rooms["kitchen"].zones.update(dict.fromkeys(rb.ZONES, 1.0))
    res = analyze(sample_plan, rb, optimise=False)
    assert _by_name(res, "Kitchen").score == pytest.approx(1.0)


def test_alias_resolution() -> None:
    rb = load_rules()
    assert rb.canonical("Bathroom") == "toilet"
    assert rb.canonical("puja") == "pooja"
    assert rb.canonical("Master Bed") == "master_bedroom"
    assert rb.canonical("jacuzzi") == "other"
    assert "SE" in rb.rule("kitchen").best_zones()
