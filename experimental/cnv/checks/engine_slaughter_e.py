"""E170: carrier SlaughterHordeContain removal, natural drone sortie/return.

Prediction (INFERRED): both carriers launch three drones; after their named
victims are deleted the retail carrier consumes returning drones, while the
removal control retains them. Counts are living drones per owner, not parking
slots or parent identity. Freeze at script frames 180 and 600. No AI tactical
result is used as container evidence. Unmeasured lifecycle details stay gaps.
"""
import re
from pathlib import Path
import labpaths


from checks.engine_modulebatch import native
from maps import infiltrator_batch
from parts import Mission, Script, Test, Unit, kindof, square


def mission():
    m = Mission(name='CampSlaughterE', map=infiltrator_batch, units=[])
    for tag, side, dx in [('On', 'p1', -1800), ('Off', 's1', 0)]:
        ident = 'CNVE170' + tag
        xml = native('AlliedAntiStructureShip', 'Units', ident).xml
        # The included render states consume local defines too; expand them
        # before cloning so the two files do not share compiler globals.
        sage = Path(labpaths.SDK3) / 'SageXML'
        states = (sage / 'Includes/SpecialModelStates.xml').read_text(encoding='utf-8-sig')
        states = states[states.index('>') + 1:states.rindex('</SpecialModelStates>')]
        original = (sage / 'Allied/Units/AlliedAntiStructureShip.xml').read_text(encoding='utf-8-sig')
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', original):
            states = states.replace('=$' + key, value).replace('$' + key, value)
        xml, count = re.subn(r'<xi:include\s+href="DATA:Includes/SpecialModelStates.xml".*?/>', states, xml, flags=re.S)
        assert count == 1
        if tag == 'Off':
            xml, count = re.subn(r'<SlaughterHordeContain\b.*?</SlaughterHordeContain>', '', xml, flags=re.S)
            assert count == 1
        m.units.append(Unit(ident, xml))
        m.put(ident, 'ship', dx, 0, side=side, role=tag + ' host', name='E170 ' + tag + ' host')
        m.put('SovietAntiAirShip', 'ship', dx, 500, side='s1' if side == 'p1' else 'p1',
              role=tag + ' target', name='E170 ' + tag + ' target')
    m.spawns.add('AlliedAttackDrone')
    return m


def check(m, corrected=False):
    t = Test()
    t.areas['E170All'] = square(2500, 2500, 2700)
    t.counters = [('E170Frame', '完成帧'), ('E170Hosts', '宿主存活'),
                  ('E170Attack', '攻击期数量'), ('E170Return', '返航后数量')]
    t.scripts = [Script('Test - frame', [('COUNTER', 'E170Frame', 0, 600)],
                        [('INCREMENT_COUNTER', 1, 'E170Frame')], once=False),
                 Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, side, weight in [('On', 'p1', 1), ('Off', 's1', 10)]:
        host, victim = m.role(tag + ' host').name, m.role(tag + ' target').name
        t.scripts += [Script('Test - quiet ' + tag, [], [
            ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 1),
            ('UNIT_CHANGE_OBJECT_STATUS', victim, 'NO_ATTACK', 1),
            ('UNIT_SET_HEALTH', victim, 100)]),
            Script('Test - heal ' + tag, [('NAMED_NOT_DESTROYED', victim)], [('UNIT_SET_HEALTH', victim, 100)], once=False),
            Script('Test - attack ' + tag, [('COUNTER', 'E170Frame', 2, 60)], [
                ('UNIT_CHANGE_OBJECT_STATUS', host, 'NO_ATTACK', 0),
                ('NAMED_ATTACK_NAMED', host, victim)]),
            Script('Test - remove victim ' + tag, [('COUNTER', 'E170Frame', 2, 240)], [('NAMED_DELETE', victim)]),
            Script('Test - alive ' + tag, [('COUNTER', 'E170Frame', 2, 600), ('NAMED_NOT_DESTROYED', host)],
                   [('INCREMENT_COUNTER', weight, 'E170Hosts')])]
        for frame, counter in [(180, 'E170Attack'), (600, 'E170Return')]:
            for n in range(1, 10):
                t.scripts.append(Script(f'Test - count {tag} {frame} {n}', [
                    ('COUNTER', 'E170Frame', 2, frame),
                    ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA', m.player(side), 2, n, kindof('AIRCRAFT' if corrected else 'DRONE'), 'E170All')],
                    [('INCREMENT_COUNTER', weight * n, counter)]))
    t.expect = [('完成帧', 0, 'ever==', 600), ('宿主存活', 0, 'ever==', 11),
                ('攻击期数量', 0, 'ever==', 55 if corrected else 33),
                ('返航后数量', 0, 'ever==', 50 if corrected else 30)]
    # Run a's DRONE meter cannot see AlliedAttackDrone (retail KindOf is AIRCRAFT).
    # Run b changes only the meter. ClipSize=5/OCL Count=1 predicts five sorties;
    # this remains a prediction, not a fitted observation.
    t.bench = ([('bench_camera', dict(x=2000, y=3400, look=False))] if corrected else []) + [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_slaughter_e': mission}
CHECKS = {'engine_slaughter_e': {'a': check, 'b': lambda m: check(m, corrected=True)}}
# Each arm's drones are counted by its own player, so the hosts (and targets) swap sides: a confound, held here
# as the one freedom; both arms read 0 (a negative baseline). Put both on p1 and count by area when E170 reopens.
CONTROL_ARMS = {'engine_slaughter_e': ('On', 'Off', 'side')}
