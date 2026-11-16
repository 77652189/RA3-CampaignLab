"""C: native SellButton disable/restore against script sale and untouched controls.

Retail a01 uses SellButton,1; a03 restores other fixed elements with 0.
A keeps SellButton disabled. B disables then restores it before the same native clicks.
Prediction: the native target survives A and is sold in B; script SELL_OBJECT sells
its separate target in both. The untouched third power plant survives both.
Alive bits: native=1, scripted=2, untouched=4; expected final A=5, B=4.
Money starts at 2000; full-health AlliedPowerPlant costs 800, refund 400.
This is a UI probe, not evidence that every fixed element is a simulation no-op.
Evidence/scope: work/re/c_mousehud_report.md. No HUD-state interface is assumed.
BENCH 11-16: A f356 and B f414 both finish alive=5, money=2400.
Native clicks select the target instead of selling it, even after restoration.
The original B positive prediction is retained as a strict xfail, not fitted away.
Final archived frames show A's dollar button grey, B's lit; no numeric HUD state
or accepted sale-mode field is published. Per-call Esc may cancel the mode
(INFERRED). Two-run budget exhausted; the action remains TODO.
"""
from maps import probe_border
from parts import Mission, Script, Test
from checks import engine_scripts8 as s8


def mission():
    m = Mission(name='CampMouseHUD', map=probe_border, units=[], facts={})
    for role, dx in (('native', 0.), ('scripted', 450.), ('untouched', 900.)):
        m.put('AlliedPowerPlant', 'stop row', dx, -500., side='p1',
              name=f'CNV MouseHUD {role}', role=role)
    return m


def check(m, restore):
    t = Test()
    actions = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
               ('PLAYER_SET_MONEY', m.player('p1'), 2000),
               ('DISABLE_MOUSE_HUD_FIXED_ELEMENT', 'SellButton', 1)]
    if restore:
        actions.append(('DISABLE_MOUSE_HUD_FIXED_ELEMENT', 'SellButton', 0))
    t.scripts.append(Script('Test - mousehud setup', [], actions))
    s8.at(t, 'mousehud script sale', 2., [('SELL_OBJECT', m.role('scripted').name)])
    s8.total(t, 'CNV_MouseHUD_Alive', '存活', [
        (w, ('NAMED_NOT_DESTROYED', m.role(role).name))
        for w, role in ((1, 'native'), (2, 'scripted'), (4, 'untouched'))])
    t.counters.append(('CNV_MouseHUD_Money', '资金'))
    t.scripts.append(Script('Test - mousehud money', [], [
        ('SET_PLAYER_MONEY_TO_COUNTER', m.player('p1'), 'CNV_MouseHUD_Money')], once=False))
    s8.frames(t, 'CNV_MouseHUD_Clock', '逻辑帧', [])
    target = m.find(m.role('native').name)
    watch = dict(every=1., sheet=False, lines=3)
    t.bench = [('bench_watch', dict(watch, seconds=4.)),
               ('bench_camera', dict(x=target.x, y=target.y, look=False)),
               ('bench_click', dict(x=1126, y=222, world=False, look=False)),
               ('bench_click', dict(x=target.x, y=target.y, look=False)),
               ('bench_watch', dict(watch, seconds=7.))]
    return t


def a(m):
    return check(m, False)


def b(m):
    return check(m, True)


MISSION = {'engine_mousehud': mission}
CHECKS = {'engine_mousehud': {'a': a, 'b': b}}
