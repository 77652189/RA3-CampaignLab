"""Native Terror Drone AttachNugget: retained/deleted nugget x live/killed parent.

PREDICT before14s 127/127/3/3, late20s 127007/127000/3006/3002.
Before packed bits: child ATTACHED64, parent VEHICLE_ATTACHED32,
parent BOOBY_TRAPPED16, child ENCLOSED8/UNATTACKABLE4, childAlive2,
parentAlive1. Late adds parentAlive4/childAlive2/live-parent attached1;
before is multiplied by1000. Dead objects' status is never queried late.
Parent NAMED_KILL at16s distinguishes native DIE_WHEN_PARENT_DIES_FROM_NOT_ME
from the simple module's surviving child. Normal damage and exact death frame
remain gaps. The native host, melee weapon and AttachUpdate are preserved;
only the negative controls remove AttachNugget. Target HP is100000 to keep
native internal damage from killing it before the scripted comparison.
MEASURED2026-11-15: retained/deleted x live/killed reads127/127/3/3
at14s; final127007/127000/3006/3002, PASS. First launch stopped in
mode selection (no samples); unchanged --no-build restart reached the map.
See work/re/c_attachterror_report.md. These snapshots do not publish the
first dispatch position/frame, damage source or parent-death notification;
complex filter and module handling remain gaps, not whole-item promotion.
"""
import re
from pathlib import Path

from checks.engine_missile import SAGE, target
from maps import probe_range
from model import status
from parts import Mission, Script, Test, Unit

LANES = ('base', 'high', 'order', 'removed')
VALUES = (127007, 127000, 3006, 3002)


def mission():
    root = Path(SAGE)
    native = (root/'Soviet/Units/SovietScoutVehicle.xml').read_text(encoding='utf-8')
    source = 'SovietScoutVehicleMeleeAttachWeapon'
    weapons = (root/'GlobalData/Weapon.xml').read_text(encoding='utf-8')
    weapon = re.search(r'<WeaponTemplate\s+id="'+source+r'".*?</WeaponTemplate>', weapons, re.S).group()
    m = Mission(name='CampAttTerror', map=probe_range, units=[], facts={})
    for lane in LANES:
        uid, wid = 'CNV_AttTerror'+lane.title(), 'CNV_AttTerrorGun'+lane.title()
        xml = native.replace('id="SovietScoutVehicle"', f'id="{uid}"', 1)
        xml = xml.replace(f'Template="{source}"', f'Template="{wid}"')
        w = weapon.replace(f'id="{source}"', f'id="{wid}"', 1)
        if lane in ('order', 'removed'):
            w, n = re.subn(r'<AttachNugget\b.*?</AttachNugget>', '', w, flags=re.S)
            assert n == 1
        xml = xml.replace('</AssetDeclaration>', w+'</AssetDeclaration>')
        victim = target('CNV_AttTerrorParent'+lane.title(), health=100000)
        m.units.extend((Unit(uid, xml, link=['WeaponTemplate:'+wid]), victim))
        m.put(uid, lane+' gun', side='p1', angle=1.5708, name='Terror '+lane+' child')
        m.put(victim.id, lane+' gun', 0, 120, side='s1', angle=4.7124,
              name='Terror '+lane+' parent')
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for phase, at in (('Fire', 6.), ('Before', 14.), ('Kill', 16.), ('Late', 20.)):
        start.append(('SET_MILLISECOND_TIMER', 'AttTerror '+phase, at))
    fire = []
    for lane in LANES:
        child, parent = ['Terror '+lane+' '+role for role in ('child', 'parent')]
        c = 'CNV_AttTerror_'+lane
        t.counters.append((c, lane+' terror packed'))
        start.extend(('UNIT_CHANGE_OBJECT_STATUS', who, 'NO_ATTACK', 1) for who in (child, parent))
        fire.extend((('UNIT_CHANGE_OBJECT_STATUS', child, 'NO_ATTACK', 0),
                     ('NAMED_ATTACK_NAMED', child, parent)))
        before = ((64, child, 'ATTACHED'), (32, parent, 'VEHICLE_ATTACHED'),
                  (16, parent, 'BOOBY_TRAPPED'), (8, child, 'ENCLOSED'),
                  (4, child, 'UNATTACKABLE'))
        for weight, who, bit in before:
            t.scripts.append(Script('Test - before '+lane+bit,
                [('TIMER_EXPIRED', 'AttTerror Before'), ('FLAG', 'AttTerror sampled Before', 0),
                 ('NAMED_NOT_DESTROYED', who), ('UNIT_HAS_OBJECT_STATUS', who, status(bit))],
                [('INCREMENT_COUNTER', 1000*weight, c)]))
        for phase, multiplier, lives in (('Before', 1000, ((2, child), (1, parent))),
                                          ('Late', 1, ((2, child), (4, parent)))):
            for weight, who in lives:
                t.scripts.append(Script('Test - alive '+phase+who,
                    [('TIMER_EXPIRED', 'AttTerror '+phase), ('FLAG', 'AttTerror sampled '+phase, 0),
                     ('NAMED_NOT_DESTROYED', who)], [('INCREMENT_COUNTER', multiplier*weight, c)]))
        t.scripts.append(Script('Test - late parent '+lane,
            [('TIMER_EXPIRED', 'AttTerror Late'), ('FLAG', 'AttTerror sampled Late', 0),
             ('NAMED_NOT_DESTROYED', parent), ('UNIT_HAS_OBJECT_STATUS', parent, status('VEHICLE_ATTACHED'))],
            [('INCREMENT_COUNTER', 1, c)]))
    for phase in ('Before', 'Late'):
        t.scripts.append(Script('Test - close '+phase, [('TIMER_EXPIRED', 'AttTerror '+phase)],
                               [('SET_FLAG', 'AttTerror sampled '+phase, 1)]))
    t.scripts.insert(0, Script('Test - start', [], start))
    t.scripts.extend((Script('Test - fire', [('TIMER_EXPIRED', 'AttTerror Fire')], fire),
                      Script('Test - kill', [('TIMER_EXPIRED', 'AttTerror Kill')],
                             [('NAMED_KILL', 'Terror '+lane+' parent') for lane in ('high', 'removed')])))
    t.expect = [(label, 22, '==', value, 24) for (_, label), value in zip(t.counters, VALUES)]
    t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
    return t


MISSION = {'engine_attachterror': mission}
CHECKS = {'engine_attachterror': {'a': check}}
