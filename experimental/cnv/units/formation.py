"""The player's two formation switches (user 2026-11-12/13, engine line D: "同速" and "密集", one toggle each, next to
the unit's own command buttons). The data half; ra3ext's CNVSync module does the work (work/re, private):

  同速 (move together)  a unit with the switch on has ObjectStatus HAS_TIBERIUM_GROWTH_MOD (a CnC3 leftover nothing in
                       RA3 sets: INFERRED). Every 15 frames CNVSync takes the player's units with it on that are moving,
                       groups them by goal point, and slows each faster one to the slowest with one of 14 SPEED
                       modifiers CNVSpd30 .. CNVSpd95 (30 % .. 95 %, put on for 30 frames and renewed each look).
  密集 (dense)          HAS_TIBERIUM_UPGRADE (the same kind of leftover); nothing reads it yet.

Retail has neither (the plain right-click and the both-buttons drag move every unit at its own speed: bench, D 84).

host(): the CNVSync carrier, a power plant copy that also declares what the two switches share (the 14 modifiers, the
  two special powers, commands and buttons) -- one declaration however many unit kinds carry the switches.
switches(unit): a Unit with both toggles added, its command set copied with our two commands after its own.
Published (host): names sync / dense = the two commands (NAMED_USE_COMMANDBUTTON_ABILITY presses them).
"""
import os
import re

import labpaths
from parts import Unit

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
TIERS = tuple(range(30, 100, 5))                   # ra3ext SYNC_TIER0 / SYNC_TIER_STEP / SYNC_TIERS
SPEED_IDS = tuple(f'CNVSpd{p}' for p in TIERS)     # ra3ext looks them up by FastHash of the lower-case id
SWITCH = {'sync': dict(status='HAS_TIBERIUM_GROWTH_MOD', image='AUA_Timebelt', title='同速',
                       desc='开着时，和一起走的队友按最慢的速度前进，一起到。'),
          'dense': dict(status='HAS_TIBERIUM_UPGRADE', image='AUA_Pack', title='密集',
                        desc='开着时，移动中队形站得更紧。')}
OFF_IMAGE = 'Button_AbilityGeneric'
HOST_EVERY, HOST_LINES = 15, 400


def ids(key):
    k = key.title()
    return dict(power=f'SpecialPower_CNVForm{k}', command=f'Command_CNVForm{k}', button=f'Button_CNVForm{k}',
                first=f'ButtonState_CNVForm{k}', second=f'ButtonState_CNVForm{k}On')


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def _decls():
    mods = ''.join(f'''	<AttributeModifier id="{i}" Category="NONE">
		<Modifier Type="SPEED" Value="{p}%"/>
	</AttributeModifier>
''' for i, p in zip(SPEED_IDS, TIERS))
    powers = ''.join(f'''	<SpecialPowerTemplate id="{ids(k)['power']}" TargetType="NONE" Flags="CAN_NOT_BE_SCRAMBLED"
		WaypointModeTerminal="false" ReloadTime="0.5s"/>
	<LogicCommand Type="SPECIAL_POWER" id="{ids(k)['command']}">
		<SpecialPower>{ids(k)['power']}</SpecialPower>
	</LogicCommand>
''' for k in SWITCH)
    return mods + powers


def _ui():
    out = ''
    for k, s in SWITCH.items():
        i = ids(k)
        out += f'''	<UnitAbilityButtonTemplate id="{i['button']}" LogicCommand="{i['command']}">
		<Data>
			<ToggleSpecialPower>
				<StateData>{i['first']}</StateData>
				<StateData>{i['second']}</StateData>
			</ToggleSpecialPower>
		</Data>
	</UnitAbilityButtonTemplate>
	<ButtonSingleStateData id="{i['first']}">
		<State Image="{s['image']}" Title="Name:CNVForm{k.title()}" Description="Desc:CNVForm{k.title()}" />
	</ButtonSingleStateData>
	<ButtonSingleStateData id="{i['second']}">
		<State Image="{OFF_IMAGE}" Title="Name:CNVForm{k.title()}On" Description="Desc:CNVForm{k.title()}On" />
	</ButtonSingleStateData>
'''
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n' + out + '</AssetDeclaration>\n')


