"""Simple tests: one small, readable check for each step of the flowchart."""

from pathlib import Path

import pytest

from vastu_analyzer import Door, House, Room, analyse, check_house, load_house, save_house
from vastu_analyzer.cli import main
from vastu_analyzer.compass import outside_walls, point_zone, room_shares, side_to_compass, zone_of_box
from vastu_analyzer.house import overlap_area
from vastu_analyzer.rules import room_type
from vastu_analyzer.scoring import score_house

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def tiny_house(kitchen_x: float, kitchen_y: float) -> House:
    """A 9 x 9 house with one 3 x 3 kitchen, which fits exactly in one grid box."""
    return House("tiny", 9, 9, rooms=[Room("Kitchen", "kitchen", kitchen_x, kitchen_y, 3, 3)])


# STEP 1-2: describe and check the house -------------------------------------------


def test_overlap_area() -> None:
    assert overlap_area(0, 0, 4, 4, 2, 2, 4, 4) == 4  # a 2 x 2 corner is shared
    assert overlap_area(0, 0, 2, 2, 5, 5, 2, 2) == 0  # far apart


def test_check_finds_mistakes() -> None:
    house = House("bad", 10, 10, north="sideways", rooms=[
        Room("A", "living", 0, 0, 6, 6),
        Room("B", "kitchen", 5, 5, 6, 6),  # sticks out and overlaps A
    ])  # fmt: skip
    problems = " ".join(check_house(house))
    assert "North" in problems
    assert "sticks out" in problems
    assert "overlap" in problems
    assert check_house(load_house(EXAMPLES / "2_builder_3bhk.json")) == []


def test_save_and_load_give_the_same_house(tmp_path: Path) -> None:
    house = load_house(EXAMPLES / "7_well_planned_3bhk.json")
    save_house(house, tmp_path / "copy.json")
    assert load_house(tmp_path / "copy.json") == house


# STEP 3-5: north, grid, which box --------------------------------------------------


def test_compass_turns_with_north() -> None:
    assert side_to_compass("up", "up") == "N"
    assert side_to_compass("up", "right") == "W"  # north on the right -> top faces west
    assert zone_of_box(0, 2, "up") == "NE"
    assert zone_of_box(0, 2, "right") == "NW"
    assert zone_of_box(1, 1, "left") == "C"


def test_room_shares() -> None:
    house = House("h", 9, 9)
    room = Room("Hall", "living", 4.5, 0, 3, 3)  # half in N box, half in NE box
    assert room_shares(room, house) == {"N": 0.5, "NE": 0.5}
    assert point_zone(8, 8, house) == "SE"
    assert outside_walls(Room("Corner", "store", 0, 6, 3, 3), house) == ["S", "W"]


# STEP 6-7: points and score --------------------------------------------------------


def test_kitchen_points_depend_on_where_it_is() -> None:
    assert score_house(tiny_house(6, 6)).rooms[0].points == 10  # south-east: best
    assert score_house(tiny_house(6, 0)).rooms[0].points == 0  # north-east: bad


def test_aliases() -> None:
    assert room_type("Bathroom") == "toilet"
    assert room_type("puja") == "pooja"
    assert room_type("jacuzzi") == "other"


def test_good_house_beats_sample_house() -> None:
    good = analyse(load_house(EXAMPLES / "7_well_planned_3bhk.json"))
    sample = analyse(load_house(EXAMPLES / "2_builder_3bhk.json"))
    assert good.score >= 80
    assert sample.score < 60
    assert good.grade == "Excellent"


def test_toilet_in_centre_blocks_brahmasthan() -> None:
    house = House("c", 9, 9, rooms=[Room("WC", "toilet", 3, 3, 3, 3)])
    assert score_house(house).centre_blocked_by == ["WC"]


# STEP 8-9: swaps and to-do list ----------------------------------------------------


def test_swap_moves_kitchen_to_south_east() -> None:
    result = analyse(load_house(EXAMPLES / "2_builder_3bhk.json"))
    first_swap = result.swaps[0]
    assert {first_swap[0], first_swap[1]} == {"Kitchen", "Bedroom 3"}
    assert first_swap[2] > result.score
    assert "Kitchen" in result.todo[0]  # the worst problem is listed first


def test_door_and_sun_advice() -> None:
    house = House("d", 9, 9, rooms=[Room("Bed", "master_bedroom", 0, 6, 3, 3)], door=Door(4.5, 9))
    todo = " ".join(analyse(house).todo)
    assert "Main door" in todo  # a south door is not ideal
    assert "west wall" in todo  # the bedroom has a hot west wall


# Command line ------------------------------------------------------------------------


def test_command_line(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["analyze", str(EXAMPLES / "2_builder_3bhk.json")]) == 0
    assert "VASTU SCORE" in capsys.readouterr().out

    bad = tmp_path / "bad.json"
    bad.write_text('{"width": 5, "depth": 5, "rooms": []}', encoding="utf-8")
    assert main(["analyze", str(bad)]) == 1
    assert "fix the drawing" in capsys.readouterr().out


# The sample houses ---------------------------------------------------------------------


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.stem)
def test_every_sample_house_is_valid(path: Path) -> None:
    assert check_house(load_house(path)) == []


def test_samples_cover_every_grade_in_order() -> None:
    results = [analyse(load_house(p)) for p in sorted(EXAMPLES.glob("*.json"))]
    scores = [r.score for r in results]
    assert scores == sorted(scores)  # files are numbered from worst to best
    assert {r.grade for r in results} == {"Poor", "Needs work", "Good", "Excellent"}


# Editing: collisions, free space, moving rooms -------------------------------------


def two_room_house() -> House:
    return House("edit", 9, 9, rooms=[Room("A", "kitchen", 0, 0, 3, 3), Room("B", "bedroom", 6, 6, 3, 3)])


def test_collision_finds_overlaps_and_outside() -> None:
    from vastu_analyzer.house import collision

    house = two_room_house()
    assert collision(house, house.rooms[0]) is None
    assert "overlap 'A'" in (collision(house, Room("C", "store", 2, 2, 3, 3)) or "")
    assert "stick out" in (collision(house, Room("C", "store", 8, 8, 3, 3)) or "")


def test_find_free_spot() -> None:
    from vastu_analyzer.house import find_free_spot

    house = two_room_house()
    assert find_free_spot(house, 3, 3) == (3.0, 0.0)  # first gap, scanning from the top-left
    full = House("full", 6, 6, rooms=[Room("Big", "living", 0, 0, 6, 6)])
    assert find_free_spot(full, 1, 1) is None


def test_move_room_moves_swaps_or_refuses() -> None:
    from vastu_analyzer.house import move_room

    house = two_room_house()
    a, b = house.rooms
    assert move_room(house, a, 3, 0)[0]  # empty space: just moves
    assert (a.x, a.y) == (3, 0)

    ok, text = move_room(house, a, 6, 6)  # dropped on B: they swap places
    assert ok
    assert "Swapped" in text
    assert (a.x, a.y, b.x, b.y) == (6, 6, 3, 0)

    ok, text = move_room(house, a, 8, 8)  # would stick out: nothing changes
    assert not ok
    assert (a.x, a.y) == (6, 6)
