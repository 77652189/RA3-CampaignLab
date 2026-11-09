r"""The proxy player on the plan simulator: sim.Sim behind the proxy player's World seam (the engine line's
RA3-EngineModel ra3model/proxy, labpaths.ENGINE_MODEL), so a level is played start to end by a player who acts as the
user says he plays (counter by unit kind, pull back the wounded, knock out the pressure source first) and a playtest
report comes out: won or lost, when, what each side lost, whether the level's clever solution (巧解) was used.

This file only calls the simulator (Sim's own world: bodies, side_sees, order_move / order_attack, act, step and
sample as Sim.run does); it changes none of sim.py's rules. Where the proxy package is not on this computer (a clean
clone) nothing here runs: available() is False and the tests skip, as sim.py's engine model does.

  python -I -X utf8 experimental/cnv/simproxy.py [level] [--until <seconds>] [--json <file>]

What the world shows the player (Observation, ra3model/proxy/world.py):
  mine    the player's own units that move (no buildings, no scenery), as Mine; good_against / rates / cost from the
          proxy's Matchup on the SDK's data when the template is a retail one, else roles_from_name (CNV_* parts)
  seen    every living, non-scenery body of an enemy or of the civilians the player sees now (Sim.side_sees: vision,
          the high-ground rule, reveals) as ai.targets.Thing; civilians' owner ''
  money   Sim.money less what the player's queued builds still owe; offers: Sim.offers (the live factories' lit
          buttons) with Matchup's good_against / rates; a 'build' order is Sim.order_build (refused when no factory
          of the player's builds it now -- A4 has none)
  home    the level's start site, or on an escort level (ESCORT) the middle of the living convoy; leads: LEADS[level] (the briefing's places), each a map site
  chokes  CHOKES[level]: each way's block site and threat source, the on-screen countdown's end (the horn), the power
          that blocks (the ice engineer's) and whether ice stands there now; the proxy decides when and which to ice
          (player._blocks, Style.block = 0 never ices: --compare plays both)
  cinematic  not SimWorld.control() (a scene holds the player's input, or the first tick has not run yet; issue
          refuses every order then); healing HEALING[level]
          (the simulator heals nobody: False); counters what each seen template is made to kill (Matchup good_against)
What the player may do (Order): 'move' (a plain move), 'attack' (Sim.order_attack on a body), 'power' with a pos (a
ground power: NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT at a waypoint made for it -- the ice engineer walks there and
builds, the simulator's R5) or with a target (noted only). losses(): every death so far (not deleted, not scenery,
not a body with a lifetime of its own -- ice walls melting are not losses), the score screen.
The end: Sim.ending ('赢' -> 'win', '输' -> 'lose'), else the run's frames run out ('timeout').
"""
import argparse
import importlib
import importlib.util
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import labpaths  # noqa: E402
import sim  # noqa: E402

FPS = 15
DIFFICULTY = 'normal'
UNTIL = 900.0                   # seconds a playtest runs to at the latest (A4 is a 14-minute level)
ENDINGS = {'赢': 'win', '输': 'lose'}

