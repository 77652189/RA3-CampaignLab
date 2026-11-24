r"""The proxy player on the plan simulator: sim.Sim behind the proxy player's World seam (experimental/cnv/proxy, a
public player of our own design: ADR 0033 3), so a level is played start to end by a player who acts as the
user says he plays (counter by unit kind, pull back the wounded, knock out the pressure source first) and a playtest
report comes out: won or lost, when, what each side lost, whether the level's clever solution (巧解) was used.

This file only calls the simulator (Sim's own world: bodies, side_sees, act, step and sample as Sim.run does; its
orders through the command port, engine/ports/command.py, R3 13e); it changes none of sim.py's rules.

  python -I -X utf8 experimental/cnv/simproxy.py [level] [--until <seconds>] [--json <file>]

What the world shows the player (Observation, proxy/world.py):
  mine    the player's own units that move (no buildings, no scenery), as Mine; good_against / rates / cost from the
          proxy's Matchup on the simulator's unit data when the template is a retail one, else roles_from_name (CNV_* parts)
  seen    every living, non-scenery body of an enemy or of the civilians the player sees now (Sim.side_sees: vision,
          the high-ground rule, reveals) as proxy world.Thing; civilians' owner ''
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
import json
import math
import os
import sys
import weakref

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import sim  # noqa: E402
import engine.combat.range as simrange  # noqa: E402
import engine.data.units as simunits  # noqa: E402
import engine.world.handle as simworld  # noqa: E402
from engine.modules import lifetime as lifetime_module  # noqa: E402
from engine.ports.command import Command  # noqa: E402
from proxy import matchup, player, report as preport, world as pworld  # noqa: E402

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

PROXY = {'world': pworld, 'player': player, 'report': preport, 'matchup': matchup}   # SimWorld.p

# What the proxy player reads on the Sim beyond the world (simworld.WORLD_API): the orders a player gives, the run's
# end and its advance, the bank and the build queues, the lit buttons, the on-screen countdowns, the input lock, the log
# it reads the minimap flashes off, and the sight it asks (forget_sight, side_sees). It sets nothing there (no WRITES:
# step 9d-1 moved its one write, the sight, onto Sim.forget_sight).
# Its orders go through the command port (`commands`, R3 13e), not the Sim's order calls.
PEERS = frozenset({'advance', 'commands', 'countdowns', 'ending', 'forget_sight', 'input', 'log', 'money', 'offers',
                   'production', 'side_sees', 'timers'})


class Peers:
    """What the proxy player may read on its Sim beyond the world: the names in PEERS, read when used."""
    __slots__ = ('host',)

    def __init__(self, host):
        self.host = host

    def __getattr__(self, name):
        if name not in PEERS:
            raise AttributeError(f'simproxy.Peers: {name} is not lent (PEERS)')
        return getattr(self.host, name)



class SimWorld:
    """A level in the plan simulator as the proxy player's World (observe / issue / step / losses)."""

    def __init__(self, level='a4', check='', script='', difficulty=DIFFICULTY, leads=None, show=False):
        import build
        self.p, self.pw = PROXY, pworld
        self.level = level
        m, t, _ = build.resolve(level, check)
        self.sim = sim.Sim(m, t, difficulty, script)
        self.show = None
        if show:        # simshow.Show: presentation records on the run's taps (it changes no rule): what the player saw
            import simshow
            self.show = simshow.attach(self.sim)
        # every read of the Sim outside this method goes through the world API and the loan (PEERS); self.sim stays
        # for play() and the tests
        self.world, self.peers = self.sim, Peers(self.sim)
        self.me = self.sim.human
        # the int id the player knows an object by: one per object (by its serial), never per name -- an old id is not
        # a new object's of the same name (review 11-19 j #2); `names` its name, for the record and the tests
        self.ids, self.names, self.things = {}, {}, weakref.WeakValueDictionary()
        home = self.sim.point('start')
        self.home = tuple(home) if home else (0.0, 0.0)
        names = LEADS.get(level, ()) if leads is None else leads
        self.leads = [tuple(q) for q in (self.sim.point(n) for n in names) if q]
        self.escort = [s.m.cast[n].name for n in ESCORT.get(level, ()) if n in s.m.cast] if (s := self.sim) else []
        self.match = matchup.Matchup()
        self._offer = {}
        self.refused = []                       # (frame, Order, why) the world would not take
        self._blips, self._log_read = [], 0     # minimap flashes seen so far (blips), how far Sim.log is read

    # ---- the clock
    @property
    def frame(self):
        return self.world.frame_now()

    def step(self, frames):
        """Run the simulator `frames` on (Sim.advance: run's ticks a slice at a time, stopping at the mission's end)."""
        self.peers.advance(frames)

    def result(self):
        e = self.peers.ending
        return ENDINGS.get(e[0], 'lose') if e else None

    def end(self, obs):
        """report.run's end(obs): the mission's own win / lose."""
        return self.result()

    # ---- what the player sees
    def _id(self, b):
        if b.serial not in self.ids:
            # never one given before (names keeps every id); the object held weakly and its serial's row dropped
            # when it is reclaimed: seeing an object kept it, and its World.late row, alive (review 11-19 m)
            i = self.ids[b.serial] = len(self.names) + 1    # names only grows, ids 1, 2, ... in a row (o #3)
            self.names[i], self.things[i] = b.name, b
            weakref.finalize(b, self.ids.pop, b.serial, None)
        return self.ids[b.serial]

    def _data(self, template):
        """(cost, good_against, rates) of a template: the SDK's data, or the name's guess for a part of ours."""
        if template not in self._offer:
            if self.match.known(template):
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
                            frozenset(p for p, f in b.ready_at.items() if f > self.world.frame_now()))

    def _thing(self, b):
        cost, _, _ = self._data(b.template)
        goal = b.goal if isinstance(b.goal, sim.Body) else None
        return pworld.Thing(self._id(b), '' if b.owner == simworld.CIV else b.owner, b.template,
                                       frozenset(b.kinds), frozenset(b.status), b.x, b.y,
                                       water=b.surface == 'water', value=float(cost), hits=simrange.hits(b.weapons),
                                       attacking_us=bool(goal and not self.world.enemy(self.me, goal.owner)))

    def enemies(self):
        return frozenset(p for p in self.world.players.values() if p != self.me and self.world.enemy(self.me, p))

    def _convoy(self):
        return [b for b in (self.world.bodies.get(n) for n in self.escort) if b is not None and b.alive]

    def where_home(self):
        convoy = self._convoy()
        if not convoy:
            return self.home
        return (sum(b.x for b in convoy) / len(convoy), sum(b.y for b in convoy) / len(convoy))

    def observe(self):
        world, peers = self.world, self.peers
        peers.forget_sight()                    # this moment's sight (Sim.fight clears it each tick too)
        mine = [self._mine(b) for b in world.living() if b.owner == self.me and self._is_unit(b)]
        seen = [self._thing(b) for b in world.living() if not b.scenery and b.owner != self.me
                and (b.owner == simworld.CIV or world.enemy(self.me, b.owner)) and peers.side_sees(self.me, b)]
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
        world, peers = self.world, self.peers
        for t, kind, text in peers.log[self._log_read:]:
            if kind == '小地图闪点':
                b = world.bodies.get(text)
                if b is not None:
                    self._blips.append((int(round(t * FPS)), float(b.x), float(b.y)))
        self._log_read = len(peers.log)
        keep = self.frame - int(BLIP_KEEP * FPS)
        self._blips = [b for b in self._blips if b[0] >= keep]
        return list(self._blips)

    def money(self):
        """What the player can still spend: the bank less what the queued builds will still take (Sim.order_build pays
        frame by frame, so the bank alone would let the player queue far more than it can pay for)."""
        return int(self.peers.money.get(self.me, 0)) - int(self.peers.production.owed(self.me))

    def offers(self):
        """The lit sidebar buttons (Sim.offers: the player's live factories, prerequisites held, not banned) as the
        proxy's Offers: KindOf / good_against / rates from the data (Matchup.offer), cost and time from the simulator."""
        out = []
        for template, cost, secs in self.peers.offers(self.me):
            _, good, rates = self._data(template)
            out.append(self.pw.Offer(template, self.match.kinds(template), int(cost),
                                     good, float(secs), rates=rates))
        return out

    def chokes(self):
        """The level's chokes (CHOKES) as the player sees them now: the countdown's end if it is on screen, whether
        an ice wall (a body with a lifetime of its own, not a unit) stands in the mouth."""
        spec = CHOKES.get(self.level)
        if not spec:
            return []
        world, peers = self.world, self.peers
        name = spec['countdown']
        at = int(round(peers.timers[name] * FPS)) if name in peers.countdowns and name in peers.timers else None
        part, ability = spec['power']
        power = world.m.ability(part, ability) if part in world.m.cast else None
        by = frozenset({world.m.cast[part].template}) if part in world.m.cast else frozenset()
        walls = [(b.x, b.y) for b in world.living() if b.life_end is not None and b.speed == 0 and not b.scenery]
        seed = simunits.module_blocks(spec['seed'], 'LifetimeUpdate', world.own)[:1] if spec.get('seed') else ()
        life = lifetime_module.LifetimeData.parse(*seed[0]).frames if seed else None
        build = life / FPS if life else 0.0
        out = []
        for way, block, source in spec['ways']:
            p, q = world.point(block), world.point(source)
            if not p or not q:
                continue
            blocked = any(math.hypot(x - p[0], y - p[1]) <= BLOCKED_R for x, y in walls)
            out.append(self.pw.Choke(way, tuple(p), tuple(q), at, power or '', by, blocked, build))
        return out

    def junctions(self):
        """{way: (x, y)}: where each of the level's ways meets the convoy's road (CHOKES 'road'), the spot a guard
        stands to meet the wave that comes out of it -- not the ice's mouth (up the street) nor the convoy."""
        spec = CHOKES.get(self.level) or {}
        road = self.world.point(spec.get('road', ''))
        out = {}
        for way, block, _source in spec.get('ways', ()):
            p = self.world.point(block)
            if road and p:
                out[way] = (float(p[0]), float(road[1]))
        return out

    # ---- what the player does
    def _body(self, i):
        b = self.things.get(i)              # the object the id was given to, still in the world's table and alive
        return b if b is not None and b.alive and self.world.bodies.get(b.name) is b else None

    def _refuse(self, o, why):
        self.refused.append((self.frame, o, why))
        return False

    def control(self):
        """The player has control: no scene holds the input (Sim.input, ENABLE_INPUT) and the first tick has run.
        Before it the level's scripts have not yet said whether a scene opens the mission (A4 locks the input in its
        first tick): orders the proxy gave at frame 0 sent a unit into lane foot and set the convoy off ~85 s early
        (round 40, 2026-11-07)."""
        return self.peers.input and self.world.t > 0

    def _do(self, kind, units=(), **kw):
        """The player's order through the command port (R3 13e): (ok, why). `units` are the bodies of his the click
        picked (alive, his), given by serial (`('objects', 'serial')`): by name the port's lookup would read a script
        reference of the same name -- an enemy's unit took the move, review 11-19 h #1, as f #1."""
        args = kw.pop('args', ())
        if units:
            args = (('objects', 'serial'),) + args
        return self.peers.commands.do(Command(kind, 'proxy', units=tuple(b.serial for b in units), args=args, **kw))

    def issue(self, o):
        world = self.world
        if not self.control():
            return self._refuse(o, 'cinematic: no control')
        if o.kind == 'build':                   # the sidebar: the shortest queue of his that builds it
            if self._do('build', player=self.me, template=o.template)[0]:
                return True
            return self._refuse(o, 'no factory of mine builds it now')
        units = [self._body(i) for i in o.units]
        units = [b for b in units if b is not None and b.owner == self.me]
        if not units:
            return self._refuse(o, 'no living unit of mine')
        if o.kind in ('move', 'attack_move'):
            if o.pos is None:
                return self._refuse(o, 'move without a place')
            self._do(o.kind, units, pos=(float(o.pos[0]), float(o.pos[1])),     # a selection: a group, the click
                     args=(('group', True), ('on_grid', True), ('drop_target', True)))   # drops their target
            return True
        if o.kind == 'attack':
            t = self._body(o.target)
            if t is None:
                return self._refuse(o, 'target gone')
            ok, why = self._do('attack', units, target=t.name, args=(('target_serial', t.serial),))   # as clicked
            return True if ok else self._refuse(o, 'attack refused: ' + why)   # (j #1); the port's say (o #1)
        if o.kind == 'power':
            if o.power == 'SpecialPower_JAIV_Transform':
                if o.target is not None or o.pos is not None:
                    return self._refuse(o, 'transform is an untargeted power')
                ok, why = self._do('power', units, power=o.power, args=(('via', 'transform'),))
                return True if ok else self._refuse(o, 'power refused: ' + why)
            if o.pos is not None:               # a ground power: the player's click (Sim.order_power: reload, ground,
                ok, why = self._do('power', units, power=o.power,    # ForbiddenObjectRange, reach), then the
                                   pos=(float(o.pos[0]), float(o.pos[1])), args=(('via', 'click'),))   # scripts' way
                if not ok:
                    return self._refuse(o, 'power refused: ' + why)
            else:
                for b in units:
                    world.note('技能', f'{world.label(b)} 用 {o.power}' + (f' 打 #{o.target}' if o.target else ''))
            return True
        return self._refuse(o, f'unknown order {o.kind}')

    # ---- the score screen
    def losses(self):
        world = self.world
        out = []
        for b in world.bodies.values():
            if b.alive or b.deleted or b.scenery or b.died_at is None or b.life_end is not None:
                continue
            cost, _, _ = self._data(b.template)
            kind = self.pw.kind_of(pworld.Thing(0, b.owner, b.template, frozenset(b.kinds),
                                                           water=b.surface == 'water'))
            out.append(self.pw.Loss(int(round(b.died_at * FPS)), '' if b.owner == simworld.CIV else b.owner,
                                    b.template, kind, int(cost)))
        return sorted(out, key=lambda l: (l.frame, l.owner, l.template))


