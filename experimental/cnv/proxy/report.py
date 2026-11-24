"""The playtest report: run the proxy player on a world once, then say what happened -- for a machine (report(), a
dict of plain JSON values, dumps()) and for a person (summary(), a few lines of Chinese; compare() for several runs).

A run (run()) is proxy/player.play plus a record: every observation the player made, every order the world took,
and how the game ended (an `end(obs)` the level gives: 'win' / 'lose' / None). The report reads only that record,
the player's own log and, when the world has it, the score screen (World.losses, proxy/world.Loss): nothing the
player could not have known after the game.

What a report holds (FORMAT 1; the keys are the contract, tests/test_proxy_report.py pins them):
    label, format, style          which run, and the player's Style knobs
    result, frames, seconds       'win' | 'lose' | 'timeout', when the run stopped
    sorties, retreats, defends    the army committed to a new target ('go') / called a sortie off ('regroup') /
                                  turned to enemies near home ('defend', once per spell of defending)
    pullbacks, rejoins            wounded units sent home / back into the army
    builds, switches, spent       units the world took orders for {template: n}; each change of what is being built
                                  (换兵: frame, from, to, against which kind); money paid for them
    firsts                        first frame of: scout, contact (scout found), build, sortie, own loss, kill
    peak_army                     most own units at one observation
    losses                        {'me': side, 'enemy': side | None}; side = {count, value, by_kind {kind: {count,
                                  value}}}; enemy None when the world has no score screen (then 'me' comes from the
                                  units that left the player's observations)
    worse_off                     'me' | 'enemy' | 'even' | None: who lost more money's worth
    goals                         {name: {met, frame, note}}: the level's puzzle checks (巧解), Goal.test(trace)
    moments                       [{frame, what, detail}] the key log entries, in order

Goals are the level's, not the player's: a Goal's test reads the whole Trace and returns the first frame the thing
held, or None. destroyed / used_power / built / reached build the common ones. Nothing here is from any program.
"""
import dataclasses
import json
import math

from proxy import world as pw

FORMAT = 1
FPS = 15
KEY = ('scout found', 'gone', 'build', 'go', 'regroup', 'defend', 'pull back', 'rejoin', 'power', 'block', 'post')
KIND_ZH = {'infantry': '步兵', 'vehicle': '车辆', 'air': '飞机', 'ship': '船', 'structure': '建筑'}
RESULT_ZH = {'win': '赢', 'lose': '输', 'timeout': '到时间没分胜负'}


@dataclasses.dataclass
class Trace:
    label: str
    style: object
    log: list                        # the player's log, [(frame, what, detail)]
    observations: list               # [Observation], one per decision
    taken: list                      # [(frame, Order)] the orders the world accepted
    losses: object                   # [Loss] from the world's score screen, or None
    result: str                      # 'win' | 'lose' | 'timeout'
    frame: int                       # the frame the run stopped at


@dataclasses.dataclass(frozen=True)
class Goal:
    name: str
    test: object                     # test(trace) -> first frame it held, or None
    note: str = ''


def run(world, proxy, frames, every=15, end=None, label=''):
    """player.play with a record. end(obs) -> 'win' / 'lose' stops the run at that decision."""
    observations, taken = [], []
    result = 'timeout'
    f = 0
    obs = None
    while f < frames:
        obs = world.observe()
        observations.append(obs)
        verdict = end(obs) if end else None
        if verdict:
            result = verdict
            break
        for o in proxy.decide(obs):
            if world.issue(o):
                taken.append((obs.frame, o))
            elif hasattr(proxy, 'refused'):
                proxy.refused(obs, o)
        world.step(every)
        f += every
    last = world.observe().frame if result == 'timeout' else obs.frame
    losses = list(world.losses()) if hasattr(world, 'losses') else None
    return Trace(label, proxy.style, list(proxy.log), observations, taken, losses, result, last)


# --- goals the levels use ----------------------------------------------------------------------------------------
def destroyed(template, name=None, note=''):
    """The enemy's `template` died (needs the score screen)."""
    def test(tr):
        me = tr.observations[0].me if tr.observations else None
        return next((l.frame for l in tr.losses or () if l.template == template and l.owner != me), None)
    return Goal(name or f'destroyed {template}', test, note)


def used_power(command, name=None, note=''):
    def test(tr):
        return next((f for f, o in tr.taken if o.kind == 'power' and o.power == command), None)
    return Goal(name or f'used {command}', test, note)


def power_at(places, radius=150.0, command=None, name=None, note='', within=None):
    """Where a ground power went (the ice engineer's ice: 冰在哪): a 'power' order aimed at a point within `radius`
    of one of `places` ((x, y), or a list of them), of `command` (None: any power), during `within` ((first, last)
    frame, either None = open; None = any time). The order is the player's choice, so a level can ask "did he ice
    one of the street mouths" without the world's walls; whether the ice then held is the world's (a level reads the
    score screen or its own counters for that)."""
    pts = [places] if places and isinstance(places[0], (int, float)) else list(places)
    lo, hi = within or (None, None)

    def test(tr):
        for f, o in tr.taken:
            if o.kind != 'power' or o.pos is None or (command is not None and o.power != command):
                continue
            if (lo is not None and f < lo) or (hi is not None and f > hi):
                continue
            if any(math.hypot(o.pos[0] - p[0], o.pos[1] - p[1]) <= radius for p in pts):
                return f
        return None
    return Goal(name or f'power at {pts}', test, note)


