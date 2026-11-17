"""Engine line A round 169 (for C's ActivateLiftObjectNugget, work/re/handoff-c.md): a lifted body's height frame by
frame and the frame it lands.

engine_lift's counters are two snapshots (7 s / 18 s) of LIFTED_INTO_AIR: they cannot give the lift's height or the
landing frame. Here every victim is engine_lift's 1000-health Hammer carrying ra3ext's CNVProbe (the same
DeletionUpdate tag as engine_knock_probe's CNV_KnockHammer), so the run folder's ra3ext.log has its x / y / z; and a
script counts, every frame, whether the victim has LIFTED_INTO_AIR (one counter a lane: the frames it was set).

Four lanes (probe_range's base / high / order / removed sites), engine_lift's gun (one 10 UNRESISTABLE shot at 6 s,
the ActivateLiftObjectNugget Lifetime 2 s -- unused, D50) and caster module (LiftVelocity 4, MaxTimeLifted 8 s);
each check sets TimeIncrement, MaxElevationFromGround and SoftLandingWeapon (JapanCommandoSoftLanding) a lane:
  fall    base: no nugget, no module (control) / soft 0.5 s / bare 0.5 s without SoftLandingWeapon / long 1 s
  height  lowlong 1 s capped at 28 / long 1 s (on soft's old site) / mid 0.7 s / soft 0.5 s (on long's old site)
Prediction from the data (D50 / D52, work/re/d50_lift_release.md): a hit lifts trunc(TimeIncrement x 15) frames --
soft / bare 7, long 15 -- z + 4 a frame while under the cap (soft / bare 28 up, long 60), then the physics drops it;
on touching down the SoftLandingWeapon puts a 0.1 s LIFTED_INTO_AIR modifier whose expiry clears the bit (landing
+ 1..2 frames). Without it (bare) the bit stays. The fall is not in the data (knock-back's 64 / 15^2 a frame^2 would
take 14 frames from 28, 21 from 60).

Bench 11-11 fall CampLPFall_mcp_1111_202526 PASS as written (work/logs/a169_liftfall.log): the hit at frame 93 (90 +
3; both releases 7 / 15 frames after it). Release = a shock with zero velocity through knock-back's own curve (the
`shock ... v=0` line from the lift's release, then a second from the physics the same frame): soft from z 240.5
(212.5 + 28 = 7 x 4) at frame 100, `build land=2310,850,212.5 a=0 b=1.75` (the +10 on the 20 grid, as knock-back),
N 20; long from 272.5 (+60, the cap: 15 x 4) at frame 108, b 2.6087, N 26 then 25. The probe writes no line while
the body is lifted or falling; its first line after is at the landing spot, soft frame 120 (= 100 + 20), long 133
(= 108 + 25), x moved 10. Counters: soft lifted 28 frames (93 .. 120: cleared one frame after it lands); bare and
long never cleared (150 frames at the end) -- long has the SoftLandingWeapon (the shock line carries it) but kept
the bit, against D52. height asks why.
"""
from maps import probe_range
from model import status
from parts import Mission, Script, Test
from checks.engine_lift import gun
from checks.engine_missile import target
from checks.engine_suppress_probe import EVERY, LINES

