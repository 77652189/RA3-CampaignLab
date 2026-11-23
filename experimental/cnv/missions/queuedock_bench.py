"""E152: one named retail miner; refinery QueueDock on/off, no spawned rival. dockqueue (pair): the refinery's queue
-- retail's pair of nodes (resources.Field twin, both facing the refinery), a named miner halfway to each, ra3ext's
dock phases on (teamlog.dock_phases): the two load together, so one comes while the other unloads."""
import math
import re
import types
from pathlib import Path

import labpaths
import resources
from maps import probe_range
from parts import Mission, Unit


def _paired():
    """probe_range with its field's second node (both facing the refinery, as retail)."""
    mp = types.ModuleType(probe_range.__name__)
    mp.__dict__.update({n: v for n, v in vars(probe_range).items() if not n.startswith('__')})
    f = probe_range.FIELDS[0]
    mp.FIELDS = [resources.Field(f.name, f.x, f.y, f.facing, 1)]
    mp.OBJECTS = resources.objects(mp.FIELDS)
    return mp


def mission(enabled=True, pair=False):
    m = Mission(name='CampDockQ' if pair else 'CampDockE' if enabled else 'CampDockOffE',
                map=_paired() if pair else probe_range, units=[], facts={'queuedock': enabled})
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
    if pair:
        m.ext, m.ext_logs = True, ('dock',)
        for k, (x, y) in enumerate(resources.nodes(m.map.FIELDS[0])):
            m.put('AlliedMiner', 'probe refinery', (x - pad.x) / 2, (y - pad.y) / 2, role=f'miner{k + 1}',
                  name=f'E152 Miner {k + 1}', angle=pad.facing)
    else:
        m.put('AlliedMiner', 'probe refinery', -110, 0, role='miner', name='E152 Miner', angle=0)
    # Check consumes the published pad; it never reads the map module.
    m.facts['dock pad'] = (pad.x, pad.y, 70.0)
    assert math.isfinite(pad.facing)
    return m


MISSION = {'engine_queuedock': mission, 'queuedockoff': lambda: mission(False),
           'dockqueue': lambda: mission(pair=True)}
