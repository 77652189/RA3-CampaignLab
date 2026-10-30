"""Our units show our names and buttons, not the retail unit's they are built on (experimental/cnv/units/look.py;
user 2026-10-29: "新单位至少要把技能图标和名称改掉"): every new unit's name label is its own and has its text, every
command button on it that is not a shared one (attack-move, stop, everyone out ...) shows one of our icons, and every
icon and button picture it names is one experimental/units makes."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'cnv'))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'units'))
import ability_icons  # noqa: E402
import parts  # noqa: E402,F401  (puts experimental/campaign on the path)
import ui_kit  # noqa: E402
from units import chronolag, convoy, festival, icewall, liberty, look, roster, train  # noqa: E402

# buttons every unit of a kind shares in retail: they stay retail's
SHARED = {'Command_AttackMove', 'Command_Stop', 'Command_Evacuate', 'Command_ActivateEjectPassengersSpecialPower',
          'Command_CaptureBuilding', 'Command_MoveToPositionAndCollect', 'Command_SovietAntiGroundAircraftEvacuate'}


def units():
    out = []
    for name in roster.NAMES:
        if name != '船闸闸门':
            out += roster.make(name)
    return out + [icewall.engineer(), icewall.wall(), icewall.seed('CNV_IceSeed', 'CNV_IceWall'), festival.sculpture(),
                  festival.reinforced(), festival.bank(), convoy.truck(), chronolag.chronolag(), liberty.liberty(),
                  liberty.turret(), train.train()]       # not liberty.rider(): a retail Guardian on the deck


def test_every_new_unit_has_its_own_name():
    for u in units():
        label = re.search(r'<DisplayName\b[^>]*>([^<]+)<', u.xml).group(1)
        assert label == f'Name:{u.id}' and u.strings.get(label), u.id


def test_every_ability_button_is_ours():
    for u in units():
        text = u.xml + ''.join(u.files.values())
        sets = dict(re.findall(r'<LogicCommandSet\s+id="([^"]+)"[^>]*>(.*?)</LogicCommandSet>', text, re.S))
        cs = re.search(r'\bCommandSet="([^"]+)"', u.xml)
        if cs is None or cs.group(1) == 'EmptyCommandSet':       # no buttons (the Liberty's turret)
            continue
        cs = cs.group(1)
        cset = sets.get(cs) or look._retail('LogicCommandSet')[cs]   # a retail set: shared buttons only (asserted)
        for cmd in re.findall(r'<Cmd>([^<]+)</Cmd>', cset):
            if cmd in SHARED:
                continue
            m = re.search(rf'<UnitAbilityButtonTemplate\b[^>]*LogicCommand="{cmd}"[^>]*>(.*?)</UnitAbilityButtonTemplate>',
                          text, re.S)
            assert m, (u.id, cmd, 'no button of ours')
            for state in re.findall(r'StateData="([^"]+)"|<StateData>([^<]+)</StateData>', m.group(1)):
                assert (state[0] or state[1]).startswith('ButtonState_'), (u.id, cmd, state)


def test_every_icon_and_picture_is_made():
    for kind, (_, buttons, model, _) in look.LOOKS.items():
        for _, key, _, _, off in buttons:
            assert key in ability_icons.ICONS, (kind, key)
            assert off is None or off[0] in ability_icons.ICONS, (kind, off)
        assert model is None or model in ui_kit.UNITS, (kind, model)
    for model, (_, _, key) in ability_icons.BADGED.items():
        assert key in ability_icons.ICONS and model in ui_kit.UNITS, model
