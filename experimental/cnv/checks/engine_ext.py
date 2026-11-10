"""Engine line D, stage 2 (ADR 0027/0028): does a module of ra3ext.dll run inside a mission? The probe unit is a copy of
retail's conscript with one more module, written as the carrier `<DeletionUpdate id="ModuleTag_CNVLog" MinFrames=30
MaxFrames=40/>`: with ra3ext injected, its create sees the tag ModuleTag_CNVLog and builds our CNVLog module instead
(an update every frame, one log line every 30 updates, 40 lines at most) -- the unit lives on; without it, the carrier is
the real DeletionUpdate and the unit is deleted 30..40 frames after it appears.

  engine_ext     Mission(ext=True)   the build writes ra3ext.allow, the bench starts the game through ra3ext_launch
  engine_extoff  Mission(ext=False)  the same mission, a plain start: the control

On the range probe map, at 'base gun' (the player's): PROBES probe units and one plain conscript (the counter's own
control: it stays 1 either way). Counters: 探针 (probes the player owns), 对照 (plain conscripts). Every second.
The dll's own lines (ra3ext loaded / create / update) are in the run folder's ra3ext.log; cnv_check prints their count.
"""
import os

import labpaths
from maps import probe_range
from parts import Mission, Test, Unit, counted

CONSCRIPT, PROBE, PROBES = 'SovietAntiInfantryInfantry', 'CNVExtProbe', 2
EVERY, LINES, RUN = 30, 40, 20.0


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def probe_unit():
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Units', CONSCRIPT + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{CONSCRIPT}"', f'id="{PROBE}"')
    x = x.replace(f'EditorName="{CONSCRIPT}"', f'EditorName="{PROBE}"')
    x = _sub1(x, '<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVLog" MinFrames="{EVERY}" MaxFrames="{LINES}"/>''')
    return Unit(PROBE, x, names=dict(unit=PROBE),
                what=f'动员兵的复制（探针）：多一个 ra3ext 的 CNVLog 模块（载体 DeletionUpdate）；没注入时 {EVERY}..{LINES} 帧后被删',
                params=dict(of=CONSCRIPT, every=EVERY, lines=LINES))


def mission(ext=True):
    m = Mission(name='CampExt' if ext else 'CampExtOff', map=probe_range, units=[probe_unit()], facts={}, ext=ext)
    for k in range(PROBES):
        m.put(PROBE, 'base gun', 40.0 * k - 20.0, 0.0, side='p1', role=f'probe {k + 1}')
    m.put(CONSCRIPT, 'base gun', 0.0, -60.0, side='p1', role='plain conscript')
    return m


def ext_test(m, ext=True):
    t = Test()
    counted('CNV_Ext_Probe', '探针', t, template=PROBE)
    counted('CNV_Ext_Plain', '对照', t, template=CONSCRIPT)
    t.expect = [('对照', 3, '==', 1), ('探针', 3, '==', PROBES if ext else 0)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


MISSION = {'engine_ext': mission, 'engine_extoff': lambda: mission(False)}
CHECKS = {'engine_ext': {'a': ext_test}, 'engine_extoff': {'a': lambda m: ext_test(m, False)}}
