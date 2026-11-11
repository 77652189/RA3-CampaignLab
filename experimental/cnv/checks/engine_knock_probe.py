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
Bench 11-10 PASS, and neither tank moved either.
Round 25, `retail` (CampKPRetail): 'yuri' = the instant gun with retail PsyonicBlast's MetaImpactNugget verbatim,
'rocket' = the strong shock in the warhead of retail's V4 rocket. Bench 11-10 PASS (all four health readings as
predicted); the yuri men stay put, the rocket's target flies (from frame 175, still airborne when the run ends at 266)
and its neighbour hops ~20 away: MetaImpact pushes only from a detonation (a projectile's), not from an instant hit.
Round 26, `land` (CampKPLand): the rocket lane alone, RUN = ORDER + 14 s. Bench 11-10 PASS (man 99, neighbour 100,
not dead): the flung man lands at frame 300 at (2300, 3060), 690 back towards the gun, and lies still; no fall damage.
This run's flight is higher than round 25's (vz 111 / frame against 65, horizontal 5.4 against 7.9), but both last
~127 frames and both are a clean parabola, z - ground = c n (N - n) for flight frame n of N.
Round 27: not chance -- four `land` runs and two `retail` runs repeat their own check's trajectory frame for frame
(retail's man lands at frame 301 at (2300, 2740)), and the neighbour's hop is the same in both checks, so the
detonation point is the same too; what differs is the mission (retail also fires the yuri lane, 1 500 away, and its
rocket man lifts a frame later).
Round 28, `late` / `late1` (CampKPLate / CampKPLate1): `land` with the rocket fired ORDER + 1/15 s / + 0.03 s. Bench
11-10 PASS both (99 / 100 / alive); both lift at 176, two frames after `land` (the script timer moves the shot in steps
of two frames, so retail's 175 is out of its reach), and the two runs are the same frame for frame: a third flight,
33 frames, apex 62 above the ground, landing at (2300, 3500). The neighbour's hop is the same as ever. Three hit frames,
three flights; the same hit frame, the same flight: the hit frame decides (hypothesis 7), the flight time is not fixed.
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
# 'yuri' (round 25): the MetaImpactNugget of retail's JapanCommandoTech1PsyonicBlast copied as it is (the same 89 /
# 250 / 8.5 plus ShockwaveDelaySeconds 1 s and an INFANTRY SpecialObjectFilter; retail flings infantry with it), on
# the instant gun; 'rocket' (round 25): 'strong' fired the retail way, retail's V4 rocket projectile whose warhead
# carries the 1.5 hit and the strong MetaImpactNugget
LANES = {'mild': (89, 50, 1.5, 30), 'strong': (89, 250, 8.5, 60), 'tank': (89, 250, 8.5, 80),
         'yuri': (89, 250, 8.5, 60), 'rocket': (89, 250, 8.5, 60)}
SITE = {'mild': 'base gun', 'strong': 'high gun', 'tank': 'order gun',   # probe_range sites
        'yuri': 'removed gun', 'rocket': 'switch gun'}
TANK, PROBE_TANK = 'SovietAntiVehicleVehicleTech1', 'CNV_KnockHammer'    # the Hammer, MaxHealth 550
TARGET = {k: PROBE for k in LANES}
TARGET['tank'] = PROBE_TANK
YURI = 'JapanCommandoTech1PsyonicBlast'
STOP = {k: 4 / 15 for k in LANES}
STOP['rocket'] = 2.0                # retail's 0.5 s pre-attack must pass before NO_ATTACK; reload 4.5 s: one rocket
RUN = ORDER + 8.0
# round 26, `land`: the rocket lane alone, run long enough for the flung man to come down (round 25: apex ~frame 238
# at z 2278, gravity ~1.02 / frame^2 -> ground 212.5 ~frame 302, the run ended at 266) and stand up again
# (Physics ShockStandingTime 1.5 s default); the yuri / shot / tank lanes keep RUN
RUNS = {'land': ORDER + 14.0, 'late': ORDER + 14.0, 'late1': ORDER + 14.0}
# round 28, `late`: `land` with the rocket fired one frame later (ORDER + 1/15; the stop timer moves with it). Round 27:
# retail's rocket man lifts at 175 and flies lower (vz0 64.55) than land's (174, 111.16). If `late` flies retail's way,
# the hit frame decides (hypothesis 7: the man's own state at that frame); if it flies land's way one frame later, what
# else fires in the mission does (hypothesis 6: shared state such as the random sequence)
FIRE = {'late': 1 / 15, 'late1': 0.03}
# engine line A round 162, `stand` / `standlate` (CampKPStand / CampKPStandlate): `land`, and at ORDER + MOVE the flung
# man is sent east (MOVE_STAND: off his landing spot, clear ground) and, on the same frame, the mild lane's man (not
# shot at: the control) the same 400 east -- the control's first move frame is the order's frame plus the start
# latency, so how long the flung man is held after landing reads off the probe log. Prediction from the data: the
# Peacekeeper's Physics is all defaults, ShockStunnedTimeLow / High 1 s + ShockStandingTime 1.5 s (PhysicsBehavior.xsd):
# held 15 + 22.5 frames after landing. Bench 11-11 `stand` PASS: the order came at frame 248 (the control moves at
# 249; script frame = mission seconds x 15), the man still in the air (lift 174, last airborne frame 299, on the
# ground at (2300, 3060) from 300), and he kept it: first step at 338 = landing + 38. `standair` (ORDER + 5, frame
# 165) came before the rocket's hit at 174: the man walked off and the rocket missed -- replaced by `standlate`,
# the order 10 frames after the landing (frame 310): the same 338 = a lock from the landing, not from the order.
MOVE = {'stand': 10.5, 'standlate': 310 / 15 - ORDER}
RUNS.update({k: ORDER + 20.0 for k in MOVE})
MOVE_STAND, MOVE_CONTROL = 'Test Knock Stand Away', 'Test Knock Control Away'
# bench 11-10: ORDER + 1/15 came out two frames late (lift 176 against land's 174); `late1` (+0.03 s) aimed at one
# frame, retail's hit frame (lift 175), and came out two frames late as well
HIT = '<DamageNugget Damage="1.5" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="0"/>'


def yuri_shock():
    """Retail's PsyonicBlast MetaImpactNugget, verbatim."""
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'GlobalData', 'Weapon.xml'), encoding='utf-8') as f:
        w = f.read()
    s = re.search(rf'<WeaponTemplate\s+id="{YURI}".*?</WeaponTemplate>', w, re.S).group(0)
    found = re.findall(r'<MetaImpactNugget.*?</MetaImpactNugget>', s, re.S)
    assert len(found) == 1 and 'ShockwaveDelaySeconds="1.0s"' in found[0] and 'Include="INFANTRY"' in found[0]
    return found[0]


def rocket_gun(uid='CNV_KnockRocket', shock=None):
    """Retail's V4 with its retail rocket (no scatter), the rocket's warhead swapped for <uid>Warhead: the 1.5 hit
    and the strong MetaImpactNugget (or `shock` = (amount, radius, z mult)), retail warhead's collide / affects flags."""
    from checks.engine_missile import home_v4
    amount, radius, zmult = shock or LANES['rocket'][:3]
    u = home_v4(uid, adjust=10.0, scatter=False)
    old = 'WarheadTemplate="SovietAntiStructureVehicleV4RocketWarhead"'
    assert u.xml.count(old) == 1
    u.xml = u.xml.replace(old, f'WarheadTemplate="{uid}Warhead"')
    warhead = (f'\t<WeaponTemplate id="{uid}Warhead" ProjectileCollidesWith="ALLIES ENEMIES NEUTRAL STRUCTURES '
               'WALLS" RadiusDamageAffects="ALLIES ENEMIES NEUTRALS SELF" Flags="ATTACK_NEEDS_LINE_OF_SIGHT '
               'NOT_ATTRACTED_BY_MAGNETS" RequiredAntiMask="ANTI_WATER ANTI_GROUND ANTI_STRUCTURE">'
               f'<Nuggets>{HIT}<MetaImpactNugget ShockWaveAmount="{amount}" ShockWaveRadius="{radius}" '
               f'ShockWaveZMult="{zmult}"/></Nuggets></WeaponTemplate>\n')
    u.xml = u.xml.replace('</AssetDeclaration>', warhead + '</AssetDeclaration>', 1)
    u.link = list(u.link) + [f'WeaponTemplate:{uid}Warhead']
    u.what = f'击飞 V4（探针）：原版火箭弹体，弹头 1.5 伤害 + MetaImpactNugget 冲击 {amount} 半径 {radius} 竖直倍数 {zmult}'
    return u


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
    if lane == 'rocket':
        return rocket_gun()
    amount, radius, zmult, _ = LANES[lane]
    uid = 'CNV_Knock' + lane.title()
    u = clip_v4('bare', hit=1.5, uid=uid, spec=(0, 1 / 15, 1.0, 1, 'PRE_FIRE', (), RUN, 'knock'))
    shock = yuri_shock() if lane == 'yuri' else (f'<MetaImpactNugget ShockWaveAmount="{amount}" '
                                                 f'ShockWaveRadius="{radius}" ShockWaveZMult="{zmult}"/>')
    u.xml, n = re.subn(r'<Nuggets>.*?</Nuggets>', lambda _: f'<Nuggets>{HIT}{shock}</Nuggets>', u.xml, flags=re.S)
    assert n == 1
    u.what = (f'击飞 V4（探针）：瞬发 1.5 伤害 + ' +
              ('原版百合子念力爆的 MetaImpactNugget 原样（延迟 1 秒、只含步兵）' if lane == 'yuri' else
               f'MetaImpactNugget 冲击 {amount} 半径 {radius} 竖直倍数 {zmult}'))
    return u


def mission():
    m = Mission(name='CampKP', map=probe_range, units=units(), facts={})
    m.ext = True                  # + the check's name: CampKPShot (<= 15)
    for lane, site in SITE.items():
        m.put('CNV_Knock' + lane.title(), site, 0, 0, side='p1', angle=1.5708, name=name(lane, 'gun'))
        m.put(TARGET[lane], site, 0, 450, side='s1', role=lane, name=name(lane, 'man'))
        m.put(TARGET[lane], site, LANES[lane][3], 450, side='s1', name=name(lane, 'near'))
    return m


CHECK_LANES = {'shot': ('mild', 'strong'), 'tank': ('tank',),    # four counter lines at most: two lanes a check
               'retail': ('yuri', 'rocket'), 'land': ('rocket',), 'late': ('rocket',),
               'late1': ('rocket',), 'stand': ('rocket',), 'standlate': ('rocket',)}
# `land` also counts whether the flung man died (a dead man's health counter keeps its last reading). Prediction from
# the data: no fall damage -- PhysicsBehavior.xsd has no fall / splat damage field and the Peacekeeper's Physics is
# all defaults -- so alive, 99.
DEAD = {'land': ('rocket',), 'late': ('rocket',), 'late1': ('rocket',), 'stand': ('rocket',), 'standlate': ('rocket',)}


def check(m, which):
    m.units = units()
    fired = CHECK_LANES[which]          # the other lanes stand there, every gun NO_ATTACK
    run = RUNS.get(which, RUN)
    late = FIRE.get(which, 0.0)
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, p), 'NO_ATTACK', 1) for k in LANES for p in ('gun', 'man', 'near')]
    stops = sorted({STOP[k] for k in fired})
    start += [('SET_MILLISECOND_TIMER', 'Knock Fire', float(ORDER + late))]
    start += [('SET_MILLISECOND_TIMER', f'Knock Stop {i}', ORDER + late + s) for i, s in enumerate(stops)]
    start += [('SET_COUNTER', f'CNV_Knock_{k}_dead', 0) for k in DEAD.get(which, ())]
    t.scripts.append(Script('Test - start', [], start))
    fire = []
    for k in fired:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Knock Fire')], fire))
    if which in MOVE:
        t.waypoints[MOVE_STAND] = (2700.0, 3060.0)          # `land`'s landing spot (2300, 3060), 400 east
        t.waypoints[MOVE_CONTROL] = tuple(m.site(SITE['mild'], 400.0, 450.0))
        t.scripts[0].do.append(('SET_MILLISECOND_TIMER', 'Knock Move', float(ORDER + late + MOVE[which])))
        t.scripts.append(Script('Test - move', [('TIMER_EXPIRED', 'Knock Move')],
                                [('MOVE_NAMED_UNIT_TO', name('rocket', 'man'), MOVE_STAND),
                                 ('MOVE_NAMED_UNIT_TO', name('mild', 'man'), MOVE_CONTROL)]))
    for i, s in enumerate(stops):
        t.scripts.append(Script(f'Test - stop {i}', [('TIMER_EXPIRED', f'Knock Stop {i}')],
                                [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 1)
                                 for k in fired if STOP[k] == s]))
    expect = {}
    for k in fired:
        for p, hp in (('man', 99), ('near', 100)):
            c = f'CNV_Knock_{k}_{p}'
            t.counters.append((c, f'{k} {p}'))
            t.scripts.append(Script(f'Test - health {k} {p}', [],
                                    [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name(k, p), c)], once=False))
            expect[f'{k} {p}'] = hp
    for k in DEAD.get(which, ()):
        c = f'CNV_Knock_{k}_dead'
        t.counters.append((c, f'{k} dead'))
        t.scripts.append(Script(f'Test - dead {k}', [('NAMED_DESTROYED', name(k, 'man'))], [('SET_COUNTER', c, 1)]))
        expect[f'{k} dead'] = 0
    t.expect = [(label, run - 2, '==', expect[label], run) for _, label in t.counters]
    t.bench = [('bench_watch', dict(seconds=run, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_probe': mission}
CHECKS = {'engine_knock_probe': {k: (lambda m, k=k: check(m, k)) for k in CHECK_LANES}}
