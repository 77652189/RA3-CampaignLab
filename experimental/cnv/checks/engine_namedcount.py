"""Named building countdown, isolated owners and untouched control.

Prediction before bench: IC/p1 set 0 at 1s is ready; IC/s4 set 2
is not script-ready even after 2s (engine_power/engine_aispecial).
At 7s swap: p1 gets 2, s4 gets 0. s5 is never touched.
Ready mask bits p1/s4/s5=1/2/4; alive mask same; zero-excess-power mask
same (comparison 2 is equality, NOT positive power); last counter is
the actual logical frame. No AI is woken.
This queries readiness, not a countdown display or an actual reload end.
Evidence and remaining clock gap: work/re/c_namedcount_report.md.
MEASURED IC: f43..143 ready=0, f153..315 ready=7, alive=7 and
zero-excess-power=0 throughout. The untouched owner changes too;
the prediction is refuted. Do not infer named countdown semantics.
MEASURED Vacuum: f41..148 ready=0, f155..300 ready=3, alive=7 and
zero-excess-power=0 throughout. Two runs do not distinguish a READY
refresh phase from host initialization or an input/timer issue; no
model implementation or inventory promotion. See report hypotheses.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8

SIDES = ('p1', 's4', 's5')
POWER = 'SpecialPowerIronCurtain'


def mission(vacuum=False):
    m = Mission(name='CampNamedVac' if vacuum else 'CampNamedCount', map=probe_border, units=[],
                facts={'power': 'SpecialPowerVacuumBomb' if vacuum else POWER})
    for k, side in enumerate(SIDES):
        for role, template, dy in (('ic', 'SovietSuperWeaponAdvanced' if vacuum else 'SovietSuperWeapon', 0.),
                                    ('plant', 'SovietPowerPlant', 400.)):
            m.put(template, 'stop row', -500.+1500.*k, -2300.+dy,
                  side=side, role=side+' '+role, name='CNV NamedCount '+side+' '+role)
    return m


def check(m):
    t = Test()
    power = m.facts['power']
    for key, seconds, values in (('first', 1., (0, 2)), ('swap', 7., (2, 0))):
        s8.at(t, key, seconds, [
            ('NAMED_SET_SPECIAL_POWER_COUNTDOWN', m.role(side+' ic').name, power, value)
            for side, value in zip(SIDES, values)])
    s8.total(t, 'CNV_NC_Ready', '就绪位', [
        (2**k, ('SKIRMISH_SPECIAL_POWER_READY', m.player(side), power))
        for k, side in enumerate(SIDES)])
    s8.total(t, 'CNV_NC_Alive', '宿主位', [
        (2**k, ('NAMED_NOT_DESTROYED', m.role(side+' ic').name))
        for k, side in enumerate(SIDES)])
    s8.total(t, 'CNV_NC_Power', '供电位', [
        (2**k, ('PLAYER_EXCESS_POWER_COMPARE_VALUE', m.player(side), 2, 0))
        for k, side in enumerate(SIDES)])
    s8.frames(t, 'CNV_NC_Frame', '逻辑帧', [])
    s8.watch(t, 15., .5)
    return t


MISSION = {'engine_namedcount': mission, 'engine_namedvac': lambda: mission(True)}
CHECKS = {'engine_namedcount': {'a': check}, 'engine_namedvac': {'a': check}}
