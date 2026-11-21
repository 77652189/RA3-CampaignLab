"""simai.Brain.act for Tactic=Engineer: every living member the target admits is sent to capture it; done once the
target is the AI's, gone, or no member can take it. The whole-run reading is engine_aiskirm.readings.toml
(skirmish_ai_engineer_tactic_captures_the_derrick)."""
from types import SimpleNamespace as NS

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.ai.core as simai  # noqa: E402


def ai(target, admits=lambda b, t: b.kind == 'engineer'):
    given = []
    me = NS(player='s1', body_of=lambda i: target if i == 7 else None, given=given,
            systems=NS(engineer_entry=admits), give=lambda what, b, target: given.append((what, b.kind, target)))
    return me


def team(*kinds):
    return NS(members=[NS(body=NS(kind=k, alive=True, mode=None, goal=None)) for k in kinds])


def act(me, t, kind='Engineer'):
    return simai.Brain.act(me, t, kind, NS(id=7))


def test_the_admitted_members_are_sent_to_capture_and_the_tactic_is_not_done():
    derrick = NS(alive=True, owner='neutral')
    me = ai(derrick)
    assert act(me, team('engineer', 'dog')) is False
    assert me.given == [('capture', 'engineer', derrick)]


def test_done_once_the_target_is_ours_or_gone_or_no_member_can_take_it():
    assert act(ai(NS(alive=True, owner='s1')), team('engineer')) is True
    assert act(ai(NS(alive=False, owner='neutral')), team('engineer')) is True
    me = ai(NS(alive=True, owner='neutral'))
    assert act(me, team('dog')) is True and me.given == []


def test_other_go_and_act_kinds_are_done_on_arrival():
    me = ai(NS(alive=True, owner='neutral'))
    assert act(me, team('engineer'), kind='SimpleAttack') is True and me.given == []
