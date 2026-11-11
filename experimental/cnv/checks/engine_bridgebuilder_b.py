"""Retail mixed pair: HB_Bridge_02 start (16), Bridge1a end (32).

Retail J02 uses this exact pair. Niagara lengths 270/700 keep known geometry.
Prediction INFERRED before bench: start config wins, HB counts 1/1/1/0/2
and 1/1/2/2/2; all five Bridge1 template counts zero. Add 1000 only when
all five zero queries succeed; missing conditions must not look like zero.
No damage, engineers, health sharing, pathing or repair.
BENCH 2026-11-11: s1-s21 = 1322/12/1322/33, all expectations PASS.
"""
from checks import engine_bridgebuilder as base
from parts import Script

FOREIGN = tuple('Bridge1_' + suffix for suffix in base.FIELDS)


def mission():
    m = base.mission()
    m.name = 'CampBridgeB'
    for o in m.objects:
        if o.flags == 32:
            o.template = 'Bridge1a'
    for role in ('short 1', 'long 1'):
        m.cast[role].template = 'Bridge1a'
    m.spawns.update(FOREIGN)
    return m


def check(m):
    t = base.check(m)
    for role in ('short', 'long'):
        t.scripts.append(Script('Bridge foreign zero ' + role, [
            ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('neutral'),
             2, 0, template, 'Bridge ' + role) for template in FOREIGN], [
            ('INCREMENT_COUNTER', 1000, 'Bridge ' + role + ' ends')], once=False))
    t.expect = [(label, start, op, value + (1000 if i % 2 == 0 else 0), until)
                for i, (label, start, op, value, until) in enumerate(t.expect)]
    return t


MISSION = {'engine_bridgebuilder_b': mission}
CHECKS = {'engine_bridgebuilder_b': {'b': check}}