def goals(w):
    """The level's puzzle checks (report Goals): where the ice went (report.power_at), its own targets destroyed.
    w: the SimWorld (its Sim read through the world API)."""
    rp = w.p['report']
    world = w.world
    out = []
    for name, sites, radius, note in ICE_GOALS.get(w.level, ()):
        pts = [tuple(q) for q in (world.point(n) for n in sites) if q]
        out.append(rp.power_at(pts, radius, name=name, note=note))
    for name, part, note in TARGET_GOALS.get(w.level, ()):
        b = world.bodies.get(world.m.cast[part].name) if part in world.m.cast else None
        if b is not None:
            out.append(rp.destroyed(b.template, name=name, note=note))
    return out


def play(level='a4', style=None, until=UNTIL, every=15, check='', script='', difficulty=DIFFICULTY, label='',
         show=False):
    """One playtest: (report dict, the SimWorld). The proxy plays until the mission ends or `until` seconds.
    show=True also reads what the player saw off the run (simshow.problems) into rep['world']['show']."""
    w = SimWorld(level, check, script, difficulty, show=show)
    p = w.p
    player = p['player'].ProxyPlayer(style)
    tr = p['report'].run(w, player, int(until * FPS), every, end=w.end, label=label or level)
    rep = p['report'].report(tr, goals(w))
    rep['world'] = {'simulator_ending': w.sim.ending_line(), 'refused': len(w.refused),
                    'guessed': sorted(w.sim.guessed)[:20]}
    if show:
        import simshow
        rep['world']['show'] = simshow.problems(w.show)
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
    rep, w = play(a.level, until=a.until, difficulty=a.difficulty, label=f'{a.level} 默认', show=a.compare)
    reps = [rep]
    print(w.p['report'].summary(rep))
    print(rep['world']['simulator_ending'])
    if a.compare:
        plain, _ = play(a.level, style=w.p['player'].Style(block=0), until=a.until, difficulty=a.difficulty,
                        label=f'{a.level} 不用关卡技能', show=True)
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
