"""Engine unit test: does an upgrade's INVULNERABLE 100% attribute modifier keep a building from losing health, and does
taking the upgrade away make it hurt-able again (docs/engine/upgrades.md 4; what A9's tower ball, units/tower_ball.py,
relies on: dark = INVULNERABLE through an AttributeModifierUpgrade, lit = none).

The probe's own target (ADR 0016 G5: built here, not from units/): retail's Soviet bunker under CNV_InvulnBox, its
garrison, aura, stealth and build dependency dropped, MaxHealth HEALTH, with two OBJECT upgrades like the ball's: Dark =
INVULNERABLE 100% (no Duration), Lit = no modifier. On the range probe map (maps/probe_range.py) each lane's gun is the
player's and its one target stands neutral until SHOW, when it is handed to the enemy, so every gun meets its target
already in the lane's state. Guns: retail's sentry gun (checks/engine_range.gun: GUN damage, 100 % on structures); the
two lanes whose target stands 450 out get their gun's High (RANGE x2 and VISION x2) at s0.

  base     250  no upgrade                                         (control: hurt)
  low      250  Dark at s0, kept                                   (hurt?)
  removed  250  Dark at s0, removed at SWAP                        (hurt?)
  order    450  Dark at s0, removed at SWAP, granted again at BACK (hurt?)
  switch   250  Dark at s0, removed at LATE (12 s after SHOW)      (hurt only from LATE?)
  high     450  the rhythm device's steps while being shot: Dark at s0; LATE: Dark off, Lit on; REDARK: Lit off, Dark on
                (does the health stop falling again at REDARK?)

Counters (the bench reads the first three lines):
  invuln A: base hurt = 1, low hurt = 10, removed hurt = 100, order hurt = 1000
  invuln B: switch hurt = 1, high hurt = 10
  invuln C: high below 90 / 75 / 60 / 45 / 30 % = 1 / 10 / 100 / 1000 / 10000 (when each appears: from the watch)

The kinds round (engine_invuln_kinds, KINDS): the same steps (removed / order keep their Dark), each lane's box another
way of being dark: base no upgrade but retail's A09 Iron Curtain aura object beside it; low / switch / high Dark =
INVULNERABLE + ObjectStatusToSet "NO_BRIBE UNDER_IRON_CURTAIN" (retail Iron Curtain's bits); removed Dark = ARMOR 1%;
order Dark = retail's AttributeModifier_IronCurtain itself (Duration 20 s).

Read (测, 2026-11-04, docs/engine/upgrades.md 4):
  engine_invuln / engine_invuln_enemy (plain INVULNERABLE, targets neutral then enemy / enemy throughout): every
    lane hurt from s7, the kept-dark ones too; high's health falls at one pace through dark, lit, dark again
    (<90 s15, <75 s23, <60 s33, <45 s43). The modifier alone does nothing.
  engine_invuln_kinds: A 100 from s7, 1100 from s19; B 11 from s19; C 1 from s25, then nothing to s49 -- the aura box
    and the kept status box never hurt; the armor box hurt at once (1 % still scratches); the retail-modifier box
    whole for 20 s, then hurt (its Duration runs out under the upgrade too); the status box hurt once its Dark is
    removed (switch), and high hurt while lit (s20-s28) then holds again once dark.
"""
import os
import re

import labpaths
from checks import engine_range
from maps import probe_range
from parts import Mission, Script, Test, Unit

RETAIL = 'SovietBunker'
BOX = 'CNV_InvulnBox'
GUN = 'CNV_InvulnGun'
HEALTH = 4000
SWAP, BACK, SHOW = 3.0, 5.0, 8.0
LATE, REDARK, RUN = SHOW + 12.0, SHOW + 20.0, SHOW + 40.0
LANES = {'base': 250, 'low': 250, 'removed': 250, 'order': 450, 'switch': 250, 'high': 450}
FAR = ('order', 'high')
STEPS = (90, 75, 60, 45, 30)


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


RETAIL_IC = 'AttributeModifier_IronCurtain'     # GlobalData/AttributeModifier.xml: INVULNERABLE + UNDER_IRON_CURTAIN, 20 s
DARK = {    # what the Dark upgrade does, per kind of box
    'plain': '<Modifier Type="INVULNERABLE" Value="100%"/>',                     # the ball's own (units/tower_ball.py)
    'status': '<Modifier Type="INVULNERABLE" Value="100%"/>',                    # + retail Iron Curtain's status bits
    'armor': '<Modifier Type="ARMOR" Value="1%"/>',                              # does the upgrade take at all?
    'retail': None,                                                               # retail's Iron Curtain modifier itself
}


