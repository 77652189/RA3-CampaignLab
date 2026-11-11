"""Engine line D, round 43 (ADR 0027/0028): E line's JetAIUpdate move (engine_jet) with ra3ext's read-only probe.

engine_jet.py (E line's check, not changed here) flies a retail Vindicator 1200 (a) or 600 (b) east at Go = 1 s and
counts frames from Go to the first entry into the goal square: bench 97 / 47 against a constant-speed 91.67 / 41.67.
This mission is the same one with one change: the jet is a copy CNV_JetProbe with one more module,
`<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, built with ext=True. ra3ext's CNVProbe
logs a `probe` line on every frame the host's x / y / z changed (and every EVERY frames), with the game frame number:
that is the jet's trajectory from spawn through Go to after arrival, and the per-frame step is its actual speed.
The probe only reads, so E line's expectations are kept: the counters must equal E line's readings.

Bench 2026-11-11 (D round 43): a PASS 97, b PASS 47 (CampJPA_mcp_1111_082745, CampJPB_mcp_1111_083208). Spawn:
xy still, z +20 a frame (TakeOffAndLandingSpeed) to frame 8, then halving towards ~386.6; no circling. Go at
script frame 16, the jet moves that same frame: step 2.7, then +0.8 a frame (12 / 15 = max speed per frame over
AccelerationSeconds 1 s) to 12.0 at frame 28, straight east. The accelerating 12 frames cover 85.2 instead of 144:
4.9 frames, E line's 5-frame gap. First entry frame 112 (a) / 62 (b), counter = entry - Go + 1.
"""
import os

import labpaths
from parts import Unit
from checks import engine_jet as jet

JET, PROBE = jet.JET, 'CNV_JetProbe'
EVERY, LINES = 150, 3000


def probe_jet():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', JET + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{JET}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{JET}"', f'id="{PROBE}"', 1).replace(f'EditorName="{JET}"', f'EditorName="{PROBE}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(PROBE, x, names=dict(unit=PROBE),
                what='原版 Vindicator 的复制（探针）：多一个 ra3ext 的 CNVProbe 模块，逐帧记位置',
                params=dict(of=JET, every=EVERY, lines=LINES))


def mission():
    m = jet.mission()
    m.name, m.ext = 'CampJP', True     # + the check's name stays <= 15 (CampJPA, CampJPB)
    m.units.append(probe_jet())
    for o in m.objects:
        if o.template == JET:
            o.template = PROBE
    for r in m.cast.values():
        if r.template == JET:
            r.template = PROBE
    return m


MISSION = {'engine_jet_probe': mission}
CHECKS = {'engine_jet_probe': {'a': jet.ordinary_move, 'b': jet.short_move}}
