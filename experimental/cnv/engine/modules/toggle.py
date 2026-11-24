"""ToggleStatusSpecialAbilityUpdate (bench 11-11 engine_toggle a-f, round 223
engine_acts_tgl / acts_btn; moved from simunits.toggle_modules / template_toggles and simtoggle.Toggles' presses in
step M5, ADR 0029, docs/engine/sim-modules.md 4): a button that steps the module to its next ToggleState, modulo
their count. The first state holds from the start; a press reads the new state the press's frame with PackTime 0 or
1 s alike (b); an UnpackTime puts it off that many seconds x 15 frames (d: the engineer's tent, 1 s -> 16 frames
with UNPACK_LAG 0 counted from the press's cell); a state with a DisabledType takes no further press (d, f; INFERRED
that DisabledType is the cause, not read in the program), nor does one while a press waits out its UnpackTime.

What a state switches -- its ObjectStatus / AttributeModifier (simmodifier.modify), its LocomotorSet's speed -- the host
re-sets when told (World.toggled: today simtoggle.entered). Which button presses which module (the command's
special power), a POWERED thing short of power and the notes stay outside (simtoggle.press).

Its state is shown in the frame record by the body's forwards `toggle_at` ({module index: state}, the modules a
press ever moved) and `armor_up` (the miner's armour toggle in its second state): several of these on one thing
record as one field, so RECORDED names none of them (its STATE: at / moved / due_at)."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                # the game's logic frames a second (bench 2026-10-28, probe align)
UNPACK_LAG = 0          # frames past UnpackTime x 15 a toggle's new state is first read (engine_toggle d: 16)


class ToggleData(module.ModuleData):
    def __init__(self, power=None, pack=0.0, unpack=0.0, states=()):
        self.power = power          # SpecialPowerTemplate: the button's special power that presses it
        self.pack = pack            # PackTime seconds (read, not acted on: engine_toggle b)
        self.unpack = unpack        # UnpackTime seconds: a press waits this long
        self.states = states        # [{status: set, modifier, disabled, locomotor, modules: <Module> ids}] of its ToggleStates

    @classmethod
    def parse(cls, head, inner):
        states = [dict(status=set((templates.attr(h, 'ObjectStatus') or '').split()),
                       conditions=set((templates.attr(h, 'ModelConditions') or '').split()),
                       modifier=templates.attr(h, 'AttributeModifier'), disabled=templates.attr(h, 'DisabledType'),
                       locomotor=templates.attr(h, 'LocomotorSet'), armor=templates.attr(h, 'ArmorSet'),
                       modules={templates.attr(mh, 'ModuleId') for mh, _ in templates.blocks(i, 'Module')})
                  for h, i in templates.blocks(inner, 'ToggleState')]
        return cls(templates.attr(head, 'SpecialPowerTemplate'), templates.secs(templates.attr(head, 'PackTime') or '0s'),
                   templates.secs(templates.attr(head, 'UnpackTime') or '0s'), states)

    def rules(self):
        """{power, pack, unpack, states}: the shape simunits.toggle_modules gave (Sim.toggles_of)."""
        return dict(power=self.power, pack=self.pack, unpack=self.unpack, states=self.states)


@factory.module('ToggleStatusSpecialAbilityUpdate')
class Toggle(module.Module, interfaces.Update, interfaces.Toggle):
    """In the frame order's toggles cell: asleep until a press's UnpackTime is out, then enters the next state."""
    DATA = ToggleData
    PHASE = 'toggles'
    STATE = ('at', 'moved', 'due_at')
    RECORDED = ()
    at = 0              # the index of its ToggleState now
    moved = False       # a press ever moved it (its index is then in the body's toggle_at)
    due_at = None       # the frame a waiting press's state is entered

    def rules(self):
        return self.data.rules()

    def state(self):
        return self.at

    def entered(self):
        return self.moved

    def press(self, frame):
        states = self.data.states
        if states[self.at % len(states)]['disabled'] or self.due_at is not None:
            return False
        delay = int(round(self.data.unpack * FPS))
        if delay:
            self.due_at = frame + delay + UNPACK_LAG
            self.world.wake(self, self.due_at)
        else:
            self._enter()
        return True

    def _enter(self):
        self.at = (self.at + 1) % len(self.data.states)
        self.moved = True
        self.world.toggled(self.thing, self)

    def update(self, frame):
        if self.due_at is None:
            return interfaces.SLEEP
        if frame < self.due_at:
            return self.due_at - frame
        self.due_at = None
        if self.thing.alive:
            self._enter()
        return interfaces.SLEEP


class OnCreateData(module.ModuleData):
    def __init__(self, powers=frozenset()):
        self.powers = powers        # the SpecialPowerTemplate(s) fired once the thing is made

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.names(head, inner, 'SpecialPowerTemplate'))


@factory.module('ActivateSpecialPowerOnCreate')
class OnCreate(module.Module, interfaces.Update):
    """Presses its thing's toggle of that power in its first update (E212 engine_oncreate_e: retail's one use, the
    _Ambush tank buster, is IN_SPIDER_HOLE from the second script frame, the plain one never; a press at f30 takes it
    out, so the toggle itself moved). A power served by no toggle: not benched, left alone."""
    DATA = OnCreateData
    PHASE = 'toggles'
    STATE = ()
    RECORDED = ()

    def update(self, frame):
        for m in self.thing.find(interfaces.Toggle):
            if self.thing.alive and m.rules()['power'] in self.data.powers:
                m.press(frame)
        return interfaces.SLEEP
