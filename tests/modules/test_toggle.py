"""The ToggleStatusSpecialAbilityUpdate module (engine/modules/toggle.py, step M5): its data read from the block, the
first state's status from the start, a press entering the next state at once (its ObjectStatus on through the host,
World.toggled) or once its UnpackTime is out in the toggles cell (engine_toggle d: 1 s -> 15 frames + UNPACK_LAG), a
state with a DisabledType or a waiting press taking no press, a dead thing's waiting press not entered, and the body's
toggle_at / armor_up in the frame record as the fields were. On the bench: engine_toggle a-f, engine_acts_tgl."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import toggle  # noqa: E402

ARMOUR = '''<GameObject id="CNV_TestArmour" Side="Soviet" KindOf="STRUCTURE">
  <Behaviors>
    <ToggleStatusSpecialAbilityUpdate id="ModuleTag_Toggle" SpecialPowerTemplate="SpecialPower_ToggleArmorUp">
      <!-- <ToggleState ObjectStatus="OLD_COMMENTED" /> -->
      <ToggleState ObjectStatus="" />
      <ToggleState ObjectStatus="GENERIC_TOGGLE_STATE SPECIAL_ARMOR_ACTIVE" />
    </ToggleStatusSpecialAbilityUpdate>
  </Behaviors>
</GameObject>'''
TENT = '''<GameObject id="CNV_TestTent" Side="Allies" KindOf="STRUCTURE">
  <Behaviors>
    <ToggleStatusSpecialAbilityUpdate id="ModuleTag_Toggle" SpecialPowerTemplate="SpecialPower_ToggleAlliedEngineerHeal"
        PackTime="1s" UnpackTime="1s">
      <ToggleState ObjectStatus="WEAPON_UPGRADED_01" />
      <ToggleState ObjectStatus="GENERIC_TOGGLE_STATE" DisabledType="HELD" LocomotorSet="NORMAL" />
    </ToggleStatusSpecialAbilityUpdate>
  </Behaviors>
</GameObject>'''


def _world():
    s = simsmall.small_world()
    s.own.update({'CNV_TestArmour': ARMOUR, 'CNV_TestTent': TENT})
    return s


def _made(s):
    return s.eng.frame if s.eng is not None else 0          # the frame Sim.add built it in (at=0)


def _run(s, frames):
    for f in frames:
        s.world.frame = f
        s.world.schedule.run('toggles', f)


def test_the_block_is_read_its_states_in_order_comments_left_out():
    s = _world()
    (d,) = s.world.data_of('CNV_TestTent', 'ToggleStatusSpecialAbilityUpdate')
    assert (d.power, d.pack, d.unpack) == ('SpecialPower_ToggleAlliedEngineerHeal', 1.0, 1.0)
    assert [(st['status'], st['disabled'], st['locomotor']) for st in d.states] == [
        ({'WEAPON_UPGRADED_01'}, None, None), ({'GENERIC_TOGGLE_STATE'}, 'HELD', 'NORMAL')]
    (d,) = s.world.data_of('CNV_TestArmour', 'ToggleStatusSpecialAbilityUpdate')
    assert [st['status'] for st in d.states] == [set(), {'GENERIC_TOGGLE_STATE', 'SPECIAL_ARMOR_ACTIVE'}]
    d = toggle.ToggleData.parse('', '')
    assert (d.power, d.pack, d.unpack, d.states) == (None, 0.0, 0.0, [])


def test_a_press_enters_the_next_state_at_once_its_status_on_and_round_again():
    s = _world()
    s.add('m', 'CNV_TestArmour', 'Player_1', 100.0, 100.0)
    b = s.bodies['m']
    (m,) = b.find(interfaces.Toggle)
    assert (b.toggle_at, b.armor_up) == ({}, False) and 'SPECIAL_ARMOR_ACTIVE' not in b.status
    assert m.press(_made(s)) is True
    assert (b.toggle_at, b.armor_up) == ({0: 1}, True) and {'GENERIC_TOGGLE_STATE', 'SPECIAL_ARMOR_ACTIVE'} <= b.status
    assert 'miner armor' in s.used and 'toggle' in s.used
    assert m.press(_made(s) + 1) is True
    assert (b.toggle_at, b.armor_up) == ({0: 0}, False) and 'SPECIAL_ARMOR_ACTIVE' not in b.status


def test_the_first_state_holds_from_the_start_an_unpack_time_puts_a_press_off_and_a_disabled_state_takes_none():
    s = _world()
    s.add('t', 'CNV_TestTent', 'Player_1', 100.0, 100.0)
    b, f = s.bodies['t'], _made(s)
    (m,) = b.find(interfaces.Toggle)
    assert 'WEAPON_UPGRADED_01' in b.status                 # the first state's bits from the start
    assert m.press(f) is True and b.toggle_at == {}         # UnpackTime 1 s: waiting
    assert m.press(f + 1) is False                          # a press while one waits: refused
    _run(s, range(f, f + 15))
    assert b.toggle_at == {} and 'GENERIC_TOGGLE_STATE' not in b.status
    _run(s, [f + 15])                                       # 15 frames + UNPACK_LAG 0 (engine_toggle d: 16 counted
    assert b.toggle_at == {0: 1} and 'GENERIC_TOGGLE_STATE' in b.status    # from the frame before the press's cell)
    assert m.press(f + 20) is False and b.toggle_at == {0: 1}   # DisabledType HELD: no further press


def test_a_dead_things_waiting_press_is_not_entered():
    s = _world()
    s.add('t', 'CNV_TestTent', 'Player_1', 100.0, 100.0)
    b, f = s.bodies['t'], _made(s)
    (m,) = b.find(interfaces.Toggle)
    assert m.press(f) is True
    s.destroy(b, 'test')
    _run(s, range(f, f + 30))
    assert m.state() == 0 and not m.entered()


def test_the_record_keeps_toggle_at_and_armor_up_where_the_fields_were():
    s = _world()
    s.add('m', 'CNV_TestArmour', 'Player_1', 100.0, 100.0)
    s.add('t', 'CNV_TestTent', 'Player_1', 300.0, 100.0)
    s.bodies['m'].find(interfaces.Toggle)[0].press(_made(s))
    state = simrecord.body_state(s.bodies['m'])
    assert (state['toggle_at'], state['armor_up']) == ({0: 1}, True)
    state = simrecord.body_state(s.bodies['t'])
    assert (state['toggle_at'], state['armor_up']) == ({}, False)
    assert not {'at', 'moved', 'due_at'} & set(state)       # several toggles a thing: one record field for all
