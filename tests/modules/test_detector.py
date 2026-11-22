"""StealthDetectorUpdate (engine/modules/detector.py): what the bench's counters cannot see. Read on the bench:
checks/engine_detector.readings.toml (a dog in range marks the hidden target, none out of range or without the module,
the mark goes with the dog)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402


def _hidden(dog_owner):
    s = simsmall.small_world([('target', 'AlliedAntiVehicleVehicleTech1', 'Player_1', 0.0, 0.0),
                              ('aura', 'AlliedAntiVehicleVehicleTech3', 'Player_1', 0.0, -100.0),
                              ('dog', 'AlliedScoutInfantry', dog_owner, 150.0, 0.0)])
    s.bodies['aura'].status.add('GENERIC_TOGGLE_STATE')        # the mirage's aura on (a script's toggle)
    return s, s.bodies['target']


def test_an_enemy_dog_makes_the_hidden_target_a_target_again():
    s, t = _hidden('Soviet_1')
    assert t.serial not in s.cloaked(s.living()) and 'INVISIBLE_DETECTED' in t.status
    t.script_status.add('NO_ATTACK')                            # a script sets another bit: the status is re-set
    s.world.modify(t)
    assert t.serial not in s.cloaked(s.living()) and 'INVISIBLE_DETECTED' in t.status
    s.bodies['dog'].x = 450.0                                   # out of DetectionRange 300: hidden, unmarked
    assert t.serial in s.cloaked(s.living()) and 'INVISIBLE_DETECTED' not in t.status


def test_the_scan_leaves_a_scripts_own_mark():
    s, t = _hidden('Soviet_1')
    s.cloaked(s.living())                                       # the scan marks first, then the script
    t.script_status.add('INVISIBLE_DETECTED')
    s.world.modify(t)
    s.bodies['dog'].x = 450.0
    s.cloaked(s.living())
    assert 'INVISIBLE_DETECTED' in t.status


def test_a_script_conditions_query_marks_nothing():
    """Review 1122ss #4: ENEMY_SIGHTED / TYPE_SIGHTED (no such viewer) and TEAM_DISCOVERED (an own team with members)
    read the hidden set without writing the scan's mark; the tick's scan still writes it."""
    s, t = _hidden('Soviet_1')
    t.team = 'Player_1/G_0_0'
    s.active.add(t.team)
    s.cond('ENEMY_SIGHTED', ['nobody', 'Enemy', 'Player_1'])
    s.cond('TYPE_SIGHTED', ['nobody', t.template, 'Player_1'])
    assert s.cond('TEAM_DISCOVERED', ['Player_1', t.team]) and 'INVISIBLE_DETECTED' not in t.status
    s.cloaked(s.living())
    assert 'INVISIBLE_DETECTED' in t.status


def test_a_friendly_dog_shows_nothing():
    s, t = _hidden('Player_1')
    assert t.serial in s.cloaked(s.living()) and 'INVISIBLE_DETECTED' not in t.status
