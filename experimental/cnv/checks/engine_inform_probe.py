"""Engine line D, round 35 (ADR 0027/0028): C line's InformTarget AI recipe with ra3ext's read-only probe on the miners.

engine_inform_ai.py (C line's check, not changed here) fires slow single shells with InformTargetNugget at AI miners
(SovietMiner: TrackIncomingWeaponFireBehavior, self-defence look-ahead 2 s, fraction 0.2) and sees only when the
armour goes up. This mission is the same one -- its mission() and check() are called as they are -- with two changes:
the miners the scripts create are a copy CNV_InfoProbeMiner with one more module,
`<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, and the mission is built with ext=True.
ra3ext's CNVProbe then logs, besides its usual probe line, an `incoming` line every time the miner's
TrackIncomingWeaponFireBehavior list changes: each entry's source id, predicted damage, predicted impact frame and
expiry frame (handoff-d round 35). The probe only reads, so C line's expectations are kept: the counters must equal
C line's readings. The impact frame is read off ra3ext.log, not asserted.
"""
import os

import labpaths
from parts import Unit
from checks import engine_inform_ai as inform

MINER, PROBE = inform.MINER, 'CNV_InfoProbeMiner'
EVERY, LINES = 150, 3000


def probe_miner():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', MINER + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{MINER}"') == 1 and x.count('<Behaviors>') == 1
    # the retail file also holds SovietMiner_Naval (inherits SovietMiner): drop it, the copy keeps only the miner
    first = x.index('</GameObject>') + len('</GameObject>')
    x = x[:first] + '\n' + x[x.index('</AssetDeclaration>'):]
    assert 'SovietMiner_Naval' not in x
    x = x.replace(f'id="{MINER}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MINER}"', f'EditorName="{PROBE}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(PROBE, x, names=dict(unit=PROBE),
                what='原版矿车的复制（探针）：多一个 ra3ext 的 CNVProbe 模块，记 TrackIncomingWeaponFire 的来弹表',
                params=dict(of=MINER, every=EVERY, lines=LINES))


def mission():
    m = inform.mission()
    m.name, m.ext = 'CampIP', True     # + the check's name stays <= 15 (CampIPA, CampIPOff)
    m.spawns.discard(MINER)
    m.spawns.add(PROBE)
    return m


def _probed(m, t):
    m.units.append(probe_miner())
    for s in t.scripts:
        s.do = [tuple(PROBE if v == MINER else v for v in a) for a in s.do]
    return t


def check(m):
    return _probed(m, inform.check(m))


def check_off(m):
    return _probed(m, inform.check_without_inform(m))


MISSION = {'engine_inform_probe': mission}
CHECKS = {'engine_inform_probe': {'a': check, 'off': check_off}}
