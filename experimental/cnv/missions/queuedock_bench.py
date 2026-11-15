"""E152: one named retail miner; refinery QueueDock on/off, no spawned rival."""
import math
import re
from pathlib import Path

import labpaths
from maps import probe_range
from parts import Mission, Unit


def mission(enabled=True):
    m = Mission(name='CampDockE' if enabled else 'CampDockOffE', map=probe_range, units=[],
                facts={'queuedock': enabled})
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedRefinery.xml').read_text(encoding='utf-8-sig')
    xml = xml.replace('id="AlliedRefinery"', 'id="CNVE152Refinery"', 1)
    # Both arms omit only the automatic competitor, retaining the retail dock bones/model.
    xml, n = re.subn(r'<SpawnBehavior\b.*?</SpawnBehavior>', '', xml, count=1, flags=re.S)
    assert n == 1
    if not enabled:
        xml, n = re.subn(r'<QueueDockBehavior\b.*?/>', '', xml, count=1, flags=re.S)
        assert n == 1
    m.units.append(Unit('CNVE152Refinery', xml))
    pad = m.where('probe refinery')
    m.put('CNVE152Refinery', 'probe refinery', role='refinery', name='E152 Refinery', angle=pad.facing)
    m.put('AlliedMiner', 'probe refinery', -110, 0, role='miner', name='E152 Miner', angle=0)
    # Check consumes the published pad; it never reads the map module.
    m.facts['dock pad'] = (pad.x, pad.y, 70.0)
    assert math.isfinite(pad.facing)
    return m


MISSION = {'engine_queuedock': mission, 'queuedockoff': lambda: mission(False)}
