"""S5 tests (the plan: docs/story/plans/s5.md). Counted: any of the Allied fleet in the canal south of the lock (it
got through: the mission is lost).

trap: the control room's guards are killed by test script at RAZE_AT -- what the burrowers' squad does in play --
  and the control room kept at full health; the fleet sets out on time, held, and never gets through; the hold
  runs out and the mission is over.
pace: as trap, then the first 反扑 wave (齐步, docs/engine/pathing.md 5) is read: one counter says which of its guardian
  tank and peacekeeper stand in the area the upgrades are taken away in (1 the tank, 10 the peacekeeper, 100 the tank
  inside 600 of the goal while the peacekeeper is not yet inside 900). Read, not judged: tank and peacekeeper in the
  area within a few seconds of each other, the 100 never up for long.
escape: nothing is done; the fleet sets out on time, gets through and the mission is lost soon after (judged by the
  end coming within THROUGH of setting out; the counter is only shown).
"""
import plan
from parts import NOT, Script, Test, counted, square

RAZE_AT, AREA = 5.0, 250.0
THROUGH = 120.0                                 # escape: from setting out, through the lock by then


def sets_out():
    """When the fleet sets out (s5.md 规则: its first rule), normal difficulty."""
    when = plan.load('s5')['规则'][0]['当']
    return plan.spans(when.split('+')[1])[1][0]


def setup(m):
    t = Test()
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    t.areas['Test south canal'] = square(*m.site('south canal'), AREA)
    counted('Test Through', '冲过船闸', t, template=m.role('fleet 1').template, player=m.player('s1'),
            area='Test south canal')
    return t


def trap(m):
    t = setup(m)
    guards = [r.name for g in ('control guard', 'control tank') for r in m.roles(g)]
    t.scripts += [Script('Test - raze', [], [('SET_MILLISECOND_TIMER', 'Test - raze timer', RAZE_AT)]),
                  Script('Test - raze now', [('TIMER_EXPIRED', 'Test - raze timer')],
                         [('NAMED_KILL', g) for g in guards]),
                  Script('Test - keep the room up', [], [('UNIT_SET_HEALTH', m.role('control room').name, 100.0)],
                         once=False)]
    hold = plan.spans(plan.load('s5')['段'][1]['开场'][-1]['倒计时'].split('+')[1])[1][0]
    end = RAZE_AT + hold
    t.expect += [('冲过船闸', 1, '==', 0, end - 10), ('ENDED', end - 10, '', None)]   # the counters go with the end
    t.bench = [('bench_watch', dict(seconds=end + 30, every=5, sheet=False, lines=len(t.counters)))]
    return t


def escape(m):
    """Judged by the end alone: the lose comes as the fleet reaches the south canal, so the counter of it there is
    seldom caught at 1 between two frames (bench 2026-10-27: 0 at s209, the defeat screen at s214). Ending within
    THROUGH of setting out is a lose -- the hold, the only win, runs far longer."""
    t = setup(m)
    out = sets_out()
    t.expect += [('ENDED', out, '', None, out + THROUGH)]
    t.bench = [('bench_watch', dict(seconds=out + THROUGH + 30, every=5, sheet=False, lines=len(t.counters)))]
    return t


def pace(m):
    """Wave 反扑 (the plan's second wave), its first lot: the tank and the peacekeeper at the goal, the tank alone ahead."""
    t = trap(m)
    t.expect = []
    tank, walker = (f'UNIT - CNV S5 W2-1 {x} 1' for x in ('AlliedAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'))
    gx, gy = m.site('control room')
    t.areas['Test Pace goal'] = square(gx, gy, 250.0)
    t.areas['Test Pace tank near'] = square(gx, gy, 600.0)
    t.areas['Test Pace walker near'] = square(gx, gy, 900.0)
    up = next((u.names['pace'] for u in m.units if u.id.startswith('CNV_Pace')), 'Upgrade_CNV_Pace0')    # (none: 齐步 off)
    t.counters = [('Test Pace', '齐步'), ('Test PaceUp', '限速')]       # (the second: 1 while the enemy holds a slowed unit)
    t.scripts += [Script('Test - paceup zero', [], [('SET_COUNTER', 'Test PaceUp', 0)], once=False),
                  Script('Test - paceup held', [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', m.player('s1'), 1, up)],
                         [('INCREMENT_COUNTER', 1, 'Test PaceUp')], once=False)]
    t.scripts += [Script('Test - pace zero', [], [('SET_COUNTER', 'Test Pace', 0)], once=False),
                  Script('Test - pace tank', [('NAMED_INSIDE_AREA', tank, 'Test Pace goal')],
                         [('INCREMENT_COUNTER', 1, 'Test Pace')], once=False),
                  Script('Test - pace walker', [('NAMED_INSIDE_AREA', walker, 'Test Pace goal')],
                         [('INCREMENT_COUNTER', 10, 'Test Pace')], once=False),
                  Script('Test - pace ahead', [('NAMED_INSIDE_AREA', tank, 'Test Pace tank near'),
                                               ('NAMED_INSIDE_AREA', walker, 'Test Pace walker near', NOT)],
                         [('INCREMENT_COUNTER', 100, 'Test Pace')], once=False)]
    t.bench = [('bench_watch', dict(seconds=RAZE_AT + 30 + 150, every=2, sheet=False, lines=2))]
    return t


# the checks per build (cnv/registry.py): build name -> {check name: check(mission) -> Test}
CHECKS = {
    's5': {'trap': trap, 'escape': escape, 'pace': pace},
}
