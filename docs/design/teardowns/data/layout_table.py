r"""layout.json (layout_measure.py) -> layout.md: one row per map, then the counts the principles quote.

  python -I -X utf8 docs/design/teardowns/data/layout_table.py

Mission types are ours, read from the objective titles and the plot (an inference, not a field in the map).
"""
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
OCT = ['东', '东北', '北', '西北', '西', '西南', '南', '东南']

# (Chinese name, type) -- type: 护送 / 摧毁 / 守点 / 突击队 / 基地对抗 / 救火 / 解谜
TYPES = {
    'a01_brightonbeach': ('盟1 布莱顿海滩', '守点'), 'a02_cannes': ('盟2 戛纳', '突击队'),
    'a03_heidelberg': ('盟3 海德堡', '护送'), 'a04_gibraltar': ('盟4 直布罗陀', '摧毁'),
    'a05_northsea': ('盟5 北海', '护送'), 'a06_mountrushmore': ('盟6 总统山', '摧毁'),
    'a07_tokyoharbor': ('盟7 东京港', '守点'), 'a08_havana': ('盟8 哈瓦那', '突击队'),
    'a09_leningrad': ('盟9 列宁格勒', '基地对抗'), 'j01_russianvillage': ('帝1 俄罗斯村', '摧毁'),
    'j02_stalingrad': ('帝2 斯大林格勒', '护送'), 'j03_odessa': ('帝3 敖德萨', '护送'),
    'j04_pearlharbor': ('帝4 珍珠港', '守点'), 'j05_deepocean': ('帝5 深海', '守点'),
    'j06_losangeles': ('帝6 洛杉矶', '摧毁'), 'j07_yokohama': ('帝7 横滨', '守点'),
    'j08_kremlin': ('帝8 克里姆林宫', '摧毁'), 'j09_amsterdam': ('帝9 阿姆斯特丹', '基地对抗'),
    's01_leningradcanals': ('苏1 列宁格勒运河', '守点'), 's02_krasna45': ('苏2 克拉斯纳 45', '突击队'),
    's03_vladivostok': ('苏3 海参崴', '基地对抗'), 's04_geneva': ('苏4 日内瓦', '摧毁'),
    's05_mykonos': ('苏5 米科诺斯', '基地对抗'), 's06_iceland': ('苏6 冰岛', '基地对抗'),
    's07_mountfuji': ('苏7 富士山', '基地对抗'), 's08_easterisland': ('苏8 复活节岛', '救火'),
    's09_newyork': ('苏9 纽约', '基地对抗'), 'ep01_a01': ('起盟1 伊贺', '护送'), 'ep01_a02': ('起盟2 大阪', '解谜'),
    'ep01_a03': ('起盟3 宫古岛', '基地对抗'), 'ep01_j01': ('起帝1 库页岛', '摧毁'),
    'ep01_j02': ('起帝2 隐岐群岛', '救火'), 'ep01_j03': ('起帝3 海参崴', '基地对抗'),
    'ep01_s01': ('起苏1 罗马尼亚', '突击队'), 'ep01_s02': ('起苏2 摩尔曼斯克', '摧毁'),
    'ep01_s03': ('起苏3 尤卡坦', '摧毁'), 'ep01_s04': ('起苏4 战斗机器人岛', '摧毁'),
    'ep01_y01': ('百1 研究所', '突击队'), 'ep01_y02': ('百2 黑色设施', '突击队'), 'ep01_y03': ('百3 大院', '突击队'),
    'ours_A4': ('我们 A4 冰雕里的兵', '护送'), 'ours_A5': ('我们 A5 巴拿马之锁', '突击队'),
    'ours_A7': ('我们 A7 鹰派', '基地对抗'), 'ours_A8': ('我们 A8 海上发布会', '摧毁'),
    'ours_J3': ('我们 J3 白鹭城下', '突击队'), 'ours_J4': ('我们 J4 冰雕里的兵', '护送'),
    'ours_J5': ('我们 J5 敌人的敌人', '守点'), 'ours_J7': ('我们 J7 拜科努尔', '突击队'),
    'ours_S2': ('我们 S2 西伯利亚快车', '护送'), 'ours_S5': ('我们 S5 巴拿马之锁', '突击队'),
    'ours_S6': ('我们 S6 拜科努尔', '守点'),
}
PLACE = {'corner': '角落', 'edge': '边上', 'entering': '边外开进', 'centre': '中间', 'outside': '图外'}


