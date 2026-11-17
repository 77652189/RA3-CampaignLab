"""ManagerBody: retail HB_Bridge_02 whole-bridge proxy, untouched / script damage.

Use Niagara's two 270-unit bridges with their original adjacent start/end flags,
on same-height banks over water. No empty bridge proxy is placed on dry land.
HB_Bridge_02 -> BaseBridge -> BaseObject; BaseBridge's ManagerBody has
InitialHealth=MaxHealth=1. Schema inherits ImmortalBody. PREDICTION (not proof):
both named start proxies read 100 percent and survive NAMED_DAMAGE 200.
The two state rows are 1 for named survival + 10 for a retail HB_Bridge_02
remaining in that bridge's area. Missing names cannot pass via frozen HP.
Damage at mission second 10 leaves a baseline despite loading time.
Only whole-proxy script damage is tested: generated pieces, shared health,
repair, killing/deleting, other templates and exact timing remain unmeasured.

BENCH 2026-11-11 a: s1-s8 100/100/11/11; s9-s25 100/80/11/11.
The XML-1HP prediction above was falsified: proxy health is a runtime value.
b: s1-s8 100/100/11/11; s9-s18 80/80/11/11; s19-s35 1/1/11/11.
270/700 bridges both lose 20 percentage points to 200 damage; 20000 more leaves
both alive at a displayed 1%. Effective internal HP/floor remain INFERRED.
No generated piece is named or hit, so shared/piece health is not verified.
"""
from types import SimpleNamespace

import platmap
from maps import island, niagara
from parts import Mission, Script, Test, square


def mission(which='a'):
    # Keep the proven map geometry; replace only the first two pairs with names.
    probe_map = SimpleNamespace(**vars(niagara))
    probe_map.PLAYERS = {**niagara.PLAYERS, **island.NEUTRAL}
    probe_map.OBJECTS = niagara.OBJECTS[4:] if which == 'a' else niagara.OBJECTS[2:4] + niagara.OBJECTS[6:]
    m = Mission(name='CampManager', map=probe_map, units=[], facts={'diagnostic': which == 'b'})
    origin = m.site('front')
    pairs = niagara.BRIDGES[:2] if which == 'a' else [niagara.BRIDGES[0], niagara.BRIDGES[2]]
    for role, (p, q) in zip(('control', 'hit'), pairs):
        for k, (x, y, angle, flags) in enumerate(platmap.bridge(p, q)):
            part = role if k == 0 else role + ' end'
            m.put('HB_Bridge_02', 'front', x - origin[0], y - origin[1],
                  side='neutral', angle=angle, flags=flags, role=part,
                  name='Manager ' + part)
        m.areas['Manager ' + role] = square((p[0] + q[0]) / 2, p[1], (q[0] - p[0]) / 2 + 10)
    return m


def check(m):
    t = Test()
    diagnostic = m.facts['diagnostic']
    t.counters = [('Manager HP ' + role, label)
                  for role, label in (('control', '原血'), ('hit', '伤血'))]
    t.counters += [('Manager state ' + role, label)
                   for role, label in (('control', '原存'), ('hit', '伤存'))]
    t.scripts = [Script('Manager start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Manager damage', 10.0)]),
        Script('Manager damage', [('TIMER_EXPIRED', 'Manager damage')], [
            ('NAMED_DAMAGE', m.role('hit').name, 200)] + ([
            ('NAMED_DAMAGE', m.role('control').name, 200),
            ('SET_MILLISECOND_TIMER', 'Manager lethal', 10.0)] if diagnostic else []))]
    if diagnostic:
        t.scripts.append(Script('Manager lethal', [('TIMER_EXPIRED', 'Manager lethal')], [
            ('NAMED_DAMAGE', m.role(role).name, 20000) for role in ('control', 'hit')]))
    for role in ('control', 'hit'):
        name, state = m.role(role).name, 'Manager state ' + role
        t.scripts += [
            Script('Manager read ' + role, [], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', name, 'Manager HP ' + role),
                ('SET_COUNTER', state, 0)], once=False),
            Script('Manager alive ' + role, [('NAMED_NOT_DESTROYED', name)], [
                ('INCREMENT_COUNTER', 1, state)], once=False),
            Script('Manager retail ' + role, [
                ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
                 3, 1, m.role(role).template, 'Manager ' + role)], [
                ('INCREMENT_COUNTER', 10, state)], once=False)]
    if diagnostic:
        t.expect = [(label, 2, '==', 11, 33) for label in ('原存', '伤存')]
        t.expect += [(label, start, '==', hp, end) for label in ('原血', '伤血')
                     for start, end, hp in ((2, 7, 100), (14, 17, 80), (24, 33, 1))]
    else:
        t.expect = [('原血', 2, '==', 100, 23), ('伤血', 2, '==', 100, 7),
                    ('伤血', 15, '==', 80, 23),
                    ('原存', 2, '==', 11, 23), ('伤存', 2, '==', 11, 23)]
    t.bench = [('bench_watch', dict(every=0.5, sheet=False, lines=4, seconds=34 if diagnostic else 24))]
    return t


MISSION = {'engine_managerbody': mission, 'engine_managerbody_b': lambda: mission('b')}
CHECKS = {'engine_managerbody': {'a': check}, 'engine_managerbody_b': {'b': check}}
