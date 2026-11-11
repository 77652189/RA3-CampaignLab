"""Engine line D, round 23 (ADR 0027/0028): knock-back (MetaImpactNugget -> Physics) read by ra3ext's probe.

The counters see only whether a man lives and how hurt he is; the trajectory of a knocked-back man is inside the
engine. The men here are engine_suppress_probe's CNV_SuppProbeMan (a Peacekeeper copy carrying ra3ext's CNVProbe,
read-only); since round 23 CNVProbe writes a line every frame its host's x / y / z moves, so
ra3ext.log in the run folder holds each man's path frame by frame.

Two lanes, one instant shot each at ORDER (V4 copies from engine_clip, rocket swapped for an instant 1.5 UNRESISTABLE
DamageNugget plus a retail MetaImpactNugget): 'mild' = Weapon.xml's ShockWaveAmount 89 / Radius 50 / ZMult 1.5,
'strong' = Amount 89 / Radius 250 / ZMult 8.5 (the retail one with ShockwaveDelaySeconds, here without the delay).
Each lane: the target man 450 in front of the gun and a neighbour NEAR to his side (inside the radius) -- the target
is hit at his own position (no horizontal direction), the neighbour off-centre (pushed away from the hit).
Everyone is NO_ATTACK but the gun's one shot. The expectations are the health predictions (target 99 = 1.5 of 150,
neighbour 100: the DamageNugget has Radius 0); the trajectories are read off ra3ext.log.
Bench 11-10 PASS, but no man moved at all (x / y / z the same every frame): this is the Peacekeeper's reading, not
yet a knock-back trajectory -- see the line's private handoff for what to try next.
"""
import re

from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_clip import ORDER, clip_v4
from checks.engine_suppress_probe import PROBE, probe_man

LANES = {'mild': (89, 50, 1.5, 30), 'strong': (89, 250, 8.5, 60)}   # amount, radius, z mult, neighbour offset
SITE = {'mild': 'base gun', 'strong': 'high gun'}                   # probe_range sites (engine_suppression's lanes)
RUN = ORDER + 8.0


def name(lane, part):
    return f'UNIT - CNV Knock {lane} {part}'


def gun(lane):
    amount, radius, zmult, _ = LANES[lane]
    uid = 'CNV_Knock' + lane.title()
    u = clip_v4('bare', hit=1.5, uid=uid, spec=(0, 1 / 15, 1.0, 1, 'PRE_FIRE', (), RUN, 'knock'))
    u.xml, n = re.subn(r'<Nuggets>.*?</Nuggets>',
                       '<Nuggets><DamageNugget Damage="1.5" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="0"/>'
                       f'<MetaImpactNugget ShockWaveAmount="{amount}" ShockWaveRadius="{radius}" '
                       f'ShockWaveZMult="{zmult}"/></Nuggets>', u.xml, flags=re.S)
    assert n == 1
    u.what = f'击飞 V4（探针）：瞬发 1.5 伤害 + MetaImpactNugget 冲击 {amount} 半径 {radius} 竖直倍数 {zmult}'
    return u


def mission():
    m = Mission(name='CampKP', map=probe_range, units=[gun(k) for k in LANES] + [probe_man()], facts={})
    m.ext = True                  # + the check's name: CampKPShot (<= 15)
    for lane, site in SITE.items():
        m.put('CNV_Knock' + lane.title(), site, 0, 0, side='p1', angle=1.5708, name=name(lane, 'gun'))
        m.put(PROBE, site, 0, 450, side='s1', role=lane, name=name(lane, 'man'))
        m.put(PROBE, site, LANES[lane][3], 450, side='s1', name=name(lane, 'near'))
    return m


def check(m):
    m.units = [gun(k) for k in LANES] + [probe_man()]
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in LANES for p in ('gun', 'man', 'near')]
    start += [('SET_MILLISECOND_TIMER', 'Knock Fire', float(ORDER)),
              ('SET_MILLISECOND_TIMER', 'Knock Stop', ORDER + 4 / 15)]
    t.scripts.append(Script('Test - start', [], start))
    fire, stop = [], []
    for k in LANES:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 1))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Knock Fire')], fire))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Knock Stop')], stop))
    expect = {}
    for k in LANES:
        for p, hp in (('man', 99), ('near', 100)):
            c = f'CNV_Knock_{k}_{p}'
            t.counters.append((c, f'{k} {p}'))
            t.scripts.append(Script(f'Test - health {k} {p}', [],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(k, p), c)], once=False))
            expect[f'{k} {p}'] = hp
    t.expect = [(label, RUN - 2, '==', expect[label], RUN) for _, label in t.counters]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_probe': mission}
CHECKS = {'engine_knock_probe': {'shot': check}}