def built(template, name=None, note=''):
    def test(tr):
        return next((f for f, o in tr.taken if o.kind == 'build' and o.template == template), None)
    return Goal(name or f'built {template}', test, note)


def reached(pos, radius=150.0, name=None, note=''):
    """An own unit came within radius of pos."""
    def test(tr):
        return next((obs.frame for obs in tr.observations
                     if any(math.hypot(u.x - pos[0], u.y - pos[1]) <= radius for u in obs.mine)), None)
    return Goal(name or f'reached {pos}', test, note)


# --- the report --------------------------------------------------------------------------------------------------
def _style(style):
    out = {}
    for f in dataclasses.fields(style):
        v = getattr(style, f.name)
        if isinstance(v, (set, frozenset)):
            v = sorted(v)
        out[f.name] = v
    return out


def _side(losses):
    by = {}
    for l in losses:
        k = by.setdefault(l.kind, {'count': 0, 'value': 0})
        k['count'] += 1
        k['value'] += l.cost
    return {'count': len(losses), 'value': sum(l.cost for l in losses), 'by_kind': dict(sorted(by.items()))}


def _own_losses_from_sight(tr):
    """Without a score screen: own units that left the observations (died -- the player cannot tell otherwise)."""
    out, last = [], {}
    for obs in tr.observations:
        now = {u.id: u for u in obs.mine}
        for i, u in last.items():
            if i not in now:
                out.append(pw.Loss(obs.frame, obs.me, u.template, pw.kind_of(u), u.cost))
        last = now
    return out


def _losses(tr):
    if not tr.observations:
        return {'me': _side([]), 'enemy': None}
    me, enemies = tr.observations[0].me, tr.observations[0].enemies
    if tr.losses is None:
        return {'me': _side(_own_losses_from_sight(tr)), 'enemy': None}
    return {'me': _side([l for l in tr.losses if l.owner == me]),
            'enemy': _side([l for l in tr.losses if l.owner in enemies])}


def _builds(tr):
    cost = {}
    for obs in tr.observations:
        for o in obs.offers:
            cost.setdefault((obs.frame, o.template), o.cost)
    why = {(f, d.split(' vs ')[0]): d.split(' vs ')[-1] for f, w, d in tr.log if w == 'build'}
    counts, switches, spent, prev = {}, [], 0, None
    for f, o in tr.taken:
        if o.kind != 'build':
            continue
        counts[o.template] = counts.get(o.template, 0) + 1
        spent += cost.get((f, o.template), 0)
        if prev is not None and o.template != prev:
            switches.append({'frame': f, 'from': prev, 'to': o.template, 'against': why.get((f, o.template))})
        prev = o.template
    return dict(sorted(counts.items())), switches, spent


def report(trace, goals=()):
    tr = trace
    count = lambda what: sum(1 for _, w, _ in tr.log if w == what)
    first = lambda what: next((f for f, w, _ in tr.log if w == what), None)
    losses = _losses(tr)
    builds, switches, spent = _builds(tr)
    me = losses['me']['value']
    enemy = losses['enemy']['value'] if losses['enemy'] is not None else None
    me_first = None
    if tr.losses is not None and tr.observations:
        mine = [l.frame for l in tr.losses if l.owner == tr.observations[0].me]
        kills = [l.frame for l in tr.losses if l.owner in tr.observations[0].enemies]
        me_first, kill_first = (min(mine) if mine else None), (min(kills) if kills else None)
    else:
        own = _own_losses_from_sight(tr)
        me_first, kill_first = (own[0].frame if own else None), None
    rep = {
        'label': tr.label,
        'format': FORMAT,
        'style': _style(tr.style),
        'result': tr.result,
        'frames': tr.frame,
        'seconds': round(tr.frame / FPS, 1),
        'sorties': count('go'),
        'retreats': count('regroup'),
        'defends': count('defend'),
        'pullbacks': count('pull back'),
        'rejoins': count('rejoin'),
        'builds': builds,
        'switches': switches,
        'spent': spent,
        'firsts': {'scout': first('scout'), 'contact': first('scout found'), 'build': first('build'),
                   'sortie': first('go'), 'own_loss': me_first, 'kill': kill_first},
        'peak_army': max((len(o.mine) for o in tr.observations), default=0),
        'losses': losses,
        'worse_off': None if enemy is None else ('me' if me > enemy else 'enemy' if enemy > me else 'even'),
        'goals': {},
        'moments': [{'frame': f, 'what': w, 'detail': str(d)} for f, w, d in tr.log if w in KEY],
    }
    for g in goals:
        f = g.test(tr)
        rep['goals'][g.name] = {'met': f is not None, 'frame': f, 'note': g.note}
    return rep


