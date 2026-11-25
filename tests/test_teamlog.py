"""experimental/cnv/teamlog.py reads ra3ext's CNVTeams lines (engine line D round 68). The lines below are copied from
bench run CampAICrT3A_mcp_1112_015804 (benches/ai/tactics/checks.py#engine_aiteams aicr3t:a, PASS): the CreateUnits MinUnits 3 team
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


# D round 158: the first line is copied from bench CampClosestA_mcp_1115_094417 (aiclosest:a; the field sid=, dropped
# since, removed): the NonDefense-type slot rejects the turret 3182 (forbid) and takes the plant 3181, nearest the
# enemy 3183 among the rest. The second line is made up (a ThreatToGround find with no candidates, another AI).
TGT = """tgt: frame=16 brain=08C13F80 slot=1 state=088B8CB0 vt=c68298 sort=5 uniq=0 found=1 kind=3 target=3181@4000:3000 n=4 cand=3163@3850:3400:1:-:e=3183:d=1544,3181@4000:3000:1:-:e=3183:d=1118,3182@3700:2400:0:forbid,3184@4100:3800:1:-:e=3183:d=1844
tgt: frame=231 brain=0A000000 slot=3 state=0B000001 vt=c6822c sort=1 uniq=0 found=0 kind=0 target=-1@0:0 n=0 cand=-
"""


def test_target_picks_reads_candidates_and_verdicts(tmp_path):
    """D158: the tgt: line of ra3ext's target-heuristic log (format in work/re/ext/ra3ext/ra3ext.cpp)."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(TGT)
    rows = teamlog.target_picks(str(p))
    assert [r['slot'] for r in rows] == [1, 3]
    a, b = rows
    assert (a['sort'], a['found'], a['target'], a['point']) == ('ClosestToEnemy', True, 3181, (4000.0, 3000.0))
    assert [c['id'] for c in a['candidates']] == [3163, 3181, 3182, 3184]
    c1, c2 = a['candidates'][1:3]
    assert (c1['ok'], c1['why'], c1['enemy'], c1['distance']) == (True, [], 3183, 1118.0)
    assert (c2['ok'], c2['why'], c2['enemy']) == (False, ['forbid'], None)
    assert (b['found'], b['target'], b['candidates'], b['sort']) == (False, None, [], 'ThreatToGround')
    assert [r['slot'] for r in teamlog.target_picks(str(p), brain='08C13F80')] == [1]


# D round 159: copied from bench CampClosestA_mcp_1115_141948 (aiclosest:a). sid = the strategic state's id; the same
# AI's teams on that run are named '2ee151d8_StaticDefense_0_0' / '19dcc78_...' (FastHash of 'cnvclosest1' /
# 'cnvclosest0'). Slot 1 (cnvclosest2, the NonDefense one) rejects the turret and takes the plant.
TGT159 = """tgt: frame=16 brain=08F81198 slot=0 state=08B864E0 sid=2ee151d8 hi=0 vt=c68298 sort=5 uniq=0 found=1 kind=3 target=3182@3700:2400 n=4 cand=3163@3850:3400:1:-:e=3183:d=1544,3181@4000:3000:1:-:e=3183:d=1118,3182@3700:2400:1:-:e=3183:d=894,3184@4100:3800:1:-:e=3183:d=1844
tgt: frame=16 brain=08F81198 slot=1 state=08B86860 sid=d2df3ca3 hi=0 vt=c68298 sort=5 uniq=0 found=1 kind=3 target=3181@4000:3000 n=4 cand=3163@3850:3400:1:-:e=3183:d=1544,3181@4000:3000:1:-:e=3183:d=1118,3182@3700:2400:0:forbid,3184@4100:3800:1:-:e=3183:d=1844
tgt: frame=16 brain=08F81198 slot=2 state=08B86130 sid=19dcc78 hi=0 vt=c68298 sort=5 uniq=0 found=1 kind=3 target=3182@3700:2400 n=4 cand=-
inc: frame=0 brain=08A47AD0 own=8@0701CAF0 eny=2@070156B0 oin=0.0000 eni=0.0000 oq=0.0000:0.0000:0.0000 eq=0.0000:0.0000:0.0000 value=4.000 above=1 res=1.0 why=zero
inc: frame=0 brain=0841C038 own=9@0701DE50 eny=-1@00000000 oin=0.0000 eni=0.0000 oq=0.0000:0.0000:0.0000 eq=0.0000:0.0000:0.0000 value=4.000 above=1 res=0.0 why=early
"""


