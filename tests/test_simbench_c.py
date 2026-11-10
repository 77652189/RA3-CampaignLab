"""Engine line C's simulator-vs-bench tests (object modules, weapon effects): each takes a reading the bench made and holds
the simulator to it, so a module can be registered in inventory.BENCHED_TESTS against it. A separate file from
test_simbench.py so line C's hunks never share a file with another line's uncommitted ones."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# loaded by file: simbench.py puts the cnv folders on the path itself (no new sys.path edit here: guard G4's ceiling)
_spec = importlib.util.spec_from_file_location('simbench_c', ROOT / 'experimental' / 'cnv' / 'simbench.py')
simbench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simbench)


def _sim_run(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return sim.Sim(m, t).run(until)


# ---- RunOffMapBehavior (sim.Sim.flee_start / flee_due; simunits.run_off_map): bench 2026-11-06 engine_runoffmap
# (checks/engine_runoffmap.py, docs/engine/runoffmap.md): the peacekeeper runs to the waypoint `RunOffMap` (a, 200 off)
# or 1000 along its facing (b), is gone 3 frames after it arrives and was never dying; a structure does not run (c);
# NAMED_STOP at frame 15 leaves him standing with the status on (d). 逃帧 = frames not removed + 1000 x frames fleeing.
def test_run_off_map_the_peacekeeper_is_gone_64_and_304_frames_after_the_order_never_dying():
    a = _sim_run('engine_runoffmap', 'a', 20.0).series[-1][1]
    b = _sim_run('engine_runoffmap', 'b', 50.0).series[-1][1]
    assert (a[1], a[3]) == (64064, 15) and (b[1], b[3]) == (304304, 15), (a, b)
    assert a[2] == a[0] - 64 and b[2] == b[0] - 304, (a, b)         # 死法 = removed frames (+ 1000 x dying: none)


def test_run_off_map_a_structure_stays_and_a_stop_takes_the_run_over_with_the_status_left_on():
    c = _sim_run('engine_runoffmap', 'c', 20.0).series[-1][1]
    d = _sim_run('engine_runoffmap', 'd', 20.0).series[-1][1]
    assert c[1] == c[0] and c[2] == 0 and c[3] == 64064, c           # the plant: there all along, never fleeing
    assert d[1] == 1000 * d[0] + d[0] and d[2] == 0 and d[3] == 0, d     # stopped at 15: still there, still fleeing


# ---- InvisibilityBroadcastUpdate (sim.Sim.cloaked; simunits.invis_broadcast): bench 2026-11-05 engine_stealth a / b
# (checks/engine_stealth.py, docs/engine/stealth.md 1-2, 4). A mirage tank carrying GENERIC_TOGGLE_STATE (a script gives
# it) hides the friendly infantry / vehicles within 175; its enemy cannot pick them, the attack order stays and fires
# the moment the aura goes off. The series is read in percent at each second (the bench's seconds run ahead of the
# simulator's, so the times are not compared, the values are).
def _stealth_series(check):
    import build
    import sim
    m, t, _ = build.resolve('engine_stealth', check)
    return {c: [row[1][i] for row in sim.Sim(m, t).run(24.0).series] for i, (c, _) in enumerate(t.counters)}


def test_invisibility_broadcast_the_aura_holds_its_guardian_at_full_health_and_the_control_dies():
    a = _stealth_series('a')
    assert a['CNV_Stealth_BaseHp'] == [100] * 25, a['CNV_Stealth_BaseHp']    # bench 光环血 100 throughout
    assert a['CNV_Stealth_HighHp'][-1] <= 10, a['CNV_Stealth_HighHp']        # bench 对照血 4 at the end
    assert a['CNV_Stealth_Bits'] == [0] * 25                                # STEALTHED never reads (stealth.md 5)


def test_invisibility_broadcast_fire_stops_the_moment_it_hides_and_the_order_waits_for_the_aura_to_drop():
    a, b = _stealth_series('a'), _stealth_series('b')
    order, late = a['CNV_Stealth_OrderHp'], b['CNV_Stealth_SwitchHp']
    assert order[:5] == [100] * 5 and 50 <= order[-1] <= 56, order        # aura off 6 s, on again: bench 54 from s15
    assert order[-1] == order[-3] and order[11] > order[-1], order        # stopped dead once the aura came back
    assert late[0] == 100 and 47 <= late[-1] <= 56 and late[-1] == late[-4], late   # bench 后隐血 50 from s10


def test_invisibility_behavior_a_house_given_garrison_can_stealth_by_script_is_shot_like_a_plain_one():
    b = _stealth_series('b')                                              # bench 隐楼血 = 明楼血 (98 at s4 .. 45)
    assert b['CNV_Stealth_HiddenHp'] == b['CNV_Stealth_PlainHp'] and b['CNV_Stealth_HiddenHp'][-1] < 80, b


# ---- WeaponSetUpdate / StatusBitsUpgrade (simunits.weapon_sets / pick_weapons, Sim.modify; bench 2026-11-09 engine_weaponset
# a / b, engine_statusbits b; docs/engine/weaponset.md). A weapon line's ObjectStatus / ForbiddenObjectStatus choose the gun:
# a conscript with GENERIC_TOGGLE_STATE throws Molotovs instead of firing the AK47 (changing in mid-fight when the script
# gives it); a Guardian under the toggle holds only the target painter (no damage); the upgrade module's HEROIC grant
# sets WEAPON_UPGRADED_01 / _02 and a removal takes it back. Bench 基准血 / 毒瓶血 / 中途血 at s41: 42 / 9 / 21.
def _series(build_name, check, until):
    import build
    import sim
    m, t, _ = build.resolve(build_name, check)
    return {c: [row[1][i] for row in sim.Sim(m, t).run(until).series] for i, (c, _) in enumerate(t.counters)}


def test_weapon_set_the_status_picks_the_gun_molotov_under_the_toggle_and_the_painter_does_no_harm():
    a = _series('engine_weaponset', 'a', 41.0)
    base, high, order = a['CNV_Wset_BaseHp'], a['CNV_Wset_HighHp'], a['CNV_Wset_OrderHp']
    assert abs(base[-1] - 42) <= 3 and abs(high[-1] - 9) <= 3 and abs(order[-1] - 21) <= 3, (base[-1], high[-1], order[-1])
    assert order[8] == base[8] and order[20] < base[20], (order, base)       # the same until the toggle, faster after it
    b = _series('engine_weaponset', 'b', 20.0)
    assert b['CNV_Wset_LowHp'] == [100] * len(b['CNV_Wset_LowHp']), b['CNV_Wset_LowHp']      # bench 涂靶血 100 throughout


def test_status_bits_upgrade_the_heroic_grant_sets_weapon_upgraded_and_a_removal_clears_it():
    b = _series('engine_statusbits', 'b', 20.0)
    assert [b[k][-1] for k in ('CNV_Sbits_HighBit', 'CNV_Sbits_OrderBit', 'CNV_Sbits_RemovedBit', 'CNV_Sbits_Other')] == \
        [1, 1, 0, 11], b                                                      # bench s7-s41: 1 1 0 11 (s1-s6: 1 0 1 11)
    assert (b['CNV_Sbits_OrderBit'][3], b['CNV_Sbits_RemovedBit'][3]) == (0, 1)


# ---- ToppleUpdate: engine_topple a / b, bench 2026-11-09 (docs/engine/crush.md).
# Each row is undestroyed frames + 1000 * dying frames + 1000000 * frames at the goal.
def test_topple_the_five_props_disappear_at_the_bench_frames_without_ever_dying():
    for build_name, check, destroyed, arrivals in (
            ('engine_topple', 'a', (162, 118, 163), (91, 91, 91)),
            ('engine_topple_b', 'b', (119, None, 170), (91, 111, 110))):
        s = _sim_run(build_name, check, 50.0)
        frames, *rows = s.series[-1][1]
        assert 710 <= frames < 1000, frames                  # the conscript's control outlasts the bench's 710
        for row, gone, arrived in zip(rows, destroyed, arrivals):
            undestroyed, dying, at_goal = row % 1000, row // 1000 % 1000, row // 1000000
            assert dying == 0, (check, row)
            assert undestroyed == frames if gone is None else abs(undestroyed - gone) <= 2, (check, row, gone)
            assert abs((frames - at_goal + 1) - arrived) <= 2, (check, row, arrived)


def test_topple_the_legacy_loop_still_drives_through_and_removes_the_props():
    import build
    import sim
    m, t, _ = build.resolve('engine_topple', 'a')
    s = sim.Sim(m, t, model=False).run(50.0)
    _, *rows = s.series[-1][1]
    assert all(row // 1000000 > 0 and row // 1000 % 1000 == 0 for row in rows), rows
    assert all(not s.body(f'UNIT - CNV Topple Prop {k}').alive for k in range(1, 4))


# PREDICTED only: the retail dummy's 100 HP, 200 script damage, 1 HP floor.
# KILL is MaxHealth damage in the reference; DELETE bypasses the body.
def test_immortal_damage_stops_at_one_hp_kill_is_damage_and_delete_removes():
    import build
    import sim
    for lane in 'ab':
        m, t, _ = build.resolve('engine_immortal', lane)
        s = sim.Sim(m, t)
        readings = []
        for half in range(29):
            s.run(half * 0.5)
            readings.append([s.counters.get(c, 0) for c, _ in t.counters])
            dummy = s.body('UNIT - CNV Immortal Dummy')
            if 2 <= half < 24 or lane == 'a':
                assert dummy.max_hp == 100 and dummy.alive
                assert dummy.hp == (100 if half < 2 else 1)
        assert readings[:2] == [[100, 0]] * 2, readings
        # 1..11.5 s: ten seconds after damage, then KILL at 11 s still leaves 1 HP.
        assert readings[2:24] == [[1, 0]] * 22, readings
        if lane == 'a':
            assert readings[24:] == [[1, 0]] * 5, readings
        else:
            assert not dummy.alive and dummy.deleted
            assert readings[24:] == [[0, 1]] * 5, readings
