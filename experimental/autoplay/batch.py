r"""Many auto-played runs of a level and what they say: win rate (with its 95 % interval), how long the runs last, how
the lost ones were lost, the fastest win's script (a shortcut candidate), whether the wins sit in the design's band.

  python -I -X utf8 experimental/autoplay/batch.py a3 a4 [--runs 20] [--personality rush counter ...] [--procs 8]
                                                       [--out work/autoplay] [--md docs/story/autoplay-report.md]
                                                       [--check-replay 3]

Each run is seeded (level / personality / seed), so a number here is reproducible; each run's script is written to
<out>/<level>/<personality>_<seed>.txt (work/ is not in git), the statistics to <out>/<level>/summary.json. A
`--check-replay k` plays the first k scripts of each cell again from the text alone and says if the ending moved:
the framework's own proof that a run is a script.

The simulator is the instrument: until the engine inventory is met (ADR 0026) these numbers are a reference only.
"""
import argparse
import concurrent.futures
import importlib.util
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def _autoplay():
    """autoplay.py by file (it loads the simulator and the players, and puts the cnv folders on the path)."""
    if 'autoplay' not in sys.modules:
        spec = importlib.util.spec_from_file_location('autoplay', os.path.join(HERE, 'autoplay.py'))
        mod = importlib.util.module_from_spec(spec)
        sys.modules['autoplay'] = mod
        spec.loader.exec_module(mod)
    return sys.modules['autoplay']


autoplay = _autoplay()
players, sim = autoplay.players, autoplay.sim

BAND = (8 * 60.0, 15 * 60.0)       # the design's length for a level (handoff-phase4: 暂定 8~15 分钟)


def one(args):
    """Worker: (level, personality, seed) -> the run as a plain dict (the simulator is rebuilt in each process)."""
    level, personality, seed, diff = args
    run, _ = autoplay.play(level, personality, seed, diff)
    return {'seed': seed, 'outcome': run.outcome, 't': run.t, 'lost': run.lost, 'left': run.left,
            'orders': len(run.lines), 'skipped': run.skipped, 'escort_lost': run.escort_lost, 'ending': run.ending, 'lines': run.lines}


def again(args):
    level, lines, diff = args
    return autoplay.replay(level, lines, diff)


def wilson(k, n, z=1.96):
    """The 95 % Wilson interval of k wins in n runs."""
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def spread(xs):
    """min / quartiles / max of a list of seconds (None for an empty list)."""
    if not xs:
        return None
    xs = sorted(xs)
    q = statistics.quantiles(xs, n=4, method='inclusive') if len(xs) > 1 else [xs[0]] * 3
    return {'min': xs[0], 'q1': q[0], 'median': q[1], 'q3': q[2], 'max': xs[-1], 'mean': statistics.fmean(xs)}


def summarize(runs):
    n = len(runs)
    wins = [r for r in runs if r['outcome'] == 'win']
    lows, highs = wilson(len(wins), n)
    ends = {}
    for r in runs:
        if r['outcome'] != 'win':
            key = r['ending'] or r['outcome']
            ends[key] = ends.get(key, 0) + 1
    return {'runs': n, 'wins': len(wins), 'win_rate': len(wins) / n if n else 0.0, 'ci95': [lows, highs],
            'outcomes': {o: sum(1 for r in runs if r['outcome'] == o) for o in ('win', 'lose', 'timeout', 'stuck')},
            'time_all': spread([r['t'] for r in runs]), 'time_win': spread([r['t'] for r in wins]),
            'time_lose': spread([r['t'] for r in runs if r['outcome'] == 'lose']),
            'in_band': sum(1 for r in wins if BAND[0] <= r['t'] <= BAND[1]),
            'lost_units': spread([float(r['lost']) for r in runs]),
            'escort_lost': spread([float(r['escort_lost']) for r in runs]),
            'lost_by': ends,
            'fastest_win': min(((r['t'], r['seed']) for r in wins), default=None)}


def cell(pool, level, personality, seeds, diff):
    runs = list(pool.map(one, [(level, personality, k, diff) for k in seeds]))
    return sorted(runs, key=lambda r: r['seed'])


