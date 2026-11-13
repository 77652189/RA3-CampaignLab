"""experimental/cnv/teamlog.py reads ra3ext's CNVTeams lines (engine line D round 68). The lines below are copied from
bench run CampAICrT3A_mcp_1112_015804 (checks/engine_aiteams.py aicr3t:a, PASS): the CreateUnits MinUnits 3 team
holds 2 Guardians at frame 511 and activates with 3 at frame 646."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]

import teamlog  # noqa: E402

LOG = """ra3ext loaded pid=1 exe=x: ok
team: frame=511 list=0 proto=08F46B20 name1='Soviet_1' name2='7203be5f_SimpleAttack_0_0' rel=1 slot=0 team=0B14B4D0 active=0 n=2 ids=3176@3881:3001,3177@3881:3041
team: frame=511 list=0 proto=08F56190 name1='Soviet_1' name2='defaultSkirmishTeamSoviet_1' rel=1 slot=0 team=081C3150 active=1 n=12 ids=36@0:0,3163@3850:3400,3166@3650:3240,3167@3650:3190,3168@3650:3140,3169@3650:3090,3170@3850:3150,3171@3850:3800,3172@4100:3800,3173@3892:3106,3174@3813:3155,3175@3882:3124
team: frame=511 list=1 proto=086012E0 name1='Soviet_1' name2='teamSoviet_1' rel=1 slot=0 team=081BFA50 active=1 n=0 ids=
teams: frame=511 player=06E37D70 index=4 ai=08B6FE60 protos=3 teams=3
team: frame=646 list=0 proto=08F46B20 name1='Soviet_1' name2='7203be5f_SimpleAttack_0_0' rel=1 pri=3 slot=0 team=0B14B4D0 active=1 n=3 ids=3176@3876:3003,3177@3892:3041,3178@3875:3110
team: frame=646 list=1 proto=086012E0 name1='Soviet_1' name2='teamSoviet_1' rel=1 slot=0 team=081BFA50 active=1 n=0 ids=
teams: frame=646 player=06E37D70 index=4 ai=08B6FE60 protos=3 teams=3
"""


def _log(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG)
    return str(p)


def test_team_size_by_logged_name(tmp_path):
    p = _log(tmp_path)
    assert teamlog.team_size(p, '7203be5f_SimpleAttack_0_0', 600) == 2
    assert teamlog.team_size(p, '7203be5f_SimpleAttack', 646) == 3
    assert teamlog.team_size(p, 'defaultSkirmishTeamSoviet_1', 511) == 12
    assert teamlog.team_sizes(p, 'teamSoviet_1', 646) == [0]
    assert teamlog.team_size(p, 'nothing', 646) == 0
    assert teamlog.team_size(p, '7203be5f_SimpleAttack', 100) == 0      # before the first sample
    assert teamlog.members(p, '7203be5f_SimpleAttack', 646) == [[(3176, 3876, 3003), (3177, 3892, 3041),
                                                                (3178, 3875, 3110)]]
    assert [t['active'] for _, ts in teamlog.samples(p) for t in ts if 'SimpleAttack' in t['names'][1]] == [0, 1]


def test_state_id_is_hashed_the_ai_way(tmp_path):
    p = _log(tmp_path)
    assert teamlog.team_size(p, 'CNVStateTF', 646) == 3            # FastHash('cnvstatetf') = 7203be5f
    assert teamlog.team_size(p, 'CNVStateTF_SimpleAttack', 511) == 2


# Engine line D round 78: copied from bench run CampAIAesOnA_mcp_1112_111517 (aiaeson:a, PASS): the StaticDefense
# Guardian 3166 idles (micro state 8, AI state 1, not ready) until its team takes enemy 3165 at frame 362 (an order on
# the object plus a point), then state 6 with that target.
LOG78 = """cmd: frame=158 msg=092CB218 type=1fb player=4 n=1 args=0:12
cmd: frame=158 msg=0860E3D0 type=22c player=4 n=5 args=7:3850.0:3400.0:212.5,1:-3.042,0:2,2:0,2:0
team: frame=361 list=0 proto=08EBA720 name1='Soviet_1' name2='7203be5f_StaticDefense_0_0' rel=1 slot=0 team=0AED8650 active=1 n=1 ids=3166@3058:3035
tstate: frame=361 team=0AED8650 mstate=8 prev=8 secs=12.00 tgt=-1 chosen=-1 tact=3163 idle=0 ready=0 mem=3166:1:0
teams: frame=361 player=06FA9D70 index=4 ai=080E8F60 protos=3 teams=3
cmd: frame=362 msg=0AEA2890 type=1f5 player=4 n=3 args=2:1,2:0,4:3166
cmd: frame=362 msg=0AEA2908 type=20d player=4 n=2 args=4:3165,7:2850.0:3300.0:205.0
team: frame=376 list=0 proto=08EBA720 name1='Soviet_1' name2='7203be5f_StaticDefense_0_0' rel=1 slot=0 team=0AED8650 active=1 n=1 ids=3166@2999:3076
tstate: frame=376 team=0AED8650 mstate=6 prev=8 secs=0.00 tgt=3165 chosen=-1 tact=3163 idle=0 ready=0 mem=3166:10:0
teams: frame=376 player=06FA9D70 index=4 ai=080E8F60 protos=3 teams=3
"""


def test_team_state_and_orders(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG78)
    p = str(p)
    s = teamlog.state_at(p, 'CNVStateTF_StaticDefense', 370)
    assert (s['frame'], s['mstate'], s['tgt'], s['tact'], s['ready'], s['mem']) == (361, 8, -1, 3163, 0, [(3166, 1, 0)])
    s = teamlog.state_at(p, 'CNVStateTF_StaticDefense', 376)
    assert (s['mstate'], s['prev'], s['tgt'], s['mem']) == (6, 8, 3165, [(3166, 10, 0)])
    assert teamlog.state_at(p, 'CNVStateTF_StaticDefense', 100) is None
    assert teamlog.commands(p)[1] == (158, 0x22c, [(3850.0, 3400.0, 212.5), -3.042, 2, 0, 0])
    assert teamlog.last_command(p, 361) == (158, 0x22c, [(3850.0, 3400.0, 212.5), -3.042, 2, 0, 0])
    assert teamlog.last_command(p, 400, (0x20d,)) == (362, 0x20d, [3165, (2850.0, 3300.0, 205.0)])
    assert [c[1] for c in teamlog.commands(p, (0x1f5, 0x1fb))] == [0x1fb, 0x1f5]


def test_aesthetics_calls_with_their_state_and_orders(tmp_path):
    """D round 83: the aesthetics manager's calls -- the state it saw on entry, its gate, and the orders it queued
    (tagged src=aes:N on the cmd lines); older lines without dest= / src= still parse."""
    p = tmp_path / 'ra3ext.log'
    p.write_text('\n'.join([
        'tstate: frame=176 team=0A mstate=8 prev=8 secs=1.00 tgt=-1 chosen=-1 tact=3163 idle=0 ready=0 mem=3166:1:0',
        'aes: frame=190 call=3 team=0A x=3850.0 y=3400.0 r=2000.0 outer=3000.0 mode=0 since=0 gate=1',
        'tstate: frame=190 team=0A mstate=8 prev=8 secs=2.00 tgt=-1 chosen=-1 tact=3163 idle=0 ready=1 '
        'mem=3166:16:1 dest=3166@3850.0:3400.0 at=aes',
        'aesend: frame=190 call=3 mode=1 since=0 sent=2',
        'cmd: frame=191 msg=0B type=1f5 player=2 n=3 args=2:1,2:0,4:3166 src=aes:3',
        'cmd: frame=191 msg=0C type=22c player=2 n=5 args=7:1859.9:3201.0:205.0,1:-3.042,0:3,0:0,0:0 src=aes:3',
        'cmd: frame=192 msg=0D type=214 player=2 n=1 args=7:1.0:2.0:3.0 src=x123456',
    ]))
    p = str(p)
    [c] = teamlog.aesthetics(p)
    assert (c['frame'], c['call'], c['centre'], c['r'], c['gate'], c['mode'], c['mode_after'], c['sent']) == \
        (190, 3, (3850.0, 3400.0), 2000.0, 1, 0, 1, 2)
    assert (c['state']['ready'], c['state']['mem'], c['state']['dest'], c['state']['at']) == \
        (1, [(3166, 16, 1)], {3166: (3850.0, 3400.0)}, 'aes')
    assert [o[1] for o in c['orders']] == [0x1f5, 0x22c]
    assert c['orders'][1][2][0] == (1859.9, 3201.0, 205.0)
    old = teamlog.states(p)['0A'][0]
    assert (old['dest'], old['at']) == ({}, None)
    assert [x[1] for x in teamlog.commands(p)] == [0x1f5, 0x22c, 0x214]


def test_member_goal_object_and_heading(tmp_path):
    """D round 86: aim= each member's AI goal object and where it is (`!` = no longer in the object map, 0 = none),
    hd= the body heading in degrees; an aes snapshot still ends with at=; older lines give {}."""
    p = tmp_path / 'ra3ext.log'
    p.write_text('\n'.join([
        'tstate: frame=300 team=0A mstate=6 prev=8 secs=0.50 tgt=3165 chosen=3165 tact=3163 idle=0 ready=0 '
        'mem=3166:10:0,3167:10:0,3168:1:0 dest=3166@10.0:20.0 aim=3166>3165@-300.5:12.0,3167>3170!,3168>0 '
        'hd=3166:180,3167:-90,3168:0',
        'tstate: frame=301 team=0A mstate=6 prev=8 secs=0.50 tgt=3165 chosen=3165 tact=3163 idle=0 ready=0 '
        'mem=3166:10:0 dest= aim=3166>3165@-300.5:12.0 hd=3166:179 at=aes',
    ]))
    a, b = teamlog.states(str(p))['0A']
    assert a['aim'] == {3166: (3165, (-300.5, 12.0)), 3167: (3170, None), 3168: (0, None)}
    assert (a['hd'], a['at']) == ({3166: 180.0, 3167: -90.0, 3168: 0.0}, None)
    assert (b['hd'], b['at']) == ({3166: 179.0}, 'aes')


def test_change_only_samples_keep_the_whole_set(tmp_path):
    """D round 81: CNVTeams writes only the changed teams between beats; `teams: ... full=0/1` closes each sample and
    samples() keeps the running set (a full sample replaces it)."""
    a = "team: frame={f} list=0 proto=P1 name1='Soviet_1' name2='teamA' rel=1 slot=0 team=T1 active=1 n={n} ids={ids}"
    b = "team: frame={f} list=1 proto=P2 name1='Soviet_1' name2='teamB' rel=1 slot=0 team=T2 active=1 n=0 ids="
    end = 'teams: frame={f} full={full} player=X index=4 ai=Y protos=2 teams={k}'
    p = tmp_path / 'ra3ext.log'
    p.write_text('\n'.join([
        a.format(f=15, n=1, ids='7@1:2'), b.format(f=15), end.format(f=15, full=1, k=2),
        a.format(f=20, n=2, ids='7@1:2,8@3:4'), end.format(f=20, full=0, k=2),       # only teamA changed
        a.format(f=30, n=2, ids='7@1:2,8@3:4'), end.format(f=30, full=1, k=1),       # teamB gone: full sample
    ]) + '\n', encoding='utf-8')
    assert teamlog.team_size(str(p), 'teamA', 25) == 2
    assert teamlog.team_sizes(str(p), 'teamB', 25) == [0]             # the unchanged team is still there
    assert teamlog.team_sizes(str(p), 'teamB', 30) == []              # dropped by the full sample


def test_bench_frames_anchor(tmp_path):
    import json
    (tmp_path / 'ra3ext.log').write_text('', encoding='utf-8')
    (tmp_path / 'index.json').write_text(json.dumps(dict(mod='M', frames=[
        dict(id=1, second=None, note='menu'), dict(id=2, second=1.1, frame=40), dict(id=3, second=3.0, frame=71),
        dict(id=4, second=5.0)])), encoding='utf-8')
    assert teamlog.bench_frames(str(tmp_path)) == [(1.1, 40), (3.0, 71), (5.0, None)]
    assert teamlog.frame_at_second(str(tmp_path), 2.8) == 71


# D round 98: the AI's base table and its base choices. Lines from bench CampBS2NewB_mcp_1113_001802 (aibs2new:b, PASS;
# the caller field redacted, the use= field as the probe writes it since): one AI base all run -- the second
# construction yard made by script at s12 never joins the table, so OLD / NEW have one candidate to pick from.
LOG98 = """base: frame=151 i=0 id=0 own=117198192 flags=0x399 anchor=0 pos=3850.0:3400.0 ctr=-0.8:-0.6 nb=0 bld= hit=0
bases: frame=151 mgr=08782340 n=1
base: frame=152 i=0 id=0 own=117198192 flags=0x1d9 anchor=0 pos=3850.0:3400.0 ctr=-0.8:-0.6 nb=2 bld=3157,3166 hit=0
bases: frame=152 mgr=08782340 n=1
bsel: frame=274 use=target ra=x0 crit=0:0:1:4:1 ref=- pick=0 model=0 cand=0:1d9:1:1
bsel: frame=280 ra=x0 crit=default ref=10.0:-20.5 pick=-1 model=-1 cand=0:4:x:0
"""


def test_base_table_and_choices(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG98, encoding='utf-8')
    assert teamlog.bases_at(str(p), 100) == []
    b, = teamlog.bases_at(str(p), 300)
    assert (b['id'], b['nb'], b['bld'], b['anchor']) == (0, 2, [3157, 3166], None)
    assert b['types'] == ['MAIN_BASE', 'POINT_CENTERED', 'LAND_CENTERED', 'ENEMIES_IN_BASE', 'OLDEST_OF_TYPE',
                          'MOST_RECENT_OF_TYPE']
    c, = teamlog.base_choices(str(p), use='target')
    assert c['crit'] == dict(required=0, excluded=0, preferred=1, not_preferred=4, sort='PREFER_NEWEST')
    assert (c['pick'], c['model'], c['ref'], c['cand']) == (0, 0, None, [(0, 0x1d9, '1', 1)])
    d, = teamlog.base_choices(str(p), use='?')         # a line without use= (older probe) counts as '?'
    assert d['crit'] is None and d['pick'] is None and d['ref'] == (10.0, -20.5) and d['cand'] == [(0, 4, 'x', 0)]


# D round 102: member target orders and the TimeToKeepTarget clock. Lines from bench CampAIEgOnA_mcp_1113_025227
# (aiegon:a, PASS; caller field redacted): state 2 scoring orders both warriors onto 3168 at f375 with Min = Max = 0,
# so the keep ends at once and every 8-frame pass re-assigns; between passes the members are not in the scoring list.
LOG102 = """kpass: frame=375 team=0AEFE460 cand=3168:1,3167:1 keep=3170:0:go,3171:0:go
kassign: frame=375 team=0AEFE460 mstate=2 src=score ra=x0 mem=3170 tgt=3168 flag=0 ret=1 w=1 prev=3168:0 start=375 until=375 keep=0 min=0.00 max=0.00 n=0
kassign: frame=383 team=0AEFE460 mstate=2 src=score ra=x0 mem=3170 tgt=3168 flag=0 ret=0 w=1 prev=3168:375 start=383 until=383 keep=0 min=0.00 max=0.00 n=0
kpass: frame=399 team=0AEFE460 cand=3168:1,3167:1 keep=
kassign: frame=495 team=0AEFE460 mstate=2 src=score ra=x0 mem=3170 tgt=3168 flag=0 ret=1 w=1 prev=- start=495 until=495 keep=0 min=0.00 max=0.00 n=1
"""


def test_target_orders_and_keep_passes(tmp_path):
    p = tmp_path / 'ra3ext.log'
    p.write_text(LOG102, encoding='utf-8')
    a, b, c = teamlog.target_orders(str(p))
    assert (a['frame'], a['src'], a['mem'], a['tgt'], a['ret'], a['wrote']) == (375, 'score', 3170, 3168, 1, True)
    assert (a['prev'], a['start'], a['until'], a['keep'], a['min'], a['max']) == ((3168, 0), 375, 375, 0, 0.0, 0.0)
    assert b['prev'] == (3168, 375) and b['ret'] == 0
    assert c['prev'] is None and c['folded'] == 1
    assert teamlog.target_orders(str(p), team='other') == []
    k, e = teamlog.keep_passes(str(p))
    assert k['cand'] == [(3168, True), (3167, True)] and k['keep'] == [(3170, 0, 'go'), (3171, 0, 'go')]
    assert e['keep'] == [] and e['frame'] == 399
    assert k['why'] == [] and e['why'] == []


def test_keep_passes_why(tmp_path):
    # D round 104 shape (made up, not a bench reading): why each keep read gave what it gave
    p = tmp_path / 'ra3ext.log'
    p.write_text('kpass: frame=551 team=0A cand=3168:1 keep=3171:0:go,3170:557:hold '
                 'why=3171:3167:gone,3170:3167:ok\n', encoding='utf-8')
    (k,) = teamlog.keep_passes(str(p))
    assert k['keep'] == [(3171, 0, 'go'), (3170, 557, 'hold')]
    assert k['why'] == [(3171, 3167, 'gone'), (3170, 3167, 'ok')]