def test_target_picks_state_id_and_income_evals(tmp_path):
    """D159: tgt: sid / hi (state id as the team names' prefix, heuristic index) and the inc: line."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(TGT159)
    rows = teamlog.target_picks(str(p))
    assert [(r['slot'], r['state_id'], r['index'], r['target']) for r in rows] == [
        (0, '2ee151d8', 0, 3182), (1, 'd2df3ca3', 0, 3181), (2, '019dcc78', 0, 3182)]
    assert rows[0]['state'] == '08B864E0'
    old = tmp_path / 'old.log'
    old.write_text(TGT)
    assert {(r['state_id'], r['index']) for r in teamlog.target_picks(str(old))} == {(None, None)}
    red = tmp_path / 'redacted.log'    # public logs write sid=redacted
    red.write_text(TGT159.replace('sid=2ee151d8', 'sid=redacted'))
    assert [r['state_id'] for r in teamlog.target_picks(str(red))] == [None, 'd2df3ca3', '019dcc78']
    a, b = teamlog.income_evals(str(p))
    assert (a['own'], a['enemy'], a['own_in'], a['enemy_in'], a['value'], a['above'], a['result'], a['why']) == \
        (8, 2, 0.0, 0.0, 4.0, True, 1.0, 'zero')
    assert (b['own'], b['enemy'], b['result'], b['why']) == (9, None, 0.0, 'early')
    assert [r['brain'] for r in teamlog.income_evals(str(p), brain='0841C038')] == ['0841C038']


# D160 bench CampAISkXOL_mcp_1115_145806 (aiskxo, a harvesting skirmish AI): non-zero inputs, own player 4, the
# enemy (player 2) not harvesting; the input climbs in deposit steps, then falls while the third tracker float holds.
INC160 = """inc: frame=1954 brain=0875C138 own=4@06F18D70 eny=2@06F166B0 oin=2250.0000 eni=0.0000 oq=0.0000:2250.0000:2250.0000 eq=0.0000:0.0000:0.0000 value=3.000 above=1 res=1.0 why=ratio=9999.0000
inc: frame=1999 brain=0875C138 own=4@06F18D70 eny=2@06F166B0 oin=2362.0000 eni=0.0000 oq=0.0000:2362.0000:2362.0000 eq=0.0000:0.0000:0.0000 value=3.000 above=1 res=1.0 why=ratio=9999.0000
inc: frame=2258 brain=08335040 own=8@06F1DAF0 eny=2@06F166B0 oin=0.0000 eni=0.0000 oq=0.0000:0.0000:0.0000 eq=0.0000:0.0000:0.0000 value=4.000 above=1 res=1.0 why=zero
inc: frame=2359 brain=0875C138 own=4@06F18D70 eny=2@06F166B0 oin=3074.0000 eni=0.0000 oq=0.0000:3074.0000:3250.0000 eq=0.0000:0.0000:0.0000 value=3.000 above=1 res=1.0 why=ratio=9999.0000
"""


def test_income_evals_nonzero_bench_rows(tmp_path):
    """D160: real non-zero rows -- the input is the tracker's middle float, the third kept apart; AIs interleave per brain."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(INC160)
    rows = teamlog.income_evals(str(p), brain='0875C138')
    assert [(r['frame'], r['own_in'], r['own_q']) for r in rows] == [
        (1954, 2250.0, (0.0, 2250.0, 2250.0)), (1999, 2362.0, (0.0, 2362.0, 2362.0)),
        (2359, 3074.0, (0.0, 3074.0, 3250.0))]
    assert all((r['own'], r['enemy'], r['enemy_in'], r['value'], r['result'], r['why']) ==
               (4, 2, 0.0, 3.0, 1.0, 'ratio=9999.0000') for r in rows)
    assert [r['frame'] for r in teamlog.income_evals(str(p))] == [1954, 1999, 2258, 2359]


UA161 = """\
ua: frame=5 ev=set obj=3181 own=4 last=5 prev=-1 src=0 hp=1000.0/1000.0 win=75
ua: frame=16 ev=gate obj=3163 secs=5 win=75 last=-1 src=0 alive=0 path=a res=0 qvt=c418f8 c=0A7423F0 cvt=c3a8b8
ua: frame=16 ev=gate obj=3181 secs=5 win=75 last=5 src=0 alive=0 path=a res=1 qvt=c418f8 c=0A85C178 cvt=c3a8b8
ua: frame=81 ev=clr obj=3181 at=81 last=5 src=0 alive=0 hits=1
"""


