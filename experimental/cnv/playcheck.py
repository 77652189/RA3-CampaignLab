r"""A level's player script (plays/<level>.txt) as a bench check: the comparison game of ADR 0023.

The same play, run by the plan simulator and by the bench, and the two readings compared: how the mission ended (win /
lose) and when, and when its phases began. The simulator takes the play as `sim.Sim(script=...)`; the bench cannot, so
this compiles the play's lines into the mission's own script actions (a Test, like any check): `派` is
ATTACK_MOVE_NAMED_UNIT_TO, `占领 <who> 进 <building>` NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED Command_CaptureBuilding, `放 <who> <ability> 在 <site>` NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT, `生产 <unit> 在 <factory>` NAMED_USE_COMMANDBUTTON_ABILITY with the factory's build button, `造`a CREATE_NAMED_ON_TEAM_AT_WAYPOINT named `UNIT - SIM Made k`, `删除` / `摧毁` NAMED_DELETE
/ NAMED_KILL, `旗标` SET_FLAG; a time is a millisecond timer set when the mission starts (or, `<flag>+<time>`, when
the flag first reads 1). The sim runs that same Test too (checks/<level>.py: CHECKS[level]['play']), so what differs
between the two is the game's rules, not the translation.

The Test counts what the plan's own scripts already make visible, no more: `玩家局阶段` (the highest CNV_<tag>_Phase_k flag
up so far), optionally a cast part's health or a template's count (WATCH, to read where a play differs; four counter lines
fit in all), and expects what the simulator and the bench agreed on (EXPECT): the mission ends (the counters go with the
interface the moment the win / lose flag comes up) and each phase begins inside its window -- one-sided early too (a
counter already up before the window is a miss), because "by then" hides a bench that is much faster. A window is the
reading +-WINDOW (15 %, ADR 0023: past it, stop and find out why) and at least SLACK seconds. Won or lost is not a counter
(they are hidden by then): it is the end card on the run's last frames (RESULT_CARD), read by looking.

Not translated (the simulator's own verbs for a script that stands for something the bench cannot be told): `血量`,
`打`, `占领 <who>` (one object, at once), `不打`, `自动打掉`, a unit named by its template (an unnamed object cannot be addressed by a script):
compiling such a line raises, so a play is never half played on one side.

  python -I -X utf8 experimental/cnv/playcheck.py <level>       -> the play's lines compiled, and what the check expects
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(HERE, 'checks'), os.path.join(os.path.dirname(HERE), 'campaign'))
                if p not in sys.path]

from parts import Script, Test, counted

PLAYS = os.path.join(HERE, 'plays')
WINDOW = 0.15           # ADR 0023: a key time off by more than this much of the simulator's is a stop-and-find-out
SLACK = 4.0             # seconds: a window is never narrower (the counters are read every few seconds, scripts run per frame)
MADE = 'UNIT - SIM Made {}'

# level -> (result, flag second, [(phase k, second it begins)]) of a play on which the simulator and the bench AGREED (the
# bench check passed on it, docs/story/sim-vs-bench-plays.md). tests/test_playcheck.py runs the simulator again: past
# WINDOW of a reading, or another result, the test is red -- stop, find out why, run the bench again, re-baseline here.
# A level not in the table has no expectations: its check only prints readings (bench and simulator not yet agreed,
# or not yet compared). result: 1 win, 2 lose
WATCH = {       # level -> [(counter label, cast part)]: its health shown beside the result (three lines at most)
    'a4': [('1号车', 'truck 1'), ('2号车', 'truck 2'), ('3号车', 'truck 3')],
    'j7': [('天狗', 'count tengu 1'), ('海啸', 'count tsunami 1')],
}
SCENE = {       # level -> (the flag the opening scene's end sets, the simulator second it comes up at): the simulator plays the
                # opening scene (a4: 79.9 s, input locked), the bench skips it (checks/a4.py OPENING), so a play's absolute
                # times are counted from that flag on both sides (a4 play 2026-11-08: the raw times put the ice 80 s late
                # on the bench -- horn 1 hit the trucks first, a loss against the simulator's win)
    'a4': ('CNV_A4_Scene_1', 79.9),
}
BENCH_ENDS = {  # level -> the mission seconds the bench watches end at: a watch ends with Esc, which fails inside a phase's
                # scene (the bench then takes the mission for ended and skips the rest, a4 win 2026-11-08 s322), so no end
                # falls inside a scene (the simulator's phase seconds + ~60 s)
    'a4': [120, 200, 240, 340, 440, 540, 640, 740, 860, 980],     # the simulator's phases less the opening scene (80 s):
                                                                  # 233 / 277 / 548 / 655, +~15 s on the bench (a4 play)
}
EXPECT = {
    'a3': (1, 85.6, [(2, 23.0), (3, 55.0)]),     # bench 2026-11-08: PASS (phases s21 / s51, the flag s79-81, the victory card)
}
RESULT_CARD = {1: '胜利', 2: '失败'}   # the card the library shows (frame of the run: win / lose); the check cannot read it


def wording(level):
    return os.path.join(PLAYS, f'{level}.txt')


def phase_flags(m):
    """{k: flag} of the plan's phase flags the mission sets (CNV_<tag>_Phase_k)."""
    out = {}
    for s in m.scripts:
        for a in s.do:
            hit = a[0] == 'SET_FLAG' and re.fullmatch(r'CNV_\w+_Phase_(\d+)', a[1])
            if hit:
                out[int(hit.group(1))] = a[1]
    return dict(sorted(out.items()))


