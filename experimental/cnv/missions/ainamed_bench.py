"""Engine probe: AI targets named in the data -- HeuristicType NamedObject / Waypoint (engine line B, layer 4;
read back by checks/engine_ainamed.py; RA3-EngineModel ra3model/ai/targets.py).

The retail campaign drives its AI almost wholly through these: AITargetHeuristicLibrary.xml has 145 NamedObject
heuristics (143 the campaign's AITarget_*) and 94 Waypoint (92 campaign), each only `Name` (an object's script name /
a waypoint's name), sometimes Relationship, Location, RequireUniqueTarget.

The map, AI and structures are aitarget_bench's (near power plant at the east gate with two turrets, far plant south
of the AI base, the player's yard on the west bank); the one always-on state sends 2-4 Peacekeepers by SimpleAttack
(EndBehavior RAMPAGE) to the probe's own heuristic, added to the personality's asset file:
  ainmfar   NamedObject Name="UNIT - CNV AI Far Plant": the far plant, though the nearest (the control aitargetnear,
            SimpleAttack + ClosestStructureHeuristic) is the near one
  ainmwp    Waypoint Name="CNV AI WP Target" at 'route 2' (north of the AI base, nothing there): the team walks there
  ainmrel   NamedObject Name="UNIT - CNV AI Far Plant" Relationship="NEUTRAL": the far plant is the player's (an enemy),
            so if Relationship filters, no target, no team leaves
  ainmnone  NamedObject Name="UNIT - CNV AI No Such Thing": a name nobody has -- no target, no team
Facts: wake at.
"""
from missions import aitarget_bench as at

HEUR = 'CNVTgtNamed'
WP = 'CNV AI WP Target'
WP_SITE = 'route 2'
FAR_NAME = 'UNIT - CNV AI Far Plant'


def heuristic_xml(kind, name, extra=''):
    return f'  <AITargetingHeuristic id="{HEUR}" HeuristicType="{kind}" Name="{name}"{extra}/>'


def mission(mod, kind, name, extra=''):
    m = at.mission(mod, HEUR, 'SimpleAttack')
    m.cnv_heuristic = (kind, name, extra)
    (fname, xml, asset), = m.assets
    head = '  <AIStrategicStateDefinition'
    assert head in xml
    m.assets = [(fname, xml.replace(head, heuristic_xml(kind, name, extra) + '\n' + head, 1), asset)]
    m.waypoint('wp target', WP, WP_SITE)
    return m


MISSION = {
    'ainmfar': lambda: mission('CampAINmFar', 'NamedObject', FAR_NAME),
    'ainmwp': lambda: mission('CampAINmWp', 'Waypoint', WP),
    'ainmrel': lambda: mission('CampAINmRel', 'NamedObject', FAR_NAME, ' Relationship="NEUTRAL"'),
    'ainmnone': lambda: mission('CampAINmNone', 'NamedObject', 'UNIT - CNV AI No Such Thing'),
}
