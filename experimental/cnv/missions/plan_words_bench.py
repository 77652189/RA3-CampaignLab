"""Engine probe for the plan words added to line up with the retail missions (docs/story/plans/retail/README.md), a
small plan compiled like a level's (plan.py) but kept here, not among the levels' plans. Read back by
checks/plan_words.py:

  - 规则 每隔: from the start, +100 money every 5 s (the first at once);
  - a random time, 开局 + 0:06~0:10: one guardian given in that window;
  - 无敌: an imperial warrior beside the player's guardians that nothing can aim at, a plain one beside it as the
    control; at 0:30 `取消无敌` and it falls like the control did.

Facts: money (at the start), bonus (each rule run), gap, give from / until, undo at.
"""
import plan

MONEY, BONUS, GAP = 3000, 100, 5.0
GIVE = (6.0, 10.0)
UNDO_AT = 30.0

PLAN = {
    '关卡': 'pw', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
    '开局': {'资金': MONEY, '部队': [
        {'单位': '守护者坦克', '数量': 2, '在': 'west field', '偏移': [250, 30], '角色': 'guardian'},
        {'单位': '帝国武士', '在': 'west field', '偏移': [200, 200], '阵营': '敌', '角色': 'shielded', '无敌': '是'},
        {'单位': '帝国武士', '在': 'west field', '偏移': [300, 200], '阵营': '敌', '角色': 'control'}]},
    '段': [{'名字': '一'}],
    '规则': [{'当': '开局', '每隔': GAP, '做': [{'资金': f'+{BONUS}'}]},
           {'当': f'开局 + {GIVE[0]:g}~{GIVE[1]:g}', '做': [{'给': {'守护者坦克': 1}, '在': 'west field'}]},
           {'当': f'开局 + {UNDO_AT:g}', '做': [{'取消无敌': 'shielded'}]}],
}


def mission(name='CampPW'):
    m = plan.Compiler(dict(PLAN), name).compile()
    m.facts.update({'money': MONEY, 'bonus': BONUS, 'gap': GAP, 'give from': GIVE[0], 'give until': GIVE[1],
                    'undo at': UNDO_AT})
    return m