def box(id=BOX, health=HEALTH, kind='plain'):
    """retail's bunker as a plain building with the ball's two upgrades (names on = Lit, off = Dark); kind: what
    Dark does (DARK)."""
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Structures', f'{RETAIL}.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{RETAIL}"', f'id="{id}"')
    x = _sub1(x, f'EditorName="{RETAIL}"', f'EditorName="{id}"')
    x = _sub1(x, 'KindOf="+GARRISON +FS_FACTORY +AUTO_RALLYPOINT +IGNORE_FOR_VICTORY', 'KindOf="+IGNORE_FOR_VICTORY')
    x = _sub1(x, ' +GARRISONABLE_UNTIL_DESTROYED"', '"')
    x = re.sub(r'\s*<GameDependency>.*?</GameDependency>', '', x, count=1, flags=re.S)
    for module, tag in (('GarrisonContain', 'ModuleTag_Garrison'),
                        ('AttributeModifierAuraUpdate', 'ModuleTag_AttributeModifierAura')):
        x, n = re.subn(rf'\s*<{module}\s+id="{tag}".*?</{module}>', '', x, count=1, flags=re.S)
        assert n == 1, module
    x, n = re.subn(r'\s*<InvisibilityBehavior\s+id="ModuleTag_Invisibility"[^>]*/>', '', x, count=1)
    assert n == 1, 'InvisibilityBehavior'
    x = _sub1(x, 'MaxHealth="1500"', f'MaxHealth="{health}"')
    up_on, up_off = f'Upgrade_{id}_Lit', f'Upgrade_{id}_Dark'
    mod_off = RETAIL_IC if kind == 'retail' else f'AttributeModifier_{id}_Dark'
    x = _sub1(x, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierUpgrade id="ModuleTag_CNV_InvulnDark" AttributeModifier="{mod_off}">
				<TriggeredBy>{up_off}</TriggeredBy>
			</AttributeModifierUpgrade>''')
    status = ' ObjectStatusToSet="NO_BRIBE UNDER_IRON_CURTAIN"' if kind == 'status' else ''
    own = '' if kind == 'retail' else f'''
	<AttributeModifier id="{mod_off}" Category="NONE"{status}>
		{DARK[kind]}
	</AttributeModifier>'''
    x = _sub1(x, '</AssetDeclaration>', f'''	<UpgradeTemplate id="{up_on}" Type="OBJECT"/>
	<UpgradeTemplate id="{up_off}" Type="OBJECT"/>{own}
</AssetDeclaration>''')
    link = [f'UpgradeTemplate:{up_on}', f'UpgradeTemplate:{up_off}'] + ([] if kind == 'retail' else
                                                                       [f'AttributeModifier:{mod_off}'])
    return Unit(id, x, link=link, names={'on': up_on, 'off': up_off},
                what=f'引擎探针：原版地堡当靶子，暗 = {kind} 修正升级，亮 = 无修正', params=dict(health=health, kind=kind))


def _key(lane):
    return lane.title()


AURA = 'A09_IronCurtainEffect'      # retail campaign A09's lasting Iron Curtain: an aura object (Range 750, 0.75 s)
KINDS = {'base': 'plain', 'low': 'status', 'removed': 'armor', 'order': 'retail', 'switch': 'status', 'high': 'status'}


def mission(owner='neutral', kinds=None):
    """owner: who holds the targets from s0 -- 'neutral' (handed to the enemy at SHOW) or 's1' (the enemy throughout:
    the gun does not pick a building itself, so it waits for its order at SHOW either way). kinds: {lane: box kind}
    (KINDS: the second round, all lanes' Dark kept from s0 but switch / high, as in invuln; base gets no upgrade but
    retail's Iron Curtain aura object on its target); None: every lane the ball's own plain box."""
    name = 'CampInvK' if kinds else 'CampInv' if owner == 'neutral' else 'CampInvE'
    lanes = kinds or {lane: 'plain' for lane in LANES}
    units = [box(f'{BOX}_{k.title()}', kind=k) for k in dict.fromkeys(lanes.values())]
    m = Mission(name=name, map=probe_range, units=units + [engine_range.gun(GUN, vision=2.0)], facts={})
    for lane, d in LANES.items():
        m.put(GUN, f'{lane} gun', role=f'{lane} gun', name=f'UNIT - CNV Invuln {_key(lane)} Gun')
        m.put(f'{BOX}_{lanes[lane].title()}', f'{lane} at {d:g}', side=owner, role=f'{lane} target',
              name=f'UNIT - CNV Invuln {_key(lane)} Target')
    if kinds:
        m.put(AURA, f'base at {LANES["base"]:g}', side=owner, dy=-60.0)
    for k in range(3):
        m.put('SovietPowerPlant', f'power {k + 1}', role=f'power {k + 1}', name=f'UNIT - CNV Invuln Power {k + 1}')
    return m


def invuln(m):
    t = Test()
    high = next(u for u in m.units if u.id == GUN).names['on']
    kept = m.name == 'CampInvK'         # the kinds round: removed / order keep their Dark (does it take at all?)

    def tg(lane):
        return m.role(f'{lane} target').name

    def up(lane, which):
        return next(u for u in m.units if u.id == m.role(f'{lane} target').template).names[which]

    timers = (('Swap', SWAP), ('Back', BACK), ('Show', SHOW), ('Late', LATE), ('Redark', REDARK))
    start = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    start += [('SET_MILLISECOND_TIMER', f'Test {k}', s) for k, s in timers]
    start += [('NAMED_RECEIVE_UPGRADE', high, m.role(f'{lane} gun').name) for lane in FAR]
    start += [('NAMED_RECEIVE_UPGRADE', up(lane, 'off'), tg(lane)) for lane in LANES if lane != 'base']
    swap = [] if kept else [('NAMED_REMOVE_UPGRADE', up(lane, 'off'), tg(lane)) for lane in ('removed', 'order')]
    back = [] if kept else [('NAMED_RECEIVE_UPGRADE', up('order', 'off'), tg('order'))]
    s1 = m.player('s1')
    # the sentry gun does not pick a building itself (bench 2026-11-04: nothing hurt, the control neither): every gun is
    # told to attack its target at SHOW and again after each switch (a gun might give up on a target it cannot hurt)
    attack = [('NAMED_ATTACK_NAMED', m.role(f'{lane} gun').name, tg(lane)) for lane in LANES]
    neutral = m.name == 'CampInv'
    show = [('NAMED_TRANSFER_OWNERSHIP_PLAYER', tg(lane), s1) for lane in LANES if neutral] + attack
    late = [('NAMED_REMOVE_UPGRADE', up('switch', 'off'), tg('switch')),
            ('NAMED_REMOVE_UPGRADE', up('high', 'off'), tg('high')),
            ('NAMED_RECEIVE_UPGRADE', up('high', 'on'), tg('high'))] + attack
    redark = [('NAMED_REMOVE_UPGRADE', up('high', 'on'), tg('high')),
              ('NAMED_RECEIVE_UPGRADE', up('high', 'off'), tg('high'))] + attack
    t.scripts += [Script('Test - start', [], start)]
    t.scripts += [Script(f'Test - {k.lower()}', [('TIMER_EXPIRED', f'Test {k}')], acts)
                  for k, acts in (('Swap', swap), ('Back', back), ('Show', show), ('Late', late), ('Redark', redark))]
    rows = (('CNV_Invuln_A', '无敌甲', [(lane, 100) for lane in ('base', 'low', 'removed', 'order')]),
            ('CNV_Invuln_B', '无敌乙', [(lane, 100) for lane in ('switch', 'high')]),
            ('CNV_Invuln_C', '无敌丙', [('high', p) for p in STEPS]))
    for counter, label, marks in rows:
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)]))
        for k, (lane, pct) in enumerate(marks):
            name, key = tg(lane), f'{_key(lane)} {pct}'
            flag = f'Test Invuln {key}'
            t.scripts += [Script(f'Test - hurt {key}', [('UNIT_HEALTH', name, 0, pct)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - dead {key}', [('NAMED_DESTROYED', name)], [('SET_FLAG', flag, 1)]),
                          Script(f'Test - hit {key}', [('FLAG', flag, 1)], [('INCREMENT_COUNTER', 10 ** k, counter)])]
    # only the control is judged (the rest is what the test is for): the plain box gets hurt; in the kinds round (base
    # under the aura) the switch box, its Dark gone at LATE, does
    t.expect = [('无敌乙', 0, 'ever>', 0, RUN)] if kept else [('无敌甲', 0, 'ever>', 0, RUN)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=3))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_invuln': mission, 'engine_invuln_enemy': lambda: mission(owner='s1'),
           'engine_invuln_kinds': lambda: mission(owner='s1', kinds=KINDS)}
CHECKS = {'engine_invuln': {'invuln': invuln}, 'engine_invuln_enemy': {'invuln': invuln},
          'engine_invuln_kinds': {'invuln': invuln}}
