"""E223: StoreCurrentStateUpdate -- how far back Tanya's time belt can take her.

Retail: AlliedCommandoTech1's ReconstituteStateSpecialAbility (SpecialPower_TimeBelt, TimeStepsBack 10 s) reads
the states her StoreCurrentStateUpdate keeps (SleepTime 0.25 s, MaxTime 5 s): the belt asks for twice what is kept.

Three clones of Tanya, one per lane: On as retail, Long with MaxTime 12 s, Short with MaxTime 2 s (with the store
taken out the game crashed a few seconds in, twice: the belt's UpdateModuleId names it). Her health is the clock: from
GO she loses 15 (of 300) every second for 12 s, at PRESS (GO + 12.5 s) the script presses her belt.
Prediction: the oldest kept state caps the jump -- On back to GO + 7.5 s's health (about 65 %), Long to GO + 2.5 s's
(about 90 %), Short to GO + 10.5 s's (about 50 %). Counters: each arm's health in percent.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted

GO, STEPS, HIT = 15 * 25, 12, 15     # frames (run 1: GO 30, the watch's first frame came after the press, s14.9)
PRESS, END = GO + 15 * STEPS + 7, GO + 15 * 20
ARMS = {'On': ('base', None), 'Long': ('high', '12s'), 'Short': ('order', '2s')}    # arm: (lane, MaxTime: None retail)
HOST, TAG = 'AlliedCommandoTech1', 'StoreCurrentStateUpdate'
BELT = 'Command_TimeBeltSpecialPower'


def mission():
    m = Mission(name='CampStoreSt', map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units' / (HOST + '.xml')).read_text(encoding='utf-8-sig')
    for arm, (lane, keep) in ARMS.items():
        ident = 'CNVE223' + arm
        xml = source.replace(f'id="{HOST}"', f'id="{ident}"', 1)
        store = re.compile(rf'\s*<{TAG}\s+id="ModuleTag_StoreCurrentStateUpdate".*?/>', re.S)
        if keep is not None:
            xml, n = store.subn(f'\n\t\t\t<{TAG} id="ModuleTag_StoreCurrentStateUpdate" SleepTime="0.25s" '
                                f'MaxTime="{keep}"/>', xml)
            assert n == 1, (arm, n)
        m.units.append(Unit(ident, xml))
        m.put(ident, lane + ' gun', side='p1', role=arm, name='E223 ' + arm, angle=1.570796)
    return m


def check(m, bleed=False):
    """bleed: 1 hit point a frame from GO to PRESS instead of the hits (the health then says the frame to 3)."""
    t = Test()
    for arm in ARMS:
        counted('E223' + arm, {'On': '原版', 'Long': '记12秒', 'Short': '记2秒'}[arm], t, health=m.role(arm).name)
    t.scripts += [Script('Test - clock', [('COUNTER', 'E223Frame', 0, END)],
                         [('INCREMENT_COUNTER', 1, 'E223Frame')], once=False),
                  Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    names = [m.role(arm).name for arm in ARMS]
    for k in range(1, STEPS + 1) if not bleed else ():
        t.scripts.append(Script(f'Test - hit {k}', [('COUNTER', 'E223Frame', 2, GO + 15 * k)],
                                [('NAMED_DAMAGE', n, HIT) for n in names]))
    if bleed:
        t.scripts.append(Script('Test - bleed', [('COUNTER', 'E223Frame', 3, GO), ('COUNTER', 'E223Frame', 0, PRESS)],
                                [('NAMED_DAMAGE', n, 1) for n in names], once=False))
    t.scripts.append(Script('Test - press', [('COUNTER', 'E223Frame', 2, PRESS)],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', n, BELT) for n in names]))
    t.expect = [('原版', 0, 'ever>', 0)]
    t.bench = [('bench_camera', dict(x=2300, y=500, look=False)),
               ('bench_watch', dict(seconds=END // 15 + 10, every=1, sheet=False, lines=3))]
    return t


MISSION = {'engine_storest_e': mission}
CHECKS = {'engine_storest_e': {'a': check, 'b': lambda m: check(m, bleed=True)}}
