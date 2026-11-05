"""Engine unit test: a building in the air (ADR 0019 layer 2, batch 5; docs/engine/air.md) -- which of retail's
pieces make a structure float, and what each does to targeting, ground paths, moving and dying.

Generals' rules (read, docs/engine/air.md 1): a weapon picks its victims by KindOf and the AIRBORNE_TARGET status
bit only, never by height; only a locomotor sets that bit, and a structure has none; an airborne object that is not
a vehicle / infantry is nobody's target. A structure's ground footprint is laid when it is placed and does not move
with it. Retail RA3 hints that an attached object can take its parent's bit (IrradiatedTargetDamageDealer:
AttachUpdate ParentStatusToCopy="AIRBORNE_TARGET").

On the range probe map (maps/probe_range.py, flat), three groups 1500 apart, the enemy's (s1) floating things each
with two of the player's IFVs (AlliedAntiAirVehicleTech1, anti-air) and two Hammers (ground only) SHOOTERS south:

  kirov   'removed gun'  a retail Kirov (SovietBomberAircraft): the aircraft-as-platform control; two of the
                         player's peacekeeper squads under it (does its crash kill them?)
  plant   'switch gun'   a carrier Kirov and CNV_FloatPlant (an Allied power plant, 5000 health, an AttachUpdate:
                         STICK_TO_PARENT TELEPORT to a same-player Kirov within RANGE) placed BELOW south of it
  plantair 'low gun'     the same with CNV_FloatPlantAir (ParentStatusToCopy="AIRBORNE_TARGET")

The Kirovs hold fire (NO_ATTACK by script). AA: the IFVs are sent at their group's target, deleted at GROUND;
GROUND: the Hammers are; SPOT: the plant group's first Hammer is sent to where its plant was placed (is the old
footprint still in the way?), the other Hammers are deleted; MOVE: both carriers fly LEG west (does the plant come
along?); KILL: all three Kirovs are killed (does a plant fall, die, stay?).

Counters (the bench reads all four):
  基洛夫血量  the kirov's health % + 1000 x the player's peacekeepers under it (a template count in an area)
  挂厂血量    CNV_FloatPlant's health %
  挂厂空血量  CNV_FloatPlantAir's health %
  挂态       plant ATTACHED 1, plantair ATTACHED 10, plant inside its carrier's goal 100, plantair inside its
             carrier's goal 1000, the plant group's first Hammer inside the plant's old spot 10000

Read (测, 2026-11-05, run CampFloatFloat_mcp_1105_053518; the bench's seconds 1-2 s ahead of the timers):
  基洛夫 2100 (2 squads + 100 %) -> 2079 s6-s14 under the IFVs, unchanged under the Hammers (2080 at s27);
  dead at s40, after which nobody resets the counter (the health action needs the living unit) and it climbs by
  2000 a frame until s46: the squads under it counted 0 from s46 -- the falling wreck killed them.
  挂厂 / 挂厂空 identical: 100 -> 92 under the IFVs (the IFV hits buildings too), -> 86 under the Hammers;
  挂态 0 throughout: neither plant ever ATTACHED nor moved with its carrier, the Hammer never got onto the plant's
  spot -- an AttachUpdate on a STRUCTURE does nothing; ParentStatusToCopy never came into play.
"""
import os

import labpaths
from maps import probe_range
from parts import Mission, Script, Test, Unit, counted, square, status

KIROV, PLANT, IFV, HAMMER = 'SovietBomberAircraft', 'AlliedPowerPlant', 'AlliedAntiAirVehicleTech1', \
    'SovietAntiVehicleVehicleTech1'
