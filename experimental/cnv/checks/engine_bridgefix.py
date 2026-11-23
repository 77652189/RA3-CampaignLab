"""A315: Command_CaptureBuilding pressed on a bridge's gatehouse (retail j07 'if first bridge destroyed').

j07 creates an AlliedEngineer on a computer team and presses NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED
Command_CaptureBuilding at 'o_bridge_00_GateHouse2' -- a name the bridge's BridgeBuilder gives its gatehouse
(retail: the start and the end object share the bridge's name; j07 asks UNIT_HEALTH <= 1 of it for 'destroyed').
Niagara's three HB_Bridge_02 (managerbody's proven geometry): a broken by NAMED_DAMAGE 20000 at s8 (managerbody b:
the proxy shows 1 %), an engineer of s1 created 150 west of its start at s14 and pressed; b the same on the whole
bridge; c broken, no engineer (control). Lane c's end keeps the start's name, as j07; a and b's end is '<name> end'.
PREDICTION (from HB_Bridge_02_GateHouse's ModuleTag_EngineerContainBridge, not measured): the engineer walks to
the gatehouse, is consumed, the broken bridge's gatehouse goes back to 100; c stays 1.

Run 1 (bench 11-22, CampBridgeFixA_mcp_1122_202051, both lanes pressed at GateHouse2): both names exist under
either naming (start name + '_GateHouse1' / '2'); GateHouse2 not within 150 of the start; 门a / 门c 100 s1-s6,
1 from s7 (the break); the engineers alive to s53, nobody repaired, s1 owns nothing; UNIT_HEALTH('Fix a', 4, 50)
held true after the break. Run 2: a presses GateHouse1 (the near one?), b GateHouse2 of the whole bridge, and
each engineer's 'left its spawn' digit tells whether the press moved it at all.
Counters: 门a the target GateHouse1's health, 门c lane c's GateHouse1; 态a / 态b digits 1 engineer alive,
10 engineer away from its spawn, 100 its target there, 1000 the target within 150 of the start, 10000 s1 owns it.
Run 2 (CampBridgeFixA_mcp_1122_202537): 门a / 态a / 态b / 门c s1-s6 100 1110 110 100; s7-s13 1 1110 110 1; s14
1 1101 101 1; s15-s17 1 1111 111 1; s18-s68 100 1110 111 1 -- a's engineer (pressed at the near GateHouse1, which is
the start's) walked up and was gone at s18 with the bridge mended, the owner kept; b's (the whole bridge's far
GateHouse2) walked off and lived on. The 10 digit is also set while the engineer does not exist (NAMED_OUTSIDE_AREA).
"""
from types import SimpleNamespace

import platmap
from maps import island, niagara
from parts import Mission, Script, Test, square

# (lane, bridge, broken, engineer's target)
LANES = (('a', 0, True, 'Fix a_GateHouse1'), ('b', 1, False, 'Fix b_GateHouse2'), ('c', 2, True, None))


def mission():
    probe_map = SimpleNamespace(**vars(niagara))
    probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
    probe_map.OBJECTS = niagara.OBJECTS[6:]                     # all three retail pairs replaced by named ones
    m = Mission(name='CampBridgeFix', map=probe_map, units=[])
    m.spawns.add('AlliedEngineer')
    ox, oy = m.site('front')
    for lane, k, _, target in LANES:
        p, q = niagara.BRIDGES[k]
        for end, (x, y, angle, flags) in zip(('', ' end'), platmap.bridge(p, q)):
            name = 'Fix ' + lane + ('' if lane == 'c' else end)
            m.put('HB_Bridge_02', 'front', x - ox, y - oy, side='neutral', angle=angle, flags=flags,
                  role=f'{lane}{end}', name=name)
        m.areas['Fix start ' + lane] = square(p[0], p[1], 150)
        if target:
            m.waypoint(lane + ' spawn', 'Fix spawn ' + lane, 'front', p[0] - 150 - ox, p[1] - oy)
            m.areas['Fix home ' + lane] = square(p[0] - 150, p[1], 40)
    return m


def check(m):
    t = Test()
    s1 = m.player('s1')
    t.scripts = [Script('Fix start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                          ('SET_MILLISECOND_TIMER', 'Fix break', 8.0),
                                          ('SET_MILLISECOND_TIMER', 'Fix press', 14.0)]),
                 Script('Fix no budget', [], [('PLAYER_SET_MONEY', s1, 0)], once=False),
                 Script('Fix break', [('TIMER_EXPIRED', 'Fix break')],
                        [('NAMED_DAMAGE', 'Fix ' + lane, 20000) for lane, _, broken, _ in LANES if broken])]
    press = []
    for lane, _, _, target in LANES:
        state, man = 'Fix state ' + lane, 'Fix man ' + lane
        if lane != 'b':
            t.counters.append(('Fix gate ' + lane, '门' + lane))
            t.scripts.append(Script('Fix read gate ' + lane, [], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', f'Fix {lane}_GateHouse1', 'Fix gate ' + lane)], once=False))
        if not target:
            continue
        t.counters.append((state, '态' + lane))
        press += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', man, 'AlliedEngineer', m.team('s1'), m.mark(lane + ' spawn')),
                  ('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', man, 'Command_CaptureBuilding', target)]
        t.scripts.append(Script('Fix zero ' + lane, [], [('SET_COUNTER', state, 0)], once=False))
        for bit, when in ((1, ('NAMED_NOT_DESTROYED', man)), (10, ('NAMED_OUTSIDE_AREA', man, 'Fix home ' + lane)),
                          (100, ('NAMED_NOT_DESTROYED', target)),
                          (1000, ('NAMED_INSIDE_AREA', target, 'Fix start ' + lane)),
                          (10000, ('NAMED_OWNED_BY_PLAYER', s1, target))):
            t.scripts.append(Script(f'Fix bit {lane} {bit}', [when], [('INCREMENT_COUNTER', bit, state)], once=False))
    t.scripts.append(Script('Fix press', [('TIMER_EXPIRED', 'Fix press')], press))
    t.expect = [('门a', 3, '==', 100, 7), ('门a', 10, '==', 1, 14), ('门c', 10, '==', 1, 60),
                ('门a', 50, '==', 100, 60), ('态a', 50, '==', 1110, 60), ('态b', 50, '==', 111, 60)]
    t.bench = [('bench_watch', dict(seconds=62, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_bridgefix': mission}
CHECKS = {'engine_bridgefix': {'a': check}}
