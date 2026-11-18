"""SecondaryDamageTracker (the freeze; engine A round 107, ALIGN 'freeze' in sim.py, INFERRED from the SDK data, never
benched; moved from simunits.tracker / freeze and the body's cold / cold_step in step M11, ADR 0029,
docs/engine/sim-modules.md 4): the cold a cryo beam leaves on a thing.

The cold goes up by what the beams deal (a SecondaryDamageNugget's Amount a shot: add; a beam's rate over a tick: the
host's chill), down by DissipateAmount each UpdateDuration, and stays within 0 .. MaxDamageClampScaler x max health
(melt). The highest EffectInfo whose Fraction of max health it reaches is its step: the modifier family reads the
step's AttributeModifier and SetUpgradedArmor (simmodifier), the host re-reads the modifiers on a change of step and
kills on a DIE_ON_ENTER one (simdamage.chill keeps the tick, the bodies with cold and that order: a pure move).

Its state keeps the names the body's fields had (cold / cold_step), so the frame record is unchanged."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class FreezeData(module.ModuleData):
    def __init__(self, every=1.0, melt=0.0, cap=1.25, steps=()):
        # {every: UpdateDuration s, melt: DissipateAmount taken off each UpdateDuration, cap: MaxDamageClampScaler (the
        # most it holds, x max health), steps: [[Fraction of max health, AttributeModifier id, OnEnterDisable,
        # SetUpgradedArmor, DIE_ON_ENTER], ...] lowest first}: the shape simunits.tracker gave (simmodifier reads it)
        self.tracker = dict(every=every, melt=melt, cap=cap, steps=[list(x) for x in steps])

    @classmethod
    def parse(cls, head, inner):
        """Retail BaseVehicle / BaseInfantry / BaseStructure: 25 a second, 200 %, 0.2 .. 0.8 slow speed and rate of
        fire to 80 .. 20 %, 1.0 frozen (UNDER_FROZEN, CryoBeamFrozenArmor). A $ define as the cap:
        MAX_SECONDARY_DAMAGE_SCALER, 200 % (the only one)."""
        cap = templates.attr(head, 'MaxDamageClampScaler') or '125%'
        cap = 2.0 if cap.startswith('=') else templates.num(cap.rstrip('%'), 125.0) / 100.0
        steps = sorted((templates.num(templates.attr(h, 'Fraction')), templates.attr(h, 'AttributeModifier'),
                        templates.attr(h, 'OnEnterDisable') == 'true', templates.attr(h, 'SetUpgradedArmor') == 'true',
                        'DIE_ON_ENTER' in (templates.attr(h, 'Options') or '').split())
                       for h, _ in templates.blocks(inner or '', 'EffectInfo'))
        return cls(templates.secs(templates.attr(head, 'UpdateDuration') or '1s'),
                   templates.num(templates.attr(head, 'DissipateAmount'), 0.0), cap, steps)


@factory.module('SecondaryDamageTracker')
class Freeze(module.Module, interfaces.Create, interfaces.Freeze):
    """No update cell of its own: the host's chill ticks it (add / melt), as before the move."""
    DATA = FreezeData
    STATE = ('cold', 'cold_step')

    def on_create(self, frame):
        self.cold = 0.0         # the secondary damage held
        self.cold_step = -1     # the highest EffectInfo reached (-1: none)

    def on_build_complete(self):
        pass

    def rules(self):
        return self.data.tracker

    def held(self):
        return self.cold

    def stage(self):
        return self.cold_step

    def add(self, amount):
        self.cold += amount

    def melt(self, dt):
        t = self.data.tracker
        hp = self.thing.max_hp
        self.cold = min(max(self.cold - t['melt'] / max(t['every'], 1e-6) * dt, 0.0), t['cap'] * hp)
        step = max((i for i, st in enumerate(t['steps']) if self.cold >= st[0] * hp), default=-1)
        moved = step != self.cold_step
        self.cold_step = step
        return moved
