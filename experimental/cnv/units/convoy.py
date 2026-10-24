"""The convoy truck (A4 / J4): a plain unarmed vehicle the mission drives, nothing of its own.

It was retail's Allied ore collector. Once the maps carry ore (docs/story/map-language.md 3), a collector drives off
to mine at the start by itself (bench 2026-10-23: truck 1 rolled into plaza 1's ambush area before the convoy left).
It is also amphibious and would ford a canal instead of taking its bridge. So this is that collector with its mining
cut out: no BaseMiner (no ore AI), no water locomotor, no deploying into an outpost, no buttons. Same model, armour,
500 health and speed 50.

Published: what it is; params health, speed.
"""
import os
import re

import make_campnew2 as c2
from parts import Unit
from units.icewall import cut, sub1

SAGE = os.path.join(c2.SDK, 'SageXML')


def truck(id='CNV_ConvoyTruck'):
    x = open(os.path.join(SAGE, 'Allied', 'Units', 'AlliedMiner.xml'), encoding='utf-8').read()
    x = re.sub(r'\s*<GameObject\s+id="AlliedMiner_Naval".*?</GameObject>', '', x, count=1, flags=re.S)
    x = sub1(x, 'source="DATA:BaseObjects/BaseMiner.xml"', 'source="DATA:BaseObjects/BaseVehicle.xml"')
    x = sub1(x, 'id="AlliedMiner"', f'id="{id}"')
    x = sub1(x, 'inheritFrom="BaseMiner"', 'inheritFrom="BaseVehicle"')
    x = sub1(x, 'EditorName="AlliedMiner"', f'EditorName="{id}"')
    x = sub1(x, 'CommandSet="AlliedMinerCommandSet"', 'CommandSet="EmptyCommandSet"')
    x = sub1(x, 'SCORE AMPHIBIOUS VEHICLE T2_UNIT HARVESTER MOVE_FOR_NOONE IGNORES_SELECT_ALL CAN_BE_FAVORITE_UNIT '
                'EXPANSION_UNIT UNPACKS_INTO_BUILDING CYCLE_SELECTION SKIRMISH_AI_CAN_BUILD_DURING_EMERGENCY_NO_INCOME"',
             'SCORE VEHICLE T2_UNIT IGNORES_SELECT_ALL"')
    x = re.sub(r'\s*<LocomotorSet\s+Locomotor="AlliedMinerWaterLocomotor".*?/>', '', x, count=1, flags=re.S)
    x = cut(x, 'ReplaceSelfSpecialAbility', 'ModuleTag_ReplaceSelf')
    x = re.sub(r'\s*<SkirmishAIInformation\s+BlockIfUnpackTargetBuildingCannotBeRebuilt="false"\s*/>', '', x, count=1)
    # the collector's AI came from BaseMiner (its ore state machine); a plain one, never picking fights
    x = re.sub(r'<!-- AI is implemented in BaseMiner class.*?-->', '<AI>\n\t\t\t<AIUpdate id="ModuleTag_AI" '
               'AutoAcquireEnemiesWhenIdle="NO"/>\n\t\t</AI>', x, count=1, flags=re.S)
    assert 'ModuleTag_AI' in x and 'BaseMiner' not in x and 'AlliedMiner_Naval' not in x
    return Unit(id, x, what='车队运输车：原版盟军矿车去掉采矿、两栖和展开，没有武器，500 血，速度 50',
                params=dict(health=500, speed=50))
