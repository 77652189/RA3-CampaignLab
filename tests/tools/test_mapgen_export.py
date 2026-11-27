from runpy import run_path
from types import SimpleNamespace

import numpy as np

from experimental.mapgen.build import MapBuild
from experimental.mapgen.buildings import Layout
from experimental.mapgen.design import Design
from experimental.mapgen.export import _interface, module_bytes
from experimental.mapgen.terrain import DesignFrame, TerrainPlan


def test_exported_mission_interface(tmp_path):
    from experimental.cnv import build as cnv
    from model import Script

    data = {
        'version': 2,
        'borders': {
            'rim': {'line': [[0, 0], [4000, 0], [4000, 4000], [0, 4000], [0, 0]]},
            'divide': {'line': [[1800, 0], [1800, 4000]]},
        },
        'blocks': {
            'west': {'at': [900, 2000], 'height': 3, 'use': 'park'},
            'east': {'at': [2700, 2000], 'height': 3, 'use': 'park'},
        },
        'points': {
            'spawn': {'block': 'west', 'at': [1200, 1800]},
            'lookout': {'block': 'east', 'at': [2700, 2200], 'use': 'watch the road'},
        },
        'states': {'eastOnly': {'playable': ['east']}, 'reopened': {}},
        'mission': {
            'starts': {'Player_1_Start': 'spawn'},
            'paths': {'patrol': ['spawn', 'lookout']},
            'regions': {'watchZone': {'point': 'lookout', 'radius': 40}},
        },
    }

    def generate(data):
        frame = DesignFrame(np.empty((500, 500), dtype=bool), (0, 0, 400, 400))
        built = MapBuild(TerrainPlan(), SimpleNamespace(pieces=()), None, Layout(()), Design(data), frame, ())
        return module_bytes(_interface(built, 0))

    source = generate(data)
    reordered = dict(reversed(tuple(data.items())))
    reordered['points'] = dict(reversed(tuple(data['points'].items())))
    reordered['states'] = dict(reversed(tuple(data['states'].items())))
    assert generate(reordered) == source

    path = tmp_path / 'generated.py'
    path.write_bytes(source)
    published = run_path(str(path))
    assert published['SITES']['lookout'].at() == (2700, 2200)
    assert published['STARTS']['Player_1_Start'] == 'spawn'
    borders = list(published['BORDERS'].values())
    assert {name: borders[index] for name, index in published['STATE_BORDERS'].items()} == {
        'base': (0, 0, 4400, 4400),
        'eastOnly': (1400, 0, 4400, 4400),
        'reopened': (0, 0, 4400, 4400),
    }

    mission = published['mission']('GeneratedMap')
    mission.put('AlliedAntiInfantryInfantry', 'spawn', name='Scout')
    mission.scripts.append(Script('Patrol', [('NAMED_INSIDE_AREA', 'Scout', 'watchZone')],
                                  [('NAMED_FOLLOW_WAYPOINTS', 'Scout', 'patrol')]))
    contract = cnv.parts.contract
    assert contract(mission) == []
    mission.scripts.append(Script('Test - missing mark', [], [('MOVE_NAMED_UNIT_TO', 'Scout', 'missing')]))
    assert contract(mission) == ["Test - missing mark: MOVE_NAMED_UNIT_TO waypoint 'missing' not published"]
