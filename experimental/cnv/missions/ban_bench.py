"""禁造 on the bench (plan.py compile_bans, 准造): the player on the festival map with a construction yard, a power
plant and a refinery, money; the airfield and the barracks banned from the start (retail Brighton Beach:
ALLOW_DISALLOW_ONE_BUILDING on the player), let go at LET_GO. Looked at by hand (bench_start, select the yard, the
build tab before and after): a human's build cannot be ordered by a script, so no counter tells it. Bench
2026-10-28 (CampBan_mcp_1028_162857): at 2 s the barracks and the airfield showed a lock, at 36 s both were open.

Published (the cast): yard; facts: let go.
"""
import plan

LET_GO = 30.0
PLAN = {
    '关卡': 'bn', '名字': '禁造试验', '地图': 'festival',
    '阵营': {'我': '盟军', '敌': '帝国'},
    '开局': {'资金': 20000, '部队': [{'单位': '建造厂', '在': 'base yard', '角色': 'yard'},
                                 {'单位': '电厂', '在': 'base power'},
                                 {'单位': '矿厂', '在': 'base refinery'}]},
    '禁造': ['机场', '兵营'],
    '规则': [{'当': f'开局 + {LET_GO:g}', '做': [{'准造': ['机场', '兵营']}, '通报 机场和兵营放开了']}],
    '段': [{'名字': '一'}],
}


def mission(name='CampBan'):
    m = plan.Compiler(dict(PLAN), name).compile()
    m.facts['let go'] = LET_GO
    return m
