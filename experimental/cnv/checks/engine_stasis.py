"""Engine unit test: a time-stop zone (A3; docs/engine/upgrades.md 5) -- every unit in an area stops, whoever owns it,
can neither be hurt nor fire, and comes back when it leaves the area or when the zone is taken away.

The probe's own zone (ADR 0016 G5: built here): CNV_StasisZone, retail's IronCurtainEffect object (no collision,
unattackable, a prop body) with its lifetime and infantry-killing weapon dropped and its aura replaced: every
RefreshDelay it gives every infantry / vehicle / structure within RADIUS, of any relationship to the zone's owner
(ALLIES ENEMIES NEUTRAL, as units/jammer.py's friends aura), the phase tank's out-of-time modifier (units/chronolag.py:
UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS, SPEED 0 %, the Chrono Rift shader) with a short Duration, so
a unit no longer refreshed comes back at most HOLD later. The zone object belongs to the enemy (s1) and is placed or
made by script; taking it away (NAMED_DELETE) is "time up".

On the range probe map (maps/probe_range.py, flat), zone 1 round 'high at 450', zone 2 round 'order at 450':

  in zone 1 from s0   mine (the player's Guardian), foot (the player's peacekeeper squad), theirs (the enemy's
                      Hammer), still (a neutral Guardian)
  outside             chaser (the enemy's Hammer, 500 south), sent through zone 1 to 500 north at CHASE;
                      shooter (the enemy's Hammer, 350 east of zone 1), told to attack mine at SHOOT and again at FREE
  zone 2              late (the player's Guardian) idles where zone 2 is made at MAKE, told to move out at MAKE + 1
  orders              at GO mine / foot / theirs / still are told to move 500 north (frozen: do they?)
                      at OUT theirs is teleported 450 east (out of zone 1: does it come back, and move?)
                      at FREE zone 1 is deleted; at FREE + 1 foot and chaser are told to move 500 north again

  calm (a neutral Guardian in zone 1) is never ordered: the control for "an order given while frozen is kept"

Counters (the bench reads all four):
  时停甲  per unit inside zone 1's area: mine 1, foot 10, theirs 100, still 1000, chaser 10000
  时停乙  late inside zone 2's area 1; theirs inside its OUT spot's area 10; mine below 100 % 100; calm inside 1000
  时停丙  the player's objects IN_STASIS (a squad counts 1)
  时停丁  the enemy's objects IN_STASIS

Read (测, 2026-11-05, twice; the bench's seconds ~1 s ahead of the timers; runs CampStopZone_mcp_1105_000543):
  甲 1111 s1-s8 though four were ordered off at s3; 11011 from s9 (theirs out, the chaser stopped inside);
  丁 1 -> 2 at s5 (the shooter, sent at mine, drove in and stopped), stays 2 after theirs left; 乙's 10 digit
  (theirs at OUT) gone at s15: teleported out, it moved on its next order; 丙 2 -> 3 at s13 (zone 2 made on late,
  which never moves after); s19 (FREE): 丙 3 -> 1, 丁 2 -> 0 within the second; mine (1) out s22 and still (1000)
  out s26 with no new order -- their s3 orders carried out -- while calm stayed to the end; mine hurt only from
  s24 (乙 100) though attacked since s4. Plug round (engine_stasis_plug plug, CampFrzPlug_mcp_1105_000346): neither
  tank through nor round the far gap in 60 s, the frozen MCV 100 % throughout, one tank frozen itself from s55.
"""
import os
import re

import labpaths
from checks import engine_block
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square, status

