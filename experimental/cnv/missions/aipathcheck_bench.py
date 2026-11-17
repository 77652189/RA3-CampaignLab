"""Engine line D round 152: AIStrategicStateDefinition.PathfindingCheckType (24 retail uses, 23 of them None; read
back by checks/engine_aipathcheck.py; RA3-EngineModel ra3model/ai/tactics.py _path_check).

The program (work/re d62_b_fields.md 1): the tactic's periodic check, once its teams are idle, puts every ground
member with no way to the target (QuickDoesPathExist) or to a spot in its weapon's reach (QuickDoesAttackPathExist)
back in the player's default team; a team left empty ends the tactic. None: no check. Not written: the tactic class's
default (SimpleAttack: QuickDoesAttackPathExist).

ainamed_bench's ainmfar (2-4 Peacekeepers by SimpleAttack, EndBehavior RAMPAGE, at a NamedObject) aimed at the
player's yard on the west bank, with Niagara's bridges taken away (aiopath_bench.disconnected: no land way across);
a passive CNVTeams host logs the team's members; the player's three turrets are taken away. The four builds differ in the state's PathfindingCheckType only:
  aipfdef    not written (the class default, QuickDoesAttackPathExist)
  aipfatk    QuickDoesAttackPathExist
  aipfpath   QuickDoesPathExist
  aipfnone   None -- the team keeps its members on the east bank
Facts: wake at; 'path check' (the value, '' not written).
"""
import types

from missions import ainamed_bench as an
from missions.aiteamfields_bench import _host

YARD = 'UNIT - CNV AI Player Yard'
STATE = '<AIStrategicStateDefinition id="CNVStateGo" MaxTargets="1"'


def _no_bridges(m):
    cp = types.ModuleType(m.map.__name__)
    cp.__dict__.update(vars(m.map))
    cp.BRIDGES = []
    cp.OBJECTS = [o for o in cp.OBJECTS if o.template != 'HB_Bridge_02']
    m.map = cp


def mission(mod, check=''):
    m = an.mission(mod, 'NamedObject', YARD)
    (fname, xml, asset), = m.assets
    assert xml.count(STATE) == 1
    if check:
        xml = xml.replace(STATE, f'{STATE} PathfindingCheckType="{check}"')
    m.assets = [(fname, xml, asset)]
    _no_bridges(m)
    # the player's turrets (two at the east gate on the team's way, one by the yard) go: nothing should shoot the team
    m.objects = [o for o in m.objects if 'Turret' not in o.name]
    m.cast = {k: r for k, r in m.cast.items() if 'turret' not in k}
    m.facts['path check'] = check
    return _host(m)


MISSION = {
    'aipfdef': lambda: mission('CampAIPfDef'),
    'aipfatk': lambda: mission('CampAIPfAtk', 'QuickDoesAttackPathExist'),
    'aipfpath': lambda: mission('CampAIPfPath', 'QuickDoesPathExist'),
    'aipfnone': lambda: mission('CampAIPfNone', 'None'),
}
