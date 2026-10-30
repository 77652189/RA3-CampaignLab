r"""Every new unit in front of the player, to click through and read what the game shows -- name, portrait, build
button, ability buttons (experimental/cnv/units/look.py) -- CampNamesLook:

  west field: the units in rows of five, 130 apart (the props among them), the Liberty north of them.

  python -I -X utf8 experimental/units/names_look.py        -> Documents\Red Alert 3\Mods\CampNamesLook
(from a worktree set CNV_SDK to the shared SDK; run ability_icons.py write / badges and ui_kit.py first)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import chronolag, convoy, festival, icewall, liberty, roster, train  # noqa: E402

NAME = 'CampNamesLook'                          # <= 15 characters, no underscore
STEP = 130


def lineup():
    """[(Unit, role)] in placing order; the extra units a unit needs ride along (the combo's child)."""
    out = []
    for name in ('超时空信标兵', '钻地运兵车', '协调器干扰车', '磁暴坦克', '式神护卫', '纸鹤侦察机', '合体机甲', '心灵巫女'):
        out += [(u, u.id) for u in roster.make(name)]
    out += [(u, u.id) for u in (icewall.engineer(), chronolag.chronolag(), convoy.truck(), train.train(),
                                icewall.wall(), festival.sculpture(), festival.reinforced(), festival.bank())]
    return out


def mission():
    units = lineup()
    carrier = liberty.liberty()
    m = parts.Mission(name=NAME, map=island, units=[u for u, _ in units] + [carrier])
    for k, (u, role) in enumerate(units):
        m.put(u.id, 'west field', 60 + STEP * (k % 5), 60 + STEP * (k // 5), name=f'UNIT - CNV Look {k}', role=role,
              angle=0.0)
    m.put(carrier.id, 'west field', 320, 60 + STEP * (len(units) // 5 + 2), name='UNIT - CNV Look Liberty',
          role='liberty', angle=0.0)
    m.scripts += [parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    return m


if __name__ == '__main__':
    print(parts.assemble(mission()))
