"""E165: retail engineer aura self-benefit, isolated from overlapping sources.

SDK AlliedEngineer AllowFilter includes allied INFANTRY and has no self exclusion.
Prediction: at f60 hurt active source, inactive source and nearby infantry to 50%;
at f210 their HP is 100/50/100. Freeze exact-health and independent survival bits.
An f61 baseline proves the injury preceded healing. The frame counter saturates
at 240; completion expectations use logical frames, independent of capture time.
No deployment-button, overlap, beneficiary ordering or exact clock claim.

MEASURED a: baseline=7, final=6, alive=7 at f210; self-full prediction failed.
Peer diagnostic tests exact 50% source against an inactive nearby engineer:
predict source/off/ally/peer=50/50/100/100, distinguishing self exclusion from
engineer-template immunity. Original a prediction is preserved. See
work/re/e165_areaself.md.
MEASURED peer: f61 baseline=15, f210 exact-health=15 and alive=15; completed
f240=240. Source is excluded, while another engineer is eligible.
"""
from maps import probe_range
from parts import Mission, Script, Test, NOT


def mission():
    m = Mission(name='CampAreaSelf', map=probe_range, units=[])
    m.put('AlliedEngineer', 'order gun', role='source', name='Self Area Source')
    m.put('AlliedEngineer', 'base gun', role='off', name='Self Area Off')
    m.put('AlliedAntiInfantryInfantry', 'order gun', 40, 0,
          role='ally', name='Self Area Ally')
    return m


def check(m):
    return _probe(m, ('source', 'off', 'ally'), (100, 50, 100))


def peer_mission():
    m = mission()
    m.name = 'CampAreaPeer'
    m.put('AlliedEngineer', 'order gun', -40, 0,
          role='peer', name='Self Area Peer')
    return m


def peer_check(m):
    return _probe(m, ('source', 'off', 'ally', 'peer'), (50, 50, 100, 100))


def _probe(m, roles, expected):
    t = Test()
    t.counters = [('E165Frame', 'frame'), ('E165Baseline', 'hurt snapshot'),
                  ('E165Final', 'healed snapshot'), ('E165Alive', 'alive snapshot')]
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        *[('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r in roles]]),
        Script('Test - frame', [('COUNTER', 'E165Frame', 0, 240)],
               [('INCREMENT_COUNTER', 1, 'E165Frame')], once=False),
        Script('Test - hurt and activate', [('COUNTER', 'E165Frame', 2, 60)], [
            ('UNIT_CHANGE_OBJECT_STATUS', m.role('source').name, 'GENERIC_TOGGLE_STATE', 1),
            *[('UNIT_SET_HEALTH', m.role(r).name, 50.) for r in roles]])]
    for frame, counter in ((61, 'E165Baseline'), (210, 'E165Final')):
        for bit, role in enumerate(roles):
            hp = 50 if frame == 61 else expected[bit]
            t.scripts.append(Script(f'Test - HP {frame} {role}', [
                ('COUNTER', 'E165Frame', 2, frame),
                ('UNIT_HEALTH', m.role(role).name, 3, hp),
                ('UNIT_HEALTH', m.role(role).name, 1, hp)],
                [('INCREMENT_COUNTER', 1 << bit, counter)]))
    for bit, role in enumerate(roles):
        t.scripts.append(Script('Test - alive ' + role, [
            ('COUNTER', 'E165Frame', 2, 210),
            ('NAMED_DESTROYED', m.role(role).name, NOT)],
            [('INCREMENT_COUNTER', 1 << bit, 'E165Alive')]))
    full = (1 << len(roles)) - 1
    for label, value in (('frame', 240), ('hurt snapshot', full),
                         ('healed snapshot', full), ('alive snapshot', full)):
        t.expect.append((label, 0, 'ever>=', value))
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4,
                                  until='c1>=240'))]
    return t


MISSION = {'engine_areaself': mission, 'engine_areaselfpeer': peer_mission}
CHECKS = {'engine_areaself': {'a': check}, 'engine_areaselfpeer': {'a': peer_check}}
