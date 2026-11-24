"""A346 PLAYER_SPECIAL_POWER_AVAILABILITY against a script's button press.

Two retail Athenas 3 000 apart (out of each other's reach): ours (p1) and Soviet_1's. At the start Soviet_1's shield
power (SpecialPower_ToggleShieldSphere) is set Disabled (an); at 5 s a script presses both shields
(NAMED_USE_COMMANDBUTTON_ABILITY, engine_activate: GENERIC_TOGGLE_STATE for 20 s). Counters 我方 / 敌方: 1 shield on,
+100 alive. Simulator before the bench: a script's press never asks the availability, 101 / 101 from 5 s.
MEASURED 11-24: 101 / 101 from f77 (readings) -- the press ignores it, so an alias for the player (retail ep01 j03's
"<1st Human Player's Enemies>") cannot be told apart this way; its expansion is the program's (each player of the
mask, l2_specialpower 4.5), test_specialpower.
"""
from maps import probe_range
from parts import Mission, Script, Test, status

POWER = 'SpecialPower_ToggleShieldSphere'
WHO = {'an': 'Soviet_1'}
SIDES = (('我方', 'p1', 'base gun'), ('敌方', 's1', 'order gun'))


def mission():
    m = Mission(name='CampAvl', map=probe_range, units=[])
    for tag, side, site in SIDES:
        m.put('AlliedAntiStructureVehicle', site, side=side, role=side, name='A346 Athena ' + side)
    return m


def check(m, which):
    t = Test()
    t.counters = [('A346Frame', '帧数')] + [('A346' + side, tag) for tag, side, _ in SIDES]
    t.scripts = [Script('Test - A346 start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('PLAYER_SPECIAL_POWER_AVAILABILITY', WHO[which], POWER, 'Disabled'),
        ('SET_MILLISECOND_TIMER', 'A346Press', 5.0)]),
        Script('Test - A346 frame', [], [('INCREMENT_COUNTER', 1, 'A346Frame')], once=False),
        Script('Test - A346 press', [('TIMER_EXPIRED', 'A346Press')], [
            ('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(side).name, 'Command_ToggleShieldSphere')
            for _, side, _ in SIDES])]
    for _, side, _ in SIDES:
        name, counter = m.role(side).name, 'A346' + side
        t.scripts += [Script('Test - A346 clear ' + side, [], [('SET_COUNTER', counter, 0)], once=False),
                      Script('Test - A346 shield ' + side, [('UNIT_HAS_OBJECT_STATUS', name, status('GENERIC_TOGGLE_STATE'))],
                             [('INCREMENT_COUNTER', 1, counter)], once=False),
                      Script('Test - A346 alive ' + side, [('NAMED_NOT_DESTROYED', name)],
                             [('INCREMENT_COUNTER', 100, counter)], once=False)]
    t.expect = [('帧数', 0, 'ever>=', 250),('我方', 0, 'ever>=', 100), ('敌方', 0, 'ever>=', 100)]
    t.bench = [('bench_watch', dict(seconds=16, every=0.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_avail': mission}
CHECKS = {'engine_avail': {w: (lambda m, w=w: check(m, w)) for w in WHO}}
