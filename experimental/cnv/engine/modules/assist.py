"""NotifyWhenAttackingBehavior + AttackAssistResponseBehavior (E144 / E, bench checks/engine_attackassist.readings.toml):
a firing notifier calls up to MaxFriendsToNotify AcceptableFriends within NotifyRadius; a friend whose response module
is the one the notifier names fires that module's weapon (WeaponSlotType) at the notifier -- retail's prism link puts
+50 % damage on the source tower. The host's fight (engine.orders.order.assist) runs it once a tick.

Data only. INFERRED: friends nearest first, a friend firing at its own foe that tick does not answer, WeaponSlotID not
read (the first line of that ordering), SleepTime not read (every fight tick). Only AcceptableFriends of Rule NONE
with IncludeThing names is read; any other filter answers nobody (a gap)."""
import re

from engine.kernel import factory, interfaces, module
from engine.ports import templates


class NotifyData(module.ModuleData):
    def __init__(self, radius=0.0, most=0, response='', relation='ALLIES', friends=frozenset(), unread=''):
        self.radius, self.most, self.response = radius, most, response
        self.relation, self.friends = relation, friends     # AcceptableFriends Relationship, IncludeThing (lower)
        self.unread = unread                                # a filter not read (its gap note); notifies nobody

    @classmethod
    def parse(cls, head, inner):
        m = re.search(r'<AcceptableFriends\b([^>]*?)(/>|>(.*?)</AcceptableFriends>)', inner or '', re.S)
        fh, fi = (m.group(1), m.group(3) or '') if m else ('', '')
        rest = re.sub(r'<IncludeThing>[^<]*</IncludeThing>', '', fi).strip()
        unread = '' if m and templates.attr(fh, 'Rule') == 'NONE' and not rest and \
            set(re.findall(r'(\w+)\s*=', fh)) <= {'Rule', 'Relationship'} else 'AcceptableFriends'
        return cls(templates.num(templates.attr(head, 'NotifyRadius'), 0.0),
                   int(templates.num(templates.attr(head, 'MaxFriendsToNotify'), 1.0)),
                   templates.attr(head, 'AssistResponseModuleId', ''), templates.attr(fh, 'Relationship', 'ALLIES'),
                   frozenset(n.lower() for n in templates.names('', fi, 'IncludeThing')), unread)


@factory.module('NotifyWhenAttackingBehavior')
class Notify(module.Module, interfaces.AssistNotify):
    DATA = NotifyData

    def callable(self, friend, relation, distance):
        """Can it call `friend` (standing `relation` to it, `distance` centre to centre)?"""
        d = self.data
        return not d.unread and relation == d.relation and friend.template.lower() in d.friends and distance <= d.radius


class ResponseData(module.ModuleData):
    def __init__(self, tag='', ordering='SECONDARY_WEAPON'):
        self.tag, self.ordering = tag, ordering

    @classmethod
    def parse(cls, head, inner):
        return cls(templates.attr(head, 'id', ''), templates.attr(head, 'WeaponSlotType', 'SECONDARY_WEAPON'))


@factory.module('AttackAssistResponseBehavior')
class Response(module.Module, interfaces.AssistResponse):
    DATA = ResponseData
