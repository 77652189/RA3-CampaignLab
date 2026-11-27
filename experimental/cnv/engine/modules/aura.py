"""AttributeModifierAuraUpdate (bench upgrades.md 5 / 5.1, engine_stasis_edge / _leave; moved from simunits.auras and
simmodifier's aura_cache / aura_beat in step M12, ADR 0029, docs/engine/sim-modules.md 4): an object that hangs
its AttributeModifier on what its ObjectFilter takes within Range, once every RefreshDelay.

It keeps its rule and the frame of its last refresh (pulse); who it hangs the modifier on, for how long and the
re-reading of their modifiers stay in the host's aura tick (simmodifier.aura_tick), in the order it had.
The port reads the block from the template's own XML alone (simunits.SELF_ONLY, as the reader it replaced: 354 retail
templates that inherit an aura -- the garrisoned civilian buildings' -- read none; reading it inherited is a
behaviour change). Its beat is its own now, not kept by the aura object's name: a thing made again under the name of
a dead one starts afresh (11 missions do not meet it).

Its state is `beat`; RECORDED names nothing: its beat had no field in the frame record."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates

FPS = 15                # the game's logic frames a second (bench 2026-10-28, probe align)


class AuraData(module.ModuleData):
    def __init__(self, rule):
        # {mod, range, refresh (frames), relation (ALLIES / ENEMIES / NEUTRAL against the aura's owner), include /
        # exclude (KindOf sets; include empty = any), active (InitiallyActive), needs (RequiredObjectStatusFlags the
        # aura object must have: the jammer's toggle), self (AllowSelf)}: the shape simunits.auras gave
        self.rule = rule

    @classmethod
    def parse(cls, head, inner):
        f = next(templates.blocks(inner, 'ObjectFilter'), ('', ''))[0]
        return cls({'mod': templates.attr(head, 'AttributeModifierName'),
                    'range': templates.num(templates.attr(head, 'Range'), 0.0),
                    'refresh': max(1, int(round(templates.secs(templates.attr(head, 'RefreshDelay', '1s')) * FPS))),
                    'relation': set((templates.attr(f, 'Relationship') or 'ALLIES ENEMIES NEUTRAL').split()),
                    'include': set((templates.attr(f, 'Include') or '').split()),
                    'exclude': set((templates.attr(f, 'Exclude') or '').split()),
                    'active': (templates.attr(head, 'InitiallyActive', 'true') or 'true').lower() != 'false',
                    'needs': set((templates.attr(head, 'RequiredObjectStatusFlags') or '').split()),
                    'self': (templates.attr(head, 'AllowSelf', 'false') or '').lower() == 'true',
                    'contained': (templates.attr(head, 'AffectContainedOnly', 'false') or '').lower() == 'true'})


@factory.module('AttributeModifierAuraUpdate')
class Aura(module.Module, interfaces.Create, interfaces.Aura):
    DATA = AuraData
    STATE = ('beat',)
    RECORDED = ()

    def on_create(self, frame):
        self.beat = None        # the frame of its last refresh (None: none yet)

    def on_build_complete(self):
        pass

    def rules(self):
        return self.data.rule

    def last_beat(self):
        return getattr(self, 'beat', None)

    def pulse(self, frame):
        """Its refresh is due at `frame` (the first at once, then every RefreshDelay counted from the first): -> True
        and the beat moved to the latest refresh at or before `frame`; else False."""
        every, beat = self.data.rule['refresh'], self.last_beat()
        if beat is not None and frame - beat < every:
            return False
        self.beat = frame if beat is None else beat + (frame - beat) // every * every
        return True
