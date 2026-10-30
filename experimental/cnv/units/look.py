"""The units line's names and buttons for our units (user 2026-10-29: "新单位至少要把技能图标和名称改掉，模型先不改也
可以"): what a player reads and sees on a unit -- its name, type and description (selection panel, build bar,
tooltip), its production button and selection portrait, each ability's icon, title and description -- ours instead
of the retail unit it is built on. Look only: weapons, powers, behaviours stay.

name(unit, name, kind, desc): the unit's DisplayName, TypeDescription and Description labels its own (strings).
button(unit, command, key, title, desc, off=None): the button of one of its commands ours: icon CNA_<key>
  (experimental/units/ability_icons.py writes it into the SDK's Art), title and description; a toggle's second state
  off = (key, title, desc). In RA3 a button belongs to a command (UnitAbilityButtonTemplate LogicCommand=...), so a
  retail command is copied under our id (Command_<unit>_<key>, the same special power), put in the unit's command set
  (a retail set copied as <unit>CommandSet) and the unit's published abilities follow it; a command of ours keeps its
  id, its button's state swapped.
icons(unit, model): its production button and portrait Button_<model> / Portrait_<model> (ui_kit.py writes them).
quiet(unit): no command buttons at all (EmptyCommandSet) -- a prop on a building's logic (ice, sculptures, gates)
  showed the bunker's 'everyone out'.
"""
import os
import re

import make_campnew2 as c2

SAGE = os.path.join(c2.SDK, 'SageXML')
_RETAIL = {}


def _retail(kind):
    """{id: element text} of retail's LogicCommand / LogicCommandSet / (mouse) UnitAbilityButtonTemplate by command."""
    if not _RETAIL:
        def read(*p):
            return open(os.path.join(SAGE, *p), encoding='utf-8').read()
        _RETAIL['LogicCommand'] = _elements(read('GlobalData', 'LogicCommand.xml'), 'LogicCommand', 'id')
        _RETAIL['LogicCommandSet'] = _elements(read('GlobalData', 'LogicCommandSet.xml'), 'LogicCommandSet', 'id')
        _RETAIL['Button'] = _elements(read('UI', 'Mouse', 'UnitAbilityButtonTemplates.xml'),
                                      'UnitAbilityButtonTemplate', 'LogicCommand')
    return _RETAIL[kind]


def _elements(text, tag, key):
    out = {}
    for m in re.finditer(rf'<{tag}\b(?:(?!<{tag}\b).)*?</{tag}>', text, re.S):
        k = re.search(rf'\b{key}="([^"]+)"', m.group(0))
        if k:
            out[k.group(1)] = m.group(0)
    return out


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def _look_file(unit):
    f = f'{unit.id}_Look.xml'
    if f not in unit.files:
        unit.files[f] = ('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
                         'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n</AssetDeclaration>\n')
        unit.also.append(f)
    return f


def _add(unit, text):
    f = _look_file(unit)
    unit.files[f] = sub1(unit.files[f], '</AssetDeclaration>', text + '\n</AssetDeclaration>')


def _include(unit, art):
    inc = f'<Include type="all" source="ART:{art}.xml" />'
    if inc not in unit.xml:
        unit.xml = sub1(unit.xml, '<Includes>', f'<Includes>\n\t\t{inc}')


def name(unit, name, kind, desc):
    x = re.sub(r'(<DisplayName\b[^>]*>)[^<]*(<)', rf'\g<1>Name:{unit.id}\2', unit.xml, count=1)
    assert x != unit.xml or f'>Name:{unit.id}<' in x, unit.id
    x = re.sub(r'(?<![A-Za-z])Description="[^"]*"', f'Description="Desc:{unit.id}"', x, count=1)
    x = re.sub(r'\bTypeDescription="[^"]*"', f'TypeDescription="Type:{unit.id}"', x, count=1)
    unit.xml = x
    unit.strings.update({f'Name:{unit.id}': name, f'Type:{unit.id}': kind, f'Desc:{unit.id}': desc})
    return unit


