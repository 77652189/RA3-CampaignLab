"""The playtest report (experimental/cnv/proxy/report.py) on the toy world: the keys a level reads, the counts, the goals,
the Chinese summary. Like test_proxy.py this pins the playtester, not retail."""
import json

from proxy import player as pp
from proxy import report as rp
from proxy import world as pw
from test_proxy import AI, AV, SPECS, _foe, _mine, _obs, _world

KEYS = {'label', 'format', 'style', 'result', 'frames', 'seconds', 'sorties', 'retreats', 'defends', 'pullbacks',
        'rejoins', 'builds', 'switches', 'spent', 'firsts', 'peak_army', 'losses', 'worse_off', 'goals', 'moments'}


def _no_structures(w):
    return lambda obs: 'win' if not any(e.owner == 'Enemy' and 'STRUCTURE' in e.spec.kindof
                                        for e in w.ents.values()) else None


def _barracks_run(style=None, label='default', goals=()):
    w = _world(('SovietBarracks', 1500, 1500), money=4000)
    tr = rp.run(w, pp.ProxyPlayer(style), 15 * 400, end=_no_structures(w), label=label)
    return w, tr, rp.report(tr, goals)


def test_report_keys_and_json():
    _, _, rep = _barracks_run()
    assert set(rep) == KEYS and rep['format'] == rp.FORMAT
    assert json.loads(rp.dumps(rep)) == rep                 # plain JSON values only
    assert rep['style']['pullback'] == 0.35
    assert isinstance(rep['style']['source_kinds'], list)
    assert set(rep['firsts']) == {'scout', 'contact', 'build', 'sortie', 'own_loss', 'kill'}


def test_barracks_run_what_happened():
    w, tr, rep = _barracks_run(goals=[rp.destroyed('SovietBarracks', '拆兵营'), rp.used_power('Command_IceWall')])
    assert rep['result'] == 'win' and rep['frames'] == tr.observations[-1].frame
    dead = next(f for f, t, _ in w.dead if t == 'SovietBarracks')
    assert dead <= rep['frames'] <= dead + 15               # the run stops at the first decision after the end
    assert rep['builds'] == {AI: sum(1 for _, o in tr.taken if o.kind == 'build')} and rep['switches'] == []
    assert rep['spent'] == 700 * rep['builds'][AI]
    assert rep['sorties'] >= 1 and rep['pullbacks'] >= 1
    f = rep['firsts']
    assert f['scout'] < f['contact'] <= f['build'] < f['sortie']
    assert rep['goals']['拆兵营'] == {'met': True, 'frame': dead, 'note': ''}
    assert rep['goals']['used Command_IceWall']['met'] is False
    enemy = rep['losses']['enemy']
    assert enemy['by_kind']['structure'] == {'count': 1, 'value': 500}
    assert enemy['count'] == sum(1 for _, _, o in w.dead if o == 'Enemy')
    me = rep['losses']['me']['value']
    assert rep['worse_off'] == ('me' if me > enemy['value'] else 'enemy' if enemy['value'] > me else 'even')
    assert all(m['what'] in rp.KEY for m in rep['moments'])
    assert [m['frame'] for m in rep['moments']] == sorted(m['frame'] for m in rep['moments'])


def test_switching_counters_and_defending():
    """Two sources, infantry and tanks: the build switches between the two counters, each switch says against
    what; the waves pull the army home, counted once per spell of defending."""
    w = _world(('SovietBarracks', 1500, 1500), ('SovietWarFactory', 1500, 0), money=4000)
    # focused defence (the toy run this pins: with the default attack-move the tanks die sooner, one switch only)
    tr = rp.run(w, pp.ProxyPlayer(pp.Style(defend_move=False)), 15 * 240)
    rep = rp.report(tr)
    assert rep['result'] == 'timeout' and set(rep['builds']) == {AI, AV}
    assert rep['switches'] and all(s['from'] != s['to'] and s['against'] in pw.KINDS for s in rep['switches'])
    assert {s['against'] for s in rep['switches']} == {'infantry', 'vehicle'}
    assert rep['defends'] >= 1 and rep['defends'] == sum(1 for _, w_, _ in tr.log if w_ == 'defend')


def test_defend_logged_once_per_spell():
    """Raiders near home for three decisions, then a different raider (still a defence): one 'defend'; home clear
    (the army goes for the barracks), then raiders again: a second."""
    p = pp.ProxyPlayer()
    army = [_mine(i, x=0, y=0) for i in (1, 2, 3)]
    barracks = _foe(9, 'SovietBarracks', {'STRUCTURE', 'FS_BARRACKS'}, 1500, 1500)
    near = lambda i: _foe(i, 'SovietAntiVehicleInfantry', {'INFANTRY'}, 200, 0)
    for f, seen in ((0, [barracks, near(5)]), (15, [barracks, near(5)]), (30, [barracks, near(6)])):
        p.decide(_obs(army, seen, frame=f))
    assert [w_ for _, w_, _ in p.log].count('defend') == 1
    p.decide(_obs(army, [barracks], frame=45))              # 5 and 6 are in sight range and not seen: gone
    assert p.target[0] == 'source'
    p.decide(_obs(army, [barracks, near(7)], frame=60))
    assert [w_ for _, w_, _ in p.log].count('defend') == 2