class Compiler:
    def __init__(self, m, t):
        self.m, self.t = m, t
        self.made = []                  # [(second or None, name)] the units a `造` line makes, in file order
        self.at_start = []              # (timer, seconds): armed when the mission starts
        self.k = 0

    def where(self, name):
        """The waypoint a place name stands for: the mission's marks and waypoints, else one of the map's sites."""
        m = self.m
        if name in m.marks:
            return m.marks[name]
        if name in m.waypoints:
            return name
        wp = f'Play {name}'
        if wp not in self.t.waypoints:
            from model import coord
            if coord(name) is not None:                             # '@x,y': a waypoint at those map coordinates
                self.t.waypoints[wp] = coord(name)
            elif name in m.cast and m.cast[name].name:               # a cast part: where it stands
                o = m.find(m.cast[name].name)
                self.t.waypoints[wp] = (o.x, o.y)
            else:
                self.t.waypoints[wp] = m.site(name)
        return wp

    def who(self, text, now):
        """The object names a line's unit text means at second `now` (None: after a flag, every `造` above it)."""
        m, text = self.m, text.strip()
        if text.startswith('名字含 '):
            part = text[4:].strip()
            for k, o in enumerate(o for o in m.objects if not o.name and part in o.template):
                o.name = f'UNIT - Play {o.template} {k + 1}'         # the simulator names an unnamed object by its template;
            names = [o.name for o in m.objects if o.name and part in o.name]          # a script needs a name to order it
            names += [a[1] for s in m.scripts for a in s.do                            # a unit the plan's own scripts make
                      if a[0].startswith('CREATE_NAMED_ON_TEAM_AT_WAYPOINT') and part in a[1] and a[1] not in names]
            names += [n for sec, n in self.made if part in n and (sec is None or now is None or sec <= now)]
            if not names:
                raise ValueError(f'play: no named object has {part!r} in its name (an unnamed object cannot be ordered by a script)')
            return names
        if text in m.cast and m.cast[text].name:
            return [m.cast[text].name]
        names = [r.name for k, r in m.cast.items() if re.fullmatch(re.escape(text) + r' \d+', k) and r.name]
        if not names:
            raise ValueError(f'play: {text!r} is no cast part with a name')
        return names

    def template(self, what):
        m = self.m
        if any(u.id == what for u in m.units):
            return what
        if what in m.cast:
            return m.cast[what].template
        return what

    def actions(self, event, now):
        verb, rest = event[1], event[2:]
        if verb == '派':
            who, where = rest
            wp = self.where(where)
            return [('ATTACK_MOVE_NAMED_UNIT_TO', n, wp) for n in self.who(who, now)]
        if verb == '走':                    # a plain move (the simulator's order_move(..., attacking=False))
            who, where = rest
            wp = self.where(where)
            return [('MOVE_NAMED_UNIT_TO', n, wp) for n in self.who(who, now)]
        if verb == '攻击':
            who, target = rest
            goal = self.who(target, now)[0]
            return [('NAMED_ATTACK_NAMED', n, goal) for n in self.who(who, now)]
        if verb == '放':
            who, ability, where = rest
            wp = self.where(where)
            out = []
            for n in self.who(who, now):
                power = self.m.ability(who.strip(), ability) if who.strip() in self.m.cast else None
                if power is None:
                    o = next((x for x in self.m.objects if x.name == n), None)
                    tmpl = o.template if o else next((a[2] for s in self.m.scripts for a in s.do      # a unit the plan's own scripts make
                                                      if a[0].startswith('CREATE_NAMED_ON_TEAM_AT_WAYPOINT') and a[1] == n), None)
                    u = next((u for u in self.m.units if tmpl and u.id == tmpl), None)
                    power = u.abilities.get(ability) if u else None
                out.append(('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', n, power or ability, wp))
            return out
        if verb == '占领' and len(rest) == 2:
            who, target = rest
            goal = self.who(target, now)[0]
            return [('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', n, 'Command_CaptureBuilding', goal)
                    for n in self.who(who, now)]
        if verb == '生产':                  # the factory's build button (a script's press = the player's click: bench
            import simunits                 # engine_production e)
            what, where = rest
            tmpl, own = self.template(what), {u.id: u.xml for u in self.m.units}
            out = []
            for n in self.who(where, now)[:1]:
                o = next((x for x in self.m.objects if x.name == n), None)
                button = simunits.build_button(o.template, tmpl, own) if o else None
                if button is None:
                    raise ValueError(f'play: {where!r} has no build button for {tmpl}')
                out.append(('NAMED_USE_COMMANDBUTTON_ABILITY', n, button))
            return out
        if verb in ('删除', '摧毁'):
            return [('NAMED_DELETE' if verb == '删除' else 'NAMED_KILL', n) for n in self.who(rest[0], now)]
        if verb == '旗标':
            return [('SET_FLAG', rest[0], rest[1])]
        if verb == '造':
            what, where, angle = rest
            name = MADE.format(len(self.made))
            self.made.append((now, name))
            wp = self.where(where)
            if angle:
                return [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', name, self.template(what),
                         self.m.team('p1'), wp, angle)]
            return [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', name, self.template(what), self.m.team('p1'), wp)]
        raise ValueError(f'play: {verb!r} has no script action (the simulator\'s own verb)')

    def play(self, level):
        import sim
        events = sim.parse_script(wording(level))
        for e in events:
            if e[0] is None:
                raise ValueError(f'play: {e[1]!r} is the simulator\'s own setting, the bench cannot play it')
        for i, e in enumerate(events):
            when = e[0]
            now = None if isinstance(when, tuple) else when
            do = self.actions(e, now)
            timer = f'Play {i}'
            if not isinstance(when, tuple) and level in SCENE:      # a time of the simulator's clock, which plays the opening
                flag, hand_back = SCENE[level]                      # scene; the bench skips it: counted from the scene's flag
                if when < hand_back:
                    raise ValueError(f'play: {when:g} s is inside the opening scene (the player has control from {hand_back:g} s)')
                when = ('@', flag, when - hand_back)
            if isinstance(when, tuple):          # ('@', flag, delta): that long after the flag first reads 1
                self.t.scripts.append(Script(f'Test - play arm {i}', [('FLAG', when[1], 1)],
                                             [('SET_MILLISECOND_TIMER', timer, float(when[2]))]))
            else:
                self.at_start.append((timer, float(when)))
            self.t.scripts.append(Script(f'Test - play {i}', [('TIMER_EXPIRED', timer)], do))
        if self.at_start:
            self.t.scripts.append(Script('Test - play start', [], [('SET_MILLISECOND_TIMER', n, s) for n, s in self.at_start]))
        return events


def build(m, level, run=None):
    """The Test of `level`'s play: the play's scripts, the counters, and (when the simulator's readings are known) the
    expectations on them. `run` overrides EXPECT[level] (a mutation, or a level not yet in the table)."""
    t = Test()
    Compiler(m, t).play(level)
    t.counters += [('Test Phase', '玩家局阶段')]
    for k, (label, part) in enumerate(WATCH.get(level, [])):        # for reading where a play differs
        if part.startswith('count '):                               # how many the player owns of that cast part's template
            counted(f'Test Watch {k}', label, t, template=m.role(part[6:]).template, most=12)
        else:                                                       # a cast part's health
            counted(f'Test Watch {k}', label, t, health=m.role(part).name)
    t.scripts.append(Script('Test - phase zero', [], [('SET_COUNTER', 'Test Phase', 0)]))
    for k, flag in phase_flags(m).items():
        t.scripts.append(Script(f'Test - phase {k}', [('FLAG', flag, 1)], [('SET_COUNTER', 'Test Phase', k)], once=False))
    if run is None:
        run = EXPECT.get(level)
    if run:
        result, end, phases = run
        t.expect += window_expect(result, end, phases)
        t.bench = [('bench_watch', dict(seconds=end * (1 + WINDOW) + SLACK + 10, every=2, sheet=False, lines=len(t.counters)))]
    if level in BENCH_ENDS:                 # a long play: watches (each at most 120 s) that end outside the phase scenes
        at, t.bench = 0.0, []
        for stop in BENCH_ENDS[level]:
            t.bench.append(('bench_watch', dict(seconds=stop - at, every=4, sheet=False, lines=len(t.counters))))
            at = stop
    return t


def window(sec):
    """(from, until) seconds for a reading of the simulator at `sec`."""
    w = max(SLACK, WINDOW * sec)
    return sec - w, sec + w


def window_expect(result, end, phases):
    """The expectations the simulator's readings make: each phase begins inside its window (not before it, up by its end),
    the mission ends inside its window and the result counter never reads the other ending."""
    out = []
    for k, sec in phases:
        if sec < SLACK:                     # begins with the mission: nothing to time
            continue
        lo, hi = window(sec)
        out += [('玩家局阶段', 2, '<', k, lo), ('玩家局阶段', hi, 'ever>=', k)]
    lo, hi = window(end)                    # `end`: the second the plan's Mission Won / Lost flag comes up
    # the counters go with the interface the moment the flag comes up (bench 2026-11-08, a3 play: no counter on the frame
    # after it, the victory card 2 s later), so ENDED is the flag's second, and the counters cannot say won or lost: that is
    # the end card on the last frames of the run (RESULT_CARD)
    out.append(('ENDED', lo, '', None, hi))
    return out


def make(level):
    """The check for CHECKS[level]['play']."""
    return lambda m: build(m, level)


def read(level, until=1800.0, native=False):
    """What the simulator reads on the play: (result, ending second, [(phase k, second it begins)], the Sim).
    native: the play as sim.Sim's own `script` (not compiled) -- the two must agree (tests/test_playcheck.py)."""
    import build as b
    import sim
    m, _, _ = b.resolve(level, '')
    if native:
        s = sim.Sim(m, None, script=wording(level)).run(until)
        t = build(m, level, run=())            # only for its counters
    else:
        t = build(m, level)
        s = sim.Sim(m, t).run(until)
    return t, s


def readings(t, s):
    """(result, ending second, phases) off the Test's counter series (`s.series`: (second, [one value per counter]))."""
    labels = [label for _, label in t.counters]
    pi = labels.index('玩家局阶段')
    phases, last = [], 0
    for sec, v in s.series:
        if v[pi] and v[pi] > last:
            last = v[pi]
            phases.append((last, sec))
    if not s.ending:                    # the simulator stops at the flag (not 5 s / 3 s later like the library): its ending is the reading
        return 0, s.t, phases
    how, sec, _ = s.ending
    return (1 if how == '赢' else 2), sec, phases


def main():
    import build as b
    level = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == 'sim':
        t, s = read(level, native='--native' in sys.argv)
        print(s.ending_line())
        print('result, ending, phases:', readings(t, s))
        return
    m, _, _ = b.resolve(level, '')
    t = build(m, level)
    for sc in t.scripts:
        print(sc.name, sc.when, sc.do)
    print('expects:', t.expect)


if __name__ == '__main__':
    main()