FOOT = 'AlliedAntiInfantryInfantry'
GROUPS = {'kirov': 'removed gun', 'plant': 'switch gun', 'plantair': 'low gun'}
FLOAT, FLOAT_AIR = 'CNV_FloatPlant', 'CNV_FloatPlantAir'
BELOW, RANGE, SHOOTERS, LEG, SPOT_R, GOAL_R = 100.0, 200.0, 600.0, 300.0, 40.0, 120.0
AA, GROUND, SPOT, MOVE, KILL, RUN = 4.0, 15.0, 25.0, 26.0, 42.0, 58.0


def _sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def float_plant(id=FLOAT, parent=KIROV, copy=False, health=5000.0, rng=RANGE):
    """A retail Allied power plant that, placed (or built) within rng of a same-player `parent`, goes onto it and
    rides it (AttachUpdate STICK_TO_PARENT TELEPORT, no offset: it sits at the parent's centre). copy: it also takes
    the parent's AIRBORNE_TARGET bit (retail IrradiatedTargetDamageDealer's ParentStatusToCopy)."""
    x = open(os.path.join(labpaths.SDK3, 'SageXML', 'Allied', 'Structures', PLANT + '.xml'), encoding='utf-8').read()
    x = _sub1(x, f'id="{PLANT}"', f'id="{id}"')
    x = _sub1(x, f'EditorName="{PLANT}"', f'EditorName="{id}"')
    x = _sub1(x, 'MaxHealth="1000.0"', f'MaxHealth="{health:.1f}"')
    copied = '\n\t\t\t\tParentStatusToCopy="AIRBORNE_TARGET"' if copy else ''
    x = _sub1(x, '\t\t</Behaviors>', f'''			<AttachUpdate id="ModuleTag_CNV_Float" Range="{rng:g}" IdleScanDelay="0.5s"
				Flags="SAME_PLAYER_ONLY STICK_TO_PARENT TELEPORT"
				AttachedObjectStatus="ATTACHED"{copied}>
				<ObjectFilter Rule="NONE" Relationship="SAME_PLAYER">
					<IncludeThing>{parent}</IncludeThing>
				</ObjectFilter>
			</AttachUpdate>
		</Behaviors>''')
    return Unit(id, x, names=dict(unit=id),
                what=f'挂在 {parent} 上的发电厂（探针）：{rng:g} 内有同一玩家的 {parent} 就瞬移上去跟着走'
                     + ('，并复制它的 AIRBORNE_TARGET' if copy else ''),
                params=dict(parent=parent, copy=copy, health=health, range=rng))


def mission():
    m = Mission(name='CampFloat', map=probe_range,
                units=[float_plant(), float_plant(FLOAT_AIR, copy=True)], facts={})
    for part, site in GROUPS.items():
        P = part.title()
        m.put(KIROV, site, side='s1', role=f'{part} kirov', name=f'UNIT - CNV Float {P} Kirov')
        for k, dx in ((1, -60), (2, 60)):
            m.put(IFV, site, dx, -SHOOTERS, side='p1', role=f'{part} ifv {k}', name=f'UNIT - CNV Float {P} IFV {k}')
            m.put(HAMMER, site, dx, -SHOOTERS - 80, side='p1', role=f'{part} hammer {k}',
                  name=f'UNIT - CNV Float {P} Hammer {k}')
    for part, tpl in (('plant', FLOAT), ('plantair', FLOAT_AIR)):
        m.put(tpl, GROUPS[part], 0, -BELOW, side='s1', role=part, name=f'UNIT - CNV Float {part.title()}')
        m.waypoint(f'{part} goal', f'CNV Float {part.title()} Goal', GROUPS[part], -LEG, 0)
    m.waypoint('plant spot', 'CNV Float Plant Spot', GROUPS['plant'], 0, -BELOW)
    for k, dx in ((1, -40), (2, 40)):
        m.put(FOOT, GROUPS['kirov'], dx, 0, side='p1', role=f'foot {k}', name=f'UNIT - CNV Float Foot {k}')
    return m