FIRE, RUN = 6.0, 13.0
SITES = ('base', 'high', 'order', 'removed')       # probe_range lanes, one caster + victim each
# check -> {site: (label, TimeIncrement s or None = no nugget and no module, SoftLandingWeapon, MaxElevationFromGround)}
CONFIGS = {
    'fall': {'base': ('base', None, False, 60), 'high': ('soft', 0.5, True, 60),
             'order': ('bare', 0.5, False, 60), 'removed': ('long', 1.0, True, 60)},
    # why long (60 up) kept the bit: lowlong lifts as long as long but no higher than soft; mid 40 up; long moved
    # to soft's site and soft to long's (the site ruled out)
    'height': {'base': ('lowlong', 1.0, True, 28), 'high': ('long', 1.0, True, 60),
               'order': ('mid', 0.7, True, 60), 'removed': ('soft', 0.5, True, 60)},
}
# from RUN - 1 s. fall: as first written (passed). height: the prediction if the fall's height decides
EXPECT = {'fall': [('base lifted frames', RUN - 1, '==', 0), ('soft lifted frames', RUN - 1, '>=', 7),
                   ('long lifted frames', RUN - 1, '>=', 15), ('bare lifted frames', RUN - 1, '>=', 60)],
          'height': [('lowlong lifted frames', RUN - 1, '<=', 40), ('long lifted frames', RUN - 1, '>=', 60),
                     ('soft lifted frames', RUN - 1, '==', 28)]}


def victim(uid):
    v = target(uid, health=1000)
    v.xml = v.xml.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    v.what += '；多一个 ra3ext 的 CNVProbe 模块，逐帧记位置'
    return v


def caster(site, config):
    _, inc, soft, cap = config[site]
    extra = ('<ActivateLiftObjectNugget Lifetime="2s"><SpecialObjectFilter Rule="ANY" Include="VEHICLE"/>'
             '</ActivateLiftObjectNugget>' if inc else '')
    u = gun('CNV_LiftP' + site.title(), 10, extra)
    u.xml = u.xml.replace('DamageType="EXPLOSIVE"', 'DamageType="UNRESISTABLE"')
    if inc:
        landing = ' SoftLandingWeapon="JapanCommandoSoftLanding"' if soft else ''
        u.xml = u.xml.replace('<Behaviors>', '<Behaviors><LiftObjectUpdate id="ModuleTag_Lift" '
                              f'CrusherModifiesVelocity="false" LiftVelocity="4" MaxElevationFromGround="{cap:g}" '
                              f'TimeIncrement="{inc:g}s" MaxTimeLifted="8s"{landing}/>', 1)
    return u


def name(site, part):
    return f'Lift probe {site} {part}'


def mission():
    m = Mission(name='CampLP', map=probe_range, units=[], facts={})
    m.ext = True                  # + the check's name: CampLPFall / CampLPHeight (<= 15)
    for site in SITES:
        u, v = caster(site, CONFIGS['fall']), victim('CNV_LiftPVictim' + site.title())
        m.units.extend((u, v))
        m.put(u.id, site + ' gun', side='p1', angle=1.5708, name=name(site, 'gun'))
        m.put(v.id, site + ' gun', 0, 450, side='s1', angle=4.7124, name=name(site, 'victim'))
    return m


def check(m, which):
    config = CONFIGS[which]
    for i, site in enumerate(SITES):   # this check's casters (the mission is built with fall's); same ids
        m.units[2 * i] = caster(site, config)
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'Lift probe fire', FIRE),
             ('SET_MILLISECOND_TIMER', 'Lift probe stop', FIRE + 4 / 15)]
    fire, stop = [], []
    for site in SITES:
        g, v, c = name(site, 'gun'), name(site, 'victim'), 'CNV_LiftP_' + site
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', n, 'NO_ATTACK', 1) for n in (g, v))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', g, v)))
        stop.append(('UNIT_CHANGE_OBJECT_STATUS', g, 'NO_ATTACK', 1))
        t.counters.append((c, config[site][0] + ' lifted frames'))
        t.scripts.append(Script('Test - lifted ' + site, [('UNIT_HAS_OBJECT_STATUS', v, status('LIFTED_INTO_AIR'))],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.extend((Script('Test - fire', [('TIMER_EXPIRED', 'Lift probe fire')], fire),
                      Script('Test - stop', [('TIMER_EXPIRED', 'Lift probe stop')], stop)))
    t.expect = EXPECT[which]
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_lift_probe': mission}
CHECKS = {'engine_lift_probe': {k: (lambda m, k=k: check(m, k)) for k in CONFIGS}}
