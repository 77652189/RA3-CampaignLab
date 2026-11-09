"""Engine unit test: the clip's rhythm (ADR 0019 layer 3; docs/engine/weapons.md; engine line C round 4) -- what comes
between one shot and the next once the first has gone: PreAttackDelay, FiringDuration, ClipReloadTime, ClipSize and
ReAcquireDetailType. engine_fire read the FIRST shot; the simulator's clip clock (Sim.shot_clock, round 2) needs the
rest: the coil (pre-attack 2.5 s + firing 0.5 s + reload 0.1 s = 3.1 s on paper) shoots on the bench about every
4.15 s -- a second a shot the data does not say.

Each shooter is retail's V4 with its rocket weapon swapped for a copy that deals ONE instant 100 (1 % of the 10 000-
health Hammer, engine_missile's target) per shot, no scatter, WeaponSpeed 999999; only the timers, ClipSize and
ReAcquireDetailType differ (VARIANTS). One variant a check, on the 'base' lane (the other variants are deleted at the
start, as in engine_fire); ordered at ORDER (every clip loaded), so the first reading is the order -> first hit, then
the frames between hit a and hit b (as engine_scatter's span: health in [100 - b + 1, 100 - a] %).

Counters (four lines): 首发 = frames from the order to the first hit; then the SPANS of the variant. The reading is
the frame count the script saw, one more than the frame the damage landed (docs/engine/weapons.md 1).

Bench 11-09 (round 4, work/bench_results/engine_clip__coil.json): `coil` -- first hit 40 frames after the order
(2.5 s -> 38, + the 2 of engine_fire's late), then hits 1-2 = 48, 2-3 = 48, 3-6 = 144 (3 x 48): one shot every 48
frames = ceil(2.5 s x 15) 38 + ceil(0.5 s) 8 + ceil(0.1 s) 2. So the coil's weapon alone is 3.2 s a shot, NOT the
~4.15 s the powerdef bench shows: the missing ~1 s is not in the clip rhythm. powerdef: a Tech1 tank (480 hp, TESLA
100 %) needs 2 shots of 450 = 96 frames; the bench kills one per ~125, so ~29 frames per KILL (retarget / acquire
after the kill), first loss 111 = ~25 acquire + 86. Next probe: a kill chain (several 480-hp tanks, a shooter that
kills in one shot, kill -> next hit frames, auto-acquire vs ordered). The other seven variants (bare, clip3, pre, fire,
coilpc, clip3p, clip3c) were built but not run (queue stopped at the 15万 handoff): run_queue.py engine_clip:<name>.
"""
import os
import re

from maps import probe_range
from parts import Mission, Script, Test, Unit
from checks.engine_missile import FAR, SAGE, TARGET_ID, V4, V4_WEAPON, _sub1, target

ORDER = 6.0
HIT = 100.0                    # a hit = 1 % of the target's 10 000
LOST_MAX = 40

# id suffix: (pre-attack s, firing s, reload s, clip, ReAcquireDetailType, spans (hit a, hit b), run seconds, label)
VARIANTS = {
    'coil':   (2.5, 0.5, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 60, '线圈同时序'),
    'coilpc': (2.5, 0.5, 0.1, 1, 'PER_CLIP', ((1, 2), (2, 3), (3, 6)), 60, '线圈同时序+PER_CLIP'),
    'pre':    (2.5, 0.0, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 45, '只有预瞄2.5'),
    'fire':   (0.0, 0.5, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 30, '只有持续0.5'),
    'bare':   (0.0, 0.0, 0.1, 1, 'PRE_FIRE', ((1, 2), (2, 3), (3, 6)), 25, '只有装填0.1'),
    'clip3':  (0.0, 0.3, 2.0, 3, 'PRE_FIRE', ((1, 2), (2, 3), (3, 4)), 45, '三发夹'),
    'clip3p': (0.5, 0.3, 2.0, 3, 'PRE_FIRE', ((1, 2), (2, 3), (3, 4)), 45, '三发夹+预瞄0.5'),
    'clip3c': (0.0, 0.3, 2.0, 3, 'PER_CLIP', ((1, 2), (2, 3), (3, 4)), 45, '三发夹+PER_CLIP'),
}
INSTANT = ('<Nuggets>\n\t\t\t<DamageNugget Damage="%g" DamageType="EXPLOSIVE" DeathType="EXPLODED" Radius="0" />\n'
           '\t\t</Nuggets>' % HIT)


def _uid(k):
    return 'CNV_Clip' + k.title()


