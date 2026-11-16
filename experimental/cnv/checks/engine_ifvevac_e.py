"""E179: original Riptide transport button versus an unpressed twin.

The retail template AlliedAntiInfantryVehicle is the Riptide, despite the
historical IFV button name. LogicCommand declares EVACUATE; TransportContain
accepts five infantry. Load one named conscript per transport at frame 15
through the existing instant-garrison action, press only one at frame 60.
Prediction: ENCLOSED snapshots at 45/120 are 11/10; alive mask stays 1111.
No direct status inputs. See work/re/e179_ifvevac.md.
"""
from maps import probe_border
from parts import Mission, Script, Test

BUTTON = 'Command_AlliedAntiInfantryVehicleEvacuate'


def mission():
    m = Mission(name='CampIFVEvac', map=probe_border, units=[], facts={})
    for role, dx in [('press', 0), ('quiet', 500)]:
        m.put('AlliedAntiInfantryVehicle', 'stop row', dx, 0,
              role=role, name='E179 ' + role)
        crew = m.crew('E179' + role)
        m.put('SovietAntiInfantryInfantry', 'stop row', dx, -100,
              role=role + ' crew', name='E179 ' + role + ' crew',
              props={'originalOwner': crew})
    return m


def check(m):
    t = Test()
    t.counters = [('E179Frame', '完成帧'), ('E179Before', '撤前'),
                  ('E179After', '撤后'), ('E179Alive', '存活')]
    t.scripts = [
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
        Script('Test - clock', [('COUNTER', 'E179Frame', 0, 120)],
               [('INCREMENT_COUNTER', 1, 'E179Frame')], once=False),
        Script('Test - load', [('COUNTER', 'E179Frame', 2, 15)], [
            ('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams['E179' + r], m.role(r).name)
            for r in ('press', 'quiet')]),
        Script('Test - press', [('COUNTER', 'E179Frame', 2, 60)],
               [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('press').name, BUTTON)])]
    for frame, counter in [(45, 'E179Before'), (120, 'E179After')]:
        for role, weight in [('press', 1), ('quiet', 10)]:
            t.scripts.append(Script(f'Test - sample {frame} {role}',
                [('COUNTER', 'E179Frame', 2, frame),
                 ('UNIT_HAS_OBJECT_STATUS', m.role(role + ' crew').name, 'ENCLOSED')],
                [('INCREMENT_COUNTER', weight, counter)]))
    for role, weight in [('press', 1), ('quiet', 10), ('press crew', 100), ('quiet crew', 1000)]:
        t.scripts.append(Script('Test - alive ' + role,
            [('COUNTER', 'E179Frame', 2, 120), ('NAMED_NOT_DESTROYED', m.role(role).name)],
            [('INCREMENT_COUNTER', weight, 'E179Alive')]))
    t.expect = [('完成帧', 0, 'ever==', 120), ('撤前', 0, 'ever==', 11),
                ('撤后', 0, 'ever==', 10), ('存活', 0, 'ever==', 1111)]
    t.bench = [('bench_watch', dict(seconds=18, every=1, sheet=False, lines=4))]
    return t


MISSION = {'ifvevac_e': mission}
CHECKS = {'ifvevac_e': {'a': check}}

