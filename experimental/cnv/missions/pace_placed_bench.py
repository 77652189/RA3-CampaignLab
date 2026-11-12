"""出动 + 齐步 on the bench (plan.py pace_placed, docs/engine/pathing.md 5b): two Tsunami tanks (75) and two Imperial
Warriors (50) placed at the harbour on the festival map from the start, sent off together at SEND to the west field
(down the road, ~2 850). Built twice: `paceplaced` with 齐步 (the tanks placed as their 67 % paced copies, granted the
upgrade as they are sent, released inside the west field's area) and `paceplacedn` without (the plain tanks). The
player's yard is on the north base, out of the road's sight; the enemy's barracks on the north camp.

Published (the cast): tank 1 / 2, foot 1 / 2, yard, camp; facts: send at.
"""
import plan

SEND = 30.0


def plan_dict(together):
    return {
        '关卡': 'pp', '名字': '齐步出动试验', '地图': 'festival',
        '阵营': {'我': '盟军', '敌': '帝国'},
        '开局': {'资金': 5000, '部队': [
            {'单位': '建造厂', '在': 'north base', '角色': 'yard'},
            {'单位': '兵营', '在': 'north camp', '阵营': '敌', '角色': 'camp'},
            {'单位': '帝国武士', '数量': 2, '在': 'harbour', '阵营': '敌', '角色': 'foot'},
            {'单位': '海啸坦克', '数量': 2, '在': 'harbour', '阵营': '敌', '角色': 'tank'}]},
        '规则': [{'当': f'开局 + {SEND:g}',
                '做': [{'出动': ['foot', 'tank'], '打': 'west field', '齐步': '是' if together else '否'}]}],
        '段': [{'名字': '一'}],
    }


def mission(together=True):
    name = 'CampPacePl' if together else 'CampPacePlN'
    m = plan.Compiler(plan_dict(together), name).compile()
    m.facts['send at'] = SEND
    return m


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'paceplaced': lambda: mission(True),
    'paceplacedn': lambda: mission(False),
}
