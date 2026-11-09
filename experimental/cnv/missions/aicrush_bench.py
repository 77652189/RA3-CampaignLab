"""Engine probe: the skirmish AI team's Crush and CrushPreference (engine line B, layer 4; read back by
checks/engine_aicrush.py; program: work/re l4_micro_engage.md 1.5 -- 0x8b1760: Crush on and (seconds to reach the
target) < CrushPreference x (...time to kill it by gun) -> drive over it, else shoot).

airetreat_bench's airet0 (12 of the player's Peacekeepers round the far plant, RetreatPowerAdvantage 0) with the AI's
four Peacekeepers swapped for four Hammers (SovietAntiVehicleVehicleTech1, CrusherLevel 20 against the Peacekeeper's
10; the team template's IncludeThing and the placed units are replaced here, the shared builders untouched):
  aicrush1   Crush true, CrushPreference 1.0 (retail) -> the model: the tanks drive into the guards
  aicrush0   Crush false -> they shoot
  aicrushlo  Crush true, CrushPreference 0.01 -> the drive is never 'worth it': they shoot
Facts: wake at.
"""
from missions import aitarget_bench as at
from missions import airetreat_bench as ar

TANK = 'SovietAntiVehicleVehicleTech1'


def mission(mod, **fields):
    m = ar.mission(mod, guards=ar.GUARDS, RetreatPowerAdvantage='0.0', **fields)
    (fname, xml, asset), = m.assets
    assert f'<IncludeThing>{at.INF}</IncludeThing>' in xml
    m.assets = [(fname, xml.replace(f'<IncludeThing>{at.INF}</IncludeThing>', f'<IncludeThing>{TANK}</IncludeThing>'),
                 asset)]
    for o in m.objects:
        if o.template == at.INF and o.side == 's1':
            o.template = TANK
    m.cast = {k: (r.__class__(TANK, r.name, r.side) if r.template == at.INF and r.side == 's1' else r)
              for k, r in m.cast.items()}
    m.cnv_units = (at.INF, TANK)
    m.spawns |= {TANK}
    return m


MISSION = {
    'aicrush1': lambda: mission('CampAICrush1', Crush='true', CrushPreference='1.0'),
    'aicrush0': lambda: mission('CampAICrush0', Crush='false'),
    'aicrushlo': lambda: mission('CampAICrushLo', Crush='true', CrushPreference='0.01'),
}
