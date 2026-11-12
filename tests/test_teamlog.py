"""experimental/cnv/teamlog.py reads ra3ext's CNVTeams lines (engine line D round 68). The lines below are copied from
bench run CampAICrT3A_mcp_1112_015804 (checks/engine_aiteams.py aicr3t:a, PASS): the CreateUnits MinUnits 3 team
holds 2 Guardians at frame 511 and activates with 3 at frame 646."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]

import teamlog  # noqa: E402

LOG = """ra3ext loaded pid=1 exe=x: ok
team: frame=511 list=0 proto=08F46B20 name1='Soviet_1' name2='7203be5f_SimpleAttack_0_0' rel=1 slot=0 team=0B14B4D0 active=0 n=2 ids=3176@3881:3001,3177@3881:3041
team: frame=511 list=0 proto=08F56190 name1='Soviet_1' name2='defaultSkirmishTeamSoviet_1' rel=1 slot=0 team=081C3150 active=1 n=12 ids=36@0:0,3163@3850:3400,3166@3650:3240,3167@3650:3190,3168@3650:3140,3169@3650:3090,3170@3850:3150,3171@3850:3800,3172@4100:3800,3173@3892:3106,3174@3813:3155,3175@3882:3124
team: frame=511 list=1 proto=086012E0 name1='Soviet_1' name2='teamSoviet_1' rel=1 slot=0 team=081BFA50 active=1 n=0 ids=
teams: frame=511 player=06E37D70 index=4 ai=08B6FE60 protos=3 teams=3
team: frame=646 list=0 proto=08F46B20 name1='Soviet_1' name2='7203be5f_SimpleAttack_0_0' rel=1 slot=0 team=0B14B4D0 active=1 n=3 ids=3176@3876:3003,3177@3892:3041,3178@3875:3110
team: frame=646 list=1 proto=086012E0 name1='Soviet_1' name2='teamSoviet_1' rel=1 slot=0 team=081BFA50 active=1 n=0 ids=
teams: frame=646 player=06E37D70 index=4 ai=08B6FE60 protos=3 teams=3
"""


def _log(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG)
    return str(p)


def test_team_size_by_logged_name(tmp_path):
    p = _log(tmp_path)
    assert teamlog.team_size(p, '7203be5f_SimpleAttack_0_0', 600) == 2
    assert teamlog.team_size(p, '7203be5f_SimpleAttack', 646) == 3
    assert teamlog.team_size(p, 'defaultSkirmishTeamSoviet_1', 511) == 12
    assert teamlog.team_sizes(p, 'teamSoviet_1', 646) == [0]
    assert teamlog.team_size(p, 'nothing', 646) == 0
    assert teamlog.team_size(p, '7203be5f_SimpleAttack', 100) == 0      # before the first sample
    assert teamlog.members(p, '7203be5f_SimpleAttack', 646) == [[(3176, 3876, 3003), (3177, 3892, 3041),
                                                                (3178, 3875, 3110)]]
    assert [t['active'] for _, ts in teamlog.samples(p) for t in ts if 'SimpleAttack' in t['names'][1]] == [0, 1]


def test_state_id_is_hashed_the_ai_way(tmp_path):
    p = _log(tmp_path)
    assert teamlog.team_size(p, 'CNVStateTF', 646) == 3            # FastHash('cnvstatetf') = 7203be5f
    assert teamlog.team_size(p, 'CNVStateTF_SimpleAttack', 511) == 2
