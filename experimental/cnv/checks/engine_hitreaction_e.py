"""E172: shielded retail Peacekeeper versus HitReactionBehavior removal.

Prediction: the original may turn to its damage source / play HIT_REACTION;
the removal control must receive the same legal shield toggle and gun hit.
The four HUD lines verify that prerequisite, not the module's effect: frame,
two health percentages, and decimal flags (toggle 1/10, hit 100/1000,
alive in starting area 10000/100000). Freeze at frame 180. No zero
difference in health or position establishes that this module is cosmetic.
Run a retains its failed diagnostic: reversed post-hit comparator and HP
sampling continuing after clock freeze. Run b fixes both and observes the
existing UNIT_HAS_MODELCONDITION interface directly. Its gate uses bits:
toggle 1/2, legal hit 4/8, final live position 16/32, ever HIT_REACTION
64/128, clear at frame 180 256/512. Prediction b = 895, not a fitted value.
Exact reaction expiry remains unmeasured.

Build r reads the facing (RotateToSourceWhenDamaged) through the shield's
armour: AlliedAntiInfantryInfantryRiotArmor takes GUN at 20 % but x5 from
the rear. The victims face west with the Conscript behind them, which fires
f60-f90 (campaign AK 4 a shot): a victim that turns to its source after the
first hit takes 0.8 a shot after it, one that does not 4 a shot. Gate: toggle
1/2, alive at f180 4/8.
"""
import math
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, square, status


def mission(name='CampHitReactE', facing=1.570796):
    m = Mission(name=name, map=probe_range, units=[])
    source = (Path(labpaths.SDK3) / 'SageXML/Allied/Units/AlliedAntiInfantryInfantry.xml').read_text(encoding='utf-8-sig')
    for tag, dy in [('On', 0), ('Off', 300)]:
        ident = 'CNVE172' + tag
        xml = source.replace('id="AlliedAntiInfantryInfantry"', f'id="{ident}"', 1)
        for key, value in re.findall(r'<Define\s+name="([^"]+)"\s+value="([^"]+)"\s*/>', xml):
            xml = xml.replace('$' + key, value)
        xml = re.sub(r'<Defines>.*?</Defines>', '', xml, flags=re.S)
        if tag == 'Off':
            xml, n = re.subn(r'<HitReactionBehavior\b.*?</HitReactionBehavior>', '', xml, flags=re.S)
            assert n == 1
        u = Unit(ident, xml)
        u.abilities = {'shield': 'Command_ToggleRiotShieldSpecialPower'}
        m.units.append(u)
        # Idle victims (north-facing; west-facing in r); damage comes from the east.
        m.put(ident, 'base gun', 0, dy, role=tag, name='E172 ' + tag, angle=facing)
        m.put('SovietAntiInfantryInfantry', 'base gun', 75, dy, side='s1',
              role=tag + ' gun', name='E172 ' + tag + ' gun', angle=3.141593)
        m.waypoint('start ' + tag, 'E172 Start ' + tag, 'base gun', 0, dy)
    return m


