"""Engine line D, round 21 (ADR 0027/0028): C line's suppression closure with ra3ext's read-only probe on the target.

engine_suppression.py (C line's check, not changed here) times how long a suppressed man takes through a gate; the
bench shows only the result. This mission is the same one -- its mission() and check() are called as they are --
with two changes: the ordinary men (AlliedAntiInfantryInfantry, every lane but 'low') are a copy CNV_SuppProbeMan
with one more module, `<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames=EVERY MaxFrames=LINES/>`, and the mission is
built with ext=True (ra3ext.allow: the bench starts the game through ra3ext_launch). ra3ext's create sees the tag and
builds CNVProbe instead of a DeletionUpdate: each frame it reads the man's SuppressionUpdate (end frame, state,
threshold), the suppression value the game's own query returns for him and the raw manager entries covering him, and
writes a line to the run folder's ra3ext.log when one of them changed (or every EVERY frames), LINES lines at most.

The probe only reads, so the counters must equal C line's readings (its expectations are kept): that is the check
that the probe does not change the game. The timing rules are read off ra3ext.log (handoff-d round 21), not asserted.
'fast' (replaces the man's template itself) and the armour lanes (no walk) are left out.
"""
import os

import labpaths
from parts import Unit
from checks import engine_suppression as supp

MAN, PROBE = 'AlliedAntiInfantryInfantry', 'CNV_SuppProbeMan'
EVERY, LINES = 15, 3000
WHICH = ('threshold', 'expiry', 'phasea', 'lifetime', 'fraction', 'tail', 'duration', 'speed')


def probe_man():
    with open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Units', MAN + '.xml'), encoding='utf-8') as f:
        x = f.read()
    assert x.count(f'id="{MAN}"') == 1 and x.count('<Behaviors>') == 1
    x = x.replace(f'id="{MAN}"', f'id="{PROBE}"', 1).replace(f'EditorName="{MAN}"', f'EditorName="{PROBE}"')
    x = x.replace('<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVProbe" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''', 1)
    return Unit(PROBE, x, names=dict(unit=PROBE),
                what=f'维和步兵的复制（探针）：多一个 ra3ext 的 CNVProbe 模块（载体 DeletionUpdate），逐帧记压制读数',
                params=dict(of=MAN, every=EVERY, lines=LINES))


def _probed(m):
    for o in m.objects:
        if o.template == MAN:
            o.template = PROBE
    for lane in supp.CASES:
        if m.role(lane).template == MAN:
            m.role(lane).template = PROBE
    return m


def mission():
    m = supp.mission()
    m.name, m.ext = 'CampSuProbe', True
    return _probed(m)


def check(m, which):
    t = supp.check(m, which)       # rebuilds m.units from C line's guns
    m.units.append(probe_man())
    _probed(m)
    return t


MISSION = {'engine_suppress_probe': mission}
CHECKS = {'engine_suppress_probe': {k: (lambda m, k=k: check(m, k)) for k in WHICH}}
