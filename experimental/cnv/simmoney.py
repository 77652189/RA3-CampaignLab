"""L4 money (ADR 0029, docs/engine/sim-layers.md): the players' money, the AI's income multiplier, income sharing and
the money cap, with the rules that pay into them from below: the deposit buildings' clock, a collector's unloading
(collect: handed to simmine), a deposit split between sharing friends (earn). It reads the world only through
simworld.WORLD_API. Other writers of the money (scripts, selling, production, repairs, spies) still write the dicts
directly; Sim.money / income / sharing / money_cap are these same dicts.
"""
from simworld import CIV


class Money:
    def __init__(self):
        self.money = {}                     # player -> money
        self.income = {}                    # player -> (AI income multiplier, fraction carried) (simai: ResourceMultiplierCheat)
        self.sharing = set()                # players sharing income (PLAYER_TOGGLE_RESOURCE_SHARING)
        self.money_cap = {}                 # PLAYER_SET_MONEY_CAP: player -> cap (scripts' money not held to it)

    def deposit_due(self, world, frame):
        """R4: the deposit buildings a player (not the neutral side) holds pay `amount` each `frames` (Generals'
        AutoDepositUpdate.update: the clock runs for the neutral too, it just pays nobody)."""
        for b in world.living():
            if b.deposit and b.deposit_at is not None and frame >= b.deposit_at:
                b.deposit_at = frame + b.deposit[2]
                if b.owner != CIV and b.deposit[1] > 0:
                    self.money[b.owner] = self.money.get(b.owner, 0) + b.deposit[1]

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
        """Money paid that is no income (a sale's refund, simbody.Life.sell): never split, never held to the cap."""
        self.money[player] = self.money.get(player, 0) + amount
