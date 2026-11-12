"""Engine line D round 68: read the AI's teams (template name -> team -> member ids) off ra3ext's CNVTeams module, on
the C line's aicr3 game (CreateUnits MinUnits 3: engine_aicreate). The mission is aicreate_bench's aicr3 plus one
object of the AI's own: a copy of the Allied power plant with `<DeletionUpdate id="ModuleTag_CNVTeams" .../>` (a
structure without CAN_ATTACK, so no team takes it), built with ext=True. Every EVERY frames the module logs the host
owner's teams to the run folder's ra3ext.log; experimental/cnv/teamlog.py reads them by name:

  team_size(run, 'CNVStateTF', frame)

The counters and expectations are engine_aicreate's (s41..: three Guardians out, four Peacekeepers home); the team
reading is read off the log after the run (BENCH below), not asserted by the bench.
"""
import os

import labpaths
from checks.engine_aicreate import a as aicreate
from missions.aicreate_bench import mission as aicreate_mission
from parts import Unit

PLANT, HOST, EVERY, LINES = 'AlliedPowerPlant', 'CNVTeamsHost', 15, 4000


def host_unit():
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', PLANT + '.xml'), encoding='utf-8').read()
    assert x.count(f'id="{PLANT}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{PLANT}"', f'id="{HOST}"').replace(f'EditorName="{PLANT}"', f'EditorName="{HOST}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''')
    return Unit(HOST, x, names=dict(unit=HOST),
                what=f'盟军电厂的复制（探针）：多一个 ra3ext 的 CNVTeams 模块，每 {EVERY} 帧记所属玩家的队伍和成员',
                params=dict(of=PLANT, every=EVERY))


def mission():
    m = aicreate_mission(3)
    m.name, m.ext = 'CampAICrT3', True
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
    return m


MISSION = {'aicr3t': mission}
CHECKS = {'aicr3t': {'a': aicreate}}