ZONE = 'CNV_StasisZone'
RADIUS = 200.0
HOLD = '1s'                 # the modifier's Duration: how long a unit stays frozen once the aura stops refreshing it
REFRESH = '0.25s'
STATUS = 'UNATTACKABLE NO_ATTACK NON_AUTOACQUIRABLE IN_STASIS'      # units/chronolag.py PHASE_STATUS
GUARDIAN, HAMMER, FOOT = 'AlliedAntiVehicleVehicleTech1', 'SovietAntiVehicleVehicleTech1', 'AlliedAntiInfantryInfantry'
GO, SHOOT, CHASE, OUT, MAKE, FREE, RUN = 3.0, 4.0, 5.0, 10.0, 14.0, 20.0, 34.0
Z1, Z2 = 'high at 450', 'order at 450'


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def zone(id=ZONE, radius=RADIUS, hold=HOLD, refresh=REFRESH, include='INFANTRY VEHICLE STRUCTURE'):
    """The time-stop zone object: put it (or CREATE_NAMED_ON_TEAM_AT_WAYPOINT it) where the zone is, NAMED_DELETE it
    when time is up. radius: the aura's reach from the object (a circle; a bigger area = several objects). hold: how
    long a unit stays stopped after it was last refreshed. include: the KindOf it stops."""
    mod = f'AttributeModifier_{id}'
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Soviet', 'Props', 'IronCurtainEffect.xml'),
             encoding='utf-8').read()
    x = _sub1(x, 'id="IronCurtainEffect"', f'id="{id}"')
    x = _sub1(x, 'EditorName="IronCurtainEffect"', f'EditorName="{id}"')
    x = _sub1(x, '<DisplayName>IronCurtainEffect</DisplayName>', f'<DisplayName>{id}</DisplayName>')
    for module, tag in (('LifetimeUpdate', 'ModuleTag_LifetimeUpdate'), ('FireWeaponUpdate', 'ModuleTag_FireWeaponUpdate'),
                        ('AttributeModifierAuraUpdate', 'ModuleTag_AttributeModifierAuraUpdate')):
        x, n = re.subn(rf'\s*<{module}\s+id="{tag}"(?:[^>]*/>|.*?</{module}>)', '', x, count=1, flags=re.S)
        assert n == 1, module
    # no UNATTACKABLE in StatusBitFlagsExclude (retail's has it): the modifier sets it, the next refresh would skip
    x = _sub1(x, '<Behaviors>', f'''<Behaviors>
			<AttributeModifierAuraUpdate id="ModuleTag_CNV_StasisAura" AttributeModifierName="{mod}"
				RefreshDelay="{refresh}" Range="{radius:g}" InitiallyActive="true" AllowSelf="false">
				<ObjectFilter Rule="ANY" Relationship="ALLIES ENEMIES NEUTRAL" Include="{include}"/>
			</AttributeModifierAuraUpdate>''')
    x = _sub1(x, '</AssetDeclaration>', f'''	<AttributeModifier id="{mod}" Category="NONE" Duration="{hold}"
		StackingLimit="1" ObjectStatusToSet="{STATUS}" Shader="ShaderOverride_ObjectsChronoRift">
		<Modifier Type="SPEED" Value="0%"/>
	</AttributeModifier>
</AssetDeclaration>''')
    return Unit(id, x, link=[f'AttributeModifier:{mod}'],
                what=f'时停区：隐形光环物体，{radius:g} 内敌我中立的步兵、车辆、建筑推出时间（不能动、不能开火、打不坏），'
                     f'离开或删掉物体后 {hold} 内恢复', params=dict(radius=radius, hold=hold, refresh=refresh))


def mission():
    m = Mission(name='CampStop', map=probe_range, units=[zone()], facts={})
    m.put(ZONE, Z1, side='s1', role='zone 1', name='UNIT - CNV Stop Zone 1')
    for part, template, side, dx, dy in (('mine', GUARDIAN, 'p1', -60, 0), ('foot', FOOT, 'p1', 0, 60),
                                         ('theirs', HAMMER, 's1', 60, 0), ('still', GUARDIAN, 'neutral', 0, -60),
                                         ('calm', GUARDIAN, 'neutral', 0, 120),
                                         ('chaser', HAMMER, 's1', 0, -500), ('shooter', HAMMER, 's1', 350, 0)):
        m.put(template, Z1, dx, dy, side=side, role=part, name=f'UNIT - CNV Stop {part.title()}')
    m.put(GUARDIAN, Z2, side='p1', role='late', name='UNIT - CNV Stop Late')
    m.waypoint('zone 2', 'CNV Stop Zone 2', Z2)
    m.waypoint('out', 'CNV Stop Out', Z1, 450, 0)
    for part, dx in (('mine', -60), ('foot', 0), ('theirs', 60), ('still', 0), ('chaser', 0)):
        m.waypoint(f'{part} north', f'CNV Stop {part.title()} North', Z1, dx, 500)
    m.waypoint('late north', 'CNV Stop Late North', Z2, 0, 500)
    return m


