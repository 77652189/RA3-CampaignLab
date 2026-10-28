"""The A4 rework's map (maps/sapporo.py) with a stand-in plan, to preview and measure it (cnv_preview sapporo) before
the A4 plan moves to it: the player at the corridor's west end, the convoy coming in off the border, the enemy on
the north plateau, the main objective the harbour and the two bonuses the rework gives (the lane's repair depot,
the TV tower) -- what terrain_measure takes the map's use from.

Published (the cast): engineer 1-2, escort, depot, tower, camp; facts none.
"""
import plan

PLAN = {
    '关卡': 'sp', '名字': '札幌返工图', '地图': 'sapporo',
    '阵营': {'我': '盟军', '敌': '帝国', '其他': {'护送队': {'阵营': '盟军', '对我': '盟友', '对敌': '敌人'}}},
    '开局': {'资金': 0, '部队': [
        {'单位': '守护者坦克', '数量': 3, '在': 'start', '角色': 'escort'},
        {'单位': 'GarageTechStructure', '在': 'lane depot', '阵营': '敌', '角色': 'depot'},
        {'单位': 'ObservationPostTechStructure', '在': 'tv tower', '阵营': '敌', '角色': 'tower'},
        {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
    '边界': 'corridor',
    '机关': {'车队': {'类型': '车队', '出发': '开局 + 0:30', '车': '护送队', '分批': [0, 50, 110]}},
    '段': [{'名字': '会场', '目标': ['护送到 2 号广场', '占修理厂'], '结束': '开局 + 3:00'},
          {'名字': '北营', '边界': 'west of the canal', '目标': ['拆北营', '占电视塔'], '结束': '段 北营 + 6:00'},
          {'名字': '最后一程', '边界': 'whole', '目标': ['送到港口']}],
    '目标': {'护送到 2 号广场': {'说明': '护送车队到 2 号广场', '标记': ['halt'], '完成': '车队.到达 halt'},
             '拆北营': {'说明': '拆掉北营', '标记': ['camp'], '完成': '摧毁 camp'},
             '送到港口': {'说明': '护送车队到港口', '标记': ['harbour'], '完成': '车队.到终点 2'},
             '占修理厂': {'奖励': True, '说明': '占领后巷的修理厂', '标记': ['depot'], '完成': '占领 depot'},
             '占电视塔': {'奖励': True, '说明': '占领西岭的电视塔', '标记': ['tower'], '完成': '占领 tower'}},
}


def mission(name='CampSap'):
    return plan.Compiler(dict(PLAN), name).compile()
