"""L7 frame loop (ADR 0029, docs/engine/sim-layers.md rule 5): the frame's order written in one place.

`CELLS` is the roster of everything that runs in a frame, by name; `FRAME` is the order with the engine model (each
engine frame of a DT tick), `OLD` the reduced order without it (once a tick: a clean clone without the private
engine model, Sim(model=False)). Both orders name cells of the one roster. A cell is `fn(s, frame, tick)`: `s` the
Sim, `frame` the engine frame as the cell sees it (`eng.frame` read when the cell runs; `frame_now()` in the old
loop), `tick` the tick's state (its start, whether its first-frame block ran).

The old loop is not yet the engine order minus the scripts cell: it runs fewer cells in another order (tech last,
expire first). Unifying it would change the clean-clone runs, so it waits for its own decision (work/re/handoff-r.md).
"""
import math

DT = 0.5                         # seconds a tick (sim.DT)
LAG = 0.0                        # the readings' clock: mission seconds, as the bench's since 4aed60f (ADR 0007: the
                                 # bench counts mission time, at 8x). Expectations written before that counted wall
                                 # seconds from the menus' end; the simulator's versions of the checks carry their own
                                 # ending (simchecks.py) and judge the counters only where they are wiring (sim.LAG)


class Tick:
    __slots__ = ('t0', 'moved')

    def __init__(self, t0):
        self.t0, self.moved = t0, False


# ---- cells (the rules stay in their owners; a cell only calls one and holds its gate)
def release(s, frame, tick):
    s.release()


def events(s, frame, tick):
    while s.events and s.events[0][0] <= s.t + 1e-9:
        s.happen(s.events.pop(0))


def tech(s, frame, tick):
    s.tech_due(frame + 1)        # before the frame's scripts (bench 11-08 engine_protocol rank: rank 2 read by the
                                 # scripts of frame 5400 = 360 s x 15)


def scripts(s, frame, tick):
    s.eng.step()


def seq(s, frame, tick):
    if s.seq:
        s.seq_due()


def handed(s, frame, tick):
    if s.handed:                 # the container's Lib_Skirmish_Setup, after the first frame's scripts
        s.off_teams(s.handed)
        s.handed = ()


def lose_health(s, frame, tick):
    s.lose_health(frame)


def autoheal(s, frame, tick):
    s.heal.autoheal(s, frame)


def passive_area_heal(s, frame, tick):
    s.heal.passive_area_heal(s)


def repairs(s, frame, tick):
    s.repairs.due(frame)


def assignments(s, frame, tick):
    s.assignments.due(frame)


def suppression(s, frame, tick):
    s.suppression_tick()


def flee(s, frame, tick):
    s.flee_due(frame)


def hunt(s, frame, tick):
    if s.hunts:
        s.hunt_due(frame)


def toggles(s, frame, tick):
    s.toggles_run(frame)


def self_power(s, frame, tick):
    s.self_power_due(frame)


def expire(s, frame, tick):
    s.expire(frame)


def garrison(s, frame, tick):
    s.garrison.due()


def frame_movers(s, frame, tick):
    if s.frame_movers:
        s.move(1.0 / s.fps, precise=True)


def build(s, frame, tick):
    s.build_due(frame)


def blast(s, frame, tick):
    s.blast_due(frame)


def wfire(s, frame, tick):
    s.wfire_due(frame)


def death_blast(s, frame, tick):
    s.death_blast_due(frame)


def spawn(s, frame, tick):
    s.spawn_due(frame)


def sweeps(s, frame, tick):
    s.sweeps.due(frame)


def deposit(s, frame, tick):
    s.deposit_due(frame)


def mine(s, frame, tick):
    s.mine_due(frame)


def produce(s, frame, tick):
    s.produce_due(frame)


def counters(s, frame, tick):
    # DISPLAY_COUNTER shows the table's value, a running timer's frames left too (bench 11-10 engine_timer stop:
    # 109 94 80 ... after RESTART_TIMER; s.counters hides running timers)
    if s.test and s.test.counters and (frame - 1) % s.fps == 0 and s.t >= LAG:
        s.series.append((int(round(s.t - LAG)), [s.eng.value(c) for c, _ in s.test.counters]))


def tick_first(s, frame, tick):
    """Default movement and acquisition: once a tick, on its first frame."""
    if not tick.moved and s.ending is None and s.t >= tick.t0 - 1e-9:
        tick.moved = True
        s.aura_tick()
        if s.combat:
            s.fight()
        if not s.shot_clock:
            s.move()


def shot_clock(s, frame, tick):
    if s.shot_clock:             # the opt-in shot_clock integrates movement each frame
        s.move(1.0 / s.fps)


def aim(s, frame, tick):
    if s.mid_aims and s.combat and s.ending is None:
        s.aim_due()


def deal(s, frame, tick):
    if s.combat and s.ending is None:
        s.deal(1.0 / s.fps)      # R6: the aimed fire frame by frame, after the frame's scripts


# ---- the old loop's own cells
def events_old(s, frame, tick):
    while s.events and s.events[0][0] <= s.t:
        s.happen(s.events.pop(0))


def scripts_old(s, frame, tick):
    for sc in s.mm.scripts:
        if sc.name in s.done or sc.name in s.disabled or not sc.levels[s.level]:
            continue
        if all(s.holds(c) for c in sc.when):
            for name, *a in sc.do:
                s.act(name, a, sc)
            if sc.once:
                s.done.add(sc.name)


def tech_old(s, frame, tick):
    s.tech_due(frame)


def motion_old(s, frame, tick):
    if s.ending:
        return
    s.aura_tick()
    if s.combat:
        s.fight()
    s.move()


CELLS = {f.__name__: f for f in (
    release, events, tech, scripts, seq, handed, lose_health, autoheal, passive_area_heal, repairs, assignments,
    suppression, flee, hunt, toggles, self_power, expire, garrison, frame_movers, build, blast, wfire, death_blast,
    spawn, sweeps, deposit, mine, produce, counters, tick_first, shot_clock, aim, deal,
    events_old, scripts_old, tech_old, motion_old)}

FRAME = ('release', 'events', 'tech', 'scripts', 'seq', 'handed', 'lose_health', 'autoheal', 'passive_area_heal',
         'repairs', 'assignments', 'suppression', 'flee', 'hunt', 'toggles', 'self_power', 'expire', 'garrison',
         'frame_movers', 'build', 'blast', 'wfire', 'death_blast', 'spawn', 'sweeps', 'deposit', 'mine', 'produce',
         'counters', 'tick_first', 'shot_clock', 'aim', 'deal')

OLD = ('release', 'events_old', 'scripts_old', 'expire', 'spawn', 'garrison', 'suppression', 'hunt', 'build',
       'deposit', 'mine', 'produce', 'tech_old', 'motion_old')

_FRAME = tuple(CELLS[n] for n in FRAME)
_OLD = tuple(CELLS[n] for n in OLD)


def step(s):
    """One DT tick from s.t (the caller moves s.t on). With the engine model: the tick's frames (those before
    s.t + DT, 7 or 8), each running FRAME in order. Without it: OLD once."""
    if s.eng is None:
        return step_old(s)
    t0, eng = s.t, s.eng
    last = math.ceil(round((t0 + DT) * s.fps, 6))
    tick = Tick(t0)
    while eng.frame < last and s.ending is None:
        s.t = eng.frame / s.fps
        for cell in _FRAME:
            cell(s, eng.frame, tick)
    s.t = t0


def step_old(s):
    tick = Tick(s.t)
    for cell in _OLD:
        cell(s, s.frame_now(), tick)
