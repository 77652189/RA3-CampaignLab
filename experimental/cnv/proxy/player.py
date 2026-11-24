"""The proxy player (after layer 4): a stand-in for the user at the mouse, first job an automated playtester.

It plays the way the user said he plays campaigns (CampaignLab memory user-playstyle-counters, docs/plan.md
engine-logic row, 2026-11-07 option A): find out what the enemy fields and build what counters it; pull the
wounded back; take out the sources of pressure (the factories / spawners the waves come from) before anything
else; defend only what reaches the base. Every knob is on Style, so a playtest can also ask "what does the most
natural play do here" with other knobs.

One decision every `every` frames (player.play): observe -> remember -> pull back / rejoin -> build -> pick a target
-> attack or scout -> unit powers. All of it goes through proxy/world.py's seam (Observation in, Order out).
Enemies are world.Thing; world.threat is the value of hostile guns around a target (is the army big enough to
go). Unit powers are not used (the retail micro manager's rounds were the private model's; ADR 0033 3).
Everything here is INFERRED from the user's description, not read from any program: there is no retail code for
a human player. log is [(frame, what, detail)] for the playtest report (proxy/report.py); `what` is one of
scout, scout found, gone, build, wait, go (the army commits to a new target: one sortie), attack (orders given),
regroup (a sortie called off: one retreat), defend (enemies near home answered: once per spell of defending),
pull back, rejoin, power, block (the level's blocking power sent at a choke: _blocks), post (the army sent to wait
for a coming threat: _post), guard (units sent to wait for a wave flashed in the fog: _guard_ghosts).
"""
import dataclasses
import math

from proxy import world as pw

FPS = 15                            # logic frames a second (Observation.frame, Choke.at)
SOURCE_KINDS = frozenset({'FS_FACTORY', 'FS_BARRACKS', 'FS_WARFACTORY', 'FS_AIRFIELD', 'FS_NAVALYARD', 'SPAWNER'})


@dataclasses.dataclass
class Style:
    pullback: float = 0.35          # INFERRED (user: "残血后撤"); retail StandardMicroManager PullbackInjuredHealthPct 0.2
    rejoin: float = 0.9             # back into the army when healed this far
    attack_ratio: float = 1.2       # go when army value x health >= this x threat around the target ...
    min_army: int = 3               # ... and at least this many are ready (a human groups up first)
    regroup_ratio: float = 0.6      # once going, come home only when the army falls below this x threat
    defend_radius: float = 600.0    # enemies this close to home are answered first, whatever the plan
    source_kinds: frozenset = SOURCE_KINDS
    lead_reach: float = 150.0       # a lead counts as looked at once a unit is this close
    reserve: int = 0                # money never spent
    # the level's blocking power (Observation.chokes: an ice wall in a street's mouth before the horn), all INFERRED
    # from the levels' own design ("看着号角倒计时，决定这一波用几道墙、留哪条街开着"), not from a recorded human
    block: int = 2                  # most chokes blocked against one coming threat; 0 = never use the power
    block_reach: float = 1500.0     # only a threat whose source is this close to home is worth a block
    block_build: float = 8.0        # seconds the power takes once the unit stands there
    block_margin: float = 4.0       # seconds the block should stand before the threat comes
    # INFERRED (a human clicks a ground power on a bare spot: the cursor turns red over a unit -- the world's
    # ForbiddenObjectRange, simulator Sim.power_refusal): keep this far from every unit in sight but the caster, at the
    # choke or the nearest such spot on rings of block_nudge, x 2, x 3 round it
    power_clearance: float = 40.0
    block_nudge: float = 40.0
    walk_speed: float = 30.0        # a unit's speed when the world gives none (map units a second)
    blocker_leash: float = 250.0    # an idle blocker stays this close to home (it walks with an escorted convoy)
    # an escort level (Observation.escort): what the level asks to keep alive comes before the sources (INFERRED from
    # the levels' design -- a convoy left alone dies to the first wave -- not from a recorded human)
    escort_reach: float = 900.0     # on an escort, the army goes only after what is this close to home
    wounded_guard: float = 250.0    # pulled-back units this close to home join a defence there; 0 = they never do
    defend_move: bool = True        # defend by attack-moving at the nearest threat (each unit fights what is in its
                                    # range, as a human A-moves home); False = every unit focuses that one enemy
    # answer a defence by kind (INFERRED: the user's "按敌人兵种换兵" carried over to who goes back): each unit goes
    # only after the enemies at home it is made for (Mine.good_against); the rest keep to home (within guard_leash)
    # and fight what reaches them there. When no unit counters any of them, everyone answers as before.
    counter_defend: bool = False
    guard_leash: float = 200.0
    # four general rules (11-07, level line's A4 review docs/story/sim-vs-bench-a4.md last section; all INFERRED from
    # how a human plays, none written for one level):
    # - Observation.cinematic: no orders while a scene plays (always; a human has no control then)
    # - focus the defence: each unit attacks, one by one, the most dangerous enemy at home it can hurt (the one made to
    #   kill most of what the player has, Observation.counters) instead of attack-moving
    defend_focus: bool = True
    # - split the defence (11-07, B r31): two bands at home at once (the A4 horn sends two streets together) each get a
    #   share of the army by danger, nearest band first; enemies up to split_margin beyond defend_radius count as at
    #   home for the split (the other band is on its way). Only with defend_focus.
    split_defend: bool = True
    split_link: float = 250.0       # enemies this close to one another are one band
    split_margin: float = 300.0
    split_stay: float = 1.5         # a band keeps the units already on it up to this x its share (no flip-flopping)
    # - stand ready: while a countdown runs, the army waits where the next threat's open way (one the player will not
    #   block) meets home, instead of hugging home
    preposition: bool = True
    post_reach: float = 500.0       # the post is on the line from home to that way's mouth, at most this far from home
    post_ahead: float = 60.0        # seconds before the threat the army starts out to the post
    post_hold: float = 25.0         # seconds after the threat the army still holds the post (the wave is on its way)
    # - no healing on the level (Observation.healing False): never pull back (a pulled-back unit never comes back)
    pullback_needs_healing: bool = True
    # - guard what flashes in the fog (11-07, B r36; A4: the horn's wave out of an unseen street reached the convoy
    #   while the whole army fought the seen one): a minimap flash (Observation.blips) within block_reach of home with
    #   no seen enemy near it is a wave on its way; it gets a share of the army (one band of as many as there are
    #   flashes plus the seen enemies), who wait on the line from home to it (guard_reach out) and fight its band once
    #   seen, until it reaches home (then the split defence has it). Only where the split defence works (defend_focus,
    #   split_defend, not counter_defend): with another defence it only thins the army (A4 old style 3:12 -> 2:32)
    ghost_guard: bool = True
    blip_hold: float = 25.0         # seconds a flash is still a wave on its way
    ghost_seen: float = 400.0       # a seen enemy this close to a flash, its guard post or its guards is of its wave
    guard_reach: float = 100.0     # a guard waits on the line from home to the flash, at most this far from home
    guard_angle: float = 45.0       # a flash within this angle (seen from home) of a fight at home is that fight's