def test_under_attack_bench_rows(tmp_path):
    """D161 bench rows (aiunderatk:a): one hit at f5 sets, clears at last + 75 + 1; the game's gate agrees at f16."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(UA161)
    ua = teamlog.under_attack(str(p))
    [e] = ua['episodes']
    assert (e['obj'], e['own'], e['set'], e['prev'], e['last'], e['clear'], e['hits'], e['src_alive']) == \
        (3181, 4, 5, -1, 5, 81, 1, False)
    assert [(g['obj'], g['result'], g['expect']) for g in ua['gates']] == [(3163, False, False), (3181, True, True)]
    assert teamlog.under_attack(str(p), obj=3163)['episodes'] == []


UA164 = """\
ua: frame=125 ev=set obj=3187 own=4 last=125 prev=-1 src=3186 hp=143.0/150.0 win=75
ua: frame=153 ev=set obj=3177 own=4 last=153 prev=-1 src=3191 hp=96.5/100.0 win=75
ua: frame=230 ev=clr obj=3177 at=229 last=153 src=3191 alive=0 hits=1
ua: frame=310 ev=clr obj=3187 at=310 last=234 src=3186 alive=1 hits=8
ua: frame=343 ev=set obj=3172 own=4 last=343 prev=-1 src=3215 hp=443.2/480.0 win=75
tgt: frame=500 brain=0 slot=0
"""


UA164_FIGHT = """\
ua: frame=5 ev=set obj=3181 own=4 last=5 prev=-1 src=0 hp=1000.0/1000.0 win=75
ua: frame=18 ev=src obj=3181 last=18 src=3185
ua: frame=18 ev=set obj=3187 own=4 last=18 prev=-1 src=3185 hp=143.0/150.0 win=75
ua: frame=110 ev=clr obj=3181 at=109 last=33 src=3185 alive=1 hits=3
ua: frame=222 ev=clr obj=3187 at=222 last=146 src=3185 alive=0 hits=9
"""


def test_under_attack_fight_ceasefire_and_deleted_source(tmp_path):
    """D164 bench (aiunderatk:a run 1115_165521): tank 3185 opens on the plant at f18 (inside the birth record's window:
    a source change, not a new set), turns to AI unit 3187, last plant hit f33 -> clear f109 with the tank alive (the
    ceasefire); 3187's last hit f146, the tank deleted f150, still cleared only at f222 = 146 + 75 + 1 (source gone)."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(UA164_FIGHT)
    eps = {e['obj']: e for e in teamlog.under_attack(str(p))['episodes']}
    assert (eps[3181]['srcs'], eps[3181]['last'], eps[3181]['clear'], eps[3181]['src_alive']) == ([0, 3185], 33, 109, True)
    assert (eps[3187]['set'], eps[3187]['prev'], eps[3187]['last'], eps[3187]['clear'], eps[3187]['src_alive'],
            eps[3187]['hits']) == (18, -1, 146, 222, False, 9)
    assert all(e['clear'] == e['last'] + e['win'] + 1 and not e['inferred'] for e in eps.values())


