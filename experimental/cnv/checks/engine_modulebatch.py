"""E145: three object modules on one plate, with independent controls.

CommandSetUpgrade: identical barracks start with an empty menu. Only 'on'
has the upgrade module. Press the new build command before and after giving
both hosts Tech2. Predict products on/off = 0/0 before, 1/0 after.
MonitorSpecialPowerTimerUpdate: identical particle cannons with/without the
monitor. Force their power ready, then busy. Predict ready bits 1/0 then 0/0.
PassiveAreaEffectBehavior: retail engineer healing with MaxBeneficiaries=1
versus unlimited. Three wounded infantry and an enemy stand in each radius.
Predict early healed counts 1/3, enemy HP 50/50. This is not a survey-clock
measurement. No full-module coverage is claimed by this recipe alone.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted

POWER = 'SpecialPowerParticleCannon'
UPGRADE = 'Upgrade_AlliedTech2'


def native(name, folder, ident):
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied' / folder / (name + '.xml')).read_text(encoding='utf-8-sig')
    xml, n = re.subn(r'\bid="' + name + '"', 'id="' + ident + '"', xml, count=1)
    assert n == 1
    xml = xml.replace('EditorName="' + name + '"', 'EditorName="' + ident + '"')
    # Local SDK constants share the compiler namespace across cloned files.
    for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
        xml = xml.replace('$' + key, value)
    xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
    return Unit(ident, xml)


def mission():
    m = Mission(name='CampModulesE', map=probe_range, units=[])
    for tag, site, enabled in (('on', 'base gun', True), ('off', 'order gun', False)):
        factory = native('AlliedBarracks', 'Structures', 'CNVBatchFactory' + tag)
        product = native('AlliedEngineer', 'Units', 'CNVBatchProduct' + tag)
        empty, menu, command = ['CNVBatch' + x + tag for x in ('Empty', 'Menu', 'Build')]
        factory.xml = factory.xml.replace('CommandSet="AlliedBarracksCommandSet"', f'CommandSet="{empty}"')
        if enabled:
            factory.xml = factory.xml.replace('</Behaviors>', f'''
                <CommandSetUpgrade id="ModuleTag_BatchMenu" CommandSet="{menu}">
                    <TriggeredBy>{UPGRADE}</TriggeredBy>
                </CommandSetUpgrade></Behaviors>''')
        assets = f'''<LogicCommandSet id="{empty}"/>
            <LogicCommandSet id="{menu}"><Cmd>{command}</Cmd></LogicCommandSet>
            <LogicCommand id="{command}" Type="UNIT_BUILD"><Object>{product.id}</Object></LogicCommand>'''
        factory.xml = factory.xml.replace('</AssetDeclaration>', assets + '</AssetDeclaration>')
        factory.link += ['LogicCommandSet:' + empty, 'LogicCommandSet:' + menu, 'LogicCommand:' + command]
        factory.abilities = {'build': command}
        m.units += [factory, product]
        m.spawns.add(product.id)
        m.put(factory.id, site, role='factory ' + tag, name='Batch Factory ' + tag)
    for tag, dx, enabled in (('on', 0, True), ('off', 500, False)):
        cannon = native('AlliedSuperWeaponAdvanced', 'Structures', 'CNVBatchMonitor' + tag)
        if not enabled:
            cannon.xml, n = re.subn(r'<MonitorSpecialPowerTimerUpdate\b[^>]*/>', '', cannon.xml)
            assert n == 1
        cannon.abilities = {'power': POWER}
        m.units.append(cannon)
        m.put(cannon.id, 'high gun', dx, 0, role='monitor ' + tag, name='Batch Monitor ' + tag)
    for tag, site, cap in (('one', 'switch gun', 1), ('all', 'low gun', 0)):
        healer = native('AlliedEngineer', 'Units', 'CNVBatchHealer' + tag)
        healer.xml, n = re.subn(r'(<PassiveAreaEffectBehavior\b)',
                               r'\1 MaxBeneficiaries="' + str(cap) + '"', healer.xml)
        assert n == 1
        m.units.append(healer)
        m.put(healer.id, site, role='healer ' + tag, name='Batch Healer ' + tag)
        for i, (dx, dy) in enumerate(((-45, 35), (0, 65), (45, 35), (0, -65))):
            role = f'{tag} target {i}'
            m.put('AlliedAntiInfantryInfantry', site, dx, dy,
                  side='s1' if i == 3 else 'p1', role=role, name='Batch ' + role)
    return m


def check(m):
    t = Test()
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1')),
             ('PLAYER_SET_BASE_POWER', m.player('p1'), 1000),
             ('PLAYER_SET_MONEY', m.player('p1'), 10000)]
    phases = {2: [], 8: [], 20: []}
    for tag in ('on', 'off'):
        factory = m.role('factory ' + tag).name
        button = m.ability('factory ' + tag, 'build')
        phases[2].append(('NAMED_USE_COMMANDBUTTON_ABILITY', factory, button))
        phases[8] += [('NAMED_RECEIVE_UPGRADE', UPGRADE, factory),
                      ('NAMED_USE_COMMANDBUTTON_ABILITY', factory, button)]
        counted('CNV_BatchProduct' + tag, 'products ' + tag, t,
                template='CNVBatchProduct' + tag, most=2)
        t.expect += [('products ' + tag, 4, '==', 0, 6),
                     ('products ' + tag, 30, '==', int(tag == 'on'), 34)]
        holder = m.role('monitor ' + tag).name
        phases[8].append(('NAMED_SET_SPECIAL_POWER_COUNTDOWN', holder, POWER, 0))
        phases[20].append(('NAMED_SET_SPECIAL_POWER_COUNTDOWN', holder, POWER, 10000))
        counter, label = 'CNV_BatchReady' + tag, 'ready ' + tag
        t.counters.append((counter, label))
        t.scripts += [Script('Test - zero ' + label, [], [('SET_COUNTER', counter, 0)], once=False),
                      Script('Test - read ' + label, [('UNIT_HAS_MODELCONDITION', holder, 'SPECIALPOWER1_READY')],
                             [('SET_COUNTER', counter, 1)], once=False)]
        t.expect += [(label, 12, '==', int(tag == 'on'), 17), (label, 25, '==', 0, 34)]
    for tag in ('one', 'all'):
        healer = m.role('healer ' + tag).name
        start.append(('UNIT_CHANGE_OBJECT_STATUS', healer, 'NO_ATTACK', 1))
        phases[8].append(('UNIT_CHANGE_OBJECT_STATUS', healer, 'GENERIC_TOGGLE_STATE', 1))
        counter, label = 'CNV_BatchHealed' + tag, 'healed ' + tag
        t.counters.append((counter, label))
        t.scripts.append(Script('Test - clear ' + tag, [], [('SET_COUNTER', counter, 0)], once=False))
        for i in range(4):
            name = m.role(f'{tag} target {i}').name
            start.append(('UNIT_CHANGE_OBJECT_STATUS', name, 'NO_ATTACK', 1))
            phases[8].append(('UNIT_SET_HEALTH', name, 50.0))
            if i < 3:
                t.scripts.append(Script(f'Test - healed {tag}{i}', [('UNIT_HEALTH', name, 4, 50)],
                                        [('INCREMENT_COUNTER', 1, counter)], once=False))
            else:
                counted('CNV_BatchEnemy' + tag, 'enemy ' + tag, t, health=name)
                t.expect.append(('enemy ' + tag, 10, '==', 50, 34))
        t.expect.append((label, 10, '==', 1 if tag == 'one' else 3, 11))
    for at, actions in phases.items():
        timer = f'Batch phase {at}'
        start.append(('SET_MILLISECOND_TIMER', timer, float(at)))
        t.scripts.append(Script(timer, [('TIMER_EXPIRED', timer)], actions))
    t.scripts.insert(0, Script('Test - batch setup', [], start))
    # Four HUD lines: decimal digits retain each independent lane. The other
    # counters remain script-local inputs, never extra DISPLAY_COUNTER lines.
    hidden = {label: counter for counter, label in t.counters}
    t.counters = []
    for family, lanes, maximum in (('products', ('on', 'off'), 2),
                                    ('ready', ('on', 'off'), 1),
                                    ('healed', ('one', 'all'), 3),
                                    ('enemy', ('one', 'all'), 100)):
        counter = 'CNV_BatchPacked' + family
        t.counters.append((counter, family))
        t.scripts.append(Script('Test - pack zero ' + family, [], [('SET_COUNTER', counter, 0)], once=False))
        for weight, lane in zip((1, 10), lanes):
            for value in ([50] if family == 'enemy' else range(1, maximum + 1)):
                t.scripts.append(Script(f'Test - pack {family} {lane} {value}',
                    [('COUNTER', hidden[family + ' ' + lane], 2, value)],
                    [('INCREMENT_COUNTER', weight if family == 'enemy' else weight * value, counter)], once=False))
    t.expect = [('products', 4, '==', 0, 6), ('products', 30, '==', 1, 34),
                ('ready', 12, '==', 1, 17), ('ready', 25, '==', 0, 34),
                ('healed', 10, '==', 31, 11), ('healed', 30, '==', 33, 34),
                ('enemy', 10, '==', 11, 34)]
    t.bench = [('bench_watch', dict(seconds=34, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_modulebatch': mission}
CHECKS = {'engine_modulebatch': {'a': check}}
