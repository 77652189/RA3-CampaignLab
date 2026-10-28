"""A side allied to the player, on the bench (plan.py 阵营 其他 对我 / 对敌, devices/convoy.py 车 / 分批): a tiny plan on
the festival map. The convoy is 护送队's -- a side of its own, the player's ally (retail Odessa, Stalingrad: the
transports a side of their own) -- and sets off in batches; truck 3 and a guardian tank of the player's start at
half health. With depot, the player owns a retail repair depot (GarageTechStructure: its PassiveAreaEffectBehavior
heals ALLIES' vehicles, the whole map, 2 % a second) -- does it mend the ally's truck, and the player's own tank (the
control)? (A4 redesign, docs/design/a4-redesign.md: the back lane's depot.)

Published (the cast): truck 1-3 (护送队's, the player's ally on Soviet_2), own tank, depot; facts leaves, batch 2,
batch 3.
"""
import plan

LEAVES, BATCHES = 5.0, [0, 25, 50]
PLAN = {
    '关卡': 'al', '名字': '盟友试验', '地图': 'festival',
    '阵营': {'我': '盟军', '敌': '帝国', '其他': {'护送队': {'阵营': '盟军', '对我': '盟友', '对敌': '敌人'}}},
    '开局': {'资金': 0, '部队': [{'单位': 'GarageTechStructure', '在': 'base barracks', '角色': 'depot'},
                             {'单位': '守护者坦克', '在': 'west field', '角色': 'own tank'}]},
    '机关': {'车队': {'类型': '车队', '出发': f'开局 + {LEAVES:g}', '车': '护送队', '分批': BATCHES}},
    '段': [{'名字': '一'}],
}


def mission(name='CampAly', depot=True):
    d = dict(PLAN)
    if not depot:
        d['开局'] = {'资金': 0, '部队': [u for u in PLAN['开局']['部队'] if u['角色'] != 'depot']}
    m = plan.Compiler(d, name).compile()
    m.facts.update({'leaves': LEAVES, 'batch 2': BATCHES[1], 'batch 3': BATCHES[2]})
    return m
