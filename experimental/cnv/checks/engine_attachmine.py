"""Native magnetic-mine AttachNugget, retained/deleted x normal/forbidden target.

The native SovietMagneticBomb host fires the native attach weapon on creation;
its one-second LifetimeUpdate, geometry and AttachUpdate are unchanged. Only
rename host/weapon and delete AttachNugget in negative controls. Create at the
parent waypoint at6s, after SPECIAL_ARMOR_ACTIVE is set in order/removed.
PREDICT111/110/110/110: ever ATTACHED1 + ever child alive10 + parent alive100
at10s. This isolates native mine dispatch and the target-status gate without
claiming the Flak Trooper projectile/OCL path or explosion damage attribution.
Raw evidence and unresolved alternatives: work/re/c_attachmine_report.md.
MEASURED a111/110/111/110: the single SPECIAL_ARMOR_ACTIVE lane attached.
b sets all three listed forbidden statuses and latches each bit independently
(AIRBORNE_TARGET1000, VEHICLE_ATTACHED2000, SPECIAL_ARMOR_ACTIVE4000).
PREDICT b111/110/7110/7110; this separates an unwritten status from mask/gate
semantics. The original a prediction remains unchanged.
MEASURED b111/110/7111/7110: all three parent bits latch, retained mine
still attaches. Two runs exhausted; gate/dispatch cause remains a gap.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE, target
from maps import probe_range
from model import status
from parts import Mission, Script, Test, Unit

LANES = ('base', 'high', 'order', 'removed')
VALUES = (111, 110, 110, 110)
SOURCE = 'SovietAntiVehicleInfantryMagneticBombAttachWeapon'


def mission():
    root = Path(SAGE)
    native = (root/'Soviet/Props/SovietMagneticBomb.xml').read_text(encoding='utf-8')
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="'+SOURCE+r'".*?</WeaponTemplate>', weapons, re.S).group()
    m = Mission(name='CampAttMine', map=probe_range, units=[], facts={})
    m.ext = True
    for lane in LANES:
        uid, wid = 'CNV_AttMine'+lane.title(), 'CNV_AttMineGun'+lane.title()
        xml = native.replace('id="SovietMagneticBomb"', f'id="{uid}"', 1)
        xml = xml.replace(f'WeaponName="{SOURCE}"', f'WeaponName="{wid}"')
        w = weapon.replace(f'id="{SOURCE}"', f'id="{wid}"', 1)
        if lane in ('high', 'removed'):
            w, count = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
            assert count == 1
        xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
        parent = target('CNV_AttMineParent'+lane.title(), health=100000)
        m.units.extend((Unit(uid, xml, link=['WeaponTemplate:'+wid]), parent))
        m.put(parent.id, lane+' gun', side='s1', name='Mine '+lane+' parent')
        m.waypoint(lane+' mine', 'Mine spawn '+lane, lane+' gun', 0, 0)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('SET_MILLISECOND_TIMER', 'Mine Spawn', 6.),
             ('SET_MILLISECOND_TIMER', 'Mine Sample', 10.)]
    spawn = []
    for lane in LANES:
        child, parent = ['Mine '+lane+' '+role for role in ('child', 'parent')]
        c = 'CNV_AttMine_'+lane
        t.counters.append((c, lane+' mine packed'))
        start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'NO_ATTACK', 1))
        if lane in ('order', 'removed'):
            start.append(('UNIT_CHANGE_OBJECT_STATUS', parent, 'SPECIAL_ARMOR_ACTIVE', 1))
        spawn.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', child, 'CNV_AttMine'+lane.title(),
                      m.team('p1'), m.mark(lane+' mine')))
        for weight, suffix, conditions in (
            (10, 'born', [('NAMED_NOT_DESTROYED', child)]),
            (1, 'attached', [('NAMED_NOT_DESTROYED', child),
                             ('UNIT_HAS_OBJECT_STATUS', child, status('ATTACHED'))]),
            (100, 'parent', [('TIMER_EXPIRED', 'Mine Sample'), ('NAMED_NOT_DESTROYED', parent)])):
            t.scripts.append(Script('Test - '+suffix+lane, conditions,
                                    [('INCREMENT_COUNTER', weight, c)]))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.append(Script('Test - spawn', [('TIMER_EXPIRED', 'Mine Spawn')], spawn))
    t.expect = [(label, 12, '==', value, 14) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=14., every=.5, sheet=False, lines=4))]
    return t


def all_forbidden(m):
    m.name = 'CampMineGate'
    t = check(m)
    for lane in ('order', 'removed'):
        parent = 'Mine '+lane+' parent'
        c = 'CNV_AttMine_'+lane
        for weight, bit in ((1000, 'AIRBORNE_TARGET'), (2000, 'VEHICLE_ATTACHED'),
                            (4000, 'SPECIAL_ARMOR_ACTIVE')):
            if bit != 'SPECIAL_ARMOR_ACTIVE':
                t.scripts[0].do.append(('UNIT_CHANGE_OBJECT_STATUS', parent, bit, 1))
            t.scripts.append(Script('Test - gate '+lane+bit,
                [('NAMED_NOT_DESTROYED', parent), ('UNIT_HAS_OBJECT_STATUS', parent, status(bit))],
                [('INCREMENT_COUNTER', weight, c)]))
    t.expect = [(label, 12, '==', value, 14) for (_, label), value in
                zip(t.counters, (111, 110, 7110, 7110))]
    return t


MISSION = {'engine_attachmine': mission}
CHECKS = {'engine_attachmine': {'a': check, 'b': all_forbidden}}
