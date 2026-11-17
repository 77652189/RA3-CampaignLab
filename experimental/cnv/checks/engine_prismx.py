"""Engine unit test: which part of the mirage tank's cannon stops it after one shot (engine line C round 13;
docs/engine/weaponset.md 4; follows engine_prism). Bench 11-09: the mirage tank fires ONE shot at a held Tsunami tank
and never again, however it is aimed; a guardian's plain cannon keeps firing. The cause is in the cannon's own data:
the cannon (id ...Tech3PrismCannon in GlobalData/Weapon.xml) is a single shot, firing 1.5 s, reload 0.1 s, auto reload,
ReAcquireDetailType PER_CLIP, flag ATTACK_NEEDS_LINE_OF_SIGHT, and its nuggets are: a laser (ActivateLaser, 1.5 s), an OCL
(the prism node object at the target), the 200 damage (PRISM, delay 0.1 s) and a suppression (radius 20).

Each lane is a CLONE of the mirage tank (CNV_PrismX<Variant>: its unit file with the id changed and its own copy of the
cannon, id <unit>Weapon, swapped in the weapon slot) with ONE thing taken away (VARIANTS). Same lane rig as engine_prism:
one attack order at ORDER on a held Tsunami tank 100 north (the enemy's, NO_ATTACK); counter = the tank's health in
percent every second. Two runs, four variants each (idle variants are deleted at the start):
  a: ctrl (the clone unchanged: must repeat the one-shot or the clone is not faithful), ocl (no OCL nugget), los (no
     ATTACK_NEEDS_LINE_OF_SIGHT), fx (no laser nugget, no suppression nugget)
  b: dis (the unit's AI state machine is the plain UnitAIStateMachine, not the disguise-when-idle one), bare (ocl + los +
     fx all gone: damage only), reacq (ReAcquireDetailType PRE_FIRE), all (bare + dis + reacq)
A lane that keeps firing drops the tank's health step by step (a Tsunami tank 380 hp, 200 a shot); the one-shot lanes stop
at 47 %.

Readings (bench 2026-11-09): runs a and b -- every lane, the control included, stops at 47 %: taking away the OCL nugget,
the line-of-sight flag, the laser and suppression nuggets, ReAcquire PER_CLIP or the disguise-when-idle state machine (and
all of them together) does not make the mirage tank fire again. Runs c, d (same day), health in % at s1-s34:
  tgt (Soviet Tech1 tank, 550 hp, the clone unchanged) 27; nodel / dtype / nofd (no 0.1 s damage delay / damage type EXPLOSIVE /
  firing duration 0) 47 47 47; clip3 / noaim / range 47 47 47; nomv (CanFireWhileMoving false) '?' (the counter unreadable
  from about s3 -- probably the Tsunami was KILLED; not yet confirmed).
CASE CLOSED (run e, same day, health + alive counters on the ctrl and tgt lanes): s1 73 1 27 0, s2-s31 73 0 27 0 -- both
targets are DEAD (alive 0) and their health counters stay at the last value read before death. There is no one-shot
mystery: a health counter freezes when its object dies (engine line A r130 found the same). The mirage tank, the
guardian and the rest fire on until the target is dead; nothing in the cannon stops it. The reading below is the
first guess, kept for the record.
First guess: Tsunami (380 hp) stops at 47 % = ~179 hp left = ONE 200 shot taken; the Soviet tank (550 hp) stops at 27 % = ~148 hp
= TWO shots taken. Both stop with less health left than one shot deals (200), as engine_prism's guardian lane did (stopped at
5 %, a shot of 16 %). So it looks like "no shot that would kill a held target" (or CanFireWhileMoving true holds the last
shot), not a flaw of the prism cannon. Next: a high-hp target (does it fire on until < 200 left?), nomv over time, the
guardian with CanFireWhileMoving toggled, a target not held (no NO_ATTACK).
"""
import os
import re

from maps import probe_range
from parts import Mission, Script, Test, Unit, counted
from checks.engine_missile import SAGE, _sub1

MIRAGE, CANNON, TANK = 'AlliedAntiVehicleVehicleTech3', 'AlliedAntiVehicleVehicleTech3PrismCannon', 'JapanAntiVehicleVehicleTech1'
ORDER, RUN = 3.0, 30.0
LANES = ('base', 'high', 'removed', 'low')          # the range map's four lane sites
# variant: (what is taken away from the weapon, whether from the unit (disguise machine) too, one line)
VARIANTS = {
    'ctrl':  ((), False, '克隆原样（对照）'),
    'ocl':   (('ocl',), False, '去掉生棱镜节点的 OCL'),
    'los':   (('los',), False, '去掉需要直线视线'),
    'fx':    (('laser', 'supp'), False, '去掉激光和压制'),
    'dis':   ((), True, '单位 AI 状态机换成普通的（不伪装）'),
    'bare':  (('ocl', 'los', 'laser', 'supp'), False, '只剩伤害'),
    'reacq': (('reacq',), False, 'ReAcquire 改 PRE_FIRE'),
    'all':   (('ocl', 'los', 'laser', 'supp', 'reacq'), True, '全去掉 + 普通状态机'),
    # second pass: runs a and b all read 47 (the one shot), so the cause is not in those parts
    'tgt':   ((), False, '克隆原样，目标换成苏联 Tech1 坦克（480 血）'),
    'nodel': (('delay',), False, '伤害去掉 0.1 秒延迟'),
    'dtype': (('dtype',), False, '伤害类型 PRISM 改 EXPLOSIVE'),
    'nofd':  (('firing',), False, '开火持续 1.5 秒改 0'),
    'clip3': (('clip3',), False, '弹夹 3 发'),
    'noaim': (('aim',), False, '去掉 AcceptableAimDelta'),
    'nomv':  (('nomove',), False, 'CanFireWhileMoving 改 false'),
    'range': (('range',), False, '射程 125 改 300'),
}
RUNS = {'a': ('ctrl', 'ocl', 'los', 'fx'), 'b': ('dis', 'bare', 'reacq', 'all'),
        'c': ('tgt', 'nodel', 'dtype', 'nofd'), 'd': ('clip3', 'noaim', 'nomv', 'range'),
        'e': ('ctrl', 'tgt')}
