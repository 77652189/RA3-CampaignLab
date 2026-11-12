"""齐步: a force of mixed speeds that arrives together (docs/engine/pathing.md 5, user 2026-11-04 "成群移动按最低速度前进").
A script cannot start the player's formation move (it only runs for units already in a formation), so the compiler does
it the way the bench showed to work (checks/engine_pace.py, `pace`: IFV and engineer at the goal in the same second):
every faster unit of the force carries an upgrade whose SPEED modifier is slowest / own, granted when it is made and taken
away when it arrives (plan.py `齐步`; contract.pace_released holds every grant to a release).

The unit is a copy of the template under an id of its own (`CNV_Pace<pct>_<template>`: the ratio is part of the id, so a
template used by two forces of different slowest members gets two copies), with one AttributeModifierUpgrade added.
Retail's own file is copied, or the XML of a unit of ours; the slowest member itself stays as it is.

Published: movers, percent, paced (a Unit), is_pace_upgrade.
"""
import math
import os
import re

import labpaths
from parts import Unit
from units.icewall import sub1

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
PREFIX = 'Upgrade_CNV_Pace'                        # every pace upgrade id begins so (contract.pace_released)
SAME = 0.995                                       # a unit within 0.5 % of the slowest needs no copy


def retail_xml(template):
    """Retail's GameObject file of a unit (Allied/Units/AlliedEngineer.xml ...)."""
    for faction in sorted(os.listdir(SAGE)):
        p = os.path.join(SAGE, faction, 'Units', template + '.xml')
        if os.path.exists(p):
            return open(p, encoding='utf-8').read()
    raise ValueError(f'{template}: no retail unit file (SageXML/*/Units)')


def movers(templates, own=None):
    """{template: speed} of those that walk, drive or sail: not buildings, not aircraft (an air group keeps its own
    pace: a fighter would stall at a tank's speed). own: {id: xml text} of the mission's units."""
    import simunits
    out = {}
    for t in templates:
        st = simunits.stats(t, own)
        if 'STRUCTURE' in st['kinds'] or 'AIRCRAFT' in st['kinds'] or st['surface'] == 'air' or not st['speed']:
            continue
        out[t] = float(st['speed'])
    return out


def percent(own, slowest):
    """The SPEED modifier that brings a unit of speed `own` down to `slowest` (rounded up: a hair early, never late)."""
    return max(1, min(99, math.ceil(slowest / own * 100 - 1e-9)))


def copy_id(template, pct):
    return f'CNV_Pace{pct}_{template}'


def is_pace_upgrade(name):
    return str(name).startswith(PREFIX)


def paced(template, pct, xml=None):
    """The unit `template` (retail's file, or `xml` for a unit of ours) as `CNV_Pace<pct>_<template>`, an upgrade
    `Upgrade_CNV_Pace<pct>_<template>` slowing it to pct % of its own speed. names['pace'] is the upgrade."""
    id_ = copy_id(template, pct)
    up, mod = f'Upgrade_{id_}', f'AttributeModifier_{id_}'
    x = xml if xml is not None else retail_xml(template)
    # retail's inheriting variants in the same file (the Tsunami's _Naval: its naval-yard build, ProductionQueueType
    # WATERCRAFT) would come along under their retail ids (lint retail-id, bench 11-12): a placed copy needs none
    x = re.sub(rf'\s*<GameObject\s+id="[^"]+"\s+inheritFrom="{re.escape(template)}".*?</GameObject>', '', x, flags=re.S)
    x = sub1(x, f'id="{template}"', f'id="{id_}"')
    x = x.replace(f'EditorName="{template}"', f'EditorName="{id_}"')
    x = sub1(x, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierUpgrade id="ModuleTag_CNV_Pace" AttributeModifier="{mod}">
				<TriggeredBy>{up}</TriggeredBy>
			</AttributeModifierUpgrade>''')
    x = sub1(x, '</AssetDeclaration>', f'''	<UpgradeTemplate id="{up}" Type="OBJECT"/>
	<AttributeModifier id="{mod}" Category="NONE">
		<Modifier Type="SPEED" Value="{pct}%"/>
	</AttributeModifier>
</AssetDeclaration>''')
    return Unit(id_, x, link=[f'UpgradeTemplate:{up}', f'AttributeModifier:{mod}'], names={'pace': up},
                what=f'{template}，升级后速度 x{pct / 100:g}（齐步：和同队最慢的一起到）', params=dict(of=template, percent=pct))
