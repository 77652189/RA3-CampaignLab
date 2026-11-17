"""Engine probe: the skirmish AI team's EnterBaseDefenses (engine line B, layer 4; read back by
checks/engine_aibasedef.py; program: work/re l4_micro_engage.md 1.7 -- the turret-order routine, called in team states 2 / 4 / 5 with
the AI player's object list of class 0x2e; state 8 only with EnterBaseDefensesWhenIdle).

Retail data: AlliedBaseDefense (the Multigunner turret; KindOf FS_BASE_DEFENSE GARRISONABLE_UNTIL_DESTROYED) carries a
GarrisonContain, ContainMax 1, PassengerFilter INFANTRY, allies inside allowed. (Soviet / Japan base defenses carry no
garrison contain; only the Allied one qualifies.)

airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0: the team
fights there, state 2, and dies) with FOUR of the AI's own AlliedBaseDefense 200 north of the far plant (80 apart: the
team stands to fight within 150 of them, one place each):
  aibd1     EnterBaseDefenses true  -> the model: Peacekeepers go into the turrets (ENCLOSED), leave the team
  aibd0     EnterBaseDefenses false -> nobody goes in
  aibdidle  EnterBaseDefenses false, EnterBaseDefensesWhenIdle true -> nobody (the team fights, never idle at a turret)
  aibdwho   as aibd1, counted by turret (who stands next to which): why only one went in. The turret-order routine takes, for each
            member in one pass, the FIRST turret of the list within 150 that it can be ordered into -- if 'can' does
            not see where the earlier members of the same pass were sent, all four go to the same turret
  aibdpre   as aibdwho, with a fifth Peacekeeper of s1 put into turret 1 by script at the start (full from s0): does
            the member's 'can be ordered into' see a full turret? Seen -> the team goes on to turret 2 and one goes in
            (进炮塔 2); not seen -> they crowd turret 1 again and nobody else gets in (进炮塔 stays 1)
Facts: wake at.
"""
from missions import airetreat_bench as ar

TURRET = 'AlliedBaseDefense'
NEAR = 200.0                             # north (+) of the far plant
SPREAD = (-120.0, -40.0, 40.0, 120.0)
EAST = 40.0
# Turrets 1 and 3 (and the sitter) stand on a wooden fence and a tree of niagara's scenery. Kept so: the round-66c
# readings were taken here, and the row moved clear (EAST -20, NEAR 150) changes which turrets are within 150 of the
# team (tests/test_simai.py turret order). tests/test_maps.py names these builds as placed so on purpose.


def mission(mod, sitter=False, **fields):
    m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', **fields)
    for k, dx in enumerate(SPREAD):
        m.put(TURRET, 'carrier home', EAST + dx, NEAR, side='s1', name=f'UNIT - CNV AI Turret {k + 1}',
              role=f'turret {k + 1}')
    if sitter:                           # garrisoned into turret 1 at s0 by the check's script
        (inf,) = m.cnv_units
        m.put(inf, 'carrier home', EAST + SPREAD[0], NEAR + 30.0, side='s1', name='UNIT - CNV AI Sitter',
              role='sitter')
    return m


IDLE_TURRETS = (-180.0, (-120.0, -40.0, 40.0, 120.0))   # aibdi*: x and the ys off 'east base' (the AI's yard): the
# four Peacekeepers stand at (-100, -90..90), each 85-90 from its nearest turret (< EnterGarrisonableStructureDistance 150)


def idle_mission(mod, **fields):
    """D round 132 (work/re/d131_triggers.md 2): EnterBaseDefensesWhenIdle acts only in the team's micro state 8 (idle /
    default) and only with EnterBaseDefenses on too. aidefense_bench's StaticDefense team (4 Peacekeepers beside the
    AI's yard, no enemy near: the team stays in state 8) without its move order, with the micro manager's two fields
    set (airetreat_bench.micro_xml) and four of the AI's AlliedBaseDefense 80-90 west of the men; the teams host
    (tstate: the team's state when they go in)."""
    from missions import aidefense_bench as ad
    from missions import airetreat_bench as ar
    from missions.aiteams_bench import host_unit, HOST
    m = ad.mission(mod, 250, 1, 1.5)
    m.scripts = [s for s in m.scripts if s.name != 'CNV AI - Move']
    (fname, xml, asset), = m.assets
    head = '  <AIStrategicStateDefinition'
    xml = xml.replace(head, ar.micro_xml(**fields) + '\n' + head, 1)
    assert xml.count('MicroManager="StandardMicroManager_MEDIUM"') == 1
    xml = xml.replace('MicroManager="StandardMicroManager_MEDIUM"', f'MicroManager="{ar.MICRO_ID}"', 1)
    m.assets = [(fname, xml, asset)]
    m.facts['micro'] = dict(fields)
    x, ys = IDLE_TURRETS
    for k, y in enumerate(ys):
        m.put(TURRET, 'east base', x, y, side='s1', name=f'UNIT - CNV AI Turret {k + 1}', role=f'turret {k + 1}')
    m.units.append(host_unit())
    m.put(HOST, 'east base', 250.0, 400.0, side='s1', role='teams host')
    m.ext = True
    return m


MISSION = {
    'aibdi1': lambda: idle_mission('CampAIBdI1', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='true'),
    'aibdi0': lambda: idle_mission('CampAIBdI0', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
    'aibdi2': lambda: idle_mission('CampAIBdI2', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='true'),
    'aibd1': lambda: mission('CampAIBd1', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
    'aibd0': lambda: mission('CampAIBd0', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='false'),
    'aibdidle': lambda: mission('CampAIBdIdle', EnterBaseDefenses='false', EnterBaseDefensesWhenIdle='true'),
    'aibdwho': lambda: mission('CampAIBdWho', EnterBaseDefenses='true', EnterBaseDefensesWhenIdle='false'),
    'aibdpre': lambda: mission('CampAIBdPre', sitter=True, EnterBaseDefenses='true',
                               EnterBaseDefensesWhenIdle='false'),
}
