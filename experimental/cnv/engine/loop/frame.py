"""L7 frame loop (ADR 0029, docs/engine/sim-layers.md rule 5): the frame's order written in one place.

`CELLS` is the roster of everything that runs in a frame, by name; `FRAME` their order, run for each engine frame of
a DT tick. A cell is `fn(s, frame, tick)`: `s` the Sim, `frame` the engine frame as the cell sees it, `tick` the
tick's state (its start, whether its first-frame block ran).

`frame` is the run's frame clock (Sim.clock, simworld.FrameClock) read when the cell runs: the scripts cell moves it
on -- the model's step its engine's frame, the public executor (Sim(model=False), a clean clone without the private
engine model) the world's clock -- so the cells after it see the next frame, as the engine has it, either way (until
step R3 ④-1, 11-18, the clean clone counted the tick's frames itself and every cell of a frame saw that frame, the
cells after the scripts one a frame earlier than with the model). Until 11-17 the clean clone
ran a reduced order of its own once a tick (step_old: fewer cells, tech last, expire first, the fight's damage
dealt at once); the merge changed its readings on purpose (work/re/handoff-r.md).
"""
import math
from time import perf_counter

from engine.world.handle import DT          # seconds a tick (sim.DT; the fight's damage step reads it too, L0)
LAG = 0.0                        # the readings' clock: mission seconds, as the bench's since 4aed60f (ADR 0007: the
                                 # bench counts mission time, at 8x). Expectations written before that counted wall
                                 # seconds from the menus' end; the simulator's versions of the checks carry their own
                                 # ending (simchecks.py) and judge the counters only where they are wiring (sim.LAG)


class Tick:
    """`moved`: the tick's first-frame block ran; `coarse`: the frame whose coarse move (non-precise Sim.move) ran,
    so the cells after it (follow ... auto_kill) run on that frame only, as move's tail did."""
    __slots__ = ('t0', 'moved', 'coarse')

    def __init__(self, t0):
        self.t0, self.moved, self.coarse = t0, False, None


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
    s.executor.step()            # the script executor port: the model's plug-in (it moves the frame on) or the public one


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
    """Its modules only (engine/modules/autoheal.py, run by step)."""


def passive_area_heal(s, frame, tick):
    s.heal.passive_area_heal(s)


def repairs(s, frame, tick):
    s.repairs.due(frame)


def assignments(s, frame, tick):
    """Its modules only (AssignSlaves dispatches: engine/modules/specialpower.py, run by step)."""


def suppression(s, frame, tick):
    """Its modules sample first (engine/modules/suppression.py, run by step); then the spent fields leave."""
    s.suppression_tick()


def flee(s, frame, tick):
    s.flee_due(frame)


def hunt(s, frame, tick):
    if s.hunts:
        s.hunt_due(frame)


def toggles(s, frame, tick):
    """Its modules only (engine/modules/toggle.py, run by step)."""


def self_power(s, frame, tick):
    s.self_power_due(frame)


def expire(s, frame, tick):
    """Its modules only (lifetimes, toppled props, sales: engine/modules/lifetime.py, topple.py, sell.py)."""


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
    """Its modules only (engine/modules/spawn.py, run by step): the drones' replacements when due."""


def sweeps(s, frame, tick):
    s.sweeps.due(frame)


def deposit(s, frame, tick):
    """Its modules only (engine/modules/deposit.py, run by step)."""


def mine(s, frame, tick):
    s.mining.mine_due(s, frame, lambda owner, give: s.wallet.collect(s, owner, give))   # L2 pays through L4


def produce(s, frame, tick):
    s.produce_due(frame)


def counters(s, frame, tick):
    # DISPLAY_COUNTER shows the table's value, a running timer's frames left too (bench 11-10 engine_timer stop:
    # 109 94 80 ... after RESTART_TIMER; s.counters hides running timers): either executor's one table, read on each
    # mission second's first frame (until R3 ④-6, 11-18, the public executor's were read by Sim.sample at the tick's
    # end, a second later, running timers as 0)
    if s.test and s.test.counters and (frame - 1) % s.fps == 0 and s.t >= LAG:
        table = s.executor.counters
        s.series.append((int(round(s.t - LAG)), [table.get(c, (0,))[0] for c, _ in s.test.counters]))


