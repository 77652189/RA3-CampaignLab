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
    assert not design.reachable("spawn", "goal", "foot", state="blocked")


def test_nested_blocks_leave_parent_ground(sketch):
    sketch["blocks"]["pond"] = {
        "parent": "ridge", "height": 2, "use": "池塘", "kind": "water", "at": [50, 150], "seed": 9,
    }
    sketch["borders"]["pond_bank"] = {
        "line": [[30, 130], [70, 130], [70, 170], [30, 170], [30, 130]],
        "pass": ["amphibian"],
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
    sketch["borders"]["duplicate"] = {"line": east["line"]}
    with pytest.raises(DesignError, match=r"duplicate \[overlap\].*east_scarp"):
        Design(sketch)


def test_t_junction_splits_face(sketch):
    sketch["roads"]["lane"] = {"line": [[100, 50], [200, 50]], "width": "alley"}
    design = Design(sketch)
    unnamed, = design.blocks.keys() - sketch["blocks"].keys()
    assert design.face_at((125, 75)) == unnamed
    assert design.face_at((125, 25)) == "square"


@pytest.mark.parametrize(("at", "message"), [
    ([100, 25], "at lies on a line"),
    ([75, 25], "same face as west"),
])
def test_block_name_identifies_invalid_face(sketch, at, message):
    sketch["blocks"]["west_copy"] = dict(sketch["blocks"]["west"], at=at)
    with pytest.raises(DesignError, match=rf"west_copy \[enclosure\] {message}"):
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
    # Scale the sketch to fit a 180-unit ramp in the gap after the explicit opening.
    alternate = {**sketch, "roads": dict(sketch["roads"])}
    alternate["roads"]["ramp"] = {"line": [[130, 50], [190, 100], [190, 140]],
                                   "width": "street", "ends": ["end"]}
    alternate = json.loads(json.dumps(alternate))
    for section in ("roads", "borders"):
        for spec in alternate[section].values():
            spec["line"] = [[10 * x, 10 * y] for x, y in spec["line"]]
            for span in spec.get("segments", {}).values():
                span["span"] = [10 * v for v in span["span"]]
    for section in ("blocks", "points"):
        for spec in alternate[section].values():
            spec["at"] = [10 * v for v in spec["at"]]
    assert Design(alternate).check_relations()["approach"] == "fail"
    sketch["borders"]["east_scarp"]["segments"]["hairpin"]["pass"] = ["foot"]
    assert Design(sketch).check_relations()["approach"] == "fail"


def test_land_use_is_shared_by_named_and_automatic_blocks():
    sketch = Design({
        'version': 2, 'blocks': {'yard': {'height': 3, 'use': '老街', 'at': [250, 200]}},
        'borders': {'frame': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]}},
        'roads': {'street': {'line': [[0, 400], [1000, 400]], 'width': 'street'}},
    })
    assert {name: spec['use'] for name, spec in sketch.blocks.items()} == {'yard': 'oldtown', '@2': 'park'}


def test_relation_endpoint_requires_a_named_location():
    data = {
        'version': 2, 'blocks': {'yard': {'height': 3, 'use': 'park', 'at': [250, 200]}},
        'borders': {'frame': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]},
                    'ring': {'line': [[400, 300], [600, 300], [600, 500], [400, 500], [400, 300]],
                             'pass': ['foot']}},
        'relations': {'walk': {'type': '通不通', 'from': 'yard', 'to': '@1', 'who': 'foot'}},
    }
    with pytest.raises(DesignError, match=r'walk.*@1.*name'):
        Design(data)


def test_named_level_vehicle_gate_uses_width_and_crossing():
    sketch = Design({
        'version': 2,
        'blocks': {'yard': {'height': 3, 'use': 'park', 'at': [500, 200]},
                   'woods': {'height': 3, 'use': 'woodland', 'at': [500, 650]}},
        'points': {'yardGate': {'block': 'yard', 'at': [500, 200]},
                   'laneEnd': {'block': 'woods', 'at': [500, 600]}},
        'borders': {'frame': {'line': [[0, 0], [1000, 0], [1000, 800], [0, 800], [0, 0]]},
                    'trees': {'line': [[0, 400], [1000, 400]], 'pass': [], 'width': 100, 'segments': {
                        'gate': {'from': 'yardGate', 'to': 'laneEnd',
                                 'pass': ['foot', 'vehicle', 'amphibian']}}}},
    })
    assert [(a, b) for a, b, _, _, name in sketch.border_sections('trees') if name == 'trees.gate'] == [
        ((450, 400), (550, 400))]