def host(id='CNVSyncHost', of='AlliedPowerPlant'):
    """The CNVSync carrier: a copy of `of` (an Allied structure) with the passive module; put one per player that uses
    the switches. Lines: at most HOST_LINES `sync:` lines in ra3ext.log (a line only when the plan changes)."""
    with open(os.path.join(SAGE, 'Allied', 'Structures', of + '.xml'), encoding='utf-8') as f:
        x = f.read()
    x = sub1(x, f'id="{of}"', f'id="{id}"')
    x = x.replace(f'EditorName="{of}"', f'EditorName="{id}"')
    x = sub1(x, '<Behaviors>', f'''<Behaviors>
			<DeletionUpdate id="ModuleTag_CNVSync" MinFrames="{HOST_EVERY}" MaxFrames="{HOST_LINES}"/>''')
    x = sub1(x, '</AssetDeclaration>', _decls() + '</AssetDeclaration>')
    ui = f'{id}_UI.xml'
    strings = {}
    for k, s in SWITCH.items():
        n = f'CNVForm{k.title()}'
        strings.update({f'Name:{n}': s['title'] + '：关', f'Desc:{n}': s['desc'] + '按下打开。',
                        f'Name:{n}On': s['title'] + '：开', f'Desc:{n}On': s['desc'] + '再按一下关掉。'})
    link = [f'AttributeModifier:{i}' for i in SPEED_IDS]
    for k in SWITCH:
        i = ids(k)
        link += [f'SpecialPowerTemplate:{i["power"]}', f'LogicCommand:{i["command"]}',
                 f'UnitAbilityButtonTemplate:{i["button"]}', f'ButtonSingleStateData:{i["first"]}',
                 f'ButtonSingleStateData:{i["second"]}']
    return Unit(id, x, files={ui: _ui()}, also=[ui], link=link, strings=strings,
                names={k: ids(k)['command'] for k in SWITCH},
                what=f'玩家队形开关的宿主（{of} 的复制）：ra3ext CNVSync 每 {HOST_EVERY} 帧给开着"同速"的移动中单位按最慢者挂减速；'
                     '也声明两个开关共用的修正、技能、按钮',
                params=dict(of=of, every=HOST_EVERY, lines=HOST_LINES))


def switches(unit):
    """`unit` (a Unit whose XML is one GameObject with a CommandSet) with both toggles: two SpecialPower +
    ToggleStatusSpecialAbilityUpdate pairs (first state empty = off; the second sets the switch's ObjectStatus) and
    its command set copied as <id>CommandSet with our two commands after its own. Needs host() in the same mod."""
    x = unit.xml
    cs = re.search(r'\bCommandSet="([^"]+)"', x).group(1)
    retail = open(os.path.join(SAGE, 'GlobalData', 'LogicCommandSet.xml'), encoding='utf-8').read()
    m = re.search(rf'<LogicCommandSet\s+id="{re.escape(cs)}">(.*?)</LogicCommandSet>', retail, re.S)
    assert m, cs
    cmds = re.findall(r'<Cmd>([^<]+)</Cmd>', m.group(1))
    mine = f'{unit.id}CommandSet'
    x = sub1(x, f'CommandSet="{cs}"', f'CommandSet="{mine}"')
    modules = ''
    for k, s in SWITCH.items():
        i = ids(k)
        modules += f'''			<SpecialPower id="ModuleTag_CNVForm{k.title()}" SpecialPowerTemplate="{i['power']}"
				UpdateModuleStartsAttack="true"/>
			<ToggleStatusSpecialAbilityUpdate id="ModuleTag_CNVForm{k.title()}Toggle" Options="RECONSTITUTE_STORED_COMMAND"
				SpecialPowerTemplate="{i['power']}">
				<ToggleState>
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
				<ToggleState ObjectStatus="{s['status']}">
					<SkirmishAiInfo ToggleHint="TOGGLE_DEFAULT"/>
				</ToggleState>
			</ToggleStatusSpecialAbilityUpdate>
'''
    x = sub1(x, '</Behaviors>', modules + '\t\t</Behaviors>')
    body = ''.join(f'\t\t<Cmd>{c}</Cmd>\n' for c in cmds + [ids(k)['command'] for k in SWITCH])
    x = sub1(x, '</AssetDeclaration>', f'''	<LogicCommandSet id="{mine}">
{body}	</LogicCommandSet>
</AssetDeclaration>''')
    unit.xml = x
    unit.link = list(unit.link) + [f'LogicCommandSet:{mine}']
    unit.abilities = dict(unit.abilities, **{f'form {k}': ids(k)['command'] for k in SWITCH})
    unit.params = dict(unit.params, switches=tuple(SWITCH))
    return unit