def _state(unit, key, title, desc):
    sid = f'ButtonState_{unit.id}_{key}'
    _include(unit, f'CNA_{key}')
    _add(unit, f'''	<ButtonSingleStateData id="{sid}">
		<State Image="CNA_{key}" Title="Name:{unit.id}_{key}" Description="Desc:{unit.id}_{key}" />
	</ButtonSingleStateData>''')
    unit.strings.update({f'Name:{unit.id}_{key}': title, f'Desc:{unit.id}_{key}': desc})
    unit.link += [f'ButtonSingleStateData:{sid}', f'PackedTextureImage:CNA_{key}', f'Texture:CNA_{key}_tex']
    return sid


def _texts(unit):
    return [unit.xml] + [unit.files[f] for f in unit.files]


def _own(unit, tag, key, value):
    """(holder, element) of our element <tag key=value> in the unit's XML or files, or None."""
    for holder in [None] + list(unit.files):
        text = unit.xml if holder is None else unit.files[holder]
        found = _elements(text, tag, key).get(value)
        if found:
            return holder, found
    return None


def _replace(unit, holder, old, new):
    if holder is None:
        unit.xml = sub1(unit.xml, old, new)
    else:
        unit.files[holder] = sub1(unit.files[holder], old, new)


def button(unit, command, key, title, desc, off=None):
    states = [_state(unit, key, title, desc)] + ([_state(unit, *off)] if off else [])
    mine = _own(unit, 'UnitAbilityButtonTemplate', 'LogicCommand', command)
    if mine:                                    # our command: its button's states swapped
        holder, template = mine
        olds = re.findall(r'StateData="([^"]+)"|<StateData>([^<]+)</StateData>', template)
        new = template
        for (a, b), s in zip(olds, states):
            new = new.replace(a or b, s, 1)
        _replace(unit, holder, template, new)
        return command
    new_id = f'Command_{unit.id}_{key}'
    _add(unit, '\t' + sub1(_retail('LogicCommand')[command], f'id="{command}"', f'id="{new_id}"'))
    template = _retail('Button')[command]
    template = re.sub(r'\bid="[^"]+"', f'id="Button_{new_id}"', template, count=1)
    template = sub1(template, f'LogicCommand="{command}"', f'LogicCommand="{new_id}"')
    olds = re.findall(r'StateData="([^"]+)"|<StateData>([^<]+)</StateData>', template)
    assert len(olds) == len(states) or (len(olds) == 2 and len(states) == 1), (command, olds)
    for i, (a, b) in enumerate(olds):
        template = template.replace(a or b, states[min(i, len(states) - 1)], 1)
    _add(unit, '\t' + template)
    cs = re.search(r'\bCommandSet="([^"]+)"', unit.xml).group(1)
    mine = _own(unit, 'LogicCommandSet', 'id', cs)
    if mine:
        holder, cset = mine
        _replace(unit, holder, cset, sub1(cset, f'<Cmd>{command}</Cmd>', f'<Cmd>{new_id}</Cmd>'))
    else:
        cset = _retail('LogicCommandSet')[cs]
        ours = f'{unit.id}CommandSet'
        cset = sub1(sub1(cset, f'id="{cs}"', f'id="{ours}"'), f'<Cmd>{command}</Cmd>', f'<Cmd>{new_id}</Cmd>')
        _add(unit, '\t' + cset)
        unit.xml = sub1(unit.xml, f'CommandSet="{cs}"', f'CommandSet="{ours}"')
        unit.link.append(f'LogicCommandSet:{ours}')
    unit.link += [f'LogicCommand:{new_id}', f'UnitAbilityButtonTemplate:Button_{new_id}']
    unit.abilities = {k: (new_id if v == command else v) for k, v in unit.abilities.items()}
    return new_id