def _d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _at(t):
    return (t.x, t.y)


class ProxyPlayer:
    def __init__(self, style=None):
        self.style = style or Style()
        self.known = {}             # Thing id -> (Thing as last seen, frame)
        self.visited = set()        # indexes into obs.leads
        self.scout = None           # Mine id
        self.wounded = set()
        self.orders = {}            # Mine id -> what it was last told ('attack', id) / ('move', pos)
        self.target = None          # (why, Thing id)
        self.going = None           # the target id the army was sent at and is still committed to
        self.log = []
        self._before = None         # the last decision's target (a new 'defend' is logged once)
        self.blocking = {}          # Choke name -> (Mine id sent, the threat's frame): a block under way
        self.at_home = []           # the enemies at home the last _pick_target saw (counter_defend picks among them)
        self.post = None            # (None, choke name, last frame to hold it): the army's post before a threat
        self.sides = {}             # Mine id -> enemy ids of the band it was given last (Style.split_defend)
        self.guards = {}            # Mine id -> the place (x, y) of the flash it guards against (Style.ghost_guard)
        self.explained = set()      # flashes (frame, x, y) a seen enemy has accounted for

    # --- what the player knows ---------------------------------------------------------------------------------
    def remember(self, obs):
        seen = {t.id for t in obs.seen}
        for t in obs.seen:
            if t.owner in obs.enemies:
                self.known[t.id] = (t, obs.frame)
        for tid, (t, _) in list(self.known.items()):
            if tid not in seen and any(_d((u.x, u.y), _at(t)) < u.sight for u in obs.mine):
                del self.known[tid]
                self.log.append((obs.frame, 'gone', f'{t.template}#{tid}'))

    def enemy_value(self):
        """Counter kind -> value of the known enemy units of that kind (structures left out: they are targets,
        not something to out-build)."""
        out = {}
        for t, _ in self.known.values():
            k = pw.kind_of(t)
            if k != 'structure':
                out[k] = out.get(k, 0.0) + (t.value or 1.0)
        return out

    # --- the decision ------------------------------------------------------------------------------------------
    def decide(self, obs):
        self.remember(obs)
        if obs.cinematic:                       # a scene: a human cannot give orders
            if not self.log or self.log[-1][1:] != ('wait', 'cinematic'):
                self.log.append((obs.frame, 'wait', 'cinematic'))
            return []
        out = []
        out += self._wounded(obs)
        out += self._build(obs)
        out += self._blocks(obs)
        blockers = self._blockers(obs)
        army = [u for u in obs.mine if u.id not in self.wounded and u.good_against and u.id != self.scout
                and u.id not in blockers]
        guard_out, guards = self._guard_ghosts(obs, army)
        out += guard_out
        army = [u for u in army if u.id not in guards]
        self._before = self.target
        self.target = self._pick_target(obs)
        if self.target is None:
            out += self._scouting(obs)
            post = self._post(obs)
            if post is not None:                # a threat is coming: wait for it where its open way meets home
                self.going = None
                out += self._stand(obs, [u for u in army if u.id != self.scout], post)
            elif obs.escort:                    # nothing to go after near the convoy: walk with it
                self.going = None
                out += self._gather(obs, [u for u in army if u.id != self.scout], 'escort')
        else:
            if self.scout is not None:          # the scout found something: it joins the army
                why, tid = self.target
                self.log.append((obs.frame, 'scout found', f'{why} {self.known[tid][0].template}#{tid}'))
                self.scout = None
            fighters = army
            if self.target[0] == 'defend':     # the enemy is at home: the wounded there fight too
                fighters = army + self._home_guard(obs)
            out += self._attack(obs, fighters)
        return out

    def _tell(self, u, order, what):
        if self.orders.get(u.id) == what and u.busy:
            return []
        self.orders[u.id] = what
        return [order]

    def _home_guard(self, obs):
        """The wounded already at home (pulled back): when enemies reach home they fight there -- there is nowhere
        safer to go (and on a level without healing they never rejoin). INFERRED, Style.wounded_guard."""
        r = self.style.wounded_guard
        if r <= 0:
            return []
        return [u for u in obs.mine if u.id in self.wounded and _d((u.x, u.y), obs.home) <= r]

    def _wounded(self, obs):
        out = []
        if not obs.healing and self.style.pullback_needs_healing:   # nowhere to heal: nobody pulls back
            for uid in sorted(self.wounded):
                self.log.append((obs.frame, 'rejoin', f'#{uid} (no healing)'))
            self.wounded.clear()
            return out
        defending = self.target is not None and self.target[0] == 'defend'   # the last decision's
        guard = {u.id for u in self._home_guard(obs)} if defending else set()
        for u in obs.mine:
            if u.id not in self.wounded and u.fraction < self.style.pullback:
                self.wounded.add(u.id)
                self.log.append((obs.frame, 'pull back', f'{u.template}#{u.id} {u.fraction:.2f}'))
            elif u.id in self.wounded and u.fraction >= self.style.rejoin:
                self.wounded.discard(u.id)
                self.log.append((obs.frame, 'rejoin', f'{u.template}#{u.id}'))
            if u.id in self.wounded and u.id not in guard and _d((u.x, u.y), obs.home) > 50:
                out += self._tell(u, pw.Order('move', (u.id,), pos=obs.home), ('move', obs.home))
        self.wounded &= {u.id for u in obs.mine}
        return out

    def _build(self, obs):
        """One counter unit per decision while the money lasts: the enemy kind whose known value is least answered
        by own units made for it, then the offer made for that kind that destroys the most of it per second per
        money spent (Offer.rates / cost, proxy/matchup.py); without rates, or on a tie, the cheapest."""
        need = self.enemy_value()
        if not need or not obs.offers:
            return []
        have = {}
        for u in obs.mine:
            for k in u.good_against:
                have[k] = have.get(k, 0.0) + u.cost * u.fraction
        for kind in sorted(need, key=lambda k: (have.get(k, 0.0) - need[k], k)):
            fits = [o for o in obs.offers if kind in o.good_against]
            if not fits:
                continue
            o = min(fits, key=lambda o: (-(o.rates.get(kind, 0.0) / o.cost if o.cost else 0.0), o.cost, o.template))
            if obs.money - self.style.reserve < o.cost:
                return []                       # save up for the counter, do not buy something else meanwhile
            self.log.append((obs.frame, 'build', f'{o.template} vs {kind}'))
            return [pw.Order('build', template=o.template)]
        return []

    def refused(self, obs, order):
        """The world would not take `order` (play / report.run tell the player). An attack on something no longer
        there: the player clicked a ghost, so it forgets it (a human sees the order fail and looks elsewhere)."""
        if order.kind == 'attack' and order.target in self.known:
            t = self.known.pop(order.target)[0]
            self.log.append((obs.frame, 'gone', f'{t.template}#{order.target}'))
        if order.kind == 'attack':
            for u in order.units:
                self.orders.pop(u, None)
        if order.kind == 'power' and order.pos is not None:
            # a refused block (reloading, a unit on the spot): the player sees the click fail and tries again at the
            # next think while there is time (the choke is free again for _blocks)
            for name, (uid, _) in list(self.blocking.items()):
                if uid in order.units:
                    del self.blocking[name]
                    self.log.append((obs.frame, 'block', f'{name} by #{uid} refused, again'))
            for u in order.units:
                self.orders.pop(u, None)

    def _pick_target(self, obs):
        st = self.style
        # UNATTACKABLE (status) and INERT (KindOf: props, smoke) cannot be aimed at in retail -- never a target; at home
        # only what can hurt is answered
        foes = [t for t, _ in self.known.values() if 'UNATTACKABLE' not in t.status and 'INERT' not in t.kindof]
        near_home = [t for t in foes if pw.kind_of(t) != 'structure' and _d(_at(t), obs.home) < st.defend_radius
                     and (t.hits or t.attacking_us or t.kindof & st.source_kinds)]
        self.at_home = near_home
        if near_home:
            return ('defend', min(near_home, key=lambda t: (_d(_at(t), obs.home), t.id)).id)
        if obs.escort:                          # keep to what the level asks to keep alive
            foes = [t for t in foes if _d(_at(t), obs.home) <= st.escort_reach]
        for why, pool in (('source', [t for t in foes if t.kindof & st.source_kinds]),
                          ('structure', [t for t in foes if pw.kind_of(t) == 'structure']),
                          ('unit', foes)):
            if pool:
                return (why, min(pool, key=lambda t: (_d(_at(t), obs.home), t.id)).id)
        return None

    def _attack(self, obs, army):
        why, tid = self.target
        t = self.known[tid][0]
        if why != 'defend':
            threat = pw.threat([k for k, _ in self.known.values()], obs.enemies, t)
            strength = sum(u.cost * u.fraction for u in army)
            if self.going == tid:
                ok = strength > 0 and strength >= self.style.regroup_ratio * threat
            else:
                ok = strength >= self.style.attack_ratio * threat and len(army) >= self.style.min_army
            if not ok:
                if self.going is not None:
                    self.log.append((obs.frame, 'regroup', f'{strength:.0f} vs {threat:.0f}'))
                self.going = None
                return self._gather(obs, army, f'{len(army)} units, {strength:.0f} vs {threat:.0f}')
        if why != 'defend' and self.going != tid:
            self.log.append((obs.frame, 'go', f'{why} {t.template}#{tid} with {len(army)}'))
        elif why == 'defend' and (self._before is None or self._before[0] != 'defend'):   # one per spell at home
            self.log.append((obs.frame, 'defend', f'{t.template}#{tid} with {len(army)}'))
        self.going = tid if why != 'defend' else self.going
        if why == 'defend' and self.style.counter_defend:
            out = self._counter_defend(obs, army)
            if out is not None:
                if out:
                    self.log.append((obs.frame, 'attack', f'defend by kind with {len(out)}'))
                return out
        if why == 'defend' and self.style.defend_focus:
            out = self._focus_defend(obs, army)
            if out is not None:
                if out:
                    self.log.append((obs.frame, 'attack', f'defend focus with {len(out)}'))
                return out
        out = []
        for u in army:
            if why == 'defend' and self.style.defend_move:
                out += self._tell(u, pw.Order('attack_move', (u.id,), pos=_at(t)), ('attack_move', tid))
            else:
                out += self._tell(u, pw.Order('attack', (u.id,), target=tid), ('attack', tid))
        if out:
            self.log.append((obs.frame, 'attack', f'{why} {t.template}#{tid} with {len(out)}'))
        return out

    def _counter_defend(self, obs, army):
        """Style.counter_defend: each unit after the nearest enemy at home of a kind it is made for; the others keep
        to home. None when nobody counters anything there (the caller then sends everyone)."""
        pick = {}
        for u in army:
            fit = [t for t in self.at_home if pw.kind_of(t) in u.good_against]
            if fit:
                pick[u.id] = min(fit, key=lambda t: (_d((u.x, u.y), _at(t)), t.id))
        if not pick:
            return None
        out = []
        for u in army:
            t = pick.get(u.id)
            if t is not None:
                if self.style.defend_move:
                    out += self._tell(u, pw.Order('attack_move', (u.id,), pos=_at(t)), ('attack_move', t.id))
                else:
                    out += self._tell(u, pw.Order('attack', (u.id,), target=t.id), ('attack', t.id))
            elif (_d((u.x, u.y), obs.home) > self.style.guard_leash
                  and not (u.busy == 'attack' and _d((u.x, u.y), obs.home) <= self.style.defend_radius)):
                out += self._tell(u, pw.Order('move', (u.id,), pos=obs.home), ('move', obs.home))
        return out

    def _counters(self, obs, t):
        c = obs.counters.get(t.template)
        return c if c is not None else pw.roles_from_name(t.template)

    def danger(self, obs, t, army):
        """How much an enemy threatens the player: its value, more for each own unit (and, on an escort, the convoy:
        counted as vehicles) of a kind it is made to kill. INFERRED (a human shoots the tank killers first)."""
        made = self._counters(obs, t)
        mine = [pw.kind_of(u) for u in army] + (['vehicle'] if obs.escort else [])
        hit = sum(1 for k in mine if k in made)
        return (t.value or 1.0) * (1.0 + hit / max(1, len(mine)))

    def _focus_defend(self, obs, army):
        """Style.defend_focus: each unit attacks the enemy at home with the highest danger x how well it hurts that
        kind (Mine.rates; any when unknown), nearest to it on a tie. None when nobody can hurt anything there."""
        now = {t.id for t in obs.seen}          # one by one at what is in sight (not a remembered ghost)
        pool = [t for t in self.at_home if t.id in self.known and t.id in now]
        if not pool:
            return None
        st = self.style
        if st.split_defend:                     # the next band out counts too: a second wave is about to be at home
            have = {t.id for t in pool}
            reach = st.defend_radius + st.split_margin
            pool += [t for t in self._threats(obs) if t.id not in have and t.id in now and _d(_at(t), obs.home) < reach]
        dz = {t.id: self.danger(obs, t, army) for t in pool}

        def eff(u, t):
            if not u.rates:
                return 1.0
            top = max(u.rates.values(), default=0.0)
            return u.rates.get(pw.kind_of(t), 0.0) / top if top > 0 else 0.0
        fit = {u.id: [t for t in pool if eff(u, t) > 0] for u in army}
        if not any(fit.values()):
            return None
        side = self._split(obs, army, pool, dz, eff) if st.split_defend else {}
        out = []
        for u in army:
            cand = [t for t in fit[u.id] if t.id in side[u.id]] if u.id in side else fit[u.id]
            if not cand:
                continue
            t = max(cand, key=lambda t: (dz[t.id] * eff(u, t), -_d((u.x, u.y), _at(t)), -t.id))
            out += self._tell(u, pw.Order('attack', (u.id,), target=t.id), ('attack', t.id))
        return out

    def _threats(self, obs):
        """Known enemies that can hurt (the filter _pick_target answers at home with), wherever they are."""
        st = self.style
        return [t for t, _ in self.known.values() if 'UNATTACKABLE' not in t.status and 'INERT' not in t.kindof
                and pw.kind_of(t) != 'structure' and (t.hits or t.attacking_us or t.kindof & st.source_kinds)]

    def _split(self, obs, army, pool, dz, eff):
        """Style.split_defend: the enemies at home in bands (Style.split_link apart at most, single link); each band gets
        a share of the army in proportion to its danger, nearest band to home first; within a band's share the units
        already fighting it stay, then the ones that hurt it best, nearest first. Mine id -> the ids of its band. One
        band: {} (everyone picks from all). INFERRED (a human splits the army when two waves come at once)."""
        groups = []
        for t in sorted(pool, key=lambda t: (_d(_at(t), obs.home), t.id)):
            near = [g for g in groups if any(_d(_at(t), _at(o)) <= self.style.split_link for o in g)]
            merged = [t] + [o for g in near for o in g]
            groups = [g for g in groups if g not in near] + [merged]
        if len(groups) < 2:
            self.sides = {}
            return {}
        groups.sort(key=lambda g: (min(_d(_at(t), obs.home) for t in g), min(t.id for t in g)))
        total = sum(dz[t.id] for t in pool) or 1.0
        worth = {u.id: u.cost * u.fraction for u in army}
        strength = sum(worth.values())
        left = [u for u in army if any(eff(u, t) > 0 for t in pool)]
        side = {}
        for i, g in enumerate(groups):
            ids = {t.id for t in g}
            mid = (sum(t.x for t in g) / len(g), sum(t.y for t in g) / len(g))
            hurt = [u for u in left if any(eff(u, t) > 0 for t in g)]
            if i == len(groups) - 1:
                take = hurt
            else:
                quota = strength * sum(dz[t.id] for t in g) / total
                on = [u for u in hurt if self.sides.get(u.id, set()) & ids]   # its band last time is (in) this one
                rest = sorted((u for u in hurt if u not in on),
                              key=lambda u: (-max(eff(u, t) for t in g), _d((u.x, u.y), mid), u.id))
                on.sort(key=lambda u: (-max(eff(u, t) for t in g), _d((u.x, u.y), mid), u.id))
                take, got = [], 0.0
                for u in on + rest:             # the ones already there leave only past split_stay x the share
                    if take and got >= quota * (self.style.split_stay if u in on else 1.0):
                        break
                    take.append(u)
                    got += worth[u.id]
            for u in take:
                side[u.id] = ids
            left = [u for u in left if u.id not in side]
        self.sides = dict(side)
        return side

    # --- guarding against what flashes in the fog -----------------------------------------------------------------
    def _toward(self, obs, p):
        """The point on the line from home to p, at most Style.guard_reach from home (where a guard waits for p)."""
        d = _d(p, obs.home)
        k = min(1.0, self.style.guard_reach / d) if d else 0.0
        return (obs.home[0] + (p[0] - obs.home[0]) * k, obs.home[1] + (p[1] - obs.home[1]) * k)

    def _ghosts(self, obs):
        """Style.ghost_guard: the waves the player expects at the minimap flashes (Observation.blips) of the last
        blip_hold seconds within block_reach of home, one per place (split_link apart; newest flash kept).
        [(place, the seen threats of that wave)]: those in sight within ghost_seen of the place, of its guard post or
        of a unit guarding it. A place stays a wave after its flash is old while such threats are left (the band its
        guards fight)."""
        st = self.style
        if not (st.ghost_guard and st.defend_focus and st.split_defend and not st.counter_defend):  # the split's part
            return []
        now = {t.id for t in obs.seen}
        seen = [t for t in self._threats(obs) if t.id in now]
        mine = {u.id: (u.x, u.y) for u in obs.mine}

        def fresh(p):
            return any(_d(p, (b[1], b[2])) <= st.split_link and obs.frame - b[0] <= st.blip_hold * FPS
                       for b in obs.blips)
        # a flash at a way the player has shut (its block stands, or is on its way: _blocks) sends nothing there: the
        # wave goes another way
        shut = [q for c in obs.chokes if c.blocked or c.name in self.blocking for q in (c.pos, c.source)]
        places = [(b[1], b[2]) for b in sorted(obs.blips, key=lambda b: (-b[0], b[1], b[2]))
                  if obs.frame - b[0] <= st.blip_hold * FPS and _d((b[1], b[2]), obs.home) <= st.block_reach
                  and not any(_d((b[1], b[2]), q) <= st.ghost_seen for q in shut)
                  # a flash where the player's units see is no guess: the wave there is fought as it is seen
                  and not any(_d((b[1], b[2]), (u.x, u.y)) <= u.sight for u in obs.mine)]
        places += sorted(set(self.guards.values()))     # a band its guards still fight
        out, taken = [], set()
        for p in places:
            if any(_d(p, q) <= st.split_link for q, _ in out):
                continue
            post = self._toward(obs, p)
            near = [mine[uid] for uid, g in self.guards.items() if uid in mine and _d(g, p) <= st.split_link]
            band = [t for t in seen if t.id not in taken and
                    min([_d(_at(t), p), _d(_at(t), post)] + [_d(_at(t), q) for q in near]) <= st.ghost_seen]
            if not band and not fresh(p):
                continue                                # an old flash with nothing left of its wave
            if any(_d(_at(t), obs.home) < st.defend_radius + st.split_margin for t in band):
                continue                                # at home: the defence (and its split) answers it
            taken |= {t.id for t in band}
            out.append((p, band))
        return out

    def _guard_ghosts(self, obs, army):
        """A share of the army for each expected wave (_ghosts): as many bands as waves, one more when other enemies
        are in sight within block_reach; each wave, nearest home first, takes its share by worth (the units already
        on it first, up to split_stay x the share, then the nearest to its post); with no other enemy in sight the
        last wave takes the rest. Guards attack-move to their post (_toward) until the wave is in sight, then each
        attacks the nearest of it. (orders, guard ids)."""
        st = self.style
        now = {t.id for t in obs.seen}
        home = st.defend_radius + st.split_margin
        fight = [_at(t) for t in self._threats(obs) if t.id in now and _d(_at(t), obs.home) < home]

        def apart(p):                           # a flash behind a fight at home is that fight's (nobody leaves it)
            a = math.atan2(p[1] - obs.home[1], p[0] - obs.home[0])
            return all(abs((math.atan2(q[1] - obs.home[1], q[0] - obs.home[0]) - a + math.pi) % (2 * math.pi)
                           - math.pi) > math.radians(st.guard_angle) for q in fight)
        ghosts = [g for g in self._ghosts(obs) if apart(g[0])] if army else []
        if not ghosts:
            self.guards = {}
            return [], set()
        now = {t.id for t in obs.seen}
        banded = {t.id for _, band in ghosts for t in band}
        other = any(t.id in now and t.id not in banded and _d(_at(t), obs.home) <= st.block_reach
                    for t in self._threats(obs))
        worth = {u.id: u.cost * u.fraction for u in army}
        quota = sum(worth.values()) / (len(ghosts) + (1 if other else 0))
        ghosts.sort(key=lambda g: (_d(g[0], obs.home), g[0]))
        seen_band = other
        left, out, guards = list(army), [], {}
        for i, (p, band) in enumerate(ghosts):
            post = self._toward(obs, p)
            on = sorted((u for u in left if u.id in self.guards and _d(self.guards[u.id], p) <= st.split_link),
                        key=lambda u: (_d((u.x, u.y), post), u.id))
            rest = sorted((u for u in left if u not in on), key=lambda u: (_d((u.x, u.y), post), u.id))
            if i == len(ghosts) - 1 and not seen_band:
                take = on + rest
            else:
                take, got = [], 0.0
                for u in on + rest:
                    if take and got >= quota * (st.split_stay if u in on else 1.0):
                        break
                    take.append(u)
                    got += worth[u.id]
            fresh = [u for u in take if u.id not in self.guards]
            for u in take:
                guards[u.id] = p
                if band:                                # the wave is in sight: the nearest of it
                    t = min(band, key=lambda t: (_d((u.x, u.y), _at(t)), t.id))
                    out += self._tell(u, pw.Order('attack', (u.id,), target=t.id), ('attack', t.id))
                    continue
                if _d((u.x, u.y), post) <= 120:
                    continue
                last = self.orders.get(u.id)
                if u.busy and last and last[0] == 'guard' and _d(last[1], post) <= 100:
                    continue
                self.orders[u.id] = ('guard', post)
                out.append(pw.Order('attack_move', (u.id,), pos=post))
            if fresh:
                self.log.append((obs.frame, 'guard', f'flash ({p[0]:.0f}, {p[1]:.0f}) with {len(take)}'
                                 + (f', {len(band)} in sight' if band else '')))
            left = [u for u in left if u.id not in guards]
        self.guards = guards
        return out, set(guards)

    # --- standing ready for a coming threat -------------------------------------------------------------------------
    def _coming(self, obs):
        """The next threat's chokes (earliest countdown, source within block_reach of home), nearest home first --
        the order _blocks blocks them in."""
        st = self.style
        coming = [c for c in obs.chokes if c.at is not None and c.at > obs.frame and
                  _d(c.source, obs.home) <= st.block_reach]
        if not coming:
            return []
        first = min(c.at for c in coming)
        return sorted((c for c in coming if c.at - first < FPS), key=lambda c: (_d(c.source, obs.home), c.name))

    def _post(self, obs):
        """Where the army waits for the coming threat (Style.preposition): of the next threat's ways the nearest one
        the player leaves open (not blocked, not among the ones _blocks will block), on the line from home to its
        mouth, at most post_reach out; held post_hold seconds after the threat. None: no threat timed, or every way
        is (to be) blocked."""
        st = self.style
        if not st.preposition or not obs.chokes:
            return None
        coming = self._coming(obs)
        if coming and coming[0].at - obs.frame <= st.post_ahead * FPS:
            # the ways the player's blockers can shut for this threat: no more than there are blockers (with one
            # engineer the second-nearest way stays open -- the army waits there, not at a way nobody will shut)
            n = min(st.block, len(self._blockers(obs) & {u.id for u in obs.mine if u.id not in self.wounded}))
            planned = {c.name for c in coming[:n]} | set(self.blocking)
            open_ = [c for c in coming if c.name not in planned and not c.blocked]
            if open_:
                self.post = (None, open_[0].name, coming[0].at + int(st.post_hold * FPS))
        if self.post is None or obs.frame > self.post[2]:
            self.post = None
            return None
        c = next((c for c in obs.chokes if c.name == self.post[1]), None)
        if c is None:
            return None
        d = _d(c.pos, obs.home)
        k = min(1.0, st.post_reach / d) if d else 0.0
        return (obs.home[0] + (c.pos[0] - obs.home[0]) * k, obs.home[1] + (c.pos[1] - obs.home[1]) * k)

    def _stand(self, obs, army, post):
        """Walk the army to the post (attack-moving: it fights what it meets on the way); re-told only when it is
        away from the post and its last post order was elsewhere (the post moves with an escorted convoy)."""
        out = []
        for u in army:
            if _d((u.x, u.y), post) <= 120:
                continue
            last = self.orders.get(u.id)
            if u.busy and last and last[0] == 'post' and _d(last[1], post) <= 100:
                continue
            self.orders[u.id] = ('post', post)
            out.append(pw.Order('attack_move', (u.id,), pos=post))
        if out and (not self.log or self.log[-1][1] != 'post'):
            self.log.append((obs.frame, 'post', f'{self.post[1]} at ({post[0]:.0f}, {post[1]:.0f}) with {len(out)}'))
        return out

    def _gather(self, obs, army, why):
        out = []
        for u in army:
            d = _d((u.x, u.y), obs.home)
            if u.busy == 'attack' and d <= self.style.defend_radius:   # fighting near home: let it finish
                continue
            if d > 150:
                out += self._tell(u, pw.Order('move', (u.id,), pos=obs.home), ('move', obs.home))
        if not self.log or self.log[-1][1] != 'wait':
            self.log.append((obs.frame, 'wait', why))
        return out

    def _scouting(self, obs):
        if not obs.leads:
            return []
        for i, p in enumerate(obs.leads):
            if any(_d((u.x, u.y), p) <= self.style.lead_reach for u in obs.mine):
                self.visited.add(i)
        todo = [i for i in range(len(obs.leads)) if i not in self.visited]
        if not todo:
            self.visited.clear()
            todo = list(range(len(obs.leads)))
        blockers = self._blockers(obs)
        free = [u for u in obs.mine if u.id not in self.wounded and u.id not in blockers]
        if not free:
            return []
        scout = next((u for u in free if u.id == self.scout), None)
        if scout is None:                       # the cheapest healthy unit looks
            scout = min(free, key=lambda u: (u.cost, u.id))
            self.scout = scout.id
        lead = min(todo, key=lambda i: (_d((scout.x, scout.y), obs.leads[i]), i))
        p = obs.leads[lead]
        out = self._tell(scout, pw.Order('move', (scout.id,), pos=p), ('move', p))
        if out:
            self.log.append((obs.frame, 'scout', f'{scout.template}#{scout.id} -> {p}'))
        return out

    # --- the level's blocking power ---------------------------------------------------------------------------------
    def _blockers(self, obs):
        """Ids of the units kept for the level's blocking power (they neither scout nor join the army)."""
        if not self.style.block or not obs.chokes:
            return set()
        by = set().union(*(c.by for c in obs.chokes))
        return {u.id for u in obs.mine if u.template in by}

    def _eta(self, u, pos, build=0.0):
        """Seconds for unit u to walk to pos and raise the block there (build: the choke's own build time, the bar
        the player has seen; 0 -> Style.block_build)."""
        return _d((u.x, u.y), pos) / (u.speed or self.style.walk_speed) + (build or self.style.block_build)

    def _bare_spot(self, obs, pos, caster):
        """Where the player clicks a ground power meant for `pos`: pos itself, or the nearest spot on the rings round it
        (Style.block_nudge) that is Style.power_clearance from every unit in sight but the caster (INFERRED)."""
        st = self.style
        if st.power_clearance <= 0 or st.block_nudge <= 0:
            return pos
        near = [(u.x, u.y) for u in obs.mine if u.id != caster] + [(t.x, t.y) for t in obs.seen]
        spots = [pos] + [(pos[0] + k * st.block_nudge * math.cos(a * math.pi / 4),
                          pos[1] + k * st.block_nudge * math.sin(a * math.pi / 4)) for k in (1, 2, 3) for a in range(8)]
        return next((p for p in spots if all(_d(p, q) >= st.power_clearance for q in near)), pos)

    def _blocks(self, obs):
        """Block the coming threat (INFERRED, the levels' design: watch the countdown, decide which ways to block and
        which to leave open). The next threat is the earliest countdown among the chokes; of its chokes the ones whose
        source is nearest home (on an escort level: the convoy) are the dangerous ones -- block up to Style.block of
        them, each with the free blocker that gets there first, sent just in time (walk + build + margin before the
        threat; earlier and the block may melt before it comes). Idle blockers keep to home."""
        st = self.style
        if not st.block or not obs.chokes:
            return []
        self.blocking = {n: j for n, j in self.blocking.items() if j[1] is not None and j[1] >= obs.frame}
        mine = {u.id: u for u in obs.mine if u.id not in self.wounded}
        busy = {uid for uid, _ in self.blocking.values()}
        out = []
        coming = self._coming(obs)
        if coming:
            # only as many ways as there are blockers: a lone engineer waits for the nearest way's moment instead of
            # being spent early on the next way out (whose moment, its walk being longer, comes first)
            n = min(st.block, len(self._blockers(obs) & set(mine)))
            for c in coming[:n]:
                if c.blocked or c.name in self.blocking:
                    continue
                free = [u for u in mine.values() if u.id not in busy and u.template in c.by
                        and c.power not in u.reloading]   # a greyed button: wait for it (or another blocker)
                if not free:
                    continue
                u = min(free, key=lambda u: (self._eta(u, c.pos, c.build), u.id))
                left = (c.at - obs.frame) / FPS
                if left > self._eta(u, c.pos, c.build) + st.block_margin:
                    continue                    # not yet: placed now it might melt before the threat comes
                busy.add(u.id)
                self.blocking[c.name] = (u.id, c.at)
                spot = self._bare_spot(obs, c.pos, u.id)
                self.orders[u.id] = ('power', spot)
                out.append(pw.Order('power', (u.id,), pos=spot, power=c.power))
                self.log.append((obs.frame, 'block', f'{c.name} by {u.template}#{u.id}, {left:.0f}s before'))
        for u in mine.values():                 # the idle ones walk with home
            if u.id in busy or u.id not in self._blockers(obs) or _d((u.x, u.y), obs.home) <= st.blocker_leash:
                continue
            last = self.orders.get(u.id)
            if u.busy and last and last[0] == 'move' and _d(last[1], obs.home) <= st.blocker_leash / 2:
                continue
            self.orders[u.id] = ('move', obs.home)
            out.append(pw.Order('move', (u.id,), pos=obs.home))
        return out



def play(world, proxy, frames, every=15):
    """Run proxy on world for `frames` frames, one decision every `every` frames. Returns the orders the world took."""
    taken = []
    f = 0
    while f < frames:
        obs = world.observe()
        for o in proxy.decide(obs):
            if world.issue(o):
                taken.append((obs.frame, o))
            else:
                proxy.refused(obs, o)
        world.step(every)
        f += every
    return taken
