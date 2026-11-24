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
GENERIC_TOGGLE_STATE; E219 minejap e: the Ore Collector's gun on during its drive costs ~3 frames, not modelled)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


@factory.module('OreMinerBehavior')
class OreMiner(module.Module, interfaces.OreMiner):
    """Its trip, no update of its own (simmine moves it in the mine cell). mine: the trip (the name the body's field
    had, so the frame record is unchanged). node / refinery: the trip's node and refinery themselves (the trip names
    them, as the record shows them; the loop goes by these -- 11-19 same-name sweep: a thing made under the name since
    is not the one picked)."""
    DATA = module.ModuleData
    STATE = ('mine', 'node', 'refinery')
    RECORDED = ('mine',)
    mine = None         # no trip yet (or a move dropped it)
    node = refinery = None

    def trip(self):
        return self.mine

    def set_trip(self, trip):
        """A new trip (nothing picked yet), or None: dropped."""
        self.mine, self.node, self.refinery = trip, None, None

    def head_for(self, node=None, refinery=None):
        """The trip's node, or refinery, picked: kept and named in the trip."""
        if node is not None:
            self.node, self.mine['node'] = node, node.name
        if refinery is not None:
            self.refinery, self.mine['ref'] = refinery, refinery.name

    def dump(self):
        """DUMP_ORE (MonitorConditionUpdate): what it carries is gone."""
        if self.mine:
            self.mine['load'] = 0


class MonitorData(module.ModuleData):
    def __init__(self, flags=frozenset(), actions=frozenset(), pre=0, post=1):
        self.flags = flags          # ModelConditionFlags: every one held
        self.actions = actions      # ActionsOnTriggered (DUMP_ORE the one retail uses)
        self.pre, self.post = pre, post     # PreDelay / PostDelay, frames

    @classmethod
    def parse(cls, head, inner):
        frames = lambda name: round(templates.secs(templates.attr(head, name)) * 15)  # noqa: E731
        return cls(templates.words(head, 'ModelConditionFlags'), templates.words(head, 'ActionsOnTriggered'),
                   frames('PreDelay'), max(1, frames('PostDelay')))


@factory.module('MonitorConditionUpdate')
class MonitorCondition(module.Module, interfaces.Update):
    """MonitorConditionUpdate (E219, checks/engine_mining.readings.toml minejap): its thing holding every flag -- CARRYING
    while its miner's trip has a load, a toggle's ModelConditions in its state now, a script's -- PreDelay frames on
    (INFERRED: held all along), it does its actions, then sleeps PostDelay. Its OCL is not made: retail's one
    (DroppedOrePile) is a 1 s prop no script counts (not SELECTABLE)."""
    DATA = MonitorData
    PHASE = 'toggles'
    ORDER = 1                   # after the toggles' own cell runs
    STATE = ('due',)
    due = None                  # the frame its PreDelay is out

    def update(self, frame):
        b, d = self.thing, self.data
        if not b.alive:
            return interfaces.SLEEP
        miner = b.find(interfaces.OreMiner)
        held = set(b.model_conditions).union(*(t.rules()['states'][t.state()].get('conditions', ())
                                               for t in b.find(interfaces.Toggle)))
        if miner is not None and miner.mine and miner.mine['load']:
            held.add('CARRYING')
        if not d.flags <= held:
            self.due = None
            return 1
        if self.due is None:
            self.due = frame + d.pre
        if frame < self.due:
            return self.due - frame
        self.due = None
        if 'DUMP_ORE' in d.actions and miner is not None:
            miner.dump()
        return d.post