def check(m, corrected=False):
    t = Test()
    t.counters = [('E172Frame', '完成帧'), ('E172OnHP', '原版血量'),
                  ('E172OffHP', '删模块血量'), ('E172Gate', '前置位')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E172Frame', 0, 180)],
                        [('INCREMENT_COUNTER', 1, 'E172Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, weight in [('On', 1), ('Off', 2 if corrected else 10)]:
        victim, gun = m.role(tag).name, m.role(tag + ' gun').name
        area = 'E172 Start ' + tag
        t.areas[area] = square(*m.point('start ' + tag), 35)
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', victim, status('NO_ATTACK'), 1),
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
            Script('Test - shield ' + tag, [('COUNTER', 'E172Frame', 2, 30)], [
                ('NAMED_USE_COMMANDBUTTON_ABILITY', victim, m.ability(tag, 'shield'))]),
            Script('Test - toggle ' + tag, [('COUNTER', 'E172Frame', 2, 60),
                ('UNIT_HAS_OBJECT_STATUS', victim, status('GENERIC_TOGGLE_STATE'))],
                [('INCREMENT_COUNTER', weight, 'E172Gate')]),
            Script('Test - attack ' + tag, [('COUNTER', 'E172Frame', 2, 75)], [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', gun, victim)]),
            Script('Test - hit ' + tag, [('COUNTER', 'E172Frame', 3 if corrected else 1, 75),
                ('NAMED_NOT_DESTROYED', victim), ('UNIT_HEALTH', victim, 0, 100),
                ('NAMED_ATTACKED_BY_OBJECTTYPE', victim, 'SovietAntiInfantryInfantry')], [
                ('INCREMENT_COUNTER', (4 if corrected else 100) * weight, 'E172Gate'),
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
            Script('Test - hp ' + tag, [('COUNTER', 'E172Frame', 2 if corrected else 0, 180 if corrected else 181)], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, 'E172' + tag + 'HP')], once=corrected),
            Script('Test - position ' + tag, [('COUNTER', 'E172Frame', 2, 180),
                ('NAMED_NOT_DESTROYED', victim), ('NAMED_INSIDE_AREA', victim, area)],
                [('INCREMENT_COUNTER', (16 if corrected else 10000) * weight, 'E172Gate')])]
        if corrected:
            reaction = ('UNIT_HAS_MODELCONDITION', victim, 'HIT_REACTION')
            t.scripts += [
                Script('Test - reaction ' + tag, [('COUNTER', 'E172Frame', 3, 75), reaction],
                       [('INCREMENT_COUNTER', 64 * weight, 'E172Gate')]),
                Script('Test - clear ' + tag, [('COUNTER', 'E172Frame', 2, 180),
                       ('NAMED_NOT_DESTROYED', victim), reaction + ('NOT',)],
                       [('INCREMENT_COUNTER', 256 * weight, 'E172Gate')])]
    t.expect = [('完成帧', 0, 'ever==', 180), ('前置位', 0, 'ever==', 895 if corrected else 111111)]
    t.bench = [('bench_camera', dict(x=850, y=550, look=False)),
               ('bench_watch', dict(seconds=65, every=1, sheet=False, lines=4))]
    return t


def check_rear(m):
    """Build r: the Conscript fires f60-f90 into both victims' backs; HP at f180."""
    t = Test()
    t.counters = [('E172Frame', '完成帧'), ('E172OnHP', '原版血量'),
                  ('E172OffHP', '删模块血量'), ('E172Gate', '前置位')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E172Frame', 0, 180)],
                        [('INCREMENT_COUNTER', 1, 'E172Frame')], once=False),
                 Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, weight in [('On', 1), ('Off', 2)]:
        victim, gun = m.role(tag).name, m.role(tag + ' gun').name
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', victim, status('NO_ATTACK'), 1),
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
            Script('Test - shield ' + tag, [('COUNTER', 'E172Frame', 2, 30)], [
                ('NAMED_USE_COMMANDBUTTON_ABILITY', victim, m.ability(tag, 'shield'))]),
            Script('Test - toggle ' + tag, [('COUNTER', 'E172Frame', 2, 59),
                ('UNIT_HAS_OBJECT_STATUS', victim, status('GENERIC_TOGGLE_STATE'))],
                [('INCREMENT_COUNTER', weight, 'E172Gate')]),
            Script('Test - attack ' + tag, [('COUNTER', 'E172Frame', 2, 60)], [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 0),
                ('NAMED_ATTACK_NAMED', gun, victim)]),
            Script('Test - cease ' + tag, [('COUNTER', 'E172Frame', 2, 90)], [
                ('UNIT_CHANGE_OBJECT_STATUS', gun, status('NO_ATTACK'), 1)]),
            Script('Test - hp ' + tag, [('COUNTER', 'E172Frame', 2, 180)], [
                ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', victim, 'E172' + tag + 'HP')]),
            Script('Test - alive ' + tag, [('COUNTER', 'E172Frame', 2, 180), ('NAMED_NOT_DESTROYED', victim)],
                   [('INCREMENT_COUNTER', 4 * weight, 'E172Gate')])]
    t.expect = [('完成帧', 0, 'ever==', 180), ('前置位', 0, 'ever==', 15)]
    t.bench = [('bench_camera', dict(x=850, y=550, look=False)),
               ('bench_watch', dict(seconds=50, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_hitreaction_e': mission, 'engine_hitreaction_r': lambda: mission('CampHitReactR', math.pi)}
CHECKS = {'engine_hitreaction_e': {'a': check, 'b': lambda m: check(m, corrected=True)},
          'engine_hitreaction_r': {'r': check_rear}}
CONTROL_ARMS = {'engine_hitreaction_e': ('On', 'Off'), 'engine_hitreaction_r': ('On', 'Off')}