def test_sortie_and_retreat_counts_follow_the_log():
    tr = rp.Trace('t', pp.Style(), [(0, 'scout', 'x'), (30, 'go', 'source A#1 with 3'), (45, 'attack', 'a'),
                                    (60, 'attack', 'a'), (90, 'regroup', '1 vs 9'), (150, 'go', 'source A#1 with 4'),
                                    (200, 'pull back', 'u'), (300, 'rejoin', 'u')],
                  [], [], [], 'lose', 300)
    rep = rp.report(tr)
    assert (rep['sorties'], rep['retreats'], rep['pullbacks'], rep['rejoins']) == (2, 1, 1, 1)
    assert rep['firsts']['sortie'] == 30 and rep['result'] == 'lose'
    assert [m['what'] for m in rep['moments']] == ['go', 'regroup', 'go', 'pull back', 'rejoin']


def test_goals_built_reached():
    _, tr, _ = _barracks_run()
    rep = rp.report(tr, [rp.built(AI), rp.built(AV), rp.reached((1500, 1500), name='摸到兵营', note='侦察'),
                         rp.reached((-5000, -5000))])
    g = rep['goals']
    assert g[f'built {AI}']['met'] and not g[f'built {AV}']['met']
    assert g['摸到兵营']['met'] and g['摸到兵营']['note'] == '侦察' and not g['reached (-5000, -5000)']['met']
    assert g[f'built {AI}']['frame'] == rep['firsts']['build']


def test_power_at_where_the_ice_went():
    ice = lambda f, pos, power='Ice': (f, pw.Order('power', (1,), pos=pos, power=power))
    tr = rp.Trace('t', pp.Style(), [], [], [ice(30, (1000, 0)), ice(90, (0, 2000)), (95, pw.Order('power', (1,),
                  target=7, power='Ice'))], None, 'timeout', 200)
    mouths = [(0, 2000), (500, 500)]
    assert rp.power_at(mouths).test(tr) == 90                       # the first order near one of the places
    assert rp.power_at((1000, 50), radius=60).test(tr) == 30        # one place, inside the radius
    assert rp.power_at((1000, 100), radius=60).test(tr) is None
    assert rp.power_at(mouths, command='Other').test(tr) is None
    assert rp.power_at(mouths, within=(0, 60)).test(tr) is None     # iced there, but too late
    assert rp.power_at([(1000, 0), (0, 2000)], within=(50, None)).test(tr) == 90
    rep = rp.report(tr, [rp.power_at(mouths, name='冻街口', note='会场')])
    assert rep['goals']['冻街口'] == {'met': True, 'frame': 90, 'note': '会场'}


class _NoScore:
    """A world without a score screen (no losses())."""
    def __init__(self, w):
        self.w = w

    def observe(self):
        return self.w.observe()

    def issue(self, o):
        return self.w.issue(o)

    def step(self, n):
        self.w.step(n)


def test_without_a_score_screen_own_losses_from_sight():
    w = _world(('SovietBarracks', 1500, 1500), ('SovietWarFactory', 1500, 0), money=4000)
    rep = rp.report(rp.run(_NoScore(w), pp.ProxyPlayer(), 15 * 240))
    assert rep['losses']['enemy'] is None and rep['worse_off'] is None
    own = [t for _, t, o in w.dead if o == 'Player']
    assert own and rep['losses']['me']['count'] == len(own)
    assert rep['losses']['me']['value'] == sum(SPECS[t].cost for t in own)
    assert '敌方损失不明' in rp.summary(rep)


def test_summary_and_compare():
    _, _, a = _barracks_run(label='默认', goals=[rp.destroyed('SovietBarracks', '拆兵营')])
    _, _, b = _barracks_run(pp.Style(min_army=99), label='很谨慎', goals=[rp.destroyed('SovietBarracks', '拆兵营')])
    s = rp.summary(a)
    assert s.splitlines()[0].startswith('试玩 默认：赢，用时 ')
    assert '出击 ' in s and '拆兵营 打通' in s and '按钱算' in s and '关键时刻：' in s
    assert b['sorties'] == 0 and b['result'] == 'timeout' and '拆兵营 没打通' in rp.summary(b)
    c = rp.compare([a, b]).splitlines()
    assert len(c) == 3 and c[0].startswith('默认：赢') and c[1].startswith('很谨慎：到时间没分胜负')
    assert c[2] == '共 2 局，赢 1；巧解打通：拆兵营 1/2'
    assert rp.clock(None) == '—' and rp.clock(15 * 75) == '1:15'


def test_report_is_deterministic():
    assert _barracks_run()[2] == _barracks_run()[2]