def mm(t):
    return sim.mmss(t) if t is not None else '—'


def row(personality, s):
    w, a = s['time_win'], s['time_all']
    lo, hi = s['ci95']
    return (f"| {personality} | {s['wins']}/{s['runs']} | {s['win_rate']:.0%}（{lo:.0%}～{hi:.0%}） | "
            f"{mm(w['median']) + '（' + mm(w['min']) + '～' + mm(w['max']) + '）' if w else '—'} | "
            f"{mm(a['median'])}（{mm(a['q1'])}～{mm(a['q3'])}） | {s['in_band']} | "
            f"{s['lost_units']['median']:.0f}{' / 护送丢 ' + format(s['escort_lost']['median'], '.0f') if s['escort_lost']['max'] else ''} | {'；'.join(f'{k}×{v}' for k, v in sorted(s['lost_by'].items())) or '—'} |")


def table(level, summaries):
    head = ['| 性格 | 赢 | 胜率（95% 区间） | 赢局时长 中位（最短～最长） | 全部局时长 中位（四分位） | 落在 8～15 分钟的赢局 | 丢单位 中位 | 没赢的收场 |',
            '|---|---|---|---|---|---|---|---|']
    return head + [row(p, s) for p, s in summaries.items()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('levels', nargs='+')
    ap.add_argument('--runs', type=int, default=20)
    ap.add_argument('--personality', nargs='*', default=list(players.PERSONALITIES))
    ap.add_argument('--procs', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument('--out', default=os.path.join((os.environ.get('CNV_WORK') or os.path.join(ROOT, 'work')), 'autoplay'))
    ap.add_argument('--md', default='', help='write the tables here as markdown')
    ap.add_argument('--check-replay', type=int, default=0)
    ap.add_argument('--difficulty', default='normal', choices=list(sim.LEVELS))
    a = ap.parse_args()
    seeds = range(1, a.runs + 1)
    md = ['# 自动玩家：胜率与时长（模拟器，参考用）', '',
          f'每格 {a.runs} 局，难度 {a.difficulty}，种子 1～{a.runs}；模拟器规则没达到引擎清单前只作参考（ADR 0026）。', '']
    bad = 0
    with concurrent.futures.ProcessPoolExecutor(a.procs) as pool:
        for level in a.levels:
            folder = os.path.join(a.out, level)
            os.makedirs(folder, exist_ok=True)
            summaries = {}
            for personality in a.personality:
                runs = cell(pool, level, personality, seeds, a.difficulty)
                for r in runs:
                    with open(os.path.join(folder, f'{personality}_{r["seed"]}.txt'), 'w', encoding='utf-8') as f:
                        f.write(f'# autoplay {level} {personality} #{r["seed"]}: {r["outcome"]} {mm(r["t"])}\n')
                        f.write('\n'.join(r['lines']) + '\n')
                summaries[personality] = summarize(runs)
                if a.check_replay:
                    for r, got in zip(runs[:a.check_replay], pool.map(again, [(level, r['lines'], a.difficulty)
                                                                                for r in runs[:a.check_replay]])):
                        if r['outcome'] in ('win', 'lose') and (got[0] != r['outcome'] or abs(got[1] - r['t']) > 1e-6):
                            bad += 1
                            print(f'REPLAY DIFFERS {level} {personality} #{r["seed"]}: {r["outcome"]} {mm(r["t"])} -> {got}')
                s = summaries[personality]
                print(f'{level} {personality}: {s["wins"]}/{s["runs"]} win, median {mm((s["time_all"] or {}).get("median"))}',
                      flush=True)
            with open(os.path.join(folder, 'summary.json'), 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=1)
            md += [f'## {level}', ''] + table(level, summaries) + ['']
            for p, s in summaries.items():
                if s['fastest_win']:
                    md.append(f'- {p} 最快的赢：{mm(s["fastest_win"][0])}（种子 {s["fastest_win"][1]}，脚本 `work/autoplay/{level}/{p}_{s["fastest_win"][1]}.txt`）')
            md.append('')
    if a.md:
        with open(a.md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(md) + '\n')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
