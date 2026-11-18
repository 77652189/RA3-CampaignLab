"""OreMinerBehavior (RA3's ore collector; docs/engine/mining.md, bench engine_mining a-g, mineturn*; moved from the
body's `mine` field in step M9, ADR 0029, docs/engine/sim-modules.md 4): a thing that mines. It keeps its trip -- the
collector loop's state, node, refinery, due frame, load, unloading count and leg (simmine.Mining._mine) -- or None
before it starts one and after a move dropped it. The loop itself, which arbitrates between miners (a node's claim and
dock, a refinery's one at a time, the refinery's own collector looking after the others), stays in simmine's mine
cell (host code) until the node is a module too.

Which things mine is now "has this module", not KindOf HARVESTER: the same on every retail template (the six miners;
BaseMiner, never placed, is the seventh block) and every mission's own templates (work/logs/m9_check.log, 1101
builds, no difference). Not read, as before the move: DeliveryCapacity / DeliveryTime (the load is simmine.MINE_LOAD,
the retail 250 / 2 s alike) and the Soviet and Japanese miners' appended ObjectStatusValidation (no mining while
GENERIC_TOGGLE_STATE)."""
from engine.kernel import factory, interfaces, module


@factory.module('OreMinerBehavior')
class OreMiner(module.Module, interfaces.OreMiner):
    """Its trip, no update of its own (simmine moves it in the mine cell). mine: the trip (the name the body's field
    had, so the frame record is unchanged)."""
    DATA = module.ModuleData
    STATE = ('mine',)
    mine = None         # no trip yet (or a move dropped it)

    def trip(self):
        return self.mine

    def set_trip(self, trip):
        self.mine = trip