# the places a level's briefing points the player at (map sites): where the proxy scouts when it knows of no target
LEADS = {
    'a4': ('plaza 1', 'lane foot', 'plaza 2', 'harbour', 'north base', 'north mouth', 'plaza 3', 'east mouth'),
}
# an escort level's convoy (cast parts): the player's 'home' is where its living members are (INFERRED: a human
# escorting keeps his army round the trucks, answers what comes at them, sends the wounded there)
ESCORT = {
    'a4': ('truck 1', 'truck 2', 'truck 3'),
}
# a level's clever solution, as places for report.power_at: (goal name, the map sites, radius, note)
ICE_GOALS = {
    'a4': (('会场冻街口', ('lane foot', 'inside 1', 'inside 2'), 200.0,
            '会场三条街（后巷、一号、二号）的街口冻上冰墙：那条街的兵改去开着的街、晚出'),
           ('最后一程冻口子', ('north mouth', 'inside 3', 'east mouth'), 200.0,
            '最后一程三个口子冻上冰墙：兵在墙后攒着')),
}
# where a level's coming threat can be blocked (proxy world.Choke): what a human sees -- the countdown on screen
# ('countdown': the timer DISPLAY_COUNTDOWN_TIMER shows), the ways the briefing and the signs point at (name, the
# site the block goes on, the site the threat comes out of), and the power that blocks (cast part, ability). The
# proxy decides when and which (player._blocks); nothing here says which way to block.
CHOKES = {
    # 'seed': what the power puts down; its lifetime is the build bar the player watches (Choke.build)
    'a4': {'countdown': 'CNV A4 Horn', 'power': ('engineer', 'freeze'), 'seed': 'CNV_A4IceSeed',
           # the road each way's threat walks onto (a site on it): a way's JUNCTION is (its block site's x, the road's y),
           # where its wave meets the convoy's road -- where the guard waits for it (SimWorld.junctions)
           'road': 'convoy start',
           'ways': (('后巷', 'lane foot', 'lane foot'), ('一号', 'inside 1', 'plaza 1'), ('二号', 'inside 2', 'plaza 2'),
                    ('北坡口', 'north mouth', 'north mouth'), ('三号广场', 'inside 3', 'plaza 3'),
                    ('东街口', 'east mouth', 'east mouth'))},
}
# levels with somewhere the wounded heal (Observation.healing): the simulator heals nobody (no auto-heal, no repair
# modelled), so every level is False until it does; A4's first part has no repair on purpose (flow/a4.md)
HEALING = {}
BLIP_KEEP = 30.0               # seconds a minimap flash stays in Observation.blips (the proxy decides how long it matters)
BLOCKED_R = 120.0             # a choke counts as blocked while a body with a lifetime of its own (ice) stands this close
# a level's own targets the report asks about: (goal name, cast part, note)
TARGET_GOALS = {
    'a4': (('拆北营指挥所', 'north command', '第 3 段：指挥所一倒港口的兵撤走、车队走最后一程'),),
}

_PROXY = {}


def _package(folder):
    """The engine model's ra3model package, loaded by file as sim.engine_model does (nothing added to sys.path, guard
    G4): its submodules then import by name through the package's own path."""
    if 'ra3model' in sys.modules:
        return sys.modules['ra3model']
    spec = importlib.util.spec_from_file_location('ra3model', os.path.join(folder, '__init__.py'),
                                                  submodule_search_locations=[folder])
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ra3model'] = mod
    spec.loader.exec_module(mod)
    return mod


def proxy():
    """The engine line's ra3model.proxy modules (world, player, report, matchup) as a namespace dict, or None."""
    if 'got' not in _PROXY:
        root = labpaths.ENGINE_MODEL
        got = None
        if os.path.isfile(os.path.join(root, 'ra3model', 'proxy', 'world.py')):
            try:
                _package(os.path.join(root, 'ra3model'))
                got = {k: importlib.import_module(f'ra3model.proxy.{k}') for k in ('world', 'player', 'report',
                                                                                   'matchup')}
                got['targets'] = importlib.import_module('ra3model.ai.targets')
                got['xmldata'] = importlib.import_module('ra3model.objects.xmldata')
            except ImportError:
                got = None
        _PROXY['got'] = got
    return _PROXY['got']


def available():
    return proxy() is not None


def _hits(weapons):
    """The domains a body's weapons hit (ai.targets.Thing.hits) from the simulator's anti masks."""
    out = set()
    for w in weapons:
        anti = w.get('anti') or ()
        if not anti:
            out.add('ground')
        for a in anti:
            if a.startswith('ANTI_AIRBORNE'):
                out.add('air')
            elif a == 'ANTI_WATER':
                out.add('water')
            elif a in ('ANTI_GROUND', 'ANTI_STRUCTURE'):
                out.add('ground')
    return frozenset(out)


