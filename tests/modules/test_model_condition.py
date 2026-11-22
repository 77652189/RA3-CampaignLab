"""The timed ModelCondition script actions (engine/script/act_object.py): TEAM_SET_MODELCONDITION_FOR_DURATION sets the
condition on every member of the team, for the unit action's measured span (seconds * 15 + 1 frames, the boundary
included). On the bench: engine_modeldur a / b (the unit action), t (the team action as s03 calls it)."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.testing.small as simsmall  # noqa: E402
import engine.script.act_object as act_object  # noqa: E402
import engine.script.cond_object as cond_object  # noqa: E402

TEAM = 'Player_1/teamCNVE'


def _world():
    s = simsmall.small_world([(n, 'JapanEngineer', 'Player_1', 100. * k, 0.)
                              for k, n in enumerate(('e1', 'e2', 'loner'))], model=False)
    s.bodies['e1'].team = s.bodies['e2'].team = TEAM
    return s, lambda c: [cond_object.unit_has_modelcondition(s, '', [n, c]) for n in ('e1', 'e2', 'loner')]


def _act(s, name, *args):
    act_object.ACTIONS[name](s, name, [TEAM, *args], None)


def test_the_team_action_sets_and_clears_every_member_and_no_one_else():
    s, lit = _world()
    _act(s, 'TEAM_SET_MODELCONDITION', 2, 1)
    s.advance(90)
    assert lit('USER_2') == [True, True, False]
    _act(s, 'TEAM_SET_MODELCONDITION', 2, 0)
    assert lit('USER_2') == [False, False, False]


def test_the_timed_team_action_times_every_member_alike_and_no_one_else():
    s, lit = _world()
    _act(s, 'TEAM_SET_MODELCONDITION_FOR_DURATION', 'EMOTION_CELEBRATING', 10., 1.)
    assert lit('EMOTION_CELEBRATING') == [True, True, False]
    s.advance(150)
    assert lit('EMOTION_CELEBRATING') == [True, True, False]
    s.advance(1)
    assert lit('EMOTION_CELEBRATING') == [False, False, False]