def icons(unit, model):
    _include(unit, f'{model}Button')
    _include(unit, f'{model}Portrait')
    x, n = re.subn(r'\bButtonImage="[^"]*"', f'ButtonImage="Button_{model}"', unit.xml)
    assert n >= 1, unit.id
    x, n = re.subn(r'\bSelectPortrait="[^"]*"', f'SelectPortrait="Portrait_{model}"', x)
    assert n >= 1, unit.id
    unit.xml = x
    for k in ('Button', 'Portrait'):
        unit.link += [f'PackedTextureImage:{k}_{model}', f'Texture:{model}{k}_tex']
    return unit


def quiet(unit):
    unit.xml = re.sub(r'\bCommandSet="[^"]*"', 'CommandSet="EmptyCommandSet"', unit.xml, count=1)
    return unit


# kind (the unit module's function) -> (name, type, description), its buttons [(command, key, title, desc, off)],
# its production button / portrait model (ui_kit.UNITS) or None, quiet. Commands: '{id}' is the unit's id; a name
# in the unit's published abilities stands for that command. Names: docs/story/units.md (our units), the voice
# line's glossary for retail words.
LOOKS = {
    'ice_engineer': (('冰幕工兵', '冰墙封路工兵', '能在路口冻出一道冰墙，挡住敌人的去路；冰墙过一阵就会化。也能占领建筑。'),
                     [('Command_{id}_Freeze', 'freeze', '冻出冰墙', '走到目标点，站着造一会儿，冻出一道挡路的冰墙（放置时拖动'
                       '可转方向）。造的时候工兵没有掩护；冰墙打得碎，过一阵也会化。', None)], 'CNIceEngineer', False),
    'ice_wall': (('冰墙', '冰幕工兵冻出的冰墙', '挡住去路的冰墙，打得碎，过一阵就会化。'), [], None, True),
    'ice_seed': (('冰核', '正在冻结的冰墙', '冰幕工兵正在冻的冰，冻好就是一道冰墙。'), [], None, True),
    'sculpture': (('冰雕', '雪祭展品', '雪祭会场的冰雕。帝国往里面藏了兵，打碎了兵就会冲出来。'), [], None, True),
    'reinforced': (('加固冰雕', '帝国加固的展品', '帝国后补的冰雕，加固过，打不碎；里面的兵倒下了还会从地道里补上来。只能冻住它的出口。'),
                   [], None, True),
    'bank': (('雪堆', '雪祭会场的雪堆', '铲起来的雪堆，挡路，不会化。'), [], None, True),
    'gate': (('船闸闸门', '船闸闸门', '横在水道上的闸门。'), [], None, True),
    'truck': (('车队运输车', '护送车辆', '车队的运输车，没有武器，归护送队指挥。'), [], None, False),
    'chronolag': (None, [('deploy', 'deploy', '展开', '展开后才能开火：向一个目标打一发时滞弹，把它暂时推出时间。展开时不能移动。',
                          ('pack', '收起', '收起炮架，可以移动，不能开火。'))], None, False),
    'beacon': (('超时空信标兵', '盟军召集步兵', '能把一片地方里的我方部队，一下子拉到自己身边。'),
               [('Command_{id}_Pull', 'pull', '召集', '指定一片地方，那里的我方部队立刻被拉到信标兵身边。', None)], 'CNBeacon', False),
    'liberty': (('自由号', '盟军空天航母', '悬停的巨型空中平台，放无人机打地面；超时空甲板能带着甲板下的部队一起跃迁。'),
                [('{command}', 'deck', '超时空跃迁', '把自由号连同甲板下的地面部队，传送到视野里的一点。', None)],
                'CNLiberty', False),
    'liberty_turret': (('自由号炮塔', '自由号的防御炮塔', '自由号平台上的炮塔，拆了它，平台就少一处火力。'), [], None, False),
    'liberty_rider': (None, [], None, False),   # a Guardian riding the deck: retail's name and buttons are right
    'burrower': (('钻地运兵车', '苏联钻地运兵车', '能钻进地下开：在地下打不着，也不能开火。能载五个步兵。'),
                 [('burrow', 'burrow', '钻入地下', '钻进地下：敌人瞄不到它，它也不能开火，开得慢一些。',
                   ('surface', '钻出地面', '钻出地面，可以开火、放下乘客。'))], 'CNBurrower', False),
    'jammer': (('协调器干扰车', '苏联干扰车', '打开干扰后原地不动，周围所有单位都会变慢，自己人也一样。'),
               [('jam', 'jam', '开始干扰', '原地停下，让周围所有单位变慢，敌我不分。',
                 ('jam_off', '停止干扰', '关掉干扰，可以移动。'))], 'CNJammer', False),
    'tesla': (('磁暴坦克', '苏联磁暴坦克', '发射磁暴电弧的坦克。打开电涌时向四周放电。'),
              [('surge', 'surge', '电涌', '向四周放电，瘫痪附近的车辆。', ('surge_off', '停止电涌', '停止放电。'))],
              'CNTesla', False),
    'train': (('装甲列车', '苏联装甲列车', '沿铁轨开的移动堡垒，车上的磁暴炮能边走边打。'),
              [('brake', 'brake', '刹车', '停下列车。', ('brake_off', '开车', '列车继续沿铁轨前进。'))], 'CNTrain', False),
    'shikigami': (('式神护卫', '帝国式神', '纸折的护卫。打开护卫后，附近的敌人都改打它，飞来的炮弹也会拐到它身上。'),
                  [('guard', 'guard', '护卫', '附近的敌人改打式神，炮弹也拐到它身上；这时它更耐打。',
                    ('guard_off', '解除护卫', '不再吸引火力。'))], 'CNShikigami', False),
    'crane': (('纸鹤侦察机', '帝国侦察机', '纸折的侦察机，没有武器，看得很远，一直隐身。'), [], 'CNCrane', False),
    'combo_parent': (('合体机甲·母机', '帝国合体机甲', '子机开进来就合体；合体后光束只打建筑。'),
                     [('Command_TriggerRushAttackSpecialPower', 'rush', '冲撞', '向前猛冲，撞开挡路的东西。', None),
                      ('part', 'part', '分离', '母机和子机分开。', None)], 'CNComboParent', False),
    'combo_child': (('合体机甲·子机', '帝国合体机甲', '开进母机就是合体。'),
                    [('Command_ToggleEnergizedArmorSpecialPower', 'armor', '能量护甲', '打开护甲，减少受到的伤害。', None)],
                    'CNComboChild', False),
    'maiden': (('心灵巫女', '帝国心灵巫女', '能把被克隆体控制的单位收回来。'),
               [('Command_{id}_Control', 'control', '收回控制', '收回附近被克隆体控制的单位。', None)], 'CNMaiden', False),
    'clone': (('克隆体', '未来科技的克隆体', '能控制附近的单位，她活着，被控制的单位就一直听她的。'), [], None, False),
}


def dress(unit, kind):
    """The unit wearing LOOKS[kind]: its names, buttons, icons. A button whose ability the unit was made without
    (the time-lag cannon with deploy=False) is left out."""
    names, buttons, model, mute = LOOKS[kind]
    if names:
        name(unit, *names)
    for command, key, title, desc, off in buttons:
        if '{' not in command and not command.startswith('Command_'):
            if command not in unit.abilities:
                continue
            command = unit.abilities[command]
        command = command.format_map({'id': unit.id, **{k: v for k, v in unit.names.items() if isinstance(v, str)}})
        button(unit, command, key, title, desc, off)
    if model:
        icons(unit, model)
    if mute:
        quiet(unit)
    return unit


def named(kind):
    """The unit function's Units wear LOOKS[kind] (dress); a call may pass look_as=<another kind>, or None for
    retail's names and buttons (one builder makes several things: the ice wall's building is the sculpture too)."""
    import functools

    def wrap(make):
        @functools.wraps(make)
        def made(*args, look_as=kind, **kwargs):
            u = make(*args, **kwargs)
            return dress(u, look_as) if look_as else u
        return made
    return wrap
