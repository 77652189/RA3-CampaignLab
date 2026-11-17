"""Named launch replay of measured radius notifications, not full AI/flight."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('radius_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


@pytest.mark.parametrize('check_name', ['a', 'b'])
def test_inform_radius_launch_replays_measured_neighbours(check_name, monkeypatch):
    import build
    import sim

    data = json.loads((ROOT / f'tests/fixtures/c_inform_radius_{check_name}.json').read_text(encoding='utf-8'))
    observed = {row['target']: row['entries'] for row in data['events'] if row['frame'] <= 302}
    assert len(observed) == 12
    m, t, _ = build.resolve('engine_inform_radius', check_name)
    e = sim.Sim(m, t)
    monkeypatch.setattr(e, 'frame_now', lambda: 302)
    bodies = {}
    for lane in ('base', 'high', 'order', 'removed'):
        gun = e.body('Info gun ' + lane)
        for label, offset in [('main', 0), ('near', 80), ('far', 320)]:
            name = lane + ' ' + label
            # Radius replay preserves the published450 separation. Exact muzzle
            # timing is outside this test; compare recipient timing to primary.
            e.add(name, 'SovietMiner', m.player('p1' if lane == 'high' else 's1'),
                  gun.x + offset, gun.y + 450)
            bodies[name] = e.body(name)
    for lane, source in zip(('base', 'high', 'order', 'removed'), (12, 13, 14, 15)):
        gun = e.body('Info gun ' + lane)
        weapon, = gun.weapons
        e.inform_launch(bodies[lane + ' main'], gun, weapon)
        primary = e.incoming.get(id(bodies[lane + ' main']), [])
        assert len(primary) == len(observed[lane + ' main'])
        for label in ('main', 'near', 'far'):
            name = lane + ' ' + label
            actual = e.incoming.get(id(bodies[name]), [])
            expected = [(id(gun), weapon['weapon_key'], row['damage'], *primary[0][3:])
                        for row in observed[name]]
            assert all(row['source'] == source for row in observed[name])
            # Engine neighbours carry the exact primary deadline, not one
            # recomputed from their longer launcher distance.
            assert all(row == observed[lane + ' main'][0] for row in observed[name])
            assert actual == expected, name
            assert bodies[name].hp == 500
