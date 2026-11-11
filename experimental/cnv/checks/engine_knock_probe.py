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
Round 24 adds a third lane, 'tank' (its own check, `cnv_check engine_knock_probe tank`, CampKPTank: four counter
lines at most, so a check fires two lanes; the others stand by NO_ATTACK): the 'strong' shot at a Hammer copy carrying the same probe (CNV_KnockHammer,
MaxHealth 550: 1.5 reads 99), a second Hammer 80 to its side -- does a vehicle move where the infantry did not?
"""
import os
import re

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit
from checks.engine_clip import ORDER, clip_v4
from checks.engine_suppress_probe import EVERY, LINES, PROBE, probe_man

# amount, radius, z mult, neighbour offset; 'tank' (round 24) = 'strong' aimed at a vehicle (hypothesis: RA3 pushes
# only vehicles), its neighbour a second tank
LANES = {'mild': (89, 50, 1.5, 30), 'strong': (89, 250, 8.5, 60), 'tank': (89, 250, 8.5, 80)}
SITE = {'mild': 'base gun', 'strong': 'high gun', 'tank': 'order gun'}   # probe_range sites
TANK, PROBE_TANK = 'SovietAntiVehicleVehicleTech1', 'CNV_KnockHammer'    # the Hammer, MaxHealth 550
TARGET = {'mild': PROBE, 'strong': PROBE, 'tank': PROBE_TANK}
RUN = ORDER + 8.0


def probe_tank():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', TANK + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{TANK}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{TANK}"', f'id="{PROBE_TANK}"', 1).replace(f'EditorName="{TANK}"', f'EditorName="{PROBE_TANK}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(PROBE_TANK, x, names=dict(unit=PROBE_TANK),
                what='锤子坦克的复制（探针）：多一个 ra3ext 的 CNVProbe 模块，逐帧记位置（击飞车道的目标）',
                params=dict(of=TANK, every=EVERY, lines=LINES))


def units():
    return [gun(k) for k in LANES] + [probe_man(), probe_tank()]


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
    m = Mission(name='CampKP', map=probe_range, units=units(), facts={})
    m.ext = True                  # + the check's name: CampKPShot (<= 15)
    for lane, site in SITE.items():
        m.put('CNV_Knock' + lane.title(), site, 0, 0, side='p1', angle=1.5708, name=name(lane, 'gun'))
        m.put(TARGET[lane], site, 0, 450, side='s1', role=lane, name=name(lane, 'man'))
        m.put(TARGET[lane], site, LANES[lane][3], 450, side='s1', name=name(lane, 'near'))
    return m


CHECK_LANES = {'shot': ('mild', 'strong'), 'tank': ('tank',)}   # four counter lines at most: two lanes a check


def check(m, which):
    m.units = units()
    fired = CHECK_LANES[which]          # the other lanes stand there, every gun NO_ATTACK
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in LANES for p in ('gun', 'man', 'near')]
    start += [('SET_MILLISECOND_TIMER', 'Knock Fire', float(ORDER)),
              ('SET_MILLISECOND_TIMER', 'Knock Stop', ORDER + 4 / 15)]
    t.scripts.append(Script('Test - start', [], start))
    fire, stop = [], []
    for k in fired:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 1))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Knock Fire')], fire))
    t.scripts.append(Script('Test - stop', [('TIMER_EXPIRED', 'Knock Stop')], stop))
    expect = {}
    for k in fired:
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
CHECKS = {'engine_knock_probe': {k: (lambda m, k=k: check(m, k)) for k in CHECK_LANES}}