def ident(key):
    k = key.replace('camp_', '')
    return next((v for p, v in TYPES.items() if k.startswith(p)), (k, '?'))


def near_oct(a, b):
    d = abs(OCT.index(a) - OCT.index(b)) % 8
    return min(d, 8 - d) <= 1


def row(key, v):
    name, kind = ident(key)
    s0 = v['stages'][0] if v['stages'] else {}
    full = v['size'][0] * v['size'][1] / 1e6
    mains = [g for g in v['goals'] if not g['bonus'] and g.get('dir')]
    bonus = [g for g in v['goals'] if g['bonus']]
    first_mains = [g for g in mains if g.get('stage') == 0]
    dirs = [g['dir'] for g in mains]
    mode = max(set(dirs), key=dirs.count) if dirs else None
    focus = sum(near_oct(d, mode) for d in dirs) / len(dirs) if dirs else None
    foes = sorted({e['dir'] for e in s0.get('enemy_clusters', []) if e['n'] >= 8 and e['dir']}, key=OCT.index)
    far = max((g for g in first_mains if g.get('dist_norm') is not None), key=lambda g: g['dist_norm'], default=None)
    r0 = far.get('routes') if far else None
    last = v['stages'][-1] if v['stages'] else {}
    return dict(key=key, name=name, kind=kind, place=s0.get('start_place'), norm=s0.get('start_norm'),
                place_last=last.get('start_place'), stages=len(v['stages']), moved=len(v.get('moved', [])),
                first_share=round(s0.get('area_km2', full) / full, 2) if s0 else None,
                foes=foes, main_dir=mode, focus=round(focus, 2) if focus is not None else None,
                main_far=far['dist_norm'] if far else None,
                routes=r0, bonus=len(bonus),
                bonus_far=sum(1 for g in bonus if (g.get('detour') or 0) > 500),
                bonus_risky=sum(1 for g in bonus if g.get('risk_dist') is not None and g['risk_dist'] < 600),
                bonus_first=sum(1 for g in bonus if g.get('stage') == 0))


def fmt(r):
    n = r['norm']
    pos = f"{PLACE.get(r['place'], r['place'])} ({n[0]:.2f}, {n[1]:.2f})" if n else '?'
    stg = f"{r['stages']}" + (f" + 移动 {r['moved']}" if r['moved'] else '')
    return (f"| {r['name']} | {r['kind']} | {pos} | {PLACE.get(r['place_last'], r['place_last'])} | {stg} | "
            f"{r['first_share'] if r['first_share'] is not None else ''} | {'、'.join(r['foes']) or '—'} | "
            f"{r['main_dir'] or '—'} | {r['focus'] if r['focus'] is not None else ''} | "
            f"{r['main_far'] if r['main_far'] is not None else ''} | {r['routes'] if r['routes'] is not None else ''} | "
            f"{r['bonus']} | {r['bonus_far']} | {r['bonus_risky']} | {r['bonus_first']} |")


def counts(rows, field):
    out = {}
    for r in rows:
        out[r[field]] = out.get(r[field], 0) + 1
    return out


