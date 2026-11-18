"""A1's trap is fair (docs/story/plans/a1.md, I20 of the 2026-11-05 CampShell acceptance): a player who sends the whole
squad to the south bridge end at the start (the natural first move) is not thrown out; one who goes on to the deck
(the patrol's own ground) is warned first, with time to stop, before the fuse is lit."""
from test_plans import small  # (puts experimental/cnv on the path)  # noqa: F401, I001
import build  # noqa: E402
import sim  # noqa: E402

SQUAD = ('tanya', 'peace', 'hawk')
WARN_TO_FIRE = 5.0          # seconds a squad that is in the patrol's reach has before the patrol falls


def run(site, until=120.0):
    m, t, _ = build.resolve('a1', '')
    script = '; '.join(f'5 派 {r} 去 {site}' for r in SQUAD)
    return sim.Sim(m, t, script=script).run(until)


def test_walking_to_the_bridge_end_does_not_end_the_mission():
    s = run('south bridgehead')
    assert not s.ending, s.ending_line()


def test_going_on_to_the_deck_is_warned_before_the_fuse_is_lit():
    s = run('deck')
    assert s.ending and s.ending[0] == '输', s.ending_line()          # the trap still is one
    warned = [t for t, k, x in s.log if k == '通报' and '停下' in x]
    fell = [t for t, k, x in s.log if k == '摧毁' and 'south patrol' in x]
    assert warned and fell, s.log
    assert fell[0] - warned[0] >= WARN_TO_FIRE, (warned, fell)


def test_the_warning_is_not_given_to_a_squad_that_stays_home():
    m, t, _ = build.resolve('a1', '')
    s = sim.Sim(m, t, script='不打').run(60.0)
    assert not [1 for _, k, x in s.log if k == '通报' and '停下' in x]