class SimWorld:
    """A level in the plan simulator as the proxy player's World (observe / issue / step / losses)."""

    def __init__(self, level='a4', check='', script='', difficulty=DIFFICULTY, leads=None, lib=None, show=False):
        import build
        p = proxy()
        if p is None:
            raise RuntimeError(f'ra3model.proxy not found under {labpaths.ENGINE_MODEL}')
        self.p, self.pw = p, p['world']
        self.level = level
        m, t, _ = build.resolve(level, check)
        if show:        # simshow.ShowSim is sim.Sim plus presentation records (it changes no rule): what the player saw
            import simshow
            self.sim = simshow.ShowSim(m, t, difficulty, script)
        else:
            self.sim = sim.Sim(m, t, difficulty, script)
        self.me = self.sim.human
        self.ids, self.names = {}, {}          # body name <-> the int id the player knows it by
        home = self.sim.point('start')
        self.home = tuple(home) if home else (0.0, 0.0)
        names = LEADS.get(level, ()) if leads is None else leads
        self.leads = [tuple(q) for q in (self.sim.point(n) for n in names) if q]
        self.escort = [s.m.cast[n].name for n in ESCORT.get(level, ()) if n in s.m.cast] if (s := self.sim) else []
        self.match = p['matchup'].Matchup(lib if lib is not None else p['xmldata'].Library())
        self._offer = {}
        self.refused = []                       # (frame, Order, why) the world would not take
        self._blips, self._log_read = [], 0     # minimap flashes seen so far (blips), how far Sim.log is read

    # ---- the clock
    @property
    def frame(self):
        s = self.sim
        return s.eng.frame if s.eng is not None else int(round(s.t * FPS))

    def step(self, frames):
        """Run the simulator `frames` on (Sim.advance: run's ticks a slice at a time, stopping at the mission's end)."""
        self.sim.advance(frames)

    def result(self):
        e = self.sim.ending
        return ENDINGS.get(e[0], 'lose') if e else None

    def end(self, obs):
        """report.run's end(obs): the mission's own win / lose."""
        return self.result()

    # ---- what the player sees
    def _id(self, b):
        if b.name not in self.ids:
            self.ids[b.name] = len(self.ids) + 1
            self.names[self.ids[b.name]] = b.name
        return self.ids[b.name]

    def _data(self, template):
        """(cost, good_against, rates) of a template: the SDK's data, or the name's guess for a part of ours."""
        if template not in self._offer:
            tpl = self.match.lib.template(template)
            if tpl is not None:
                o = self.match.offer(template)
                self._offer[template] = (o.cost, o.good_against, o.rates)
            else:
                self._offer[template] = (0, self.pw.roles_from_name(template), {})
        return self._offer[template]

    def _is_unit(self, b):
        return b.alive and not b.scenery and b.speed > 0 and 'STRUCTURE' not in b.kinds

    def _mine(self, b):
        cost, good, rates = self._data(b.template)
        busy = 'attack' if isinstance(b.goal, sim.Body) else ('move' if b.path or b.building else '')
        return self.pw.Mine(self._id(b), b.template, frozenset(b.kinds), b.x, b.y, b.hp, b.max_hp, cost,
                            max((w['range'] for w in b.weapons), default=0.0), b.vision or 300.0, good, (), busy,
                            rates, float(b.speed or 0.0),
                            frozenset(p for p, f in b.ready_at.items() if f > self.sim.frame_now()))

    def _thing(self, b):
        cost, _, _ = self._data(b.template)
        goal = b.goal if isinstance(b.goal, sim.Body) else None
        return self.p['targets'].Thing(self._id(b), '' if b.owner == sim.CIV else b.owner, b.template,
                                       frozenset(b.kinds), frozenset(b.status), b.x, b.y,
                                       water=b.surface == 'water', value=float(cost), hits=_hits(b.weapons),
                                       attacking_us=bool(goal and not self.sim.enemy(self.me, goal.owner)))

    def enemies(self):
        return frozenset(p for p in self.sim.players.values() if p != self.me and self.sim.enemy(self.me, p))

    def _convoy(self):
        return [b for b in (self.sim.bodies.get(n) for n in self.escort) if b is not None and b.alive]

    def where_home(self):
        convoy = self._convoy()
        if not convoy:
            return self.home
        return (sum(b.x for b in convoy) / len(convoy), sum(b.y for b in convoy) / len(convoy))

    def observe(self):
        s = self.sim
        s.seen = {}                             # this moment's sight (Sim.fight clears it each tick too)
        mine = [self._mine(b) for b in s.living() if b.owner == self.me and self._is_unit(b)]
        seen = [self._thing(b) for b in s.living() if not b.scenery and b.owner != self.me
                and (b.owner == sim.CIV or s.enemy(self.me, b.owner)) and s.side_sees(self.me, b)]
        return self.pw.Observation(self.frame, self.me, self.money(), self.where_home(), mine, seen, self.offers(),
                                   self.enemies(), list(self.leads), self.chokes(), escort=bool(self._convoy()),
                                   cinematic=not self.control(), healing=HEALING.get(self.level, False),
                                   counters={t.template: self._data(t.template)[1] for t in seen},
                                   blips=self.blips())

    def blips(self):
        """[(frame, x, y)] the minimap flashes (the scripts' OBJECT_CREATE_RADAR_EVENT, Sim.log '小地图闪点', named by
        the object they flash on) of the last BLIP_KEEP seconds, where that object stands: a human sees the flash even
        where the fog hides the object. Read off the log as it grows (a flash is placed when first read: observe runs
        every decision, before the flashed object has walked off)."""
        s = self.sim
        for t, kind, text in s.log[self._log_read:]:
            if kind == '小地图闪点':
                b = s.bodies.get(text)
                if b is not None:
                    self._blips.append((int(round(t * FPS)), float(b.x), float(b.y)))
        self._log_read = len(s.log)
        keep = self.frame - int(BLIP_KEEP * FPS)
        self._blips = [b for b in self._blips if b[0] >= keep]
        return list(self._blips)

    def money(self):
        """What the player can still spend: the bank less what the queued builds will still take (Sim.order_build pays
        frame by frame, so the bank alone would let the player queue far more than it can pay for)."""
        s = self.sim
        owed = sum(j['cost'] - j['paid'] for q in s.queues.values() for j in q if j['owner'] == self.me)
        return int(s.money.get(self.me, 0)) - int(owed)

    def offers(self):
        """The lit sidebar buttons (Sim.offers: the player's live factories, prerequisites held, not banned) as the
        proxy's Offers: KindOf / good_against / rates from the data (Matchup.offer), cost and time from the simulator."""
        out = []
        for template, cost, secs in self.sim.offers(self.me):
            tpl = self.match.lib.template(template)
            _, good, rates = self._data(template)
            out.append(self.pw.Offer(template, frozenset(tpl.kinds) if tpl is not None else frozenset(), int(cost),
                                     good, float(secs), rates=rates))
        return out

    def chokes(self):
        """The level's chokes (CHOKES) as the player sees them now: the countdown's end if it is on screen, whether
        an ice wall (a body with a lifetime of its own, not a unit) stands in the mouth."""
        spec = CHOKES.get(self.level)
        if not spec:
            return []
        s = self.sim
        name = spec['countdown']
        at = int(round(s.timers[name] * FPS)) if name in s.countdowns and name in s.timers else None
        part, ability = spec['power']
        power = s.m.ability(part, ability) if part in s.m.cast else None
        by = frozenset({s.m.cast[part].template}) if part in s.m.cast else frozenset()
        walls = [(b.x, b.y) for b in s.living() if b.life_end is not None and b.speed == 0 and not b.scenery]
        life = sim.simunits.lifetime(spec['seed'], s.own)[0] if spec.get('seed') else None
        build = life / FPS if life else 0.0
        out = []
        for way, block, source in spec['ways']:
            p, q = s.point(block), s.point(source)
            if not p or not q:
                continue
            blocked = any(math.hypot(x - p[0], y - p[1]) <= BLOCKED_R for x, y in walls)
            out.append(self.pw.Choke(way, tuple(p), tuple(q), at, power or '', by, blocked, build))
        return out

    def junctions(self):
        """{way: (x, y)}: where each of the level's ways meets the convoy's road (CHOKES 'road'), the spot a guard
        stands to meet the wave that comes out of it -- not the ice's mouth (up the street) nor the convoy."""
        spec = CHOKES.get(self.level) or {}
        road = self.sim.point(spec.get('road', ''))
        out = {}
        for way, block, _source in spec.get('ways', ()):
            p = self.sim.point(block)
            if road and p:
                out[way] = (float(p[0]), float(road[1]))
        return out

    # ---- what the player does
    def _body(self, i):
        b = self.sim.bodies.get(self.names.get(i))
        return b if b is not None and b.alive else None

    def _refuse(self, o, why):
        self.refused.append((self.frame, o, why))
        return False

    def control(self):
        """The player has control: no scene holds the input (Sim.input, ENABLE_INPUT) and the first tick has run.
        Before it the level's scripts have not yet said whether a scene opens the mission (A4 locks the input in its
        first tick): orders the proxy gave at frame 0 sent a unit into lane foot and set the convoy off ~85 s early
        (round 40, 2026-11-07)."""
        return self.sim.input and self.sim.t > 0

    def issue(self, o):
        s = self.sim
        if not self.control():
            return self._refuse(o, 'cinematic: no control')
        if o.kind == 'build':
            return True if s.order_build(self.me, o.template) else self._refuse(o, 'no factory of mine builds it now')
        units = [self._body(i) for i in o.units]
        units = [b for b in units if b is not None and b.owner == self.me]
        if not units:
            return self._refuse(o, 'no living unit of mine')
        if o.kind in ('move', 'attack_move'):
            if o.pos is None:
                return self._refuse(o, 'move without a place')
            for b in units:
                b.goal = None
            s.order_group(units, (float(o.pos[0]), float(o.pos[1])), o.kind == 'attack_move')   # a selection: a group
            return True
        if o.kind == 'attack':
            t = self._body(o.target)
            if t is None:
                return self._refuse(o, 'target gone')
            for b in units:
                s.order_attack(b, t.name)
            return True
        if o.kind == 'power':
            if o.pos is not None:               # a ground power: the player's click (Sim.order_power: reload, ground,
                whys = []                       # ForbiddenObjectRange, reach), then the scripts' way at a waypoint
                for b in units:
                    ok, why = s.order_power(b, o.power, o.pos)
                    if not ok:
                        whys.append(why)
                if len(whys) == len(units):
                    return self._refuse(o, f'power refused: {", ".join(sorted(set(whys)))}')
            else:
                for b in units:
                    s.note('技能', f'{s.label(b)} 用 {o.power}' + (f' 打 #{o.target}' if o.target else ''))
            return True
        return self._refuse(o, f'unknown order {o.kind}')

    # ---- the score screen
    def losses(self):
        s = self.sim
        out = []
        for b in s.bodies.values():
            if b.alive or b.deleted or b.scenery or b.died_at is None or b.life_end is not None:
                continue
            cost, _, _ = self._data(b.template)
            kind = self.pw.kind_of(self.p['targets'].Thing(0, b.owner, b.template, frozenset(b.kinds),
                                                           water=b.surface == 'water'))
            out.append(self.pw.Loss(int(round(b.died_at * FPS)), '' if b.owner == sim.CIV else b.owner,
                                    b.template, kind, int(cost)))
        return sorted(out, key=lambda l: (l.frame, l.owner, l.template))