def test_under_attack_inferred_clear_at_log_end(tmp_path):
    """D164 bench rows (aiunderatk:a run 1115_164206): ra3ext writes a clear only at the next hit anywhere; an episode
    still open when the log (any line's frame) runs past last + win gets clear = last + win + 1, inferred, alive None."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(UA164)
    eps = {e['obj']: e for e in teamlog.under_attack(str(p))['episodes']}
    assert (eps[3177]['clear'], eps[3177]['src_alive'], eps[3177]['inferred']) == (229, False, False)
    assert (eps[3187]['clear'], eps[3187]['last'], eps[3187]['src_alive'], eps[3187]['inferred']) == (310, 234, True, False)
    assert (eps[3172]['clear'], eps[3172]['src_alive'], eps[3172]['inferred']) == (419, None, True)
    p.write_text(UA164.replace('frame=500', 'frame=400'))
    assert teamlog.under_attack(str(p), obj=3172)['episodes'][0]['clear'] is None


DOCK165 = """\
dock: frame=155 obj=12 kind=withnode old=2006 new=2009 goal=10 pos=1 cargo=0
dock: frame=156 obj=10 kind=node old=2002 new=2003 goal=0 pos=-1 cargo=-1
dock: frame=186 obj=12 kind=withnode old=2009 new=2007 goal=10 pos=1 cargo=250
dock: frame=200 obj=12 kind=other old=2001 new=14 goal=11 pos=2000 cargo=250 vt=x1
dock: frame=289 obj=12 kind=deliver old=2011 new=2001 goal=11 pos=1 cargo=250
dock: frame=319 obj=12 kind=deliver old=2001 new=2012 goal=11 pos=1 cargo=0
exc: frame=200 code=xc0000005 eip=x1 addr=x8 rw=0
"""


def test_dock_phases_bench_rows(tmp_path):
    """D165 bench (dockphase:a): the miner waits at node pad 1 f155..186 (load 250 lands when WaitLoad ends, the node
    in Load f156..186), unloads at refinery pad 1 f289..319 (cargo 250 -> 0). The off arm faulted at f200, the frame
    the miner's machine entered DeliverOre toward a refinery without QueueDock."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(DOCK165)
    r = teamlog.dock_phases(str(p))
    rows = [(x['frame'], x['kind'], x['old_name'], x['new_name'], x['pos'], x['cargo']) for x in r['phases']]
    assert rows == [(155, 'withnode', 'UpdatePad1', 'WaitLoad', 1, 0), (156, 'node', 'WaitForMiner', 'Load', -1, -1),
                    (186, 'withnode', 'WaitLoad', 'SetPad2', 1, 250), (200, 'other', None, None, 2000, 250),
                    (289, 'deliver', 'UpdatePad1', 'Unload', 1, 250), (319, 'deliver', 'Unload', 'SetPad2', 1, 0)]
    assert [(f['frame'], f['code'], f['rw']) for f in r['faults']] == [(200, 'xc0000005', 0)]
    assert [x['frame'] for x in teamlog.dock_phases(str(p), obj=10)['phases']] == [156]


# D round 166: copied from bench CampPointTinyA_mcp_1115_202922 (aipointtiny:a, the bench meant to set SearchRange 1;
# the game read 1500 there). The Point heuristic writes a point, not an object: target id 0, the point and its search
# are the pt= fields.
TGT166 = """tgt: frame=16 brain=0844D5E8 slot=0 state=0898A828 sid=ab309529 hi=0 vt=c6832c sort=3 uniq=0 found=1 kind=0 target=0@0:0 n=0 cand=- pt=2890:3011:162 new=1 base=0:3163@3850:3400 r=1500 mask=1 tries=40 pc=2809:3955:1,4461:3123:0,3386:2972:0,4487:3847:0,3302:2098:0,3457:3737:0,4708:2470:0,3509:3506:0,4367:3750:0,2970:4286:0,2492:3635:1,4383:4231:0,4075:2049:0,4111:4850:0,4577:3080:0,4771:2486:0,2486:3248:0,4322:2450:0,3917:3998:0,3079:2419:0,3069:3945:0,3801:3643:0,2626:3668:1,2433:3074:1,2690:3739:1,3452:3275:0,2494:3469:1,3495:4687:0,3738:4097:0,4943:3867:0,2626:2837:0,3301:2046:0,2792:4145:1,2890:3011:1,3093:4103:0,4438:3021:0,3872:2841:0,3239:2200:0
"""


def test_target_picks_point_search(tmp_path):
    """D166: Point heuristic -- picked point, search origin (selected base), range, Location mask, random candidates."""
    p = tmp_path / 'ra3ext.log'
    p.write_text(TGT166 + TGT159)
    rows = [r for r in teamlog.target_picks(str(p))]
    ps = rows[0]['point_search']
    assert rows[0]['target'] == 0 and rows[0]['found']
    assert (ps['point'], ps['new'], ps['base'], ps['anchor'], ps['origin'], ps['range'], ps['mask'], ps['tries']) == (
        (2890.0, 3011.0, 162.0), True, 0, 3163, (3850.0, 3400.0), 1500.0, 1, 40)
    kept = [c['point'] for c in ps['candidates'] if c['ok']]
    assert len(ps['candidates']) == 38 and len(kept) == 8 and all(c['threat'] is None for c in ps['candidates'])
    # ThreatToWater with no threat samples falls back to the kept point nearest the origin
    ox, oy = ps['origin']
    assert min(kept, key=lambda q: (q[0] - ox) ** 2 + (q[1] - oy) ** 2) == ps['point'][:2]
    assert all('point_search' not in r for r in rows[1:])
