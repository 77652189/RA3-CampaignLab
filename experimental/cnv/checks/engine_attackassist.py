"""E144: isolate AttackAssistResponseBehavior's named secondary-weapon response.

Two prism notification sources attack enemy Hammers at 300. Each has a friendly
responder 250 behind it (enemy outside the responder's primary range). Only
the first responder has the requested response module. Its secondary weapon
is an allied MAGIC damage marker, rather than retail's prism modifier.
Prediction: both enemy targets lose HP; only the source with a response loses
HP. This probes dispatch, not retail tower buffs, arbitration or exact timing.

E144's two starts crashed; this recipe enters (11-21): the sources fire, no
marker reaches either source -- a negative baseline (engine_attackassist.readings.toml).
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted
from benches.weapon.firing.checks import engine_missile
missile = engine_missile()["shared"]
target = missile.target
TARGET_ID = missile.TARGET_ID
_sub1 = missile._sub1


def tower(uid):
    native = 'AlliedBaseDefenseAdvanced'
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (native + '.xml')).read_text(encoding='utf-8')
    xml = _sub1(xml, f'id="{native}"', f'id="{uid}"')
    xml = _sub1(xml, f'EditorName="{native}"', f'EditorName="{uid}"')
    return Unit(uid, xml)


def mission():
    return Mission(name='CampAssist', map=probe_range, units=[target()])


def probe(m):
    t = Test()
    starts = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
              ('PLAYER_SET_BASE_POWER', m.player('p1'), 1000),
              ('SET_MILLISECOND_TIMER', 'Assist order', 8.0),
              ('SET_MILLISECOND_TIMER', 'Assist stop', 12.0)]
    orders, stops = [], []
    for lane, site, enabled in (('on', 'base gun', True), ('off', 'order gun', False)):
        source_id, response_id = 'CNV_AssistSource' + lane, 'CNV_AssistResponse' + lane
        source = tower(source_id)
        # Keep retail primary's one-second preattack window for notifications.
        source.xml, n = re.subn(r'(<ActiveBody\b[^>]*\bMaxHealth=")[^"]+',
                                r'\g<1>10000', source.xml)
        assert n == 1, n
        source.xml, n = re.subn(r'<NotifyWhenAttackingBehavior\b.*?</NotifyWhenAttackingBehavior>', f'''
            <NotifyWhenAttackingBehavior id="ModuleTag_AssistNotify" NotifyRadius="500"
                SleepTime="0.1s" MaxFriendsToNotify="1"
                AssistResponseModuleId="ModuleTag_AttackAssistResponse">
                <AcceptableFriends Rule="NONE" Relationship="ALLIES">
                    <IncludeThing>{response_id}</IncludeThing>
                </AcceptableFriends>
            </NotifyWhenAttackingBehavior>''', source.xml, flags=re.S)
        assert n == 1, n
        marker_id = response_id + 'Marker'
        marker = f'''<WeaponTemplate id="{marker_id}" AttackRange="500" WeaponSpeed="999999"
            RadiusDamageAffects="ALLIES" RequiredAntiMask="ANTI_STRUCTURE" ClipSize="1" AutoReloadsClip="AUTO">
            <PreAttackDelay MinSeconds="0s" MaxSeconds="0s"/>
            <FiringDuration MinSeconds="0s" MaxSeconds="0s"/>
            <ClipReloadTime MinSeconds="10s" MaxSeconds="10s"/>
            <Nuggets><DamageNugget Damage="100" DamageType="MAGIC" DeathType="NORMAL"/></Nuggets>
            </WeaponTemplate>'''
        response = tower(response_id)
        response.xml, n = re.subn(r'<NotifyWhenAttackingBehavior\b.*?</NotifyWhenAttackingBehavior>',
                                  '', response.xml, flags=re.S)
        assert n == 1, n
        response.xml = _sub1(response.xml, '</AssetDeclaration>', marker + '</AssetDeclaration>')
        response.xml = _sub1(response.xml, 'Template="AlliedBaseDefenseAdvancedPrismLink"',
                            f'Template="{marker_id}"')
        if not enabled:
            response.xml, n = re.subn(r'<AttackAssistResponseBehavior\b[^>]*/>', '', response.xml)
            assert n == 1, n
        response.link.append('WeaponTemplate:' + marker_id)
        m.units += [source, response]
        names = [f'UNIT - Assist {lane} {role}' for role in ('source', 'response', 'target')]
        for template, name, distance, side in (
                (source_id, names[0], 0, 'p1'), (response_id, names[1], -250, 'p1'),
                (TARGET_ID, names[2], 300, 's1')):
            m.put(template, site, 0, distance, side=side, role=name, name=name)
        starts += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in (names[0], names[2])]
        orders += [('UNIT_CHANGE_OBJECT_STATUS', names[0], 'NO_ATTACK', 0),
                   ('NAMED_ATTACK_NAMED', names[0], names[2])]
        stops += [('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1) for name in names[:2]]
        for role, name in (('source', names[0]), ('target', names[2])):
            label = lane + ' ' + role
            counted('CNV_Assist_' + lane + role, label, t, health=name)
            t.expect.append((label, 1, '==', 100, 5))
            t.expect.append((label, 15, '<' if role == 'target' or enabled else '==', 100, 19))
    t.scripts = [Script('Test - Assist setup', [], starts),
                 Script('Test - Assist order', [('TIMER_EXPIRED', 'Assist order')], orders),
                 Script('Test - Assist stop', [('TIMER_EXPIRED', 'Assist stop')], stops)] + t.scripts
    t.bench = [('bench_watch', dict(seconds=19, every=1, sheet=False, lines=4))]
    return t


def retail(m, hushed=False):
    """Check b, as retail plays it: towers auto-acquire (no script attack), retail weapons. Each lane's source is
    retail's prism tower with the target 300 north (its 350 range); 250 south stands retail's tower (on) or the same
    without AttackAssistResponseBehavior (off; not an AcceptableFriend either). Data prediction: on's link (+50 %
    damage for 2 s per link) makes its target lose HP about 1.5x as fast as off's. Check c (hushed; review xx #5): on's
    mate holds NO_ATTACK from the start -- prediction: it links nothing, on's target ends like off's."""
    t = Test()
    quiet = tower('CNV_AssistQuiet')
    for block in (r'<AttackAssistResponseBehavior\b[^>]*/>',      # its notifier too: one naming a response module
                  r'<NotifyWhenAttackingBehavior\b.*?</NotifyWhenAttackingBehavior>'):   # its host lacks crashes (E144)
        quiet.xml, n = re.subn(block, '', quiet.xml, flags=re.S)
        assert n == 1, n
    m.units.append(quiet)
    starts = [('MAP_REVEAL_ALL_PERM', m.player('p1')), ('PLAYER_SET_BASE_POWER', m.player('p1'), 1000)]
    # review xx #4: '<100' for both passed without the on lane's responder (71 / 71); on must end below off's floor
    for lane, site, mate, op, bound in (('on', 'base gun', 'AlliedBaseDefenseAdvanced', '>=' if hushed else '<=',
                                         64 if hushed else 62), ('off', 'order gun', quiet.id, '>=', 64)):
        for template, role, dy, side in (('AlliedBaseDefenseAdvanced', 'source', 0, 'p1'), (mate, 'mate', -250, 'p1'),
                                         (TARGET_ID, 'target', 300, 's1')):
            name = f'UNIT - Assist {lane} {role}'
            m.put(template, site, 0, dy, side=side, role=name, name=name)
            if role == 'target' or hushed and (lane, role) == ('on', 'mate'):
                starts.append(('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1))
            if role == 'target':
                counted('CNV_Assist_' + lane, lane + ' target', t, health=name)
                t.expect += [(lane + ' target', 10, '<', 100, 30), (lane + ' target', 28, op, bound, 31)]
    t.scripts = [Script('Test - Assist setup', [], starts)] + t.scripts
    t.bench = [('bench_watch', dict(seconds=31, every=1, sheet=False, lines=2))]
    return t


MISSION = {'engine_attackassist': mission}
CHECKS = {'engine_attackassist': {'a': probe, 'b': retail, 'c': lambda m: retail(m, True)}}
