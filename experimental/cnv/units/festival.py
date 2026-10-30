"""The snow festival's props (A4 / J4 札幌雪祭, docs/story/outline.md A4): built on the ice wall's building
(units/icewall.py), neither melts.

sculpture: an ice sculpture the enemy hides troops in -- breakable; the mission spawns its troops where it stood
  when it breaks (missions/a4.py), so it holds nothing itself. It wears CNIceSculpt (a Tripo ice dragon on a
  plinth, experimental/units/ice_kit.py) and leaves small ice rubble when broken (icewall.dress).
reinforced: the sculptures nothing breaks (devices/ice_plazas.py 无敌: A4's plazas 2 and 3) -- the same building in
  CNIceSculptHard, the dragon in darker, bluer ice and a size bigger (a4.md: "颜色发暗、比别的厚一圈").
bank: a long snow bank, the festival plazas' walls: it blocks the way like an ice wall and stays. It wears
  CNSnowBank (a shovelled berm 220 long, ice_kit.bank; retail has no snow drift) and leaves nothing when broken.

Published: what each is, params (the wall's length / thick / health; model, rubble).
"""
from units import icewall as iw


def sculpture(id='CNV_IceSculpture', size=40, health=400, model='CNIceSculpt', leaves='CNIceRubbleS',
              look_as='sculpture'):
    return iw.wall(id, length=size, thick=size, lifetime=None, health=health, model=model, leaves=leaves,
                   look_as=look_as,
                   what=f'冰雕：{size} 见方的建筑，{health} 血，不化；打碎时关卡在原地放出藏着的兵')


def reinforced(id='CNV_IceSculptureHard', size=40, health=400, model='CNIceSculptHard', leaves='CNIceRubbleS'):
    return sculpture(id, size, health, model, leaves, look_as='reinforced')


def bank(id='CNV_SnowBank', length=220, thick=24, health=5000, model='CNSnowBank'):
    """model: its look (icewall.dress); None keeps the bunker's."""
    return iw.wall(id, length=length, thick=thick, lifetime=None, health=health, model=model, leaves=None,
                   look_as='bank',
                   what=f'雪堆：长 {length} 的墙，围出会场的广场，挡路、不化')
