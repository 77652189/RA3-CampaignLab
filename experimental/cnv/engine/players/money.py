"""L4 money (ADR 0029, docs/engine/sim-layers.md): the players' money, the AI's income multiplier, income sharing and
the money cap, with the rules that pay into them from below: a deposit building's payment, a collector's unloading
(collect: handed to simmine), a deposit split between sharing friends (earn). It reads the world only through
simworld.WORLD_API. A sale's refund, a repair's cost, a spy's theft and a build job's instalment (instal) go through the methods; other
writers of the money (scripts, simai's other buys) still write the dicts directly; Sim.money / income / sharing / money_cap are
these same dicts.
"""
import math

import engine.players.tech as simtech
from engine.world.handle import CIV


class Money:
    def __init__(self):
        self.money = {}                     # player -> money
        self.income = {}                    # player -> (AI income multiplier, fraction carried) (simai: ResourceMultiplierCheat)
        self.sharing = set()                # players sharing income (PLAYER_TOGGLE_RESOURCE_SHARING)
        self.money_cap = {}                 # PLAYER_SET_MONEY_CAP: player -> cap (scripts' money not held to it)

    def start(self, players, sides=None):
        """Each of `players` (a map's PLAYERS: key -> name) starts with its faction's PlayerTemplate StartingMoney
        (10000 each; bench 11-24 engine_area cash, entered through the campaign menu: Player_1, Soviet_1..6 exactly
        10000 before any script; 38 of the 40 retail missions then set it by script). A civilian / neutral template
        has none: 0 (Generals' Player::init takes the template's money; not read). `sides`: the mission's SidesList
        props by player (playerFaction). Returns `players`."""
        sides = sides or {}
        for slot, p in players.items():
            f = simtech.faction_of(p, sides.get(p) or sides.get(slot))
            self.money[p] = simtech.factions()[f]['cash'] if f else 0
        return players

    def deposit(self, owner, amount):
        """R4: a deposit building's amount (engine/modules/deposit.py, through World.pay) to its holder, a player --
        not the neutral side (Generals' AutoDepositUpdate.update: the clock runs for the neutral too, it just pays
        nobody); not held to the money cap."""
        if owner != CIV:
            self.money[owner] = self.money.get(owner, 0) + amount

    def earn(self, world, owner, amount):
        """Income (a collector's deposit) with PLAYER_TOGGLE_RESOURCE_SHARING (d115 19, bench 11-14 engine_share all):
        a sharing earner gives each Friend that shares too amount // (k + 1) of every deposit and keeps the rest (one
        sharer: 125 / 125 a load; two: 124 / 63 / 63). Scripts' money is never split (engine_acts flow)."""
        mates = [p for p in sorted(self.sharing) if p != owner and world.relations.get((owner, p)) == 'Friend'] \
            if owner in self.sharing else []
        cut = amount // (len(mates) + 1)
        for p in mates:
            self._pay(p, cut)
        self._pay(owner, amount - cut * len(mates))

    def _pay(self, player, amount):
        """One deposit under PLAYER_SET_MONEY_CAP: not paid at all if it would take the money over the cap (bench 11-15
        mineturn0 cap: cap 400, 8 a frame of the second load paid to 394, nothing after; capz: cap 0, no income ever).
        Scripts' money is not held to it (engine_acts_tel). A shared cut checked by its receiver's cap: INFERRED."""
        have = self.money.get(player, 0)
        cap = self.money_cap.get(player)
        if cap is not None and have + amount > cap:
            return
        self.money[player] = have + amount

    def collect(self, world, owner, give):
        """A collector's unloading `give` into `owner`'s money (simmine hands this in): an AI's income multiplier first
        (ResourceMultiplierCheat, simai sets self.income: x it, whole units paid, the fraction kept, l2_mining 4), then
        earn."""
        if owner in self.income:
            mult, frac = self.income[owner]
            frac += give * mult
            give = int(frac)
            self.income[owner] = (mult, frac - give)
        self.earn(world, owner, give)

    def credit(self, player, amount):
        """Money paid that is no income (a sale's refund, simbody.Life.sell; what a spy takes, siminfiltrator): never
        split, never held to the cap."""
        self.money[player] = self.money.get(player, 0) + amount

    def held(self, player):
        """A player's money now (none: 0)."""
        return self.money.get(player, 0)

    def charge(self, player, amount):
        """Money taken that the caller has checked is there (held): the skirmish AI's instalments on a structure it
        builds (simai Brain), a repair's cost (simrepair), what a spy steals (siminfiltrator). A player with no money
        entry ends at -amount (the AI pays only what it holds)."""
        self.money[player] = self.money.get(player, 0) - amount

    def multiply_income(self, player, mult):
        """An AI player's income multiplier (ResourceMultiplierCheat: simai sets it as the brain starts; collect
        applies it), the fraction carried reset."""
        self.income[player] = (mult, 0.0)

    def instal(self, player, job, progress):
        """A build job's instalment to `progress` (per cent; 100: a full job's rest) taken if held -- its cost so far
        rounded up less what it paid, never below 0 (a battlefield job paid over its progress gets no refund); whether
        it was. Sim.production.due and the AI's yards (simai Brain.yard_due)."""
        owe = max(0, min(job['cost'], math.ceil(round(job['cost'] * progress / 100.0, 9))) - job['paid'])
        if owe and owe > self.held(player):     # nothing owed goes through on any money (a script's -1: review 1120ff)
            return False
        self.charge(player, owe)
        job['paid'] += owe
        return True
