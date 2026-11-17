"""E158 RadarBehavior: isolated retail dish / module-removal HUD control.

Prediction (INFERRED, before bench): without the native PlayerSpellBook
RadarBehavior, the minimap works only with the dish's module, and stops after
the dish is deleted at 12 seconds. The second build removes only that module.
No reveal-all, radar UI toggle, or injected effect state is used. Four counters
measure frame, dish survival, support survival and sufficient power, NOT radar.
Saved full frames must be inspected for the independent minimap output.
SpellBook is linked over retail under its own id; no other radar host is placed.
This diagnostic alone does not register module coverage. See work/re/e158_radar.md.

MEASURED 2026-11-15: both prerequisites PASS. On: f151=1/1/1,
minimap terrain; f303=0/1/1, Allied emblem. Off: f149=1/1/1,
f308=0/1/1, emblem both times. Named model provider replay passes;
PLAYER_HAS_POWER script replay is a separate strict xfail.
E159 engine_radarlow:a: f147=1/1/1, f302=1/1/0; minimap terrain
in both frames. Supply/demand 150/75 -> 50/75 after plant deletion.
Only this retail dish's low-power case is measured; other hosts remain gaps.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test, Unit


def without_radar(xml):
    xml, count = re.subn(r'<RadarBehavior\b[^>]*/>', '', xml)
    assert count == 1
    return xml


def mission(enabled=True):
    m = Mission(name='CampRadarE' if enabled else 'CampRadarOffE', map=probe_range,
                facts={'radar_module': enabled})
    sage = Path(labpaths.SDK3) / 'SageXML'
    spellbook = (sage / 'System/PlayerSpellBook.xml').read_text(encoding='utf-8-sig')
    m.assets.append(('E158SpellBook.xml', without_radar(spellbook), 'GameObject:PlayerSpellBook'))
    m.replaces.append('GameObject:PlayerSpellBook')
    source = (sage / 'Allied/Structures/AlliedRadarDish.xml').read_text(encoding='utf-8-sig')
    ident = 'CNVE158Radar'
    source = source.replace('id="AlliedRadarDish"', f'id="{ident}"', 1)
    m.units.append(Unit(ident, source if enabled else without_radar(source)))
    m.put(ident, 'base gun', role='dish', name='E158 dish')
    m.put('AlliedConstructionYard', 'base gun', 0, 650, role='yard', name='E158 yard')
    m.put('AlliedPowerPlant', 'base gun', 400, 0, role='power', name='E158 power')
    return m


def check(m):
    t = Test()
    t.counters = [('E158Frame', '帧数'), ('E158Dish', '宿主量'),
                  ('E158Support', '前置量'), ('E158Power', '供电量')]
    t.scripts = [
        Script('Test - E158 start', [], [('SET_MILLISECOND_TIMER', 'E158 delete', 12.)]),
        Script('Test - E158 frame', [], [('INCREMENT_COUNTER', 1, 'E158Frame')], once=False),
        Script('Test - E158 clear', [], [('SET_COUNTER', c, 0) for c, _ in t.counters[1:]], once=False),
        Script('Test - E158 dish', [('NAMED_NOT_DESTROYED', m.role('dish').name)],
               [('SET_COUNTER', 'E158Dish', 1)], once=False),
        Script('Test - E158 support', [('NAMED_NOT_DESTROYED', m.role('yard').name),
                                      ('NAMED_NOT_DESTROYED', m.role('power').name)],
               [('SET_COUNTER', 'E158Support', 1)], once=False),
        Script('Test - E158 powered', [('PLAYER_HAS_POWER', m.player('p1'))],
               [('SET_COUNTER', 'E158Power', 1)], once=False),
        Script('Test - E158 delete', [('TIMER_EXPIRED', 'E158 delete')],
               [('NAMED_DELETE', m.role('dish').name)]),
    ]
    t.expect = [('宿主量', 5, '==', 1, 10), ('宿主量', 16, '==', 0, 20),
                ('前置量', 5, '==', 1, 20), ('供电量', 5, '==', 1, 20)]
    t.bench = [('bench_watch', dict(seconds=24, every=1, sheet=False, lines=4))]
    return t


def low_power_mission():
    """E159: retail supply 150 -> 50, demand 75; only the plant is deleted.

    INFERRED prediction: the dish lacks POWERED KindOf, so radar may remain
    available even when PLAYER_HAS_POWER becomes false. HUD decides the rule.
    SpellBook isolation is identical to E158. See work/re/e159_radar_power.md.
    """
    m = mission()
    m.name = 'CampRadarLowE'
    for i in range(3):
        m.put('AlliedBarracks', 'base gun', 650 + i * 250, 650,
              role=f'load{i}', name=f'E159 load{i}')
    return m


def low_power_check(m):
    t = check(m)
    # Preserve dish and all consumers; change only the supply at 12 seconds.
    t.scripts[-1] = Script('Test - E159 remove supply', [('TIMER_EXPIRED', 'E158 delete')],
                           [('NAMED_DELETE', m.role('power').name)])
    t.scripts[4] = Script('Test - E159 consumers',
                         [('NAMED_NOT_DESTROYED', m.role(r).name)
                          for r in ('yard', 'load0', 'load1', 'load2')],
                         [('SET_COUNTER', 'E158Support', 1)], once=False)
    t.expect = [('宿主量', 5, '==', 1, 20), ('前置量', 5, '==', 1, 20),
                ('供电量', 5, '==', 1, 10), ('供电量', 16, '==', 0, 20)]
    return t


def two_provider_mission():
    """E160: same retail providers, delete first at 12s and last at 24s.

    INFERRED prediction before bench: terrain -> terrain -> emblem.
    Independent named survival/power counters establish prerequisites; the
    saved HUD frames decide radar output. See work/re/e160_radar_multi.md.
    MEASURED: f114=1/1/1 terrain, f197=0/1/1 terrain, f386=0/0/1 emblem.
    Slow-run wall-time expectations failed; retained without widening them.
    Named logic-frame replays assert the measured lifetime and HUD instead.
    """
    m = mission()
    m.name = 'CampRadarTwoE'
    m.put('CNVE158Radar', 'base gun', -500, 0, role='second', name='E160 second')
    return m


def two_provider_check(m):
    t = check(m)
    t.counters.insert(2, ('E160Second', '第二宿主'))
    t.counters = [(c, label) for c, label in t.counters if c != 'E158Support']
    t.scripts[0].do.append(('SET_MILLISECOND_TIMER', 'E160 last', 24.))
    t.scripts[2].do.append(('SET_COUNTER', 'E160Second', 0))
    t.scripts[2].do = [a for a in t.scripts[2].do if a[1] != 'E158Support']
    t.scripts.insert(4, Script('Test - E160 second',
                              [('NAMED_NOT_DESTROYED', m.role('second').name)],
                              [('SET_COUNTER', 'E160Second', 1)], once=False))
    # Four HUD lines: the last line proves power AND both support hosts.
    support = t.scripts.pop(5)
    t.scripts[5].when.extend(support.when)
    t.scripts.append(Script('Test - E160 last', [('TIMER_EXPIRED', 'E160 last')],
                            [('NAMED_DELETE', m.role('second').name)]))
    t.expect = [('宿主量', 5, '==', 1, 10), ('宿主量', 16, '==', 0, 32),
                ('第二宿主', 5, '==', 1, 20), ('第二宿主', 28, '==', 0, 32),
                ('供电量', 5, '==', 1, 32)]
    t.bench = [('bench_watch', dict(seconds=36, every=1, sheet=False, lines=4))]
    return t


def death_mission():
    """E161: retail 500 HP dish, 250 damage at 6s, 1000 damage at 12s.

    NAMED_DAMAGE is the measured health-changing entry in engine_immortal.
    INFERRED prediction: 100 -> 50 percent while alive, then destroyed;
    terrain before the lethal hit, emblem afterwards. Retail SlowDeath has
    an 8s destruction delay: this does not predict its exact unregister frame.
    No delete, forced health, reveal, or radar toggle. See work/re/e161_radar_death.md.
    MEASURED: f87=0/100, f95/f173=0/50 (gone/HP), terrain;
    f182=1/0 HUD shutdown transition, f192/f374=1/0 emblem. Support=1.
    Queue expectations PASS; exact unregister frame remains unmeasured.
    """
    m = mission()
    m.name = 'CampRadarDeadE'
    return m


def death_check(m):
    t = Test()
    dish = m.role('dish').name
    t.counters = [('E161Frame', '帧数'), ('E161Gone', '死亡'),
                  ('E161HP', '血量'), ('E161Support', '供电前置')]
    t.scripts = [
        Script('Test - E161 start', [], [('SET_MILLISECOND_TIMER', 'E161 hurt', 6.),
                                        ('SET_MILLISECOND_TIMER', 'E161 lethal', 12.)]),
        Script('Test - E161 frame', [], [('INCREMENT_COUNTER', 1, 'E161Frame')], once=False),
        Script('Test - E161 hp', [], [('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', dish, 'E161HP')], once=False),
        Script('Test - E161 gone', [('NAMED_DESTROYED', dish)], [('SET_COUNTER', 'E161Gone', 1)]),
        Script('Test - E161 clear support', [], [('SET_COUNTER', 'E161Support', 0)], once=False),
        Script('Test - E161 support', [('PLAYER_HAS_POWER', m.player('p1')),
                                      ('NAMED_NOT_DESTROYED', m.role('yard').name),
                                      ('NAMED_NOT_DESTROYED', m.role('power').name)],
               [('SET_COUNTER', 'E161Support', 1)], once=False),
        Script('Test - E161 hurt', [('TIMER_EXPIRED', 'E161 hurt')], [('NAMED_DAMAGE', dish, 250)]),
        Script('Test - E161 lethal', [('TIMER_EXPIRED', 'E161 lethal')], [('NAMED_DAMAGE', dish, 1000)]),
    ]
    t.expect = [('血量', 0, 'ever<=', 50, 40), ('死亡', 0, 'ever>=', 1, 40),
                ('供电前置', 0, '==', 1, 40)]
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


def transfer_mission(incoming=False):
    """E162: reciprocal scripted owner transfer, NOT engineer capture.

    INFERRED prediction: outgoing local HUD terrain -> emblem; incoming
    emblem -> terrain. Both owners retain live yards/plants and power.
    Two runs observe the local HUD as old and new owner respectively;
    no claim about the unobserved Soviet_4 HUD. See work/re/e162_radar_owner.md.
    MEASURED: out f91 owner1 terrain -> f312 owner2 emblem;
    in f87 owner2 emblem -> f282 owner1 terrain; alive/support=1 throughout.
    Exact transfer callback timing and engineer capture remain gaps.
    """
    m = mission()
    m.name = 'CampRadarInE' if incoming else 'CampRadarOutE'
    m.facts['incoming'] = incoming
    if incoming:
        m.objects[0].side = 's4'
        m.cast['dish'].side = 's4'
    m.put('AlliedConstructionYard', 'high gun', 0, 650, side='s4',
          role='other yard', name='E162 other yard')
    m.put('AlliedPowerPlant', 'high gun', 400, 0, side='s4',
          role='other power', name='E162 other power')
    return m


def transfer_check(m):
    t = Test()
    dish = m.role('dish').name
    t.counters = [('E162Frame', '帧数'), ('E162Owner', '归属量'),
                  ('E162Alive', '存活量'), ('E162Support', '供电前置')]
    t.scripts = [
        Script('Test - E162 start', [], [('SET_MILLISECOND_TIMER', 'E162 swap', 12.)]),
        Script('Test - E162 frame', [], [('INCREMENT_COUNTER', 1, 'E162Frame')], once=False),
        Script('Test - E162 clear', [], [('SET_COUNTER', c, 0) for c, _ in t.counters[1:]], once=False),
        Script('Test - E162 alive', [('NAMED_NOT_DESTROYED', dish)],
               [('SET_COUNTER', 'E162Alive', 1)], once=False),
        Script('Test - E162 support', [('PLAYER_HAS_POWER', m.player(s)) for s in ('p1', 's4')]
               + [('NAMED_NOT_DESTROYED', m.role(r).name)
                  for r in ('yard', 'power', 'other yard', 'other power')],
               [('SET_COUNTER', 'E162Support', 1)], once=False),
    ]
    for value, side in ((1, 'p1'), (2, 's4')):
        t.scripts.append(Script('Test - E162 owner ' + side,
                                [('NAMED_OWNED_BY_PLAYER', m.player(side), dish)],
                                [('SET_COUNTER', 'E162Owner', value)], once=False))
    t.scripts.append(Script('Test - E162 transfer', [('TIMER_EXPIRED', 'E162 swap')],
                            [('NAMED_TRANSFER_OWNERSHIP_PLAYER', dish,
                              m.player('p1' if m.facts['incoming'] else 's4'))]))
    before, after = (2, 1) if m.facts['incoming'] else (1, 2)
    t.expect = [('归属量', 0, 'ever>=', before, 40),
                ('归属量', 0, 'ever==', after, 40),
                ('存活量', 0, '==', 1, 40), ('供电前置', 0, '==', 1, 40)]
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


MISSION = {'engine_radar': mission, 'engine_radaroff': lambda: mission(False),
           'engine_radarlow': low_power_mission, 'engine_radartwo': two_provider_mission,
           'engine_radardeath': death_mission, 'engine_radarout': transfer_mission,
           'engine_radarin': lambda: transfer_mission(True)}
CHECKS = {name: {'a': {'engine_radarlow': low_power_check,
                      'engine_radartwo': two_provider_check,
                      'engine_radarout': transfer_check, 'engine_radarin': transfer_check,
                      'engine_radardeath': death_check}.get(name, check)} for name in MISSION}
