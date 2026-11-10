"""PREDICTED pressure readings; unpressured controls aligned to round 6 BENCH.

The held infantry receive a finite burst at 6 s, then walk 150 units at 9 s
(duration: at 10 s, then a second 150-unit leg at 17 s). Four lanes compare
25/26 hits of value 2 lasting 3 s, and 5/6 hits of value 10 lasting 1 s.
The immune lane uses Tanya with the same six-hit gun. Each gun is a cloned
V4 carrying only the pressure effect plus 0.1 unresistable damage per hit.
The value-2 lanes split the burst over two guns (13+12 / 13+13), keeping
all contributions inside 3 s at the existing 2-frame shot spacing. A single
26-shot gun would take longer than 3 s and cannot cross 50 under this rule.
Armor uses separate one-shot 40-damage guns at 11 s, after a health reset
at 9 s. Every health counter has its adjacent ALIVE counter.

Field interpretation: radius 20 by centre, expiry per contribution, sum >50
(strict, so 25*2 and 5*10 do not trigger); sample every 1 s; refresh the
5 s effect at every above-threshold sample. These comparison, expiry,
sample phase and refresh rules are INFERRED, pending bench. No linear
decay rate is given. The effect's ARMOR 75% and SPEED 75 mean factors .75.
SUPPRESSED is a MODEL condition in the data, so use arrival frames rather
than pretending that the object-status script condition can read it.
ForceMove's ARMOR 125% and Cover's SUPPRESSABILITY 9999 are out of scope;
the probe uses plain move orders, no force move or cover.

PREDICTED final counters, in declaration order:
  threshold: 44, 58, 44, 55 (25*2, 26*2, 5*10, 6*10)
  speed:     44, 55 (control / pressure)
  armor:     73, 1, 80, 1 (health%, ALIVE; control / pressure)
  duration:  44, 45, 51, 45 (control early/late, pressure early/late)
  immune:    44, 40 (ordinary 5-hit control / Tanya with 6 hits)
The ordinary infantry has Speed 50 and MaxHealth 150. Armor: round(100 *
(150-40)/150)=73; round(100 * (150-40*.75)/150)=80. All ALIVE readings
stay 1. The prediction test enables the existing shot_clock for these
finite bursts; the armor guns reload in 60 s, so exactly one hit.
The six-hit effect expires at frame 181 (last high sample 106 + 75), the
26-hit effect at 211 (136 + 75). Immune infantry have no such rule.
Walk rule: integrate Speed / 15 after each script frame; scripts observe
crossing on the next frame. Entry is 145 units from spawn. Unpressured
ceil(145*15/50)=44 and ceil(145*15/55)=40 are round 6 BENCH readings.
High: ceil(145/2.5)=58, all suppressed. Six-hit pressure: move frame 136,
45 slowed steps before expiry 181 cover 112.5, then ceil(32.5/(50/15))=10
normal steps => 55. Duration: move frame 151, 30 slowed steps cover 75,
then 21 normal steps cover 70 => 51. The second leg is measured from the
actual first crossing: control overshoots to 146 2/3, pressure to 145;
next gate is 295, so both need 45 normal steps (round 6 late control: 45).
No separate speed-specific offset is fitted. Pressure results remain
predictions, not bench readings; no suppression model has been confirmed.
Arrival counters count script frames
from each move order until crossing the timing gate at goal y-5 (inclusive).
The destination is 75 units beyond the goal; the gate retains the old square's
entry line and extends to the destination. On entry the script stops the walker.
This avoids waypoint stopping tolerance and skipped narrow areas in the simulator.
Timers and health percentages MUST be Python floats: map encoding stores ints
in a different slot, leaving the engine's real-valued argument at zero.

Round 8 placement: guns stand on their named pads; walkers and every route
point shift north 350 together, retaining the round 7 relative geometry.
Player guns face north, 450 behind the man (side guns about 461 away),
inside the inherited V4 range 200..500. Clip/kill bench at 450 confirms the
instant clone fires after NO_ATTACK is cleared. The timing area now uses
crush's square(..., 40), centred 35 beyond the goal: the same y-5 entry
line and y+75 exit, with lateral tolerance 40 instead of 5. m.mark() and
the NO_ATTACK sequence already match the proven probes. The 60 s reload
and custom finite burst remain predictions; bare's bench verifies its
initial shot, not this exact magazine. Round 5's nonstop frame counters
do not distinguish no movement from a missed narrow gate or AI orders.
"""
import re