def main():
    data = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
    rows = [row(k, v) for k, v in data.items() if 'error' not in v]
    retail = [r for r in rows if not r['key'].startswith('ours')]
    ours = [r for r in rows if r['key'].startswith('ours')]
    head = ('| 关 | 类型 | 出生点（第一块可玩区，归一化 x, y） | 扩到最后 | 阶段 | 第一块占全图 | 第一块里敌方据点方位 | '
            '主目标主方向 | 主目标集中度 | 第一块最远主目标（对角线比） | 去它的陆路条数 | 奖励 | 要绕路 | 贴着敌人 | 第一块里就有 |')
    sep = '|' + '---|' * 15
    lines = ['# 战役地图的空间布局：测量总表', '',
             '由 [layout_measure.py](layout_measure.py) 量、[layout_table.py](layout_table.py) 汇总（2026-10-27）；原始数据 [layout.json](layout.json)。'
             '各列的定义见 layout_measure.py 开头；"类型"是按目标标题和剧情归的类（推断）。', '',
             '## 原版 40 关', '', head, sep] + [fmt(r) for r in retail] + \
            ['', '## 我们的 11 关（各关最新的完整构建）', '', head, sep] + [fmt(r) for r in ours] + ['', '## 统计', '']

    def share(rs, pred):
        return f"{sum(1 for r in rs if pred(r))}/{len(rs)}"
    for label, rs in (('原版', retail), ('我们', ours)):
        c = counts(rs, 'place')
        lines.append(f"- **{label}出生点（第一块可玩区）**：" + '，'.join(f"{PLACE[k]} {v}" for k, v in sorted(c.items(), key=lambda q: -q[1])))
        cl = counts(rs, 'place_last')
        lines.append(f"  - 扩到最后一块可玩区时：" + '，'.join(f"{PLACE[k]} {v}" for k, v in sorted(cl.items(), key=lambda q: -q[1])))
        fs = [r['first_share'] for r in rs if r['first_share'] is not None]
        lines.append(f"  - 第一块可玩区占全图：中位数 {st.median(fs):.2f}；一开局就是全图的 {share(rs, lambda r: r['first_share'] == 1.0)}")
        nf = [len(r['foes']) for r in rs]
        lines.append(f"  - 第一块里敌方据点（≥ 8 个物体的聚团）在几个方位：中位数 {st.median(nf)}；≥ 3 个方位的 {share(rs, lambda r: len(r['foes']) >= 3)}")
        mf = [r['main_far'] for r in rs if r['main_far'] is not None]
        lines.append(f"  - 第一块里最远的主目标离出生点（推进纵深）：中位数 {st.median(mf):.2f} 条第一块对角线；< 0.15 的 {share(rs, lambda r: r['main_far'] is not None and r['main_far'] < 0.15)}")
        rr = [r for r in rs if r['routes']]
        lines.append(f"  - 去那个主目标的陆路：有陆路的 {len(rr)} 关里，只有 1 条的 {sum(r['routes'] == 1 for r in rr)}，2 条的 {sum(r['routes'] == 2 for r in rr)}，3 条以上的 {sum(r['routes'] >= 3 for r in rr)}；"
                     f"没有陆路（要走水路、两栖或空中）的 {share(rs, lambda r: r['routes'] == 0)}")
        lines.append(f"  - 有奖励目标的 {share(rs, lambda r: r['bonus'] > 0)}；奖励目标共 {sum(r['bonus'] for r in rs)} 个，"
                     f"要绕路（> 500）{sum(r['bonus_far'] for r in rs)} 个，贴着敌方据点（< 600）{sum(r['bonus_risky'] for r in rs)} 个，"
                     f"第一块可玩区里就有 {sum(r['bonus_first'] for r in rs)} 个")
        lines.append(f"  - 会扩边界或移动窗口的 {share(rs, lambda r: r['stages'] > 1 or r['moved'])}")
    lines += ['', '### 原版：出生点位置 × 类型', '', '| 类型 | 角落 | 边上 / 边外开进 | 中间 |', '|---|---|---|---|']
    for kind in ('护送', '摧毁', '突击队', '守点', '基地对抗', '救火', '解谜'):
        rs = [r for r in retail if r['kind'] == kind]
        if not rs:
            continue
        lines.append(f"| {kind} | {sum(r['place'] == 'corner' for r in rs)} | "
                     f"{sum(r['place'] in ('edge', 'entering') for r in rs)} | {sum(r['place'] == 'centre' for r in rs)} |")
    lines += ['', '原版从中间出发的：' + '、'.join(f"{r['name']}（{r['kind']}）" for r in retail if r['place'] == 'centre') + '；'
              '扩到最后才变成中间的：' + ('、'.join(f"{r['name']}（{r['kind']}）" for r in retail
                                         if r['place'] != 'centre' and r['place_last'] == 'centre') or '无') + '。']
    with open(os.path.join(HERE, 'layout.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[-30:]))


if __name__ == '__main__':
    main()
