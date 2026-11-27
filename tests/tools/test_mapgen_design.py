import json
from pathlib import Path

import pytest

from experimental.mapgen.design import Design, DesignError, load


@pytest.fixture
def example():
    path = Path(__file__).resolve().parents[2] / "docs/mapgen/format.md"
    return path.read_text(encoding="utf-8").split("```json\n", 1)[1].split("\n```", 1)[0]


@pytest.fixture
def sketch(example):
    return json.loads(example)


def test_load_a1_like_sketch(tmp_path, example):
    source = tmp_path / "design.json"
    source.write_text(example, encoding="utf-8")
    design = load(source)
    assert design.check_relations() == {
        "approach": "pass", "sealed_route": "pass", "muster_space": "needs the grid",
    }
    assert design.reachable("west", "square", "vehicle")
    assert not design.reachable("west", "square", "vehicle", without="main")
    assert design.reachable("spawn", "goal", "foot", state="blocked")


def test_nested_blocks_leave_parent_ground(sketch):
    sketch["blocks"]["pond"] = {
        "parent": "ridge", "height": 2, "use": "池塘", "kind": "water", "ring": ["pond_bank"], "seed": 9,
    }
    sketch["borders"]["pond_bank"] = {
        "line": [[30, 130], [70, 130], [70, 170], [30, 170], [30, 130]],
        "sides": ["pond", "ridge"], "pass": ["amphibian"],
    }
    design = Design(sketch)
    assert design.reachable("ridge", "pond", "amphibian")
    assert not design.reachable("ridge", "pond", "foot")
    assert design.block_seed("pond") == 9
    sketch["points"]["goal"]["at"] = [40, 140]
    with pytest.raises(DesignError, match=r"goal \[point\]"):
        Design(sketch)


def test_shared_border_written_once(sketch):
    assert Design(sketch).reachable("square", "ridge", "vehicle")
    east = sketch["borders"]["east_scarp"]
    east["segments"]["hairpin"]["span"] = [20, 101]
    with pytest.raises(DesignError, match=r"east_scarp.hairpin \[span\]"):
        Design(sketch)
    east["segments"]["hairpin"]["span"] = [20, 80]
    east["sides"].reverse()
    with pytest.raises(DesignError, match=r"east_scarp \[sides\]"):
        Design(sketch)
    east["sides"] = ["ridge", None]
    sketch["borders"]["duplicate"] = {"line": east["line"], "sides": [None, "square"]}
    sketch["blocks"]["square"]["ring"][2] = "-duplicate"
    with pytest.raises(DesignError, match=r"duplicate \[overlap\].*east_scarp"):
        Design(sketch)


def test_road_ending_in_a_block(sketch):
    # The junction is in the middle of main, with no authored vertex there.
    sketch["roads"]["lane"] = {"line": [[100, 50], [150, 50]], "width": "alley"}
    with pytest.raises(DesignError, match=r"lane \[dangling\] end"):
        Design(sketch)
    sketch["roads"]["lane"]["ends"] = ["end"]
    Design(sketch)
    sketch["roads"]["solo"] = {"line": [[20, 20], [30, 20]], "width": "alley", "ends": ["start", "end"]}
    with pytest.raises(DesignError, match=r"solo \[road_network\]"):
        Design(sketch)


def test_road_meets_no_pass_border(sketch):
    # The spur meets the closed range at 62.5 world units from its border's start.
    sketch["roads"]["spur"] = {"line": [[100, 50], [25, 150]], "width": "alley", "ends": ["end"]}
    with pytest.raises(DesignError, match=r"spur \[road_no_pass\].*west_scarp.sealed"):
        Design(sketch)


def test_missing_reference_identifies_owner(sketch):
    sketch["states"]["blocked"]["pass"]["east_scarp.missing"] = []
    with pytest.raises(DesignError, match=r"blocked \[reference\].*east_scarp.missing"):
        Design(sketch)
    del sketch["states"]["blocked"]["pass"]["east_scarp.missing"]
    sketch["relations"]["approach"]["who"] = "tank"
    with pytest.raises(DesignError, match=r"approach \[reference\].*tank"):
        Design(sketch)


def test_only_through_c_requires_a_path_and_no_bypass(sketch):
    assert Design(sketch).check_relations()["approach"] == "pass"
    # An unannotated contact at arc length 90 creates a second route down the ridge.
    sketch["roads"]["ramp"] = {"line": [[130, 50], [190, 100], [190, 140]],
                                "width": "street", "ends": ["end"]}
    assert Design(sketch).check_relations()["approach"] == "fail"
    del sketch["roads"]["ramp"]
    sketch["borders"]["east_scarp"]["segments"]["hairpin"]["pass"] = ["foot"]
    assert Design(sketch).check_relations()["approach"] == "fail"
