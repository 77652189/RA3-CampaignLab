"""Native Tanya C4: nugget retained/deleted x normal/EXPLOSIVES_ATTACHED parent.

Preserve the native host, weapon selection and AttachUpdate. Only rename the
host/attach weapon and remove AttachNugget in high/removed. Scripted parent
EXPLOSIVES_ATTACHED in order/removed isolates ForbiddenParentStatus; it is
not evidence of the native explosives lifecycle. No instant-shot substitute.
Prediction before bench: base attaches, sets MARCH_OF_DEATH, detonates the
10000HP Hammer and survives; deleted nugget and forbidden-parent lanes do
not attach or detonate. Module-autonomous attachment is an alternative.
Packed: parent HP% * 100 + child alive8 + parent alive16 + ever child
ATTACHED1 + ever parent MARCH_OF_DEATH2 + ever parent EXPLOSIVES_ATTACHED4.
Expect15/10024/10028/10028. Latches include the scripted bit from start.
No claim of exact dispatch, detach, damage source or complete Attach cover.
Measured a:11/10024/10030/10028. The forbidden parent gets MARCH_OF_DEATH
without child ATTACHED. Original expectations are retained. b removes only
ForbiddenParentStatus from the modules; predict11/10024/15/10028.
Measured b confirms11/10024/15/10028; both retained-nugget parents die.
The normal parent never latched EXPLOSIVES_ATTACHED before death in either
run. These are diagnostic observations; native module replay remains a gap.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE, target
from maps import probe_range
from model import status
from parts import Mission, Script, Test, Unit

LANES = ('base', 'high', 'order', 'removed')
VALUES = (15, 10024, 10028, 10028)


def mission():
    root = Path(SAGE)
    native = (root / 'Allied/Units/AlliedCommandoTech1.xml').read_text(encoding='utf-8')
    source = 'AlliedCommandoAttachWeapon'
    weapons = (root / 'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="' + source + r'".*?</WeaponTemplate>', weapons, re.S).group()
    m = Mission(name='CampAttC4', map=probe_range, units=[], facts={})
    m.ext = True
    for lane in LANES:
        uid, wid = 'CNV_AttC4' + lane.title(), 'CNV_AttC4Gun' + lane.title()
        xml = native.replace('id="AlliedCommandoTech1"', f'id="{uid}"', 1)
        xml = xml.replace(f'Template="{source}"', f'Template="{wid}"')
        w = weapon.replace(f'id="{source}"', f'id="{wid}"', 1)
        if lane in ('high', 'removed'):
            w, n = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
            assert n == 1
        xml = xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                          'MinFrames="15" MaxFrames="4000"/>', 1)
        xml = xml.replace('</AssetDeclaration>', w + '</AssetDeclaration>')
        victim = target('CNV_AttC4Parent' + lane.title(), health=10000)
        victim.xml = victim.xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                                        'MinFrames="15" MaxFrames="4000"/>', 1)
        m.units.extend((Unit(uid, xml, link=['WeaponTemplate:' + wid]), victim))
        m.put(uid, lane + ' gun', side='p1', angle=1.5708, name='C4 ' + lane + ' child')
        m.put(victim.id, lane + ' gun', 0, 120, side='s1', angle=4.7124, name='C4 ' + lane + ' parent')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('SET_MILLISECOND_TIMER', 'C4 Fire', 6.)]
    fire = []
    for lane in LANES:
        child, parent = ['C4 ' + lane + ' ' + role for role in ('child', 'parent')]
        c = 'CNV_AttC4_' + lane
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (child, parent))
        if lane in ('order', 'removed'):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'EXPLOSIVES_ATTACHED', 1))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS', child, 'NO_ATTACK', 0), ('NAMED_ATTACK_NAMED', child, parent)))
        t.counters.append((c, lane + ' c4 packed'))
        for weight, who, bit in ((1, child, 'ATTACHED'), (2, parent, 'MARCH_OF_DEATH'),
                                  (4, parent, 'EXPLOSIVES_ATTACHED')):
            t.scripts.append(Script('Test - latch ' + lane + bit,
                [('NAMED_NOT_DESTROYED', who), ('UNIT_HAS_OBJECT_STATUS', who, status(bit))],
                [('INCREMENT_COUNTER', weight, c + ' ever')]))
        t.scripts.append(Script('Test - reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
        t.scripts.append(Script('Test - hp ' + lane, [('NAMED_NOT_DESTROYED', parent)],
            [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', parent, c), ('COUNTER_MATH_VALUE', c, 2, 100),
             ('INCREMENT_COUNTER', 16, c)], once=False))
        t.scripts.append(Script('Test - child alive ' + lane, [('NAMED_NOT_DESTROYED', child)],
            [('INCREMENT_COUNTER', 8, c)], once=False))
        t.scripts.append(Script('Test - pack ' + lane, [],
            [('COUNTER_MATH_COUNTER', c, 0, c + ' ever')], once=False))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.append(Script('Test - fire', [('TIMER_EXPIRED', 'C4 Fire')], fire))
    t.expect = [(label, 22, '==', value, 24) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
    return t


def without_parent_gate(m):
    m.name = 'CampAttC4Gate'
    for u in m.units:
        if u.id.startswith('CNV_AttC4') and not u.id.startswith('CNV_AttC4Parent'):
            u.xml, n = re.subn(r'\s+ForbiddenParentStatus="EXPLOSIVES_ATTACHED"', '', u.xml)
            assert n == 1
    t = check(m)
    t.expect = [(label, 22, '==', value, 24) for (_, label), value in
                zip(t.counters, (11, 10024, 15, 10028))]
    return t


MISSION = {'engine_attachc4': mission}
CHECKS = {'engine_attachc4': {'a': check, 'b': without_parent_gate}}