ALIVE = ('e',)              # runs that also count whether the target is still alive (health + alive per lane)
TARGETS = {'tgt': 'SovietAntiVehicleVehicleTech1'}


def _uid(k):
    return 'CNV_PrismX' + k.title()


def _n(k, part):
    return f'UNIT - CNV PrismX {k.title()} {part}'


def _strip(s, what):
    for w in what:
        if w == 'ocl':
            s, n = re.subn(r'\s*<WeaponOCLNugget\b[^>]*/>', '', s)
        elif w == 'laser':
            s, n = re.subn(r'\s*<ActivateLaserNugget\b[^>]*/>', '', s)
        elif w == 'supp':
            s, n = re.subn(r'\s*<SuppressionNugget\b[^>]*/>', '', s)
        elif w == 'los':
            s, n = s.replace('ATTACK_NEEDS_LINE_OF_SIGHT ', ''), 1
            assert 'ATTACK_NEEDS_LINE_OF_SIGHT' not in s
        elif w == 'delay':
            s, n = re.subn(r'\s*DelayTimeSeconds="0\.1s"', '', s)
        elif w == 'dtype':
            s, n = s.replace('DamageType="PRISM"', 'DamageType="EXPLOSIVE"'), 1
        elif w == 'firing':
            s, n = re.subn(r'(<FiringDuration\s+MinSeconds=")1\.5s("\s+MaxSeconds=")1\.5s"', r'\g<1>0s\g<2>0s"', s)
        elif w == 'clip3':
            s, n = re.subn(r'ClipSize="1"', 'ClipSize="3"', s)
        elif w == 'aim':
            s, n = re.subn(r'\s*AcceptableAimDelta="10d"', '', s)
        elif w == 'nomove':
            s, n = re.subn(r'CanFireWhileMoving="true"', 'CanFireWhileMoving="false"', s)
        elif w == 'range':
            s, n = re.subn(r'AttackRange="125\.0"', 'AttackRange="300.0"', s)
        elif w == 'reacq':
            s, n = s.replace('ReAcquireDetailType="PER_CLIP"', 'ReAcquireDetailType="PRE_FIRE"'), 1
        assert n == 1, (w, n)
    return s


def prism_clone(k):
    what, plain_ai, line = VARIANTS[k]
    id, wid = _uid(k), _uid(k) + 'Weapon'
    x = open(os.path.join(SAGE, 'Allied', 'Units', MIRAGE + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{MIRAGE}"', f'id="{id}"')
    x = re.sub(rf'EditorName="{MIRAGE}"', f'EditorName="{id}"', x)
    x = _sub1(x, f'Template="{CANNON}"', f'Template="{wid}"')
    if plain_ai:
        x = _sub1(x, 'StateMachine="DisguiseWhenIdleAIStateMachine"', 'StateMachine="UnitAIStateMachine"')
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{CANNON}".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = _sub1(s, f'id="{CANNON}"', f'id="{wid}"')
    s = _strip(s, what)
    x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
    return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                what=f'幻影坦克克隆（探针）：{line}', params=dict(away=list(what), plain_ai=plain_ai))


def mission():
    m = Mission(name='CampPrismX', map=probe_range, units=[prism_clone(k) for k in VARIANTS], facts={})
    placed = set()
    for run, ks in RUNS.items():
        for lane, k in zip(LANES, ks):
            if k in placed:                     # run e reuses ctrl and tgt: placed once
                continue
            placed.add(k)
            m.put(_uid(k), f'{lane} gun', side='p1', role=f'prismx {k}', name=_n(k, 'Man'))
            m.put(TARGETS.get(k, TANK), f'{lane} gun', 0.0, 100.0, side='s1', role=f'prismx {k} target', name=_n(k, 'Tank'))
    return m


def prismx_test(m, run):
    t = Test()
    p1 = m.player('p1')
    ks = RUNS[run]
    idle = [k for k in VARIANTS if k not in ks]
    start = [('NAMED_DELETE', _n(k, part)) for k in idle for part in ('Man', 'Tank')]
    start += [('UNIT_CHANGE_OBJECT_STATUS', _n(k, 'Tank'), 'NO_ATTACK', 1) for k in ks]
    start += [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('NAMED_ATTACK_NAMED', _n(k, 'Man'), _n(k, 'Tank')) for k in ks]))
    for k in ks:
        counted(f'CNV_PrismX_{k.title()}Hp', k, t, health=_n(k, 'Tank'))
        if run in ALIVE:                        # a dead target's health counter freezes at its last reading (engine line A r130)
            c = f'CNV_PrismX_{k.title()}Alive'
            t.counters.append((c, k + ' 活'))
            t.scripts += [Script(f'Test - {c} one', [], [('SET_COUNTER', c, 1)], once=False),
                          Script(f'Test - {c} dead', [('NAMED_DESTROYED', _n(k, 'Tank'))], [('SET_COUNTER', c, 0)], once=False)]
    t.expect = [(ks[0], 0, 'ever<=', 99, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_prismx': mission}
CHECKS = {'engine_prismx': {run: (lambda m, run=run: prismx_test(m, run)) for run in RUNS}}
