"""The plan words for what the player sees, on the bench (docs/design/teardowns/layout.md 3; plan.py scene /
compile_shown): a tiny plan on the festival map, two phases.

  - 看: opens with a 过场 -- the camera to the harbour (the far east end) and back. The bench gets into the mission
    only some seconds after it began (bench 2026-10-27: the first frame was past this one), so the second phase's
    is the one the frames show.
  - 北营 (from AT): a 过场 -- the camera to the north base, the whole map for a look, back to the west field -- and
    two goals: one on the clock after the hand-back, a bonus shown only once the player's dog gets to the convoy
    start (亮出).

Published (the cast): dog (the player's), camp (the enemy's); facts 过场 看, 过场 北营, 段 北营; goals
'Objective01 - CNV SC' and 'Bonus01 - CNV SC' (their shown flags CNV_SC_Objective01_Shown, CNV_SC_Bonus01_Shown);
the scenes' flags CNV_SC_Scene_1 / _2.
"""
import plan

AT = 30.0                                       # the second phase begins, seconds from the start
PLAN = {
    '关卡': 'sc', '名字': '过场试验', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
    '开局': {'资金': 0, '部队': [{'单位': '警犬', '在': 'west field', '角色': 'dog'},
                             {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
    '段': [{'名字': '看', '过场': [{'镜头': 'harbour', '秒': 3}, {'镜头': 'west field', '秒': 2}],
           '结束': f'开局 + {AT:g}'},
          {'名字': '北营', '目标': ['看过了', '找到车队'],
           '过场': [{'镜头': 'camp', '秒': 3}, {'揭全图': '看一眼'}, {'停': 4}, {'镜头': 'west field', '秒': 2},
                   {'闪烁': 'dog'}]}],
    '目标': {'看过了': {'说明': '交还控制以后亮出', '标记': ['camp']},
           '找到车队': {'奖励': True, '说明': '警犬走到车队出发点才亮出', '标记': ['convoy start'],
                    '亮出': 'dog 进入 convoy start'}},
}


def mission(name='CampScene'):
    return plan.Compiler(PLAN, name).compile()
