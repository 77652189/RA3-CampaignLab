r"""A built map's terrain against the retail campaign maps (docs/design/principles.md P24-P27): the design line's
ruler (docs/design/teardowns/data/terrain_measure.py, read only here) run on one map -- a preview's .map, a mod's
.big or a mod name -- and set against the retail maps' quartiles from its table (terrain.json, the 40 retail rows).

  python -I -X utf8 experimental/campaign/terrainref.py <map or mod>     -> TERRAIN lines (what cnv_preview shows)

Read over the last stage (the whole playable area by the end), except 'first used' (the first stage's).
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, 'docs', 'design', 'teardowns', 'data')
TABLE = os.path.join(DATA, 'terrain.json')

# (label, where, key, the better side: 'up' more is closer to retail, 'down' less, '' either)
MEASURES = [
    ('主路过的隘口', 'terrain', 'chokes_on_main', 'up'),            # P27
    ('主路旁有高地的比例', 'terrain', 'overlook', 'up'),            # P27
    ('隘口', 'terrain', 'chokes', 'up'),
    ('路口 / km²', 'terrain', 'junctions_per_km2', 'up'),
    ('能上去的高台', 'terrain', 'raised_plateaus', 'up'),          # P26
    ('坡道', 'terrain', 'ramps', 'up'),
    ('能驻军的建筑', 'terrain', 'garrison', 'up'),                 # P25
    ('墙段', 'terrain', 'cover', 'up'),
    ('任务用到的比例', 'use', 'used', 'up'),                       # P24
    ('空地块', 'roles', 'empty', 'down'),
    ('远景（走不到）', 'terrain', 'backdrop', ''),
]
SHARES = {'overlook', 'used', 'empty', 'backdrop'}


def value(stage, where, key):
    if where == 'roles':
        return stage['use']['roles'].get(key)
    return stage[where].get(key)


def retail_ranges():
    """{key: (q1, median, q3)} over the retail rows' last stages."""
    data = json.load(open(TABLE, encoding='utf-8'))
    rows = [v for k, v in data.items() if not k.startswith('ours_') and v.get('stages')]
    out = {}
    for label, where, key, _ in MEASURES:
        vs = sorted(x for x in (value(r['stages'][-1], where, key) for r in rows) if x is not None)
        if len(vs) >= 4:
            q = statistics.quantiles(vs, n=4)
            out[key] = (q[0], statistics.median(vs), q[2])
    return out


def measure(source):
    sys.path[:0] = [p for p in (HERE, DATA) if p not in sys.path]       # python -I leaves the script's folder out
    import maprender
    import terrain_measure
    return terrain_measure.measure(os.path.basename(source), maprender.load(source))


def report(source):
    got = measure(source)
    if not got.get('stages'):
        return ['TERRAIN no stage measured']
    last, ranges, out, low = got['stages'][-1], retail_ranges(), [], []
    for label, where, key, better in MEASURES:
        v = value(last, where, key)
        if v is None or key not in ranges:
            continue
        q1, med, q3 = ranges[key]
        off = (better == 'up' and v < q1) or (better == 'down' and v > q3)
        if off:
            low.append(label)
        f = (lambda x: f'{x:.0%}') if key in SHARES else (lambda x: f'{round(x, 1):g}')
        out.append(f'{label} {f(v)}（原版 {f(q1)}～{f(q3)}，中位 {f(med)}）' + (' ←' if off else ''))
    first = got['stages'][0]['use']['used']
    head = 'TERRAIN ' + ('和原版范围比，偏离：' + '、'.join(low) if low else '都在原版范围里') + f'；第一块用到 {first:.0%}'
    return [head] + ['TERRAIN ' + x for x in out]


if __name__ == '__main__':
    print('\n'.join(report(sys.argv[1])))