def clip_v4(k):
    """Retail's V4 under CNV_Clip<K>, its rocket weapon swapped for a one-DamageNugget instant copy with the
    variant's timers (ADR 0016 G5: the probe builds it)."""
    pre, firing, reload, clip, reacq, _, _, label = VARIANTS[k]
    id = _uid(k)
    wid = id + 'Weapon'
    x = open(os.path.join(SAGE, 'Soviet', 'Units', V4 + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{V4}"', f'id="{id}"')
    x = re.sub(rf'EditorName="{V4}"', f'EditorName="{id}"', x)
    x = _sub1(x, f'Template="{V4_WEAPON}"', f'Template="{wid}"')
    w = open(os.path.join(SAGE, 'GlobalData', 'Weapon.xml'), encoding='utf-8').read()
    s = re.search(rf'\t*<WeaponTemplate\s+id="{V4_WEAPON}".*?</WeaponTemplate>\n', w, re.S).group(0)
    s = _sub1(s, f'id="{V4_WEAPON}"', f'id="{wid}"')
    s = _sub1(s, 'inheritFrom="ScatterableWeapon"', '')
    s = _sub1(s, 'WeaponSpeed="200"', 'WeaponSpeed="999999"')
    s = _sub1(s, 'ClipSize="1"', f'ClipSize="{clip}"')
    s = _sub1(s, 'ReAcquireDetailType="PRE_FIRE"', f'ReAcquireDetailType="{reacq}"')
    s, n = re.subn(r'<Nuggets>.*?</Nuggets>', INSTANT, s, flags=re.S)
    assert n == 1, n
    s, n = re.subn(r'\s*<ScatterRadiusVsType\s+Radius="0\.1">.*?</ScatterRadiusVsType>', '', s, flags=re.S)
    assert n == 1, n
    s = _sub1(s, 'MinSeconds=".5s"\n\t\t  MaxSeconds=".5s"', f'MinSeconds="{pre:g}s"\n\t\t  MaxSeconds="{pre:g}s"')
    s = _sub1(s, '<FiringDuration\n\t\t\tMinSeconds="1.0s"\n\t\t\tMaxSeconds="1.0s"',
              f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
    s, n = re.subn(r'(<ClipReloadTime\s+MinSeconds=")4\.5s("\s+MaxSeconds=")5\.5s"', rf'\g<1>{reload:g}s\g<2>{reload:g}s"', s)
    assert n == 1, n
    x = _sub1(x, '</AssetDeclaration>', s + '</AssetDeclaration>')
    return Unit(id, x, link=[f'WeaponTemplate:{wid}'], names=dict(unit=id, weapon=wid),
                what=f'弹夹节奏 V4（探针）：瞬发 {HIT:g} 伤害、预瞄 {pre:g} 秒、开火持续 {firing:g} 秒、装填 {reload:g} 秒、'
                     f'弹夹 {clip} 发、{reacq}，其余同原版',
                params=dict(pre=pre, firing=firing, reload=reload, clip=clip, reacq=reacq))


def mission():
    m = Mission(name='CampClip', map=probe_range, units=[clip_v4(k) for k in VARIANTS] + [target()], facts={})
    for k in VARIANTS:
        m.put(_uid(k), 'base gun', side='p1', role=f'clip {k}', name=f'UNIT - CNV Clip {k.title()}')
    m.put(TARGET_ID, 'base gun', 0, FAR, side='s1', role='clip target', name='UNIT - CNV Clip Target')
    return m


def clip_test(m, k):
    pre, firing, reload, clip, reacq, spans, run, label = VARIANTS[k]
    t = Test()
    shooter, tg = m.role(f'clip {k}').name, m.role('clip target').name
    idle = [m.role(f'clip {i}').name for i in VARIANTS if i != k]
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('NAMED_DELETE', x) for x in idle]
    start += [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in (shooter, tg)]
    start += [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]
    t.scripts.append(Script('Test - start', [], start))
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                             ('NAMED_ATTACK_NAMED', shooter, tg), ('SET_FLAG', 'Test Ordered', 1)]))
    t.counters.append(('CNV_Clip_First', '首发'))
    t.scripts.append(Script('Test - CNV_Clip_First', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                            [('INCREMENT_COUNTER', 1, 'CNV_Clip_First')], once=False))
    for i, (a, b) in enumerate(spans):
        c = f'CNV_Clip_S{i}'
        t.counters.append((c, f'{a}-{b}'))
        t.scripts.append(Script(f'Test - {c}', [('UNIT_HEALTH', tg, 0, 100 - a + 1), ('UNIT_HEALTH', tg, 3, 100 - b + 1)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
    a, b = spans[-1]
    t.expect = [(f'{a}-{b}', 0, 'ever>=', (b - a) * 2, run - 1)]
    t.bench = [('bench_watch', dict(seconds=run, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_clip': mission}
CHECKS = {'engine_clip': {k: (lambda m, k=k: clip_test(m, k)) for k in VARIANTS}}
