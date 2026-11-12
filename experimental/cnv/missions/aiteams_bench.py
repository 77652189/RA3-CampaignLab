"""Engine line D round 68: aicreate_bench's aicr3 plus one object of the AI's own, a copy of the Allied power plant
with ra3ext's CNVTeams module (`<DeletionUpdate id="ModuleTag_CNVTeams" .../>`; a structure without CAN_ATTACK, so
no team takes it), built with ext=True. Every EVERY frames the module logs the host owner's teams to the run folder's
ra3ext.log (read by experimental/cnv/teamlog.py). Its check is checks/engine_aiteams.py.
"""
import os

import labpaths
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
