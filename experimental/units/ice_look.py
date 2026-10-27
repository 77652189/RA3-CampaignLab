r"""The ice models (ice_kit.py) worn by the 冰幕工兵's wall and core (experimental/cnv/units/icewall.py, which still
wears the Soviet bunker's model), on a bench scene to look at -- CampIceLook:

  west field: a wall placed at the start (lasts 120 s) with a retail Guardian beside it for scale; the engineer
  sent at 5 s to build a core 170 north of him (the core melts into a wall, as in A4); a second placed wall 300
  east with two enemy Hammers ordered at it at 8 s (how it breaks); two ice sculptures (units/festival.py), the
  third Hammer ordered at the far one.

  python -I -X utf8 experimental/units/ice_look.py            -> Documents\Red Alert 3\Mods\CampIceLook
(from a worktree set CNV_SDK to the shared SDK; run ice_kit.py first: it writes the models into the SDK's Art)

dress(unit, model) is the whole change a unit module needs: the bunker's two draws become one of our model, its
model include ours.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'cnv'))
import parts                                    # noqa: E402  (puts experimental/campaign on the path)
from maps import island                         # noqa: E402
from units import festival as fest              # noqa: E402
from units import icewall as iw                 # noqa: E402

NAME = 'CampIceLook'                            # <= 15 characters, no underscore
GUARDIAN = 'AlliedAntiVehicleVehicleTech1'
HAMMER = 'SovietAntiVehicleVehicleTech1'


def rubble(id='CNV_IceRubble', model='CNIceRubble', life=6, sink=5):
    """What a shot-down wall leaves: low broken ice (ice_kit's CNIceRubble) lying `life` seconds, then sinking into
    the ground over `sink`. Not retail's frozen-infantry shards: those are Side Neutral (BaseCollapsingObject) and
    came out the neutral player's red (bench 2026-10-26). Its own house colour off besides; no collision."""
    x = f'''<?xml version="1.0" encoding="UTF-8"?>
<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
	<Tags></Tags>
	<Includes>
		<Include type="all" source="ART:{model}.w3x" />
	</Includes>
	<GameObject id="{id}" Side="Neutral" EditorSorting="MISC_MAN_MADE" TransportSlotCount="0"
		CommandSet="EmptyCommandSet" KindOf="NO_COLLIDE UNATTACKABLE NOT_AUTOACQUIRABLE CLEARED_BY_BUILD DEBRIS"
		RadarPriority="NOT_ON_RADAR">
		<DisplayName>Ice Rubble</DisplayName>
		<ArmorSet Armor="NoArmor" />
		<Draws>
			<ScriptedModelDraw id="ModuleTag_Draw" OkToChangeModelColor="false">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{model.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
			</ScriptedModelDraw>
		</Draws>
		<Behaviors>
			<LifetimeUpdate id="ModuleTag_LifeTime" MinLifetime="{life}s" MaxLifetime="{life}s" />
			<SlowDeath id="ModuleTag_Death" SinkDelay="0s" SinkRate="{16 / sink:.2f}" DestructionDelay="{sink}s">
				<DieMuxData DeathTypes="ALL" />
			</SlowDeath>
		</Behaviors>
		<Body>
			<PropBody id="ModuleTag_Body" />
		</Body>
		<Geometry>
			<Shape Type="SPHERE" MajorRadius="20.0" Height="20.0" />
		</Geometry>
		<VisionInfo VisionRange="0" ShroudClearingRange="0" />
	</GameObject>
</AssetDeclaration>
'''
    return parts.Unit(id, x, what=f'碎冰：冰墙被打碎后留下的冰渣，{life} 秒后沉进地里', params=dict(model=model))


def dress(unit, model, leaves=None):
    """The unit (an icewall.wall / seed, the bunker's XML) wearing `model` (an ART: model, ice_kit.py), leaving the
    object `leaves` (a rubble()) when shot down -- nothing when it melts (FADED) -- instead of the bunker's rubble,
    and cracking instead of its little explosion on every death (melting too). leaves=None: nothing left."""
    x = re.sub(r'<Draws>.*?</Draws>', f'''<Draws>
			<ScriptedModelDraw id="ModuleTag_Draw" OkToChangeModelColor="true" StaticModelLODMode="true">
				<ModelConditionState ParseCondStateType="PARSE_DEFAULT">
					<Model Name="{model.upper()}" />
				</ModelConditionState>
				<AnimationState ParseCondStateType="PARSE_DEFAULT">
				</AnimationState>
			</ScriptedModelDraw>
		</Draws>''', unit.xml, count=1, flags=re.S)
    x, n = re.subn(r'source="ART:SBBunker_SKN\.w3x"', f'source="ART:{model}.w3x"', x)
    assert n == 1 and 'SBBunker_SKN"' not in x, n
    # the little explosion on every death (melting too) becomes retail's unfreeze crack, a sound only (the event
    # cannot go: its FXListBehavior must keep one)
    x, n = re.subn(r'(<Event\s+Index="onDeath"\s+FX=)"FX_Civ_Explosion_Tiny"', r'\1"FX_UnFreeze"', x)
    assert n == 1, n
    if leaves is None:
        x = iw.cut(x, 'CreateObjectDie', 'ModuleTag_CreateObjectDie')
    else:
        ocl = f'OCL_{unit.id}_Rubble'
        x = parts_sub1(x, 'CreationList="SBBunker_Die_OCL">\n\t\t\t\t<DieMuxData\n\t\t\t\t\tDeathTypes="ALL"\n'
                          '\t\t\t\t\tDeathTypesForbidden="SUICIDED" />',
                       f'CreationList="{ocl}">\n\t\t\t\t<DieMuxData DeathTypes="ALL" DeathTypesForbidden="SUICIDED FADED" />')
        x = parts_sub1(x, '</AssetDeclaration>', f'''	<ObjectCreationList id="{ocl}">
		<CreateObject Options="IGNORE_ALL_OBJECTS" Disposition="LIKE_EXISTING" Count="1">
			<CreateObject>{leaves.id}</CreateObject>
		</CreateObject>
	</ObjectCreationList>
</AssetDeclaration>''')
        unit.link = unit.link + [f'ObjectCreationList:{ocl}']
    unit.xml = x
    unit.params['model'] = model
    return unit


def dress_engineer(unit, texture='CNIceEngineer'):
    """The engineer (icewall.engineer, the retail Allied engineer's XML) in his own texture (ice_kit.engineer_texture)
    wherever he wears his model -- the bunker's placing-cursor way (<Texture Original New> in a model state)."""
    x, n = re.subn(r'(Name="AUEngineer_SKN"\s*/>)', rf'\1\n\t\t\t\t\t<Texture Original="AUEngineer" New="{texture}" />',
                   unit.xml)
    assert n >= 1, n
    x = parts_sub1(x, '<Includes>', f'<Includes>\n\t\t<Include type="all" source="ART:{texture}.xml" />')
    unit.xml = x
    unit.params['texture'] = texture
    return unit


def parts_sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def mission():
    ice = rubble()
    chips = rubble('CNV_IceRubbleS', 'CNIceRubbleS')
    placed = dress(iw.wall('CNV_IceWallL', length=160, shape='square', lifetime=120), 'CNIceWall', ice)
    wall = dress(iw.wall('CNV_IceWallLB', length=160, shape='square'), 'CNIceWall', ice)
    core = dress(iw.seed('CNV_IceSeedL', wall.id), 'CNIceSeed')
    eng = dress_engineer(iw.engineer('CNV_IceEngL', wall_id=core.id))
    sculpt = dress(fest.sculpture('CNV_IceSculptL'), 'CNIceSculpt', chips)
    m = parts.Mission(name=NAME, map=island, units=[placed, wall, core, eng, ice, chips, sculpt])
    m.put(sculpt.id, 'west field', 240, 20, name='UNIT - CNV Look Sculpture', role='sculpture', angle=-1.5708)
    m.put(sculpt.id, 'west field', 470, -20, name='UNIT - CNV Look Sculpture B', role='sculpture target',
          angle=-1.5708)
    # all east of the field's middle: x -220 was the shallows (bench 2026-10-26: he rode there on his jet ski)
    m.put(placed.id, 'west field', 60, 170, name='UNIT - CNV Look Wall', role='wall', angle=0.0)
    m.put(GUARDIAN, 'west field', 190, 190, role='guardian', angle=1.5708)
    m.put(eng.id, 'west field', 60, -170, name='UNIT - CNV Look Engineer', role='engineer')
    m.waypoint('spot', 'CNV Look Spot', 'west field', 60, 0)
    m.put(placed.id, 'west field', 360, 60, name='UNIT - CNV Look Target', role='target', angle=0.0)
    for k, dx in enumerate((-60, 0, 60)):
        m.put(HAMMER, 'west field', 360 + dx, -90, side='s1', name=f'UNIT - CNV Look Hammer {k + 1}',
              role=f'hammer {k + 1}')
    m.scripts += [
        parts.Script('Look - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                          ('SET_MILLISECOND_TIMER', 'Look - freeze timer', 5.0),
                                          ('SET_MILLISECOND_TIMER', 'Look - attack timer', 8.0)]),
        parts.Script('Look - freeze', [('TIMER_EXPIRED', 'Look - freeze timer')],
                     [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', m.role('engineer').name,
                       m.ability('engineer', 'freeze'), m.mark('spot'))]),
        parts.Script('Look - attack', [('TIMER_EXPIRED', 'Look - attack timer')],
                     [('NAMED_ATTACK_NAMED', h.name, m.role('target').name) for h in m.roles('hammer')[:2]] +
                     [('NAMED_ATTACK_NAMED', m.role('hammer 3').name, m.role('sculpture target').name)]),
    ]
    return m


if __name__ == '__main__':
    print(parts.assemble(mission()))
