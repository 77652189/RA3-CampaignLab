"""The AIUpdate family's order state (cmd_pack C2): a unit's stance (GUARD 0, AGGRESSIVE 1, HOLD_POSITION 2, HOLD_FIRE
3; stance.md), TEAM_ALLOW_AI_AUTOACQUIRE, an armed unit's AutoAcquireEnemiesWhenIdle words, its goal, mode and fire at
the ground; (C3) its chase, (C4) its waypoint path and plain move's end, whose rules (they ask other things) stay
engine.orders.order's: Body fields once (Body's forwards). Attached at its first setting (`of`, Body's `aiupdate`), else defaults."""
from engine.kernel import factory, interfaces, module


@factory.module('AIOrderState')
class AIOrderState(module.Module, interfaces.AIUpdate):
    RECORDED = ('hold_fire', 'hold_paused', 'stance', 'ai_acquire', 'acquire', 'goal', 'mode', 'ground_fire',
                'chase', 'home', 'auto_to', 'resume', 'spot', 'engaged', 'follow', 'move_to')
    STATE = RECORDED + ('ordered',)     # read by order_attack alone: in the snapshot, not the frame record
    hold_fire, hold_paused, stance, ai_acquire, acquire = False, False, 0, False, frozenset()
    ordered = False     # its goal is an attack order's (not the AI's pursuit alone; an attack-move clears it)
    goal, mode, ground_fire = None, 'idle', None    # goal: a point or a thing; mode: 'move' / 'attack' (stops to fight) ...
    # idle_chase: the enemy it went after by itself, where it stood (walks back to), the way's end that rule gave it;
    chase = home = auto_to = resume = spot = None   # attack_chase: the attack-move's end; (goal id, x, y) of a fire_spot
    engaged = False                                 # an attack-mover with an enemy in range holds
    follow = move_to = None     # order_follow's {label, waypoint, ...} (a team shares one); a plain move's end (held_up)

    def engage(self):
        """Sim.aim fired (none engaged before it: fight, aim_due): an attack-mover holds while it fights."""
        self.engaged = self.mode == 'attack'

    def forget(self):
        """Its chase by itself and the attack-move it turned from end (an order of its own since; a teleport)."""
        self.chase = self.resume = self.auto_to = None

    def command(self, order, target=None):
        """An order's own writes (C2; the port resolves unit and target, keeps the walk): 'attack' (`target` its goal,
        attacking), 'goal' (`target` its goal alone: the AI's pursuit, INFERRED e135), 'stop' (no goal), 'idle' (no
        goal, idle), 'ground' (idle, firing at the point `target` till another order); all but 'goal' end a ground fire.
        An attack given under HOLD_FIRE fires (stance.md b)."""
        if order == 'attack':
            self.hold_paused = False
        if order != 'goal':
            self.ground_fire = target if order == 'ground' else None
        if order != 'goal' or target is not self.goal:
            self.ordered = order == 'attack'
        self.goal = target if order in ('attack', 'goal') else None
        if order not in ('goal', 'stop'):
            self.mode = 'attack' if order == 'attack' else 'idle'

    def set_stance(self, stance, aimed):
        """UNIT_SET_STANCE; `aimed`: it is on an object -- going HOLD_FIRE keeps that attack without firing it."""
        hold = stance == 3
        if hold != self.hold_fire:
            self.hold_paused = hold and aimed
        self.hold_fire, self.stance = hold, stance

    def set_auto_acquire(self, on):
        self.ai_acquire = on


def of(thing):
    """`thing`'s AIOrderState, attached the first time (World.attach, its Body module's world)."""
    return thing.find(interfaces.AIUpdate) or thing.find(interfaces.Body).world.attach(thing, 'AIOrderState')


def writer(field):
    """Body's setter of a C2b field till its writers' families move (guard: WRITTEN): none attached for a default (an
    unarmed unit's acquire), but a ground_fire is in the record once written (STATE; no forward), None too."""
    def write(thing, value):
        if field == 'ground_fire' or value != getattr(AIOrderState, field) or thing.find(interfaces.AIUpdate):
            setattr(of(thing), field, value)
    return write


ground_fire = property(lambda thing: getattr(thing.find(interfaces.AIUpdate), 'ground_fire', None), writer('ground_fire'))
