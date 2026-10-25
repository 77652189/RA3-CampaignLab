"""The plan's 敌方AI section on the bench (plan.py compile_ai, enemy_ai.py): a small plan on the Niagara map whose
Allied enemy, a construction yard at the east base, is given to the skirmish AI with a generated personality --
power plants capped at 2, barracks at 1. Read back by checks/ai.py (plan): it builds within its caps, and its army
comes over once told to.

Facts: wake at, attack at, money, caps.
"""
import plan

WAKE_AT, ATTACK_AT, MONEY = 30.0, 120.0, 30000     # bench 2026-10-25 (ai/wake): 10000 went on its base, no army
CAPS = {'电厂': 2, '兵营': 1}
WATCH = 480.0                                   # after 进攻: 240 s showed its army at home (bench 2026-10-25)

PLAN = {
    '关卡': 'ap', '地图': 'niagara', '阵营': {'我': '盟军', '敌': '盟军'},
    '开局': {'部队': [
        {'单位': '建造厂', '在': 'east base', '阵营': '敌', '角色': 'ai yard'},
        {'单位': '建造厂', '在': 'base yard', '角色': 'player yard'},
        {'单位': '守护者坦克', '数量': 3, '在': 'base edge', '角色': 'guardian'}]},
    '段': [{'名字': '一'}],
    '敌方AI': {'性格': '平衡', '基地': 'east base', '资金': MONEY, '唤醒': f'开局 + {WAKE_AT:g}',
             '进攻': f'开局 + {ATTACK_AT:g}', '上限': dict(CAPS)},
}


def mission(name='CampAP'):
    m = plan.Compiler(dict(PLAN), name).compile()
    m.spawns |= {'AlliedPowerPlant', 'AlliedBarracks'}                 # what the AI builds, the check counts
    m.facts.update({'wake at': WAKE_AT, 'attack at': ATTACK_AT, 'money': MONEY, 'power cap': CAPS['电厂'],
                    'barracks cap': CAPS['兵营'], 'watch after attack': WATCH})
    return m
