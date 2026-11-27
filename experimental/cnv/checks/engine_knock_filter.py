"""Retail MagneticSingularity filter, real template identities, two controls.

a retains the retail filter, b removes only that filter. Both lanes invert.
Prediction: normal Hammer moves in both; ordinary infantry/aircraft and the
iron-curtained Hammer are rejected by a; the two IncludeThing identities
(Terror Drone and Tesla Trooper, both INFANTRY) override kind exclusion.
Their status precedence is tested by the iron-curtained Tesla Trooper.
No whole-power, airborne radius or native Iron Curtain lifecycle claim.
Bench a/b PASS: both99/99/status3/status3; shocks per lane4/7.
Aircraft has no shock in either control and no probe-position record: gap.
Retail candidates publish shock records but not the attempted probe module;
only the Hammer probes' positions are used in landing assertions.
c (A394): yuri the retail filter, rocket without it; still-on-its-spot (a 3 box)
counters for the plain Hammer, infantry, iron-curtained Hammer ('near') and Tesla Trooper.
A counter per lane: 1 Hammer + 2 infantry + 4 near + 8 Tesla Trooper. Prediction: yuri 6, rocket 0.
Bench CampKFilterC_mcp_1126_230211 PASS: 15 15 to s11.53, 6 0 from s12.0.
"""
import os
import re

import labpaths
from model import Obj, Script, Unit, square, status
from checks import engine_knock_invert as invert
from checks import engine_knock_probe as probe


# Keep original IDs: renaming a copy would invalidate IncludeThing evidence.
CANDIDATES = {
    'drone': ('SovietScoutVehicle', 0, 65),
    'tesla': ('SovietHeavyAntiVehicleInfantry', -65, 0),
    'teslaic': ('SovietHeavyAntiVehicleInfantry', -45, -45),
    'infantry': ('AlliedAntiInfantryInfantry', 0, -65),
    'aircraft': ('SovietAntiGroundAircraft', 45, 45),
    'normal': (probe.PROBE_TANK, 45, -45),
}


def observed_template(template):
    side = 'Allied' if template.startswith('Allied') else 'Soviet'
    path = os.path.join(labpaths.SDK3, 'SageXML', side, 'Units', template + '.xml')
    with open(path, encoding='utf-8') as f:
        xml = f.read()
    assert xml.count('<Behaviors>') == 1
    xml = xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                      'MinFrames="15" MaxFrames="3000"/>', 1)
    return Unit(template, xml, names={'unit': template},
                what='Retail identity with read-only position probe')


def mission():
    m = invert.mission()
    m.name = 'CampKFilter'
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        for part, (template, dx, dy) in CANDIDATES.items():
            m.objects.append(Obj(template, victim.x + dx, victim.y + dy,
                                 side=victim.side, name=probe.name(lane, part), site=victim.site))
    return m


HOME = ('normal', 'infantry', 'near', 'tesla')


def check(m, plain=False, home=False):
    t = invert.check(m, plain=True)
    payload = invert.retail_shock()
    for uid in ('CNV_KnockYuri', 'CNV_KnockRocket'):
        gun = next(u for u in m.units if u.id == uid)
        if plain or (home and uid == 'CNV_KnockRocket'):
            payload = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', payload, flags=re.S)
        gun.xml, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', lambda _: payload, gun.xml, flags=re.S)
        assert n == 1
    m.units += [observed_template(tpl) for tpl in sorted({c[0] for c in CANDIDATES.values()})
                if tpl != probe.PROBE_TANK]
    start = next(s for s in t.scripts if s.name == 'Test - start')
    for lane in ('yuri', 'rocket'):
        for part in CANDIDATES:
            start.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, part), 'NO_ATTACK', 1))
        for part in ('near', 'teslaic'):
            start.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, part), 'UNDER_IRON_CURTAIN', 1))
    # Observe the two actual status bits rather than equating a script command
    # with successful state creation. Health of the direct victims is retained.
    t.counters = [c for c in t.counters if c[1].endswith('man')]
    t.scripts = [s for s in t.scripts if not (s.name.startswith('Test - health') and s.name.endswith('near'))]
    for lane in ('yuri', 'rocket'):
        counter = 'CNV_KFilter_' + lane
        t.counters.append((counter, lane + ' status'))
        t.scripts.append(Script('Test - status reset ' + lane, [], [('SET_COUNTER', counter, 0)], once=False))
        for part, weight in (('near', 1), ('teslaic', 2)):
            t.scripts.append(Script('Test - status ' + lane + part,
                [('UNIT_HAS_OBJECT_STATUS', probe.name(lane, part), status('UNDER_IRON_CURTAIN'))],
                [('INCREMENT_COUNTER', weight, counter)], once=False))
    t.expect = [(lane + ' man', 22, '==', 99, 24) for lane in ('yuri', 'rocket')]
    t.expect += [(lane + ' status', 22, '==', 3, 24) for lane in ('yuri', 'rocket')]
    if home:
        t.counters, t.expect = [], []
        t.scripts = [s for s in t.scripts if not s.name.startswith(('Test - status', 'Test - health', 'Test - dead'))]
        for lane in ('yuri', 'rocket'):      # one counter a lane: the sum of 2^k for each HOME[k] still on its spot
            c = 'CNV_KFilter_' + lane
            t.counters.append((c, lane + ' home'))
            t.scripts.append(Script('Test - away ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
            for k, part in enumerate(HOME):
                o = next(o for o in m.objects if o.name == probe.name(lane, part))
                area = probe.name(lane, part + ' home')
                t.areas[area] = square(o.x, o.y, 3)
                t.scripts.append(Script(f'Test - home {lane} {part}', [('NAMED_INSIDE_AREA', o.name, area)],
                                        [('INCREMENT_COUNTER', 2 ** k, c)], once=False))
            t.expect.append((lane + ' home', 22, '==', 6 if lane == 'yuri' else 0, 24))
        t.bench = [('bench_watch', dict(seconds=24, every=.5, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_knock_filter': mission}
CHECKS = {'engine_knock_filter': {'a': check, 'b': lambda m: check(m, plain=True),
                                  'c': lambda m: check(m, home=True)}}