def dumps(rep):
    return json.dumps(rep, ensure_ascii=False, indent=1, sort_keys=True)


# --- for a person ------------------------------------------------------------------------------------------------
def clock(frame):
    if frame is None:
        return '—'
    s = int(frame // FPS)
    return f'{s // 60}:{s % 60:02d}'


def _side_zh(side):
    return f'{side["count"]} 个 / {side["value"]} 块'


def _worst_kind(side):
    if not side or not side['by_kind']:
        return None
    k = max(side['by_kind'], key=lambda k: (side['by_kind'][k]['value'], k))
    return KIND_ZH.get(k, k)


MOMENT_ZH = {'scout found': '发现', 'gone': '确认没了', 'build': '造', 'go': '出击', 'regroup': '收兵',
             'defend': '回防', 'pull back': '残血后撤', 'rejoin': '归队', 'power': '放技能',
             'block': '挡路'}


def summary(rep, moments=8):
    """A few lines of Chinese for a person reading the playtest."""
    st = rep['style']
    lines = [f'试玩 {rep["label"] or "（未命名）"}：{RESULT_ZH.get(rep["result"], rep["result"])}，'
             f'用时 {clock(rep["frames"])}（第 {rep["frames"]} 帧）',
             f'打法：残血 {st.get("pullback")} 后撤、{st.get("rejoin")} 归队；兵力到威胁的 {st.get("attack_ratio")} 倍'
             f'且至少 {st.get("min_army")} 个才出击，掉到 {st.get("regroup_ratio")} 倍收兵；'
             f'关卡技能挡路 {"每波最多 " + str(st["block"]) + " 处" if st.get("block") else "不用"}']
    sw = rep['switches']
    sw_zh = '；'.join(f'{clock(s["frame"])} {s["from"]} → {s["to"]}' + (f'（对{KIND_ZH.get(s["against"], s["against"])}）'
                                                                       if s['against'] else '') for s in sw[:3])
    lines.append(f'出击 {rep["sorties"]} 次，收兵 {rep["retreats"]} 次，回防 {rep["defends"]} 次，'
                 f'残血后撤 {rep["pullbacks"]} 次（归队 {rep["rejoins"]}）；造兵 {sum(rep["builds"].values())} 个、'
                 f'花 {rep["spent"]} 块，换兵 {len(sw)} 次' + (f'：{sw_zh}' if sw else ''))
    lo = rep['losses']
    if lo['enemy'] is None:
        lines.append(f'损失：我方 {_side_zh(lo["me"])}（没有结算数据，敌方损失不明）')
    else:
        who = {'me': '我方吃亏', 'enemy': '敌方吃亏', 'even': '打平'}[rep['worse_off']]
        worst = _worst_kind(lo['me'])
        lines.append(f'损失：我方 {_side_zh(lo["me"])}，敌方 {_side_zh(lo["enemy"])}，按钱算{who}'
                     + (f'；我方主要丢的是{worst}' if worst else ''))
    if rep['goals']:
        lines.append('巧解：' + '；'.join(f'{n} ' + (f'打通（{clock(g["frame"])}）' if g['met'] else '没打通')
                                          for n, g in rep['goals'].items()))
    key = [m for m in rep['moments'] if m['what'] in ('scout found', 'go', 'regroup', 'defend', 'power', 'block')]
    if key:
        lines.append('关键时刻：' + '；'.join(f'{clock(m["frame"])} {MOMENT_ZH[m["what"]]} {m["detail"]}'
                                            for m in key[:moments]) + ('……' if len(key) > moments else ''))
    return '\n'.join(lines)


def compare(reps):
    """Several runs side by side (many runs, many Styles): one line each, then the tally."""
    lines = []
    for r in reps:
        lo = r['losses']
        enemy = lo['enemy']['value'] if lo['enemy'] is not None else '?'
        met = sum(g['met'] for g in r['goals'].values())
        lines.append(f'{r["label"] or "-"}：{RESULT_ZH.get(r["result"], r["result"])} {clock(r["frames"])}，'
                     f'出击 {r["sorties"]} 收兵 {r["retreats"]}，'
                     f'挡路 {sum(m["what"] == "block" for m in r["moments"])} 次，损失 我 {lo["me"]["value"]} / 敌 {enemy}，'
                     f'巧解 {met}/{len(r["goals"])}')
    if reps:
        wins = sum(r['result'] == 'win' for r in reps)
        names = sorted({n for r in reps for n in r['goals']})
        tally = '，'.join(f'{n} {sum(r["goals"].get(n, {}).get("met", False) for r in reps)}/{len(reps)}' for n in names)
        lines.append(f'共 {len(reps)} 局，赢 {wins}' + (f'；巧解打通：{tally}' if tally else ''))
    return '\n'.join(lines)
