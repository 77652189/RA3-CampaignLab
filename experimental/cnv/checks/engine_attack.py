"""Engine unit test: what "attacked by player" reads once the attacker is gone (E2).

Bench 2026-11-04: NAMED_ATTACKED_BY_PLAYER is not "the player has ever hit it". It holds while the last unit that hit
the target is still there (between its shots too) and turns false the frame that unit is deleted or killed, the
target alive and hit all along. Two pairs far apart in the west field, each a player's guardian shooting an enemy
guardian; at GONE s the attacker of pair A is deleted, the attacker of pair B killed (by then the fight has cost each
target about a third of its health: the health counters show the hits stop and the target still up). Counters per
target, set every frame: 1 while the condition holds.
A plan's "<t> 打 <谁>" (plan.py) fires on the frame of the hit, so this matters to a condition read later, and to a
hit by a unit that dies of it (a suicide unit, a plane shot down).
"""
from maps import festival
from parts import Mission, Script, Test, counted, square
import checks.engine_scripts8 as s8
from checks.engine_area import FOES, FRIENDS, OURS

GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
GONE, RUN = 6.0, 16.0
PAIRS = {'A': (-300, -150), 'B': (300, -150)}          # (dx, dy) in the west field; 600 apart, out of each other's range


def mission():
    m = Mission(name='CampAttack', map=festival, facts={})
    for k, (dx, dy) in PAIRS.items():
        m.put(GUARDIAN, 'west field', dx, dy, name=f'UNIT - CNV Attacker {k}', role=f'attacker {k}')
        m.put(GUARDIAN, 'west field', dx, dy + 150, side='s1', name=f'UNIT - CNV Target {k}', role=f'target {k}')
    return m


def gone(m):
    t = Test()
    p1 = m.player('p1')
    t.scripts += [Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Gone', GONE)]
                         + [('NAMED_ATTACK_NAMED', m.role(f'attacker {k}').name, m.role(f'target {k}').name)
                            for k in PAIRS]),
                  Script('Test - gone', [('TIMER_EXPIRED', 'Test Gone')],
                         [('NAMED_DELETE', m.role('attacker A').name), ('NAMED_KILL', m.role('attacker B').name)])]
    for k, label in (('A', '甲被我方打'), ('B', '乙被我方打')):          # A's attacker deleted, B's killed
        counter = f'CNV_Attacked_{k}'
        t.counters.append((counter, label))
        t.scripts += [Script(f'Test - attacked {k} zero', [], [('SET_COUNTER', counter, 0)], once=False),
                      Script(f'Test - attacked {k}', [('NAMED_ATTACKED_BY_PLAYER', m.role(f'target {k}').name, p1)],
                             [('SET_COUNTER', counter, 1)], once=False)]
        # the reading a second before GONE is already the frame after it (the bench's seconds lag the mission's)
        t.expect += [(label, 1, '==', 1, GONE - 1), (label, GONE + 1, '==', 0)]
    # did the shooting happen at all, and is the target still up when its attacker goes: the target's health
    counted('CNV_Attacked_HpA', '甲血量', t, health=m.role('target A').name)
    counted('CNV_Attacked_HpB', '乙血量', t, health=m.role('target B').name)
    t.expect += [(hp, 0, 'ever<', 100) for hp in ('甲血量', '乙血量')] + \
                [(hp, GONE, '>', 0, GONE + 1) for hp in ('甲血量', '乙血量')]     # alive: it is the attacker that went
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


def alias(m):
    """als (A348, l2_scripts1 1: a player argument is a mask): both attacks from the start, nobody removed. Every frame
    打 = NAMED_ATTACKED_BY_PLAYER(target A) FOES 1 / OURS 2 / FRIENDS 4 / <All Players> 8; 主 = NAMED_OWNED_BY_PLAYER
    FOES target A 1 / OURS target A 2 / OURS attacker A 4 / FRIENDS attacker A 8 + NAMED_DISCOVERED(OURS, target A) 16;
    型 = PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA(Guardian, the field: all four) <All Players> >= 3 1 / >= 2 2,
    FOES == 2 4, OURS == 2 8. Predicted: 打 0 then 10, 主 21, 型 15 (a mask's count summed; each player's alone: 14)."""
    t = Test()
    t.areas['Test field'] = square(*m.site('west field'), 450)
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] + [
        ('NAMED_ATTACK_NAMED', m.role(f'attacker {k}').name, m.role(f'target {k}').name) for k in PAIRS]))
    ta, aa = m.role('target A').name, m.role('attacker A').name
    s8.total(t, 'CNV_Attacked_By', '打', [(w, ('NAMED_ATTACKED_BY_PLAYER', ta, who)) for w, who in (
        (1, FOES), (2, OURS), (4, FRIENDS), (8, '<All Players>'))])
    s8.total(t, 'CNV_Attacked_Own', '主', [(w, ('NAMED_OWNED_BY_PLAYER', who, u)) for w, who, u in (
        (1, FOES, ta), (2, OURS, ta), (4, OURS, aa), (8, FRIENDS, aa))] + [(16, ('NAMED_DISCOVERED', OURS, ta))])
    s8.total(t, 'CNV_Attacked_Type', '型', [(w, ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', who, cmp, n,
                                                  GUARDIAN, 'Test field')) for w, who, cmp, n in (
        (1, '<All Players>', 3, 3), (2, '<All Players>', 3, 2), (4, FOES, 2, 2), (8, OURS, 2, 2))])
    s8.watch(t, 8, every=0.5)
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_attack': mission}
CHECKS = {'engine_attack': {'gone': gone, 'als': alias}}
