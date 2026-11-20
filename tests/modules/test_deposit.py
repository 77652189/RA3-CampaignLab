"""The AutoDepositUpdate module (engine/modules/deposit.py, step M4): its data read from the block as the bench says
(a4 derrick: 500 when taken, 15 every 2 s = 30 frames), the holder paid in the deposit cell every interval from the
frame it was made -- the neutral side paid nothing --, a capture paying the bonus and setting the clock an interval on,
read from the merged template, and its rules and next frame in the frame record
where the body's fields were. On the bench: checks/a4 derrick (tests/test_simbench.py), engine_bankcapture."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simrecord  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402
import engine.data.units as simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import deposit  # noqa: E402
from engine.world.handle import CIV  # noqa: E402

DERRICK = '''<GameObject id="CNV_TestDerrick" Side="Neutral" KindOf="STRUCTURE">
  <Behaviors>
    <AutoDepositUpdate id="ModuleTag_Deposit" DepositInterval="2s">
      <InitialCaptureBonus Account="0" Amount="500" />
      <Deposit Account="0" Amount="15" />
    </AutoDepositUpdate>
  </Behaviors>
</GameObject>'''
HEIR = '''<GameObject id="CNV_TestDerrickHeir" inheritFrom="CNV_TestDerrick" Side="Neutral" KindOf="STRUCTURE">
  <Behaviors />
</GameObject>'''


def test_the_block_is_read_as_the_bench_says_seconds_x_15_cut_down():
    d = deposit.DepositData.parse(' id="ModuleTag_Deposit" DepositInterval="2s"',
                                  '<InitialCaptureBonus Amount="500" /><Deposit Amount="15" />')
    assert (d.bonus, d.amount, d.frames) == (500.0, 15.0, 30)
    assert deposit.DepositData.parse(' DepositInterval="0.99s"', '').frames == 14
    d = deposit.DepositData.parse('', '')
    assert (d.bonus, d.amount, d.frames) == (0.0, 0.0, 0)


def _world():
    s = simsmall.small_world()
    s.own.update({'CNV_TestDerrick': DERRICK, 'CNV_TestDerrickHeir': HEIR})
    return s


def _run(s, frames):
    for f in frames:
        s.world.schedule.run('deposit', f)


def test_the_holder_is_paid_every_interval_from_the_frame_it_was_made_the_neutral_nobody():
    s = _world()
    s.add('mine', 'CNV_TestDerrick', 'Player_1', 100.0, 100.0)
    s.add('free', 'CNV_TestDerrick', CIV, 300.0, 100.0)
    mine, free = s.bodies['mine'], s.bodies['free']
    m = mine.find(interfaces.Deposit)
    assert isinstance(m, deposit.Deposit) and mine.deposit == (500.0, 15.0, 30)
    made = s.eng.frame if s.eng is not None else 0          # the frame Sim.add built it in (at=0)
    assert mine.deposit_at == made + 30                     # Generals: the first deposit an interval after it is made
    before = s.wallet.held('Player_1')
    _run(s, range(made, made + 30))
    assert s.wallet.held('Player_1') == before
    _run(s, [made + 30])
    assert s.wallet.held('Player_1') == before + 15 and mine.deposit_at == made + 60
    assert free.deposit_at == made + 60 and s.wallet.held(CIV) == 0     # the clock runs, it pays nobody
    _run(s, range(made + 31, made + 61))
    assert s.wallet.held('Player_1') == before + 30


def test_a_capture_pays_the_bonus_and_sets_the_clock_an_interval_on():
    s = _world()
    s.add('free', 'CNV_TestDerrick', CIV, 300.0, 100.0)
    free = s.bodies['free']
    made = free.deposit_at - 30
    _run(s, range(made, made + 10))
    free.owner = 'Player_1'
    assert free.find(interfaces.Deposit).capture(made + 10) == 500.0
    assert free.deposit_at == made + 40
    before = s.wallet.held('Player_1')
    _run(s, range(made + 10, made + 40))
    assert s.wallet.held('Player_1') == before             # not at made + 30: the clock moved on
    _run(s, [made + 40])
    assert s.wallet.held('Player_1') == before + 15


def test_the_inherited_block_is_read_and_the_record_keeps_the_fields():
    s = _world()
    # Compiled OilDerrick_OnWater and CNV_TestDerrickHeir: one AutoDepositUpdate, bonus 500, deposit 15 every 2s.
    (block,) = simunits.module_blocks('CNV_TestDerrickHeir', 'AutoDepositUpdate', s.own)
    rule = deposit.DepositData.parse(*block)
    assert (rule.bonus, rule.amount, rule.frames) == (500.0, 15.0, 30)
    s.add('heir', 'CNV_TestDerrickHeir', 'Player_1', 100.0, 100.0)
    s.add('mine', 'CNV_TestDerrick', 'Player_1', 300.0, 100.0)
    heir, mine = s.bodies['heir'], s.bodies['mine']
    assert isinstance(heir.find(interfaces.Deposit), deposit.Deposit)
    assert (heir.deposit, heir.deposit_at) == ((500.0, 15.0, 30), mine.deposit_at)
    state = simrecord.body_state(heir)
    assert (state['deposit'], state['deposit_at']) == (heir.deposit, heir.deposit_at)
    state = simrecord.body_state(mine)
    assert state['deposit'] == (500.0, 15.0, 30) and state['deposit_at'] == mine.deposit_at


def test_a_dead_derrick_pays_nothing():
    s = _world()
    s.add('mine', 'CNV_TestDerrick', 'Player_1', 100.0, 100.0)
    mine = s.bodies['mine']
    at, before = mine.deposit_at, s.wallet.held('Player_1')
    s.destroy(mine, 'test')
    _run(s, [at, at + 30])
    assert s.wallet.held('Player_1') == before
