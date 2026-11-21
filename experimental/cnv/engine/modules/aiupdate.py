"""The AIUpdate family's order state (cmd_pack C2a): a unit's stance (GUARD 0, AGGRESSIVE 1, HOLD_POSITION 2, HOLD_FIRE
3; stance.md) and TEAM_ALLOW_AI_AUTOACQUIRE, the Body fields they were (Body's forwards). Attached at its first setting
(`of`, Body's `aiupdate`); a unit never given one reads the defaults."""
from engine.kernel import factory, interfaces, module


@factory.module('AIOrderState')
class AIOrderState(module.Module, interfaces.AIUpdate):
    STATE = ('hold_fire', 'hold_paused', 'stance', 'ai_acquire')
    hold_fire, hold_paused, stance, ai_acquire = False, False, 0, False

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