def float_test(m):
    t = Test()

    def n(part):
        return m.role(part).name

    kirovs = [n(f'{p} kirov') for p in GROUPS]
    ifvs = [n(f'{p} ifv {k}') for p in GROUPS for k in (1, 2)]
    hammers = [n(f'{p} hammer {k}') for p in GROUPS for k in (1, 2)]
    target = {'kirov': n('kirov kirov'), 'plant': n('plant'), 'plantair': n('plantair')}
    acts = {
        'AA': [('NAMED_ATTACK_NAMED', n(f'{p} ifv {k}'), target[p]) for p in GROUPS for k in (1, 2)],
        'Ground': [('NAMED_DELETE', u) for u in ifvs] +
                  [('NAMED_ATTACK_NAMED', n(f'{p} hammer {k}'), target[p]) for p in GROUPS for k in (1, 2)],
        'Spot': [('MOVE_NAMED_UNIT_TO', n('plant hammer 1'), m.mark('plant spot'))] +
                [('NAMED_DELETE', u) for u in hammers if u != n('plant hammer 1')],
        'Move': [('MOVE_NAMED_UNIT_TO', n(f'{p} kirov'), m.mark(f'{p} goal')) for p in ('plant', 'plantair')],
        'Kill': [('NAMED_KILL', k) for k in kirovs],
    }
    timers = (('AA', AA), ('Ground', GROUND), ('Spot', SPOT), ('Move', MOVE), ('Kill', KILL))
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))] +
                            [('UNIT_CHANGE_OBJECT_STATUS', k, 'NO_ATTACK', 1) for k in kirovs] +
                            [('SET_MILLISECOND_TIMER', f'Test {k}', s) for k, s in timers]))
    t.scripts += [Script(f'Test - {k.lower()}', [('TIMER_EXPIRED', f'Test {k}')], acts[k]) for k, _ in timers]

    counted('CNV_Float_Kirov', '基洛夫血量', t, health=target['kirov'])
    counted('CNV_Float_Plant', '挂厂血量', t, health=target['plant'])
    counted('CNV_Float_Air', '挂厂空血量', t, health=target['plantair'])

    for p in ('plant', 'plantair'):
        t.areas[f'Test {p.title()} Goal'] = square(*m.point(f'{p} goal'), GOAL_R)
    t.areas['Test Plant Spot'] = square(*m.point('plant spot'), SPOT_R)
    rows = [(1, ('UNIT_HAS_OBJECT_STATUS', target['plant'], status('ATTACHED'))),
            (10, ('UNIT_HAS_OBJECT_STATUS', target['plantair'], status('ATTACHED'))),
            (100, ('NAMED_INSIDE_AREA', target['plant'], 'Test Plant Goal')),
            (1000, ('NAMED_INSIDE_AREA', target['plantair'], 'Test Plantair Goal')),
            (10000, ('NAMED_INSIDE_AREA', n('plant hammer 1'), 'Test Plant Spot'))]
    t.counters.append(('CNV_Float_Bits', '挂态'))
    t.scripts.append(Script('Test - CNV_Float_Bits zero', [], [('SET_COUNTER', 'CNV_Float_Bits', 0)], once=False))
    t.scripts += [Script(f'Test - CNV_Float_Bits {step}', [cond], [('INCREMENT_COUNTER', step, 'CNV_Float_Bits')],
                         once=False) for step, cond in rows]

    # four counter lines at most: the peacekeepers under the kirov ride on its health counter as thousands
    t.areas['Test Under Kirov'] = square(*m.site(GROUPS['kirov']), 250.0)
    t.scripts += [Script(f'Test - CNV_Float_Kirov foot {k}', [
        ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', m.player('p1'), 3, k, FOOT, 'Test Under Kirov')],
        [('INCREMENT_COUNTER', 1000, 'CNV_Float_Kirov')], once=False) for k in range(1, 13)]
    # a measurement: no expectations, the readings are written up in docs/engine/air.md
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=4))]
    return t


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_float': mission}
CHECKS = {'engine_float': {'float': float_test}}
