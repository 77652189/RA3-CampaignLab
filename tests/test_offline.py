"""The plan's offline checks (experimental/cnv/offline.py) and the unit numbers they stand on (simunits)."""
import os
import sys
from copy import copy, deepcopy
from pathlib import Path

from testcache import content_key

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]
import offline  # noqa: E402
import engine.data.units as simunits  # noqa: E402

_walk = offline.walk
_replay = {}


def a4_walk(level):
    """Keep the replay, giving each reader a world of its own for specimen creation."""
    import labpaths
    import plan
    import sim
    from engine.ports.observe import Observe

    compiler = plan.Compiler(plan.load(level))
    mission = compiler.compile()
    script = offline.anchored(offline.WALK[level], compiler)
    voice = getattr(mission, 'voice', None)
    video = getattr(mission, 'video', None)
    clips = getattr(video, 'clips', {})
    movies = Path(labpaths.GAME) / 'Data' / 'Movies'
    radar = {clips.get(a[1], movies / f'{a[1]}.vp6') for s in mission.scripts for a in s.do + s.orelse
             if a[0] == 'MOVIE_PLAY_RADAR'}
    key = (level, script, repr(mission.scripts), repr(mission.strings), sim.UNTIL, sim.DT, sim.QUIET,
           content_key(Path(ROOT) / 'experimental', plan.path(level), simunits.SAGEXML,
                       simunits.INDEX, simunits.CACHE, simunits.COMBAT_CACHE,
                       Path(labpaths.ENGINE_MODEL) / 'ra3model',
                       *(wav for _, wav, _, group in getattr(voice, 'items', ()) if not group),
                       *sorted(radar, key=str)))
    if key not in _replay:
        obs, *timeline = _walk(level)
        _replay.clear()
        _replay[key] = obs, timeline
    obs, timeline = _replay[key]

    # Read the final observation, but put specimens and sight bookkeeping in a separate
    # world with the same map, clock and player weapon upgrades.
    world = sim.Sim(mission, script=script)
    world.t, world.clock.frame = obs.t, obs.frame()
    world.player_ups.update((side, set(obs.player_upgrades(side))) for side in (obs.human, obs.foe))
    reader, specimens = copy(obs), Observe(world)
    reader.specimen = specimens.specimen
    reader.looks = specimens.looks
    return reader, *deepcopy(timeline)


def test_a_number_written_as_a_define_is_the_defines():
    """Most retail units see with ShroudClearingRange '=$STANDARD_SHROUD_CLEAR' (GlobalDefines: 500); read as a
    number it was missed, and every unit saw 200 (2026-10-29)."""
    assert simunits.number('<X ShroudClearingRange="=$STANDARD_SHROUD_CLEAR" />', 'ShroudClearingRange') == 500.0
    own = '<Defines><Define name="MY_HP" value="321" /></Defines><Body MaxHealth="=$MY_HP" />'
    assert simunits.number(own, 'MaxHealth') == 321.0
    assert simunits.number('<Body MaxHealth="=50000" />', 'MaxHealth') == 50000.0
    assert simunits.number('<Body VisionRange="200" />', 'VisionRange') == 200.0
    assert simunits.number('<Body />', 'VisionRange') is None
    assert simunits.stats('AlliedAntiVehicleVehicleTech1')['shroud'] == 500.0


def test_a4_offline(monkeypatch):
    """A4's walkthrough wins and runs through the plan's four stages; the high-ground claims hold on sapporo; the
    fight model's numbers give the counters the plan leans on (the javelin beats the tsunami, the tank buster beats
    the guardian, the peacekeeper the tank buster)."""
    monkeypatch.setattr(offline, 'walk', a4_walk)
    text, problems = offline.report('a4')
    assert '结局：赢' in text
    assert '段：会场 0:00，港口生变' in text and '北营' in text and '布防' in text and '最后一程' in text
    assert not [p for p in problems if p.startswith('sight')], problems
    # the plateau towers' three claims (K7: the back lane's three went with its hill)
    assert text.count('\n- 过 ') == 3 and '\n- 不对 ' not in text
    obs, _, _, _ = a4_walk('a4')
    body = {}

    def b(t, owner):
        body[(t, owner)] = body.get((t, owner)) or obs.specimen(f'#t {len(body)}', t, owner)
        return body[(t, owner)]
    javelin, tsunami = b('AlliedAntiVehicleInfantry', obs.human), b('JapanAntiVehicleVehicleTech1', obs.foe)
    guardian, buster = b('AlliedAntiVehicleVehicleTech1', obs.human), b('JapanAntiVehicleInfantry', obs.foe)
    peacekeeper = b('AlliedAntiInfantryInfantry', obs.human)
    assert offline.ratio(obs, javelin, tsunami) > 1
    assert offline.ratio(obs, guardian, buster) < 1
    assert offline.ratio(obs, peacekeeper, buster) > 1