from maps import probe_range
from parts import Mission, Script, Test, square
from checks.engine_clip import ORDER, clip_v4

CASES = {'base': (25, 2, 3), 'high': (26, 2, 3),
         'order': (5, 10, 1), 'removed': (6, 10, 1), 'low': (6, 10, 1)}
# Copy clip's 6 s order; shift the round 7 schedule by the same 5 s.
SHIFT = ORDER - 1.0
RUN = 18 + SHIFT


def name(lane, part):
    return f'UNIT - CNV Supp {lane} {part}'


def gun(lane, armor=False, second=False):
    hits, value, duration = CASES[lane]
    if value == 2 and not armor:
        hits = hits // 2 if second else (hits + 1) // 2
    uid = 'CNV_Supp' + lane.title() + ('Armor' if armor else 'Second' if second else '')
    u = clip_v4('bare', hit=40 if armor else .1, uid=uid,
                spec=(0, 1 / 15, 60, 1 if armor else hits, 'PRE_FIRE', (), RUN, 'pressure'))
    effect = '' if armor else f'<SuppressionNugget Radius="20" Suppression="{value}" DurationSeconds="{duration}s"/>'
    u.xml, n = re.subn(r'<Nuggets>.*?</Nuggets>',
                       f'<Nuggets><DamageNugget Damage="{40 if armor else .1}" DamageType="UNRESISTABLE" '
                       f'DeathType="NORMAL" Radius="0"/>{effect}</Nuggets>', u.xml, flags=re.S)
    assert n == 1
    return u


def mission():
    units = [gun(k, a) for k in CASES for a in (False, True)] + [gun(k, second=True) for k in ('base', 'high')]
    m = Mission(name='CampSu', map=probe_range, units=units, facts={})
    for lane in CASES:
        for armor in (False, True):
            m.put('CNV_Supp' + lane.title() + ('Armor' if armor else ''), f'{lane} gun',
                  100 if armor else 0, 0, side='p1', angle=1.5708,
                  name=name(lane, 'armor' if armor else 'gun'))
        if lane in ('base', 'high'):
            m.put('CNV_Supp' + lane.title() + 'Second', f'{lane} gun', -100, 0,
                  side='p1', angle=1.5708, name=name(lane, 'second'))
        # Stasis' benched s1 theirs/chaser follow MOVE_NAMED_UNIT_TO + m.mark().
        # Clip's target is 450 from its V4: retain the inherited 200..500 range.
        m.put('AlliedCommandoTech1' if lane == 'low' else 'AlliedAntiInfantryInfantry',
              f'{lane} gun', 0, 450, side='s1', role=lane, name=name(lane, 'man'))
        m.waypoint(lane + ' goal', 'Supp ' + lane + ' goal', f'{lane} gun', 0, 600)
        m.waypoint(lane + ' late', 'Supp ' + lane + ' late', f'{lane} gun', 0, 750)
        # Walk THROUGH the timing gate, rather than stopping short of a tiny destination square.
        for leg, dy in (('goal', 675), ('late', 825)):
            m.waypoint(lane + ' ' + leg + ' runout', 'Supp ' + lane + ' ' + leg + ' runout',
                       f'{lane} gun', 0, dy)
    return m