def goals(world):
    """The level's puzzle checks (report Goals): where the ice went (report.power_at), its own targets destroyed."""
    rp = world.p['report']
    s = world.sim
    out = []
    for name, sites, radius, note in ICE_GOALS.get(world.level, ()):
        pts = [tuple(q) for q in (s.point(n) for n in sites) if q]
        out.append(rp.power_at(pts, radius, name=name, note=note))
    for name, part, note in TARGET_GOALS.get(world.level, ()):
        b = s.bodies.get(s.m.cast[part].name) if part in s.m.cast else None
        if b is not None:
            out.append(rp.destroyed(b.template, name=name, note=note))
    return out


def play(level='a4', style=None, until=UNTIL, every=15, check='', script='', difficulty=DIFFICULTY, label='',
         lib=None, show=False):
    """One playtest: (report dict, the SimWorld). The proxy plays until the mission ends or `until` seconds.
    show=True also reads what the player saw off the run (simshow.problems) into rep['world']['show']."""
    w = SimWorld(level, check, script, difficulty, lib=lib, show=show)
    p = w.p
    player = p['player'].ProxyPlayer(style)
    tr = p['report'].run(w, player, int(until * FPS), every, end=w.end, label=label or level)
    rep = p['report'].report(tr, goals(w))
    rep['world'] = {'simulator_ending': w.sim.ending_line(), 'refused': len(w.refused),
                    'guessed': sorted(w.sim.guessed)[:20]}
    if show:
        import simshow
        rep['world']['show'] = simshow.problems(w.sim)
    return rep, w


