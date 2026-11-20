"""Production during the sell animation and on the deletion frame."""
import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.ports.command import Command  # noqa: E402
from engine.testing.small import small_world  # noqa: E402

PLAYER = 'Player_1'
ENGINEER = 'AlliedEngineer'


@pytest.mark.parametrize(('sale_frame', 'paid_before_sale', 'final_paid', 'made'), [
    (8, 27, 124, False),    # last production frame 37: ceil(500*37/150) = 124
    (131, 437, 500, False),  # deletion on frame 161 precedes production, so the ready engineer never exits
    (140, 467, 500, True),  # the engineer exits on frame 161, before deletion on 170
])
def test_sale_refunds_the_structure_and_the_queue_runs_only_while_it_is_alive(
        sale_frame, paid_before_sale, final_paid, made):
    s = small_world([('factory', 'AlliedBarracks', PLAYER, 600, 600),
                     ('plant', 'AlliedPowerPlant', PLAYER, 900, 600)], model=False)
    f = s.bodies['factory']
    s.money[PLAYER] = 1000
    assert s.commands.do(Command('build', player=PLAYER, template=ENGINEER)) == (True, '')
    s.produce_due(1)
    s.produce_due(sale_frame)
    assert s.queues[f.serial][0]['paid'] == paid_before_sale  # ceil($500 * sale_frame/150)

    s.clock.frame = sale_frame
    s.act('SELL_OBJECT', [f.name], None)
    delete_frame = sale_frame + 30  # BaseStructure's 2 s SellTime at 15 fps
    assert f.alive and 'SOLD' in f.script_status and f.sell_end == delete_frame
    assert s.power(PLAYER) == (100, 25)
    assert s.money[PLAYER] == 1000 - paid_before_sale + 250  # full-health $500 Barracks, 50%
    s.clock.frame = sale_frame + 1
    s.t = s.clock.frame / s.fps
    s.advance(30)  # the real frame loop runs expire before produce

    assert f.deleted and not f.alive and f.serial not in s.queues
    assert s.power(PLAYER) == (100, 0)
    assert s.money[PLAYER] == 1000 + 250 - final_paid  # only the building refund
    assert [b.made_by for b in s.living() if b.template == ENGINEER] == ([f.name] if made else [])