def check(m, which):
    t = Test()
    lanes = tuple(CASES)[:4] if which == 'threshold' else (('order', 'low') if which == 'immune' else ('order', 'removed'))
    # Match benched clip: reveal p1, hold both sides, then release only the gun.
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, part), 'NO_ATTACK', 1)
              for k in CASES for part in ('gun', 'armor', 'man')]
    start += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 1) for k in ('base', 'high')]
    start += [('SET_MILLISECOND_TIMER', 'Supp Fire', ORDER),
              ('SET_MILLISECOND_TIMER', 'Supp Move', SHIFT + (5.0 if which == 'duration' else 4.0)),
              ('SET_MILLISECOND_TIMER', 'Supp Late', SHIFT + 12.0),
              ('SET_MILLISECOND_TIMER', 'Supp Armor', SHIFT + 6.0)]
    t.scripts.append(Script('Test - start', [], start))
    fire = []
    for k in lanes:
        fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'gun'), 'NO_ATTACK', 0),
                 ('NAMED_ATTACK_NAMED', name(k, 'gun'), name(k, 'man'))]
        if k in ('base', 'high'):
            fire += [('UNIT_CHANGE_OBJECT_STATUS', name(k, 'second'), 'NO_ATTACK', 0),
                     ('NAMED_ATTACK_NAMED', name(k, 'second'), name(k, 'man'))]
    fire.append(('SET_FLAG', 'Supp Ordered', 1))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'Supp Fire')], fire))
    for k in lanes:
        man = m.role(k).name
        if which == 'armor':
            t.scripts.append(Script('Test - reset ' + k, [('TIMER_EXPIRED', 'Supp Move')], [('UNIT_SET_HEALTH', man, 100.0)]))
            t.scripts.append(Script('Test - armor ' + k, [('TIMER_EXPIRED', 'Supp Armor')], [
                ('UNIT_CHANGE_OBJECT_STATUS', name(k, 'armor'), 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', name(k, 'armor'), man)]))
            hp, alive = 'CNV_Supp_' + k + '_HP', 'CNV_Supp_' + k + '_ALIVE'
            t.counters += [(hp, k + ' 血'), (alive, k + ' 活')]
            t.scripts += [Script('Test - health ' + k, [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', man, hp)], once=False),
                          Script('Test - alive ' + k, [], [('SET_COUNTER', alive, 1)], once=False),
                          Script('Test - dead ' + k, [('NAMED_DESTROYED', man)], [('SET_COUNTER', alive, 0)], once=False)]
            continue
        for leg, timer in [('goal', 'Supp Move')] + ([('late', 'Supp Late')] if which == 'duration' else []):
            wp, c, flag = m.mark(k + ' ' + leg + ' runout'), 'CNV_Supp_' + k + '_' + leg, 'Supp moving ' + k + leg
            x, y = m.point(k + ' ' + leg)
            area = 'Supp area ' + k + leg
            # Crush uses square(..., 40); keep the existing y-5 entry line,
            # but allow lateral pathing drift rather than a ten-unit-wide slit.
            t.areas[area] = square(x, y + 35, 40)
            t.counters.append((c, k + ' ' + leg))
            t.scripts.append(Script('Test - move ' + k + leg, [('TIMER_EXPIRED', timer)],
                                    [('MOVE_NAMED_UNIT_TO', man, wp), ('SET_FLAG', flag, 1)]))
            t.scripts.append(Script('Test - arrived ' + k + leg, [('NAMED_INSIDE_AREA', man, area)], [('NAMED_STOP', man), ('SET_FLAG', flag, 0)]))
            t.scripts.append(Script('Test - frames ' + k + leg, [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 1, c)], once=False))
    predicted = {'threshold': (44, 58, 44, 55), 'speed': (44, 55),
                 'armor': (73, 1, 80, 1), 'duration': (44, 45, 51, 45), 'immune': (44, 40)}
    # judge has no 'at end' operator: require equality throughout the final 2 s.
    t.expect = [(label, RUN - 2, '==', value, RUN)
                for (_, label), value in zip(t.counters, predicted[which])]
    # Keep every lane visible for the entire observation; no gun-digit takeover.
    t.bench = [('bench_watch', dict(seconds=RUN, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_suppression': mission}
CHECKS = {'engine_suppression': {k: (lambda m, k=k: check(m, k))
                               for k in ('threshold', 'speed', 'armor', 'duration', 'immune')}}