def tick_first(s, frame, tick):
    """Default movement and acquisition: once a tick, on its first frame."""
    if not tick.moved and s.ending is None and s.t >= tick.t0 - 1e-9:
        tick.moved = True
        s.aura_tick()
        if s.combat:
            s.fight()
        if not s.shot_clock:
            s.move()
            tick.coarse = frame


def shot_clock(s, frame, tick):
    if s.shot_clock:             # the opt-in shot_clock integrates movement each frame
        s.move(1.0 / s.fps)
        tick.coarse = frame


# ---- right after a coarse move, on its frame only (tick_first / shot_clock): what move's tail was
def follow(s, frame, tick):
    if tick.coarse == frame:
        s.follow_due()


def capture(s, frame, tick):
    if tick.coarse == frame:
        s.capture_due()


def infiltrate(s, frame, tick):
    if tick.coarse == frame:
        s.infiltrators.tick()


def auto_kill(s, frame, tick):
    if tick.coarse == frame:
        s.auto_kill_due()


def aim(s, frame, tick):
    if s.mid_aims and s.combat and s.ending is None:
        s.aim_due()


def deal(s, frame, tick):
    if s.combat and s.ending is None:
        s.deal(1.0 / s.fps)      # R6: the aimed fire frame by frame, after the frame's scripts


CELLS = {f.__name__: f for f in (
    release, events, tech, scripts, seq, handed, lose_health, autoheal, passive_area_heal, repairs, assignments,
    suppression, flee, hunt, toggles, self_power, expire, garrison, frame_movers, build, blast, wfire, death_blast,
    spawn, sweeps, deposit, mine, produce, counters, tick_first, shot_clock, follow, capture, infiltrate, auto_kill,
    aim, deal)}

FRAME = ('release', 'events', 'tech', 'scripts', 'seq', 'handed', 'lose_health', 'autoheal', 'passive_area_heal',
         'repairs', 'assignments', 'suppression', 'flee', 'hunt', 'toggles', 'self_power', 'expire', 'garrison',
         'frame_movers', 'build', 'blast', 'wfire', 'death_blast', 'spawn', 'sweeps', 'deposit', 'mine', 'produce',
         'counters', 'tick_first', 'shot_clock', 'follow', 'capture', 'infiltrate', 'auto_kill', 'aim', 'deal')



def _with_modules(name, cell):
    """A cell as the frame runs it: first the update modules whose PHASE is its name (the kernel's schedule, at the
    same frame), then what of the cell is not yet a module. So a module file picks any cell of FRAME by its PHASE and
    nothing here changes (tests/test_kernel.py: a PHASE not in FRAME is red)."""
    def run(s, frame, tick):
        s.world.frame = frame       # what a broadcast wakes a module at (World.wake, step K2)
        s.world.schedule.run(name, frame)
        cell(s, frame, tick)
    run.__name__ = name
    return run


_FRAME = tuple(_with_modules(n, CELLS[n]) for n in FRAME)


def timed(totals):
    """FRAME's cells, each adding its wall seconds to totals[name]: the peak benchmark's per-cell clock
    (simbench_peak: step(s, timed(totals))); the plain loop pays nothing for it."""
    def clock(cell):
        name = cell.__name__

        def run(s, frame, tick):
            t0 = perf_counter()
            cell(s, frame, tick)
            totals[name] = totals.get(name, 0.0) + perf_counter() - t0
        return run
    return tuple(clock(c) for c in _FRAME)


def step(s, cells=_FRAME):
    """One DT tick from s.t (the caller moves s.t on): the tick's frames (those before s.t + DT, 7 or 8), each
    running FRAME in order (`cells`: the same order, timed()'s). The frame: the engine model's (its scripts cell moves
    it on); without the model the tick's own count from its first frame, the same for every cell of a frame."""
    t0, clock = s.t, s.clock
    last = math.ceil(round((t0 + DT) * s.fps, 6))
    tick = Tick(t0)
    while clock.frame < last and s.ending is None:
        s.t = clock.frame / s.fps
        for cell in cells:
            cell(s, clock.frame, tick)
    s.t = t0