def report(level='a4', **kw):
    """The playtest report alone (play()'s first half)."""
    return play(level, **kw)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('level', nargs='?', default='a4')
    ap.add_argument('--until', type=float, default=UNTIL)
    ap.add_argument('--level', dest='difficulty', default=DIFFICULTY, choices=list(sim.LEVELS))
    ap.add_argument('--json', default='', help='write the whole report here (with --compare: a list of both)')
    ap.add_argument('--compare', action='store_true', help="also play without the level's power and compare")
    a = ap.parse_args()
    if not available():
        print(f'没有代理玩家（{labpaths.ENGINE_MODEL} 下没有 ra3model/proxy）')
        sys.exit(2)
    rep, w = play(a.level, until=a.until, difficulty=a.difficulty, label=f'{a.level} 默认', show=a.compare)
    reps = [rep]
    print(w.p['report'].summary(rep))
    print(rep['world']['simulator_ending'])
    if a.compare:
        plain, _ = play(a.level, style=w.p['player'].Style(block=0), until=a.until, difficulty=a.difficulty,
                        label=f'{a.level} 不用关卡技能', lib=w.match.lib, show=True)
        reps.append(plain)
        print(w.p['report'].compare(reps))
        for r in reps:         # what the player saw on each run (simshow.problems: K5 black edge, K1 captions, I1, flow)
            probs = r['world']['show']
            print(f'## 玩家看到的（{r.get("label", "")}）：{len(probs)} 个问题')
            for x in probs:
                print('- ' + x)
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(reps if a.compare else rep, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
