"""Engine line D round 77: aiskcap (B's, missions/aiskirm_bench.py, unchanged) with ra3ext's CNVOrders module
(`<DeletionUpdate id="ModuleTag_CNVOrders" .../>`, passive) added to a copy s1 already owns, so no template changes:

  aiskcapo: on the copied barracks CNVAIBarracks (aiskcap's own new template; only a behavior is added).
  aiskcapy: on a copy of the AI's construction yard (CNVOrdersYard) -- a template swap; on the bench (D 77) this
            changes the game: the new Peacekeepers stay at the cap of 2 to s168 (aiskcap: 3 at s150).

Every frame the module hashes the AI brain's order registry and, when it changed (and every EVERY frames), logs each
order (vtable, template id, state, kind, whether its id is in the UnitBuilder's vector) to the run folder's
ra3ext.log. Question (B handoff 148, D 76): is the order that takes CNVNewPK past its SpecificUnitCap of 2 after ~s150
a UnitBuilder order? Its check is checks/engine_aiorders.py (aiskcap's y).
"""
import dataclasses
import os

import labpaths
from missions.aiskirm_bench import NEW_BARRACKS, mission as aiskirm_mission
from parts import Unit

YARD, HOST, EVERY, LINES = 'AlliedConstructionYard', 'CNVOrdersYard', 150, 20000
MODULE = f'<DeletionUpdate id="ModuleTag_CNVOrders" MinFrames="{EVERY}" MaxFrames="{LINES}"/>'


def host_unit():
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', YARD + '.xml'), encoding='utf-8').read()
    assert x.count(f'id="{YARD}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{YARD}"', f'id="{HOST}"').replace('<Behaviors>', f'<Behaviors>\n\t\t\t{MODULE}')
    return Unit(HOST, x, names=dict(unit=HOST), what='原建造厂附带被动 AI 单表日志（CNVOrders）', params=dict(every=EVERY))


def on_yard():
    m = aiskirm_mission('CampAISkCapY2', new=True, cap=2)
    ai_yard = [o for o in m.objects if o.template == YARD and o.side == 's1']
    assert len(ai_yard) == 1
    m.objects[m.objects.index(ai_yard[0])] = dataclasses.replace(ai_yard[0], template=HOST)
    for role in m.cast.values():
        if role.template == YARD and role.side == 's1':
            role.template = HOST
    m.units.append(host_unit())
    m.ext = True
    return m


def on_barracks():
    m = aiskirm_mission('CampAISkCapO', new=True, cap=2)
    (u,) = [u for u in m.units if u.id == NEW_BARRACKS]
    assert u.xml.count('<Behaviors>') == 1
    u.xml = u.xml.replace('<Behaviors>', f'<Behaviors>\n\t\t\t{MODULE}')
    m.ext = True
    return m


MISSION = {'aiskcapo': on_barracks, 'aiskcapy': on_yard}