def zone_test(m):
    t = Test()
    t.areas['Test Zone 1'] = square(*m.site(Z1), RADIUS + 20)      # the aura's circle and a little: an edge stop counts
    t.areas['Test Zone 2'] = square(*m.site(Z2), RADIUS + 20)
    t.areas['Test Out'] = square(*m.point('out'), 60)

    def n(part):
        return m.role(part).name

    timers = (('Go', GO), ('Shoot', SHOOT), ('Chase', CHASE), ('Out', OUT), ('Make', MAKE), ('Late', MAKE + 1),
              ('Free', FREE), ('Again', FREE + 1))
    s1 = m.player('s1')
    acts = {
        'Go': [('MOVE_NAMED_UNIT_TO', n(p), m.mark(f'{p} north')) for p in ('mine', 'foot', 'theirs', 'still')],
        'Shoot': [('NAMED_ATTACK_NAMED', n('shooter'), n('mine'))],
        'Chase': [('MOVE_NAMED_UNIT_TO', n('chaser'), m.mark('chaser north'))],
        'Out': [('UNIT_TELEPORT_TO_WAYPOINT', n('theirs'), m.mark('out'))],
        'Make': [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'UNIT - CNV Stop Zone 2', ZONE, m.team('s1'), m.mark('zone 2'))],
        'Late': [('MOVE_NAMED_UNIT_TO', n('late'), m.mark('late north')),
                 ('MOVE_NAMED_UNIT_TO', n('theirs'), m.mark('theirs north'))],
        'Free': [('NAMED_DELETE', n('zone 1')), ('NAMED_ATTACK_NAMED', n('shooter'), n('mine'))],
        'Again': [('MOVE_NAMED_UNIT_TO', n(p), m.mark(f'{p} north')) for p in ('foot', 'chaser')],
    }
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                            [('SET_MILLISECOND_TIMER', f'Test {k}', s) for k, s in timers]))
    t.scripts += [Script(f'Test - {k.lower()}', [('TIMER_EXPIRED', f'Test {k}')], acts[k]) for k, _ in timers]

    def digits(counter, label, rows):
        """counter = sum of 10**k for each condition that holds this frame"""
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        t.scripts += [Script(f'Test - {counter} {k}', [cond], [('INCREMENT_COUNTER', 10 ** k, counter)], once=False)
                      for k, cond in enumerate(rows)]

    digits('CNV_Stop_A', '时停甲', [('NAMED_INSIDE_AREA', n(p), 'Test Zone 1')
                                  for p in ('mine', 'foot', 'theirs', 'still', 'chaser')])
    digits('CNV_Stop_B', '时停乙', [('NAMED_INSIDE_AREA', n('late'), 'Test Zone 2'),
                                  ('NAMED_INSIDE_AREA', n('theirs'), 'Test Out'),
                                  ('UNIT_HEALTH', n('mine'), 0, 100),            # mine below 100 %
                                  ('NAMED_INSIDE_AREA', n('calm'), 'Test Zone 1')])  # the one never ordered
    counted('CNV_Stop_C', '时停丙', t, status=status('IN_STASIS'), most=12)     # a squad counts its every man
    counted('CNV_Stop_D', '时停丁', t, status=status('IN_STASIS'), player=s1, most=12)
    # judged (the bench's seconds run up to ~1 s ahead of the mission's timers): the four ordered off at GO stay
    # (A 1111 till theirs is taken out at OUT); the chaser stops inside (A ever 1xxxx); nobody hurts mine before FREE
    # (B's 100 digit); every enemy unit is back in time soon after FREE (D 0). When each comes back: from the watch.
    t.expect = [('时停甲', GO + 1, '==', 1111, OUT - 2), ('时停甲', 0, 'ever>=', 10000, OUT),
                ('时停乙', 0, '<', 1100, FREE - 1), ('时停丁', FREE + 2, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


PLUG_RADIUS = 45.0      # the plug round's zones: the two MCVs (30 either side of the gap's middle), not much more


def plug_mission():
    """engine_block's enemy lanes (maps/probe_block.py: a 60-wide straight gap plugged by two enemy MCVs, a far gap
    open, way round ~950) with a small zone on each plug: do frozen cars block a narrow way?"""
    m = engine_block.mission()
    m.name = 'CampFrz'
    m.units = [zone(radius=PLUG_RADIUS)]
    for lane in ('enemy move', 'enemy attack'):
        m.put(ZONE, f'{lane} plug', side='s1', name=f'UNIT - CNV Frz {engine_block._key(lane)} Zone')
    return m


def plug(m):
    """A tank each, ordered by move / attack-move to the goal past the frozen plug (engine_block.enemy's orders and
    latched counters: 1 by the far gap, 10 at the goal); the attack lane's front MCV's health; the player's objects
    IN_STASIS (did a tank pushing into the plug get frozen itself?)."""
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for lane, kind in (('enemy move', 'move'), ('enemy attack', 'attack_move')):
        order += engine_block._go(m, t, lane, kind)
        engine_block._scored(m, t, lane)
    counted('Test Frz Plug Hp', '冻车血量', t, health=m.role('enemy attack plug 1').name)
    counted('Test Frz Mine', '我方时滞', t, status=status('IN_STASIS'), most=4)
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=60, every=3, sheet=False, lines=4))]
    t.expect = [('冻车血量', 0, '>=', 100)]       # the control: a frozen MCV is never hurt
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_stasis': mission, 'engine_stasis_plug': plug_mission}
CHECKS = {'engine_stasis': {'zone': zone_test}, 'engine_stasis_plug': {'plug': plug}}
