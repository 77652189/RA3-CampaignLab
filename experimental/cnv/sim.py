r"""The plan simulator: a level's timeline and ending in seconds, without the game (user 2026-10-27: "把策划案模拟器做
完整，先把开发效率提升上去，最后再把游戏实际和策划案模拟器对齐").

It runs the mission as built -- parts.merged(mission, check): the scripts the compiler wrote (plan.py and the
devices), the objectives' reveal scripts, a check's own -- the way the game runs a map's scripts: every frame each
active script in order, all its conditions true, its actions at once (later scripts see them in the same frame), a
once-script then off. Where the engine line's script engine model is on this computer (ADR 0019 layer 1,
labpaths.ENGINE_MODEL) it runs them, 15 frames a second; elsewhere (a clean clone) an older loop does, a DT tick a
frame. The world is what those scripts ask about: named objects and their owners, health, positions;
flags, counters, timers; objectives; the border, reveals, the camera. Units move along the map's walkable ground
(water for ships, both for amphibians, a straight line for aircraft) at their game speed (simunits.py), routed on the
map's own height field. They fight by a deterministic model from the game's data (Sim.fight: the nearest enemy in
range, damage per second against armour); the player's orders are a script of events (below) -- "60 派 tank 去
north camp", "120 摧毁 north barracks", "90 血量 yuriko 1" -- which can also overrule the fight. A skirmish AI is
not simulated (only what the scripts send). Whatever the engine does that the simulator only guesses at is listed
(ALIGN, and each run's 'guessed' lines): the bench settles those last.

  python -I -X utf8 experimental/cnv/sim.py <level> [--check <check>] [--script <file or "t 动作 ...; ...">]
                                             [--level easy|normal|hard] [--until <seconds>]

A script (剧本), one event a line (or ';' between them), times in seconds or m:ss:
  <t> 派 <谁> 去 <地点>     attack-move (a map site, a mark, a trigger area, a named object, '@x,y' map coordinates)
  <t> 走 <谁> 去 <地点>     a plain move (MOVE_NAMED_UNIT_TO / order_move(..., attacking=False)): fires on the way, does
                            not stop to fight
  <t> 摧毁 <谁>             destroyed (killed by the player)
  <t> 删除 <谁>             gone without dying
  <t> 血量 <谁> <百分比>     health set
  <t> 打 <谁>               attacked by the player (NAMED_ATTACKED_BY_PLAYER)
  <t> 占领 <谁>             now the player's
  <t> 占领 <谁> 进 <建筑>    the player's capture order (NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED Command_CaptureBuilding,
                            order_capture): the engineer walks to the building and takes it at its side
  <t> 旗标 <名字> <值>       a flag set outright (a check's or a device's)
  <t> 生产 <单位> 在 <工厂>   the player's build order at that factory (NAMED_USE_COMMANDBUTTON_ABILITY with its build
                            button): paid as it builds, the build time, out at its door -- '30 生产 AlliedEngineer 在
                            barracks' (bench 2026-11-08 engine_production e: a script's press = the player's click)
  <t> 造 <单位> 在 <地点> [角度]  the player makes one (a unit id of the mission's, a cast part's template, a retail
                            template): an engineer's ice -- '40 造 CNV_IceWall 在 inside 1 1.57'
  <t> 买 <协议>             the player buys a protocol (simtech.Book.buy: known, not held, not locked, its dependencies
                            held, the points there) -- '400 买 PlayerTech_Allied_SatelliteSweep'
  自动打掉 <秒>             every enemy that has been that long within REACH (300) of something of the player's is
                            destroyed (the player fights back where the enemy comes to them)
  不打                      the fight model off (a check of the wiring alone)
  高地不挡                  the high-ground rule off: low ground sees high ground (the Generals way)
  <谁>: a cast part ('yuriko'), a group of them ('tank' = tank 1, tank 2 ...), an object's name, 名字含 <text>
  (every object whose name holds it: '名字含 W1-' a plan's first wave), 敌人 在 <地点> (the enemy's there), 队 <队名>
  (a team's members: 'player/team' or the bare name -- a retail map's unnamed units, retail.py).
"""
import argparse
import collections.abc
import dataclasses
import importlib.util
import math
import os
import re
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import simgarrison  # noqa: E402
import simsweep  # noqa: E402
import simunits  # noqa: E402
from ctx import FUNC_LATE, PANEL_CLEAR  # noqa: E402
from model import coord, facing  # noqa: E402

TEAM_FOLLOWS = ('TEAM_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS_EXACT', 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS',
                'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT')      # Sim.order_follow
TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP') \
    + TEAM_FOLLOWS                                                  # E3: need a live team
SHOW_FLAG = re.compile(r'CNV_\w+_Show_\d+')       # ctx.Talk.show: a 功能 line's caption is asked for
SCENE_FLAG = re.compile(r'CNV_\w+_InScene')       # ctx.Talk.scening

DT = 0.5                        # seconds a tick
UNTIL = 1800.0                  # a run stops here at the latest (30 minutes)
QUIET = 120.0                   # nothing pending this long and no ending: stuck

# A script's superweapon at a waypoint: [(frames after the cast, [(centre distance, damage)])], nothing past the last
# distance. Proton collider: bench 2026-11-07 engine_super p / q (base defenses of 1000 at 0 / 150 / 240 / 300): the
# first hit 56 frames after the cast (+-1), the others in rows ~7 frames apart (INFERRED +15 / +45); the one at 300
# untouched (XML Radius 250); the centre hit once only (the beams sweep: not a taper, not modelled further).
SUPERWEAPON_HITS = {
    'SpecialPowerParticleCannon': [
        (56, [(0.0, 560.0), (150.0, 500.0), (240.0, 390.0), (250.0, 390.0)]),
        (71, [(0.0, 0.0), (150.0, 440.0), (240.0, 340.0), (250.0, 340.0)]),
        (101, [(0.0, 0.0), (150.0, 0.0), (240.0, 150.0), (250.0, 150.0)]),
    ],
    # Vacuum Imploder: engine_super v / w (base defenses at 0 / 150 / 280 / 350): the first loss 62 frames after the cast
    # (the 4 s seed), then gradual in rows ~7 frames apart (~16 % / 11 % / 8 % a row) until 5 / 1 / 1 % are left (the
    # centre after 6 rows, 150 after 9, 280 after ~13); 350 untouched (XML Radius 300). Rows of 7 frames: INFERRED.
    'SpecialPowerVacuumBomb': [
        (62 + 7 * k, [(0.0, 158.0 if k < 6 else 0.0), (150.0, 110.0 if k < 9 else 0.0), (280.0, 76.0), (300.0, 76.0)])
        for k in range(13)
    ],
    # Psionic Decimator (the Empire's): engine_super d / e (base defenses of 1000 at 0 / 150 / 250 / 350): all within 250
    # dead 61 frames after the cast, 350 whole (XML: 4 s, damage 2000, radius 300 -- one hit, flat inside, INFERRED).
    'SpecialPowerTelekineticProjectorDevice': [(61, [(0.0, 2000.0), (300.0, 2000.0)])],
}
# Iron Curtain: engine_super j -- a scripted cast keeps tanks at 0 and 150 from the waypoint whole against enemy fire for
# ~355 frames (the 20 s modifier + the 3 s effect); NAMED_DAMAGE goes through (i). XML: vehicles and structures, aura
# 100, yet g / a (each tank shot by one enemy of its own, NAMED_ATTACK_NAMED, open ground): tanks at 100 / 300 / 500 /
# 800 whole till ~354, at 850 / 950 / 1050 / 1150 hit from frame ~20 -- the reach between 800 and 850 (800 taken; k / l /
# m / o / s were muddled by the enemies picking other targets).
# Nanoswarm Hive: engine_super n -- tanks at 0 and 150 untouched by enemy fire 497+ frames (the run's end), 250 hit from
# frame ~27 (XML radius 200, IN_STASIS 20 s; the end of the stasis not seen -- INFERRED 497); NAMED_DAMAGE goes through.
# Name -> (reach by centre, frames, kinds covered or None for all).
# Frames a superweapon's script cast takes over its ReloadTime before it is ready again: engine_super f -- the proton
# collider ready 5550 frames after the cast (ReloadTime 360 s = 5400; the 150 maybe the cast's own delay: INFERRED,
# the others not measured).
RELOAD_LAG = {'SpecialPowerParticleCannon': 150}
CURTAIN = {'SpecialPowerIronCurtain': (800.0, 355, {'VEHICLE', 'STRUCTURE'}),
           'SpecialPowerNanoSwarmHive': (200.0, 497, None)}


def hit_at(table, d):
    """The damage of one hit's table at centre distance `d`: linear between its distances, 0 past the last."""
    if d > table[-1][0]:
        return 0.0
    for (d0, v0), (d1, v1) in zip(table, table[1:]):
        if d <= d1:
            return v0 + (v1 - v0) * (d - d0) / (d1 - d0) if d1 > d0 else v1
    return table[-1][1]
CIV = 'PlyrCivilian'
CMP = {0: lambda a, b: a < b, 1: lambda a, b: a <= b, 2: lambda a, b: a == b, 3: lambda a, b: a >= b,
       4: lambda a, b: a > b, 5: lambda a, b: a != b}
WON, LOST = 'Mission Won', 'Mission Lost'
LEVELS = {'easy': 0, 'normal': 1, 'hard': 2}
NEAR = 800.0                    # an enemy this close to something of the player's is a threat (the tension curve)
ATTACK_SLACK = 10.0             # R3: an attacker stops this far inside its range of the target (a guess)
CAPTURE_REACH = 20.0           # R4: an engineer this far outside a building's round is at its side (a guess)
# HOOKS 7, ore mining (docs/engine/mining.md, bench 2026-11-05 engine_mining a-e): a load 250 (retail miners'
# DeliveryCapacity), loaded at the node in 30 frames starting the frame after the miner docks, unloaded at the refinery
# in 30 frames from its arrival, 8 a frame and the rest on the last; the node then plays 150 frames (move to extract,
# extract, move to deliver: 60 + 30 + 60) before it takes the next miner; past MaximumGatheredValue (30000) a load is 60
MINE_LOAD, MINE_DOCK, MINE_REST, MINE_FULL, MINE_EMPTY = 250, 30, 150, 30000, 60
MINE_RETRY = 15                # no node / refinery found: the miner idles 1 s and looks again
MINE_DRIVE_EXTRA = 50          # frames a leg takes beyond straight distance / speed: fitted to engine_mining a (a trip of
                               # 269 = 2 x 104 + 30 + 30 + 1, the refinery 180 from its node, the miner 50 a second: 54)
REACH = 300.0                  # 自动打掉: an enemy this close to something of the player's is being fought
SPREAD = 30.0                   # a reinforcement team's units this far apart round its waypoint (Sim.reinforce, INFERRED)
LINGER = 0.0                   # a killed unit's death (its slow death): still in the game's name cache, where it fell
                                # (docs/engine/script-semantics.md 4.2) -- the bench (2026-10-28, probe death): out of
                                # the area from the reading the kill shows in; the guess was 3 s
GRID = 20.0                     # routing cells (world units)
COLUMN_GAP = 44.0              # infantry column march's ends, across and back (bench 11-09 a01: ~44-50; Generals 22)
HOLD_SPOTS = True              # every move's goal kept off other units' spots (Sim.claims): the game's (bench 11-09,
                               # a01's two infantry; checks/engine_spots.py, three trucks sent alone to one point)
ARRIVE = 1.5 * GRID             # a plain move that ends farther than this from where it was sent stopped short (held_up)
UNPACK_POWER = 'SpecialPower_UnpackReplaceSelf'     # the deploy buttons' power (LogicCommand.xml: MCVs, eggs, miner)
REPLACE_FRAMES = 6             # a ReplaceSelfSpecialAbility at its point: the replacement 6 frames on (engine_build a)
BUILD_STEP = 5.0               # a builder on his way (R5) moves in steps this long, to see where he gets within range
HIGH_STEP = 50.0                # ShroudClearingHeight's default: a viewer does not discover a cell this much above its own
                                # (bench, docs/engine/vision.md; a unit's own value is Body.clear_height). Cell by cell,
                                # no line of sight; ENEMY_SIGHTED is a range query and ignores it
FIRE_SEEN = 3.0                 # a bombarder (a weapon longer than its own vision) that fired this lately is seen
LAG = 0.0                       # the readings' clock: mission seconds, as the bench's since 4aed60f (ADR 0007: the
                                # bench counts mission time, at 8x). Expectations written before that counted wall
                                # seconds from the menus' end; the simulator's versions of the checks carry their own
                                # ending (simchecks.py) and judge the counters only where they are wiring

# what the simulator assumes of the engine ("待对齐清单"): printed with every run that leans on one of them. Settled
# by the Generals / Zero Hour source (docs/engine/script-semantics.md, the section given) unless marked 未对齐: those
# the source cannot tell for RA3, for the bench to settle last
ALIGN = {
    'protocols': '未对齐: protocol points as the program keeps them (simtech.py: rank experience 1 a second, 360 a '
                 'rank, the cap, the set-points rule; bench 11-08 engine_protocol pts / ailock); no experience from '
                 'kills, no red alert multiplier; a computer player spends its points at once on a protocol of its '
                 'faction, which one a guess (its personality\'s choice: engine line B)',
    'timer unset': 'TIMER_EXPIRED of a timer never set: false (源码 3)',
    'destroyed unborn': 'NAMED_DESTROYED / NAMED_NOT_DESTROYED of a named object never made: both false (源码 4.2)',
    'deleted': 'NAMED_DELETE: destroyed for NAMED_DESTROYED from the next frame, never "attacked" (源码 4.2)',
    'kind all players': '未对齐（红警3与《将军》不同）: PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA counts every '
                        'player\'s objects, the scenery\'s buildings too (bench 2026-10-25 probe/count; the Generals '
                        'source counts the one player\'s only)',
    'units in area': 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA: any object of that player, buildings and the still too (源码 '
                     '4.1)',
    'discovered': '未对齐: NAMED_DISCOVERED: inside the player\'s sight (vision / shroud range) or a reveal; on the '
                  'bench 2026-10-27 (sight look) it read 1 for every target, 400 off too (the source: ALWAYS_VISIBLE '
                  'objects and ones out of the partition count as clear -- a guess why)',
    'group move': 'units ordered together stop apart, each where it stood from the one nearest the goal (cut to 6 '
                  'radii) on a free spot (Generals AIGroup::groupMoveToPosition; RA3 not read)',
    'column march': '3+ infantry sent 100+ off stop in 3 columns 22 apart, rows 22 back (Generals '
                    'friend_moveInfantryToPos, its ends only; the thresholds 3 / 100 INFERRED; RA3 not read)',
    'death linger': 'a killed unit is gone from areas and counts from the next reading: LINGER 0 (bench 2026-10-28, '
                    'probe death; the Generals source keeps it while it dies, 源码 4.2)',
    'both endings': '未对齐: won and lost in one frame: Generals runs the frame\'s later scripts and takes the last; '
                    'RA3\'s "Mission Won" / "Mission Lost" flags are its own (源码 4.5)',
    'inverted': 'a NOT condition is the plain negation: the compiler reads it off a flag two every-frame scripts '
                'keep (parts.unnot) -- the game ignores the inverted bit of a .map\'s own scripts (bench 2026-10-29, '
                'probe align; retail\'s scripts are compiled into the stream)',
    'frame rate': 'a tick is DT 0.5 s; RA3 runs about 15 script frames a mission second (bench 2026-10-28, probe '
                  'align; Generals 30; a timer runs out ceil(seconds x rate) frames on: 源码 3) -- the timeline is '
                  'good to about half a second',
    'engine model': 'the scripts run in the engine line\'s script engine model (ADR 0019 layer 1: RA3-EngineModel '
                    'ra3model/scripts.py, labpaths.ENGINE_MODEL): 15 frames a mission second, a timer ceil(seconds x '
                    '15) frames counted down before the scripts, counters and timers in one table, ENABLE_SCRIPT arms '
                    'a fired once-script again, a NOT read off the flags parts.unnot writes (as the game runs them); '
                    'units move and fight once a DT tick, on its first frame',
    'difficulty side':'未对齐: a script\'s difficulty bits are taken at the level the run is given; the game takes '
                       'the difficulty of the side the script list belongs to, that side\'s AI\'s if it has one '
                       '(源码 1) -- which side our scripts belong to is to check',
    'border reveal': 'a permanent reveal made before MAP_SWITCH_BORDER covers the new ground too (bench 2026-10-28, '
                     'probe reveal; the Generals source says the two go badly together: 源码 4.4)',
    'ra3 only': '未对齐: actions RA3 has and Generals does not, as we understand them (源码 6): ',
    'superweapon': 'a script\'s superweapon cast (SUPERWEAPON_HITS rows, CURTAIN): fires though the power is not '
                   'charged (bench engine_super p / q), but not again in the reload its own last cast started '
                   '(bench engine_scripts8b pdis; INFERRED rule)',
    'unpack': 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT with a ReplaceSelfSpecialAbility button (an MCV, a Japanese '
              'egg): it drives to the point, 6 frames after it is there the replacement stands there with its name and '
              'health share (bench engine_unpack mcv / egg, engine_build a)',
    'special power': 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT / NAMED_USE_COMMANDBUTTON_ABILITY: logged, no effect '
                     '(a jump, a carrier\'s drop: the device\'s own scripts say what follows)',
    'ai': 'a skirmish AI (UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_*): woken and logged; what it builds and when it '
          'attacks is not simulated (bench 2026-10-27 aistep: it may never build a kind it is let to)',
    'lifetime': 'an object with a LifetimeUpdate (our ice walls, cores, smoke) is killed seconds x 15 frames (cut '
                'down) after the frame it was made, and its CreateObjectDie for that death type makes what it lists '
                'there that frame (bench 2026-11-07 engine_life: a 30 s wall lived 450 frames, a 5.5 s core 82, the '
                'core\'s wall there at once; nothing of the dead lingers in an area). Min and Max apart: their '
                'middle (a guess); retail templates\' lifetimes are not read',
    'freeze': 'the cryo beam (SecondaryDamageNugget, simunits.freeze): its Amount a shot (x RATE_OF_FIRE) adds to '
              'the target\'s cold, DissipateAmount comes off a second (spread over the second), held up to '
              'MaxDamageClampScaler x max health; the highest EffectInfo Fraction x max health reached hangs its '
              'modifier (0.2 .. 0.8: speed and rate of fire 80 .. 20 %), 1.0 freezes: UNDER_FROZEN, stopped and '
              'silent (OnEnterDisable), the ArmorSet of Conditions SECONDARY_DAMAGE (CryoBeamFrozenArmor, Default '
              '90000 %: any hit breaks it), DIE_ON_ENTER kills. INFERRED from the SDK data (the tracker\'s update '
              'not read in the program, not benched): Fraction of max health, only the highest step\'s modifier, '
              'no armour on the Amount, the Iron Curtain keeps it off',
    'modifier': 'attribute modifiers (simunits.effect, Sim.modify / aura_tick) from upgrades held and aura objects '
                'near: SPEED x speed, RANGE x weapon range only, VISION x sight, INVULNERABLE + UNDER_IRON_CURTAIN '
                'no damage, a Duration runs out (bench docs/engine/upgrades.md 1, 2, 4); an aura hangs its modifier '
                'on its filter\'s units within Range for the Duration, IN_STASIS stops, silences, shields (5: the '
                'stasis zone). INFERRED: ARMOR / DAMAGE_MULT / RATE_OF_FIRE x damage (weapons.md, read), '
                'StatusBitsUpgrade, NON_AUTOACQUIRABLE not taken by itself, the aura edge by centre. Not read: '
                'modifiers a ToggleState or a weapon nugget hangs',
    'assemble': 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT to a unit with an AssembleStructureSpecialAbilityUpdate for it '
                '(the ice engineer): he walks till within its StartAbilityRange of the spot, stops, and the structure '
                'is made there the next frame (bench 2026-11-07 engine_life: within range, the core one frame after '
                'the order). A script\'s cast heeds neither the power\'s reload nor its placing rules (bench '
                '2026-11-07 engine_skill: again 8 s into a 20 s reload, 20 from a tank, on a cliff, in the sea -- '
                'all built), it starts the reload anew. The player\'s click (Sim.order_power) is refused while '
                'reloading, off pathable ground, within ForbiddenObjectRange of an object (INFERRED: not measured). '
                'Not modelled: his being busy while it builds',
    'capture': 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED Command_CaptureBuilding: at its side the building changes hands, '
               'a deposit building pays its bonus then its amount each interval (R4, bench 2026-11-07 a4 derrick)',
    'nearest ref':'SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER: the unnamed one nearest the team\'s middle (R2, bench 2026-11-07 engine_ref)',
    'create unnamed': '未对齐: CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT (_WITH_ORIENTATION): the named one\'s maker without a '
                      'name, a new object each run, on the team (RA3 1.13: the same three calls as the named one); '
                      'not benched',
    'nearest ref any': '未对齐:SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER: as the unnamed one\'s (nearest ref), '
                       'named objects too; not read, not benched',
    'team destroyed': '未对齐: TEAM_DESTROYED: no object of the team left, the dying counted (Generals '
                      'evaluateIsDestroyed; not read in RA3, not benched); a team nobody was ever in is not destroyed',
    'production': 'Sim.order_build (simproxy\'s player): BuildTime x 15 frames, paid frame by frame up to '
                  'ceil(cost x progress) (single-float progress), a frame it cannot pay does not go on, the unit out '
                  'DoorOpeningTime (10 frames) after it is full at UnitCreatePoint, walking to NaturalRallyPoint '
                  '(bench 2026-11-05 engine_production a-d); short of power (supply < demand: EnergyProduction of the '
                  'owner\'s living objects) 15 x trunc(BuildTime / f), f 0.3 to 0.5 (engine_production c / d). Not '
                  'modelled: the factory\'s veterancy',
    'power': 'PLAYER_EXCESS_POWER_COMPARE_VALUE: supply - demand of the player\'s living objects (EnergyProduction; '
             'not measured)',
    'attack': 'NAMED_ATTACK_NAMED: the attacker goes to its target; the fight is the script\'s (摧毁)',
    'guard': 'UNIT_GUARD_AREA: goes to the area\'s middle and stays',
    'bridge deck': 'a bridge is walkable deck from its start to its end object (BRIDGE_DECK wide); bench '
                   '2026-10-27 (reroute): a wall on a deck stops nobody',
    'health of the dead': 'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of a dead object: 0 in the frame a script killed it '
                          '(bench 2026-10-28, probe death), else the counter keeps its last value (bench 11-09 '
                          'pend_scripts9 rel; engine_float / engine_spawn / engine_super)',
    'combat': '未对齐: the fight model -- each armed unit fires each weapon (its PRIMARY one a slot) at the nearest '
              'enemy in that weapon\'s range it can hit, damage per second (one clip, then the reload) x the '
              'target\'s armour percent (a type its armour does not name: 100 %); an attack-mover holds while it '
              'fights, a plain move goes on (stopped short of where it was sent, it holds its fire till its next '
              'order: held_up, bench 2026-11-07 a4 demoeng); the range is measured between the two bounding circles (R8, bench '
              '2026-11-07 engine_acquire: a Guardian 150 fires at a tank 180 off, centre to centre); '
              'no veterancy, no splash, no garrisons, no abilities; '
              'health, damage, range, rate, armour from SageXML (simunits.fight); a script\'s 摧毁 / 自动打掉 '
              'overrides it, 不打 turns it off -- to be tuned on the bench at the end. One rule measured: nobody '
              'fires at our ice walls unless ordered to (bench 2026-10-28, a4 hold: four tank busters let out '
              'behind plaza 2\'s ice left the 1500-health wall whole its 30 s; the fight model had it down in 7 s)',
    'acquire': 'an idle unit goes after the nearest enemy within its VisionRange plus the enemy\'s radius, fires, and '
               'walks back to where it stood (bench 2026-11-07 engine_acquire: a Guardian, vision 200, goes at 200 '
               'and 220, not at 240; guarding or attack-moving past at 260 / 400: nothing); the exact limit, and how '
               'near it stops (beyond 11.6 inside its reach at 200), are not read',
    'high ground': '未对齐: the discovery rule is the bench\'s (docs/engine/vision.md): a unit does not discover a '
                   'cell its own ShroudClearingHeight (default 50) or more above the one it stands on, cell by cell, '
                   'no line of sight (aircraft see anyhow); 高地不挡 turns it off. Not aligned: nobody fires at what '
                   'its side does not see, a bombarder that fired in the last FIRE_SEEN s is seen by all (guesses, '
                   'the design line\'s terrain card, docs/design/teardowns/terrain.md 2); a script\'s reveal that '
                   'shuts again (about 9 s by default) and ENEMY_SIGHTED (a range query: true on the high ground '
                   'where NAMED_DISCOVERED is not) are not modelled',
}
# RA3's own actions and conditions (docs/engine/script-semantics.md 6: in neither source): run as we understand them,
# each run that uses one lists it under 'ra3 only'
RA3_ONLY = {'ATTACK_MOVE_NAMED_UNIT_TO', 'ATTACK_MOVE_TEAM_TO', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
            'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', 'UNIT_TELEPORT_TO_WAYPOINT', 'UNIT_GUARD_AREA',
            'UNIT_SET_HEALTH', 'NAMED_SET_MAX_HEALTH', 'UNIT_CHANGE_OBJECT_STATUS',
            'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', 'SET_MISSION_OBJECTIVE_STATUS', 'LINK_MISSION_OBJECTIVE_TO_OBJECT',
            'LINK_MISSION_OBJECTIVE_TO_WAYPOINT', 'CAMPAIGN_CREATE_AUTO_SAVE', 'MOVE_CAMERA_TO_NAMED',
            'PLAYER_SET_PLAYER_POWER_POINTS', 'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'SET_PLAYER_MONEY_TO_COUNTER',
            'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', 'ALLOW_DISALLOW_ONE_BUILDING', 'ALLOW_DISALLOW_ONE_UPGRADE',
            'SKIRMISH_AI_MAKE_BASE', 'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', 'SKIRMISH_AI_TRANSFER_ALL', 'SKIRMISH_AI_USE_REBUILD_SYSTEM',
            'SKIRMISH_AI_USE_REPAIRS', 'UNIT_AI_TRANSFER_ALL', 'PATH_MUSIC_PLAY_EVENT',
            'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM', 'CAMERA_ENTERED_AREA',
            'PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', 'SET_COUNTER_TO_COUNTER', 'COUNTER_MATH_COUNTER'}

# Sim.unmodeled's kinds: what a run met and the simulator does not act on (Sim.gap). The names are simcoverage.py's
# (the level line's static register; it imports sim, so they are spelled here too) plus 状态 (a status bit an upgrade
# sets; a script's bit is a 脚本动作 under its refined name, as simcoverage reports it)
GAP_WEAPON, GAP_UPGRADE, GAP_ACTION, GAP_CONDITION, GAP_COMMAND, GAP_STATUS = \
    '武器', '升级', '脚本动作', '脚本条件', '命令', '状态'
# the object statuses sim.py acts on (tested with `in b.status`; IN_STASIS = IMMOBILE NO_ATTACK UNATTACKABLE in
# Sim.modify); tests/test_sim.py checks the list against the source
ACTED_STATUS = frozenset({'SOLD', 'GENERIC_TOGGLE_STATE', 'IMMOBILE', 'NO_ATTACK', 'UNATTACKABLE', 'NON_AUTOACQUIRABLE', 'IN_STASIS', 'UNDER_FROZEN'})
# a script's power or button by itself, as simcoverage.refined names it
BUTTON_ACTIONS = ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY',
                  'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED')


def refined(name, a):
    """An action's name told apart by what it is told to do where that matters: the status bit, the power, the button
    (simcoverage.refined's spelling: NAME:ARG)."""
    if name == 'UNIT_CHANGE_OBJECT_STATUS' and len(a) > 1:
        return f'{name}:{a[1][2] if isinstance(a[1], tuple) else a[1]}'
    if name in BUTTON_ACTIONS and len(a) > 1:
        return f'{name}:{a[1]}'
    return name


# actions that change nothing the scripts ask about: logged on the timeline (the player sees or hears them)
SHOWN = {'SHOW_MILITARY_CAPTION': '通报', 'CAMPAIGN_CREATE_AUTO_SAVE': '存档', 'PATH_MUSIC_PLAY_EVENT': '音乐',
         'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM': '战况音乐', 'NAMED_FLASH': '闪烁', 'NAMED_SHOW_INFOBOX': '信息框',
         'OBJECT_CREATE_RADAR_EVENT': '小地图闪点', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT': '原版播报',
         'PLAY_SOUND_EFFECT': '配音', 'MOVIE_PLAY_RADAR': '头像'}
# HAS_FINISHED_AUDIO / _VIDEO (work/re/l2_scripts1.md 2.3 / 2.4): the game waits for the clients' end-of-play report,
# not a time; we place it. A dubbed line, x1 as a player hears it (bench 11-04 checks/engine_dialog.py): heard
# AUDIO_LEAD s after the play, done at its length after that (4.34 s line -> 5.3 s). A radar clip (bench movie.py
# play): done its own length after the play (CNVTEST01, 95 frames at 23.976 = 3.96 s: 63 game frames, 4.2 s);
# a full-screen one never reads done. Lengths we cannot read (a retail line, a retail clip) take the guesses below.
AUDIO_LEAD, AUDIO_GUESS, VIDEO_GUESS = 0.9, 2.5, 4.0
SOUND_PLAYS = ('PLAY_SOUND_EFFECT', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT')
# the skirmish AI's script switches, kept per player for simai (work/re l4_aiswitches.md; docs/engine/aiswitches.md)
AI_SWITCHES = ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', 'SKIRMISH_AI_USE_REPAIRS', 'SKIRMISH_AI_USE_REBUILD_SYSTEM')
IGNORED = {'DISPLAY_COUNTER', 'HIDE_COUNTER',
           'CAMERA_LETTERBOX_BEGIN', 'CAMERA_LETTERBOX_END',
           'SET_COOP_AI_COMMAND_UI_ENABLED'}

# ---- the engine line's script engine (ADR 0019 layer 1). Where it is not on this computer (a clean clone) the
# simulator runs its own older loop: every DT tick each script once, timers as seconds, NOT as a plain negation.
SEEN_CORE = {'SET_FLAG', 'SET_MISSION_OBJECTIVE_STATUS', 'DISPLAY_COUNTDOWN_TIMER'}   # the timeline's notes on them
CHANGES = {'INCREMENT_COUNTER', 'DECREMENT_COUNTER', 'SET_MILLISECOND_TIMER', 'SET_RANDOM_MSEC_TIMER'}
_MODEL = {}


def engine_model():
    """RA3-EngineModel's ra3model/scripts.py (labpaths.ENGINE_MODEL, CNV_ENGINE_MODEL overrides it) as a module, or
    None where it is not there. Loaded by file: this adds nothing to sys.path, and the model's code stays in its own
    private repository (ADR 0018)."""
    import labpaths
    path = os.path.join(labpaths.ENGINE_MODEL, 'ra3model', 'scripts.py')
    if path not in _MODEL:
        mod = None
        if os.path.isfile(path):
            name = 'ra3model_scripts'
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod             # dataclasses look their module up while the file runs
            spec.loader.exec_module(mod)
        _MODEL[path] = mod and (mod, _engine_class(mod))
    return _MODEL[path]


def skirmish_setup(map_module, players):
    """The published players the container gives Lib_Skirmish_Setup (model.handed_to_ai: Soviet_1 / 2 / 3 unless the
    map module changes them). Its start-up UNIT_AI_TRANSFER_ALL takes their units off every team after the first
    frame's mission scripts -- the container's SidesList has our list (Player_1's) before theirs (bench 11-09
    engine_scripts9 memb2: a start-up UNIT_SET_TEAM does not survive it): Sim.off_teams. The library's other start-up
    scripts (SKIRMISH_AI_MAKE_BASE ...) are not run: engine line B's simai wakes an AI at the mission's own wake, as
    its bench readings were matched (tests/test_simai); the container's other libraries (Lib_End_Mission ...) neither."""
    from model import handed_to_ai
    return tuple(sorted(p for p in handed_to_ai(map_module) if p in players))


def _engine_class(scripts):
    class SimEngine(scripts.Engine):
        """The model's engine with the simulator as its World, watching the core actions it reports on (a flag's
        scene, caption, ending; an objective; a countdown shown; something changed). A random timer runs to its
        latest, as the beat sheet counts."""
        script = None

        def action(self, name, a, s=None):
            sim, self.script = self.world, s
            if name in SEEN_CORE:
                sim.act(name, list(a), s)
            elif name in CHANGES:
                sim.change()
            if name == 'SET_RANDOM_MSEC_TIMER':
                name, a = 'SET_MILLISECOND_TIMER', (a[0], a[2])
            elif name == 'COUNTER_MATH_COUNTER' and scripts.as_int(a[1]) not in (0, 1):
                sim.used.add(f'COUNTER_MATH_COUNTER code {a[1]}')
            super().action(name, a, s)
    return SimEngine


class Counters(collections.abc.MutableMapping):
    """The engine's one counter / timer table as the simulator's counters: a plain counter's value by name."""

    def __init__(self, eng):
        self.eng = eng

    def __getitem__(self, k):
        c = self.eng.counters[k]
        if c[1]:
            raise KeyError(k)
        return c[0]

    def __setitem__(self, k, v):
        self.eng.counter(k)[0] = v

    def __delitem__(self, k):
        del self.eng.counters[k]

    def __iter__(self):
        return (k for k, c in self.eng.counters.items() if not c[1])

    def __len__(self):
        return sum(1 for _ in self)


class Timers(collections.abc.Mapping):
    """... and as its timers: a running countdown's mission second it runs out at (at or before now once out)."""

    def __init__(self, sim, fps):
        self.sim, self.fps = sim, fps

    def __getitem__(self, k):
        c = self.sim.eng.counters[k]
        if not c[1]:
            raise KeyError(k)
        return self.sim.t + c[0] / self.fps

    def __iter__(self):
        return (k for k, c in self.sim.eng.counters.items() if c[1])

    def __len__(self):
        return sum(1 for _ in self)


@dataclasses.dataclass
class Body:
    """An object in the simulated world."""
    name: str
    template: str
    owner: str
    x: float
    y: float
    speed: float = 0.0
    surface: str = 'ground'
    vision: float = 0.0
    kinds: frozenset = frozenset()
    immortal: bool = False          # body module: health changes cannot take it below 1 HP
    prop: str = None                # PropBody (simunits.prop_body): no health; 'stays' / 'dies' to a script kill
    max_hp: float = 100.0
    hp: float = 100.0
    immune_until: int = -1          # the frame an Iron Curtain's protection ends (weapons and superweapons, not scripts)
    armor: dict = dataclasses.field(default_factory=dict)      # damage type -> percent taken (simunits.fight)
    weapons: list = dataclasses.field(default_factory=list)    # [{range, dps, type, anti}]
    acquire: frozenset = frozenset({'YES'})                     # AutoAcquireEnemiesWhenIdle words (simunits.acquire)
    radius: float = 0.0                                         # R8: Geometry's bounding circle (simunits.radius)
    sight: float = 0.0                                          # R8: its VisionRange alone (vision: with the shroud)
    chase: object = None                                        # R8 idle_chase: the enemy it went after by itself,
    home: tuple = None                                          # where it stood then (it walks back),
    auto_to: tuple = None                                       # and the way's end that rule gave it
    stood_for: tuple = None                                     # the goal it was told and stands short of (send)
    spot: tuple = None                                          # (goal id, goal x, y): sent to a fire_spot for it
    engaged: bool = False                                       # an attack-mover with an enemy in range: holds
    alive: bool = True
    deleted: bool = False
    path: list = dataclasses.field(default_factory=list)       # world points still to go
    goal: object = None                                         # what it is after: a point, or a Body (attack)
    close_since: float = None                                   # an enemy: since when it is within REACH of the
                                                                # player's (自动打掉)
    made_by: str = ''                                           # the script that created it
    made_at: float = 0.0
    scenery: bool = False
    team: str = ''
    instance: int = 0                   # which instance of a team template (CREATE_REINFORCEMENT_TEAM: 1, 2, ...)
    guessed: list = dataclasses.field(default_factory=list)    # what of its numbers simunits only guessed
    clear_height: float = HIGH_STEP                             # its ShroudClearingHeight (simunits: 50 unless written)
    angle: float = 0.0
    dest: object = None                                         # where it was sent (rerouted when the way changes)
    status: set = dataclasses.field(default_factory=set)       # IMMOBILE (stays put), UNATTACKABLE (the player
                                                                # cannot destroy it) ...
    indestructible: bool = False                                # the Indestructible panel flag: takes no damage
    upgrades: set = dataclasses.field(default_factory=set)     # NAMED_RECEIVE_UPGRADE / _REMOVE_UPGRADE (modify)
    up_since: dict = dataclasses.field(default_factory=dict)   # upgrade -> the frame it was given (a Duration runs)
    script_status: set = dataclasses.field(default_factory=set)  # UNIT_CHANGE_OBJECT_STATUS's bits; `status` is these
                                                                # + the modifiers' (modify)
    slots: object = None                                        # simunits.weapon_sets: the weapons chosen by status (None: fixed)
    auras_on: dict = dataclasses.field(default_factory=dict)   # modifier id -> (until frame, xml) an aura hung on it
    shielded: bool = False                                      # INVULNERABLE + Iron Curtain bits on it (simunits.effect)
    taken: float = 1.0                                          # ARMOR factor: damage taken x (INFERRED)
    cold: float = 0.0                                           # the cryo beam's secondary damage held (deal, R freeze)
    cold_step: int = -1                                         # ... the highest EffectInfo reached (-1: none)
    suppression_rule: object = None
    suppression_hits: list = dataclasses.field(default_factory=list)  # (expiry frame, value)
    suppressed_until: int = -1                                  # model condition, NOT an object status
    suppression_next: int = 0
    dealt: float = 1.0                                          # DAMAGE_MULT x RATE_OF_FIRE: damage dealt x (INFERRED)
    base: dict = None                                           # speed, vision, sight, weapons before modifiers
    deposit: tuple = None                                       # R4: its AutoDepositUpdate (bonus, amount, frames)
    deposit_at: int = None                                      # ... the frame of its next deposit
    died_at: float = None                                       # killed or deleted then
    last_hit: str = None                                        # the player whose damage came last (None: a
                                                                # script's NAMED_KILL, or never hit)
    last_by: str = None                                         # the object whose damage came last (E2: the game
                                                                # keeps its id, and "attacked by the player" holds
                                                                # only while that object stands and is the player's);
                                                                # None: no object of ours (a run script's hit)
    mode: str = 'idle'                                          # 'move' (a plain move: fires, does not stop) or
                                                                # 'attack' (attack-move, attack named: stops to fight)
    move_to: tuple = None                                       # where its last plain move sent it (held_up)
    fired_at: float = None                                      # a bombarder's last shot (seen by all a while)
    life_end: int = None                                        # its LifetimeUpdate kills it after this frame's
                                                                # scripts (simunits.lifetime, R1)
    leaves: list = dataclasses.field(default_factory=list)      # what that death makes where it stood
    building: tuple = None                                      # (structure, (x, y), stand): told to build there (R5)
    replace: bool = False                                       # building = its ReplaceSelfSpecialAbility: it turns into it
    unpack_end: int = None                                      # a structure made in the run: unpacking until then
    read_until: int = None                                      # killed by NAMED_DAMAGE in this frame: bits still read
    sell_end: int = None                                        # SELL_OBJECT: the frame the sale deletes it (sell)
    mine: dict = None                                           # a harvester's trip (mine_due): state, node,
                                                                # refinery, due frame, load, paid, leg
    ready_at: dict = dataclasses.field(default_factory=dict)   # special power -> the frame its reload ends (a cast,
                                                                # the script's too, starts it anew: order_power)
    crusher: int = 0                                            # CrusherInfo (simunits.crush): drives over what is
    crushable: object = None                                    # of a lower level; None: cannot be crushed
    lies: float = 0.0                                           # seconds it lies dying once killed (SlowDeath's
                                                                # DestructionDelay), the crush's death only (R9)
    linger: float = 0.0                                         # ... the lie this death has (LINGER, or `lies`)
    topple: object = None                                       # simtopple.rules: prop removal after contact / settling
    toppled: bool = False
    topple_end: int = None
    follow: dict = None                                         # on a waypoint path (order_follow): label, the waypoint
                                                                # it is going to, how; shared by a team that goes as one
    frame_move: bool = False                                    # paths through topple props need frame-sized collision steps
    drive_speed: float = 0.0
    hold_fire: bool = False                                     # UNIT_SET_STANCE 3 (HOLD_FIRE): fires only at a
                                                                # target it was ordered on (stance.md a / b / d / e)

    def damage(self, amount):
        """The body's health floor (Generals reference: internalChangeHealth). A PropBody takes none (engine_propbody a)."""
        if self.prop:
            return
        self.hp = max(1.0 if self.immortal else 0.0, self.hp - amount)

    @property
    def health(self):
        """Health in percent of its maximum (what the scripts read); a PropBody's reads 0 (engine_propbody a)."""
        return 100.0 * self.hp / self.max_hp if self.max_hp and not self.prop else 0.0

    @health.setter
    def health(self, pct):
        self.hp = self.max_hp * float(pct) / 100.0
        if self.immortal:
            self.hp = max(1.0, self.hp)


def same_team(have, asked):
    """A team as a script names it: 'player/team' or the bare team name (the game looks either up: work/re
    l2_scripts1.md 1); a body's team is kept as 'player/team' where the map or the script gave the player."""
    return have == asked or ('/' not in asked and have.split('/', 1)[-1] == asked)


def inside(pts, x, y):
    """Point in polygon (even-odd)."""
    c, n = False, len(pts)
    for k in range(n):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


class Areas(dict):
    """The map's trigger areas by name. A name the map does not have reads as an empty area (nobody is inside it)
    and is noted in `missing`: retail s01's 'Introduction - Delete Planes' names 'AREA - P2 Delete Aircraft',
    which the map does not define, and the game plays on (bench 2026-11-08, retail-q4-q5.md). INFERRED: the
    game's behaviour for an unknown area name is not read from the program, only that it does not stop."""

    def __init__(self, areas):
        super().__init__(areas)
        self.missing = set()

    def __missing__(self, name):
        self.missing.add(name)
        return ()


def _local(s, x, y):
    """A point in a bar's own frame (u along its length, v across)."""
    cx, cy, a = s[0], s[1], s[2]
    dx, dy = x - cx, y - cy
    return dx * math.cos(a) + dy * math.sin(a), -dx * math.sin(a) + dy * math.cos(a)


def _in_shape(s, x, y):
    """Whether a point is within a `Sim.blocks` footprint: (x, y, r) a round, (x, y, angle, length, thick) a bar."""
    if len(s) == 3:
        return (x - s[0]) ** 2 + (y - s[1]) ** 2 <= s[2] ** 2
    u, v = _local(s, x, y)
    return abs(u) <= s[3] / 2 and abs(v) <= s[4] / 2


def _line_hits(s, x0, y0, x1, y1):
    """Whether the segment (x0, y0)-(x1, y1) crosses a `Sim.blocks` footprint."""
    if len(s) == 3:
        cx, cy, r = s
        dx, dy = x1 - x0, y1 - y0
        n = dx * dx + dy * dy
        k = 0.0 if n == 0 else min(max(((cx - x0) * dx + (cy - y0) * dy) / n, 0.0), 1.0)
        return (x0 + k * dx - cx) ** 2 + (y0 + k * dy - cy) ** 2 <= r * r
    (u0, v0), (u1, v1) = _local(s, x0, y0), _local(s, x1, y1)
    lo, hi = 0.0, 1.0                                   # Liang-Barsky clip against |u| <= L/2, |v| <= T/2
    for p0, p1, h in ((u0, u1, s[3] / 2), (v0, v1, s[4] / 2)):
        d = p1 - p0
        if d == 0:
            if abs(p0) > h:
                return False
            continue
        ta, tb = (-h - p0) / d, (h - p0) / d
        lo, hi = max(lo, min(ta, tb)), min(hi, max(ta, tb))
        if lo > hi:
            return False
    return True


def f32(x):
    """x as a single float (the game's production progress, docs/engine/production.md)."""
    return float(np.float32(x))


LOW_POWER = {'penalty': 1.0, 'min': 0.3, 'max': 0.5}   # GameData LowEnergyPenaltyModifier, Min / Max-
                                                        # LowEnergyProductionSpeed (retail; work/re/l2_production.md)


def power_factor(supply, demand, rules=LOW_POWER):
    """A player's low-power speed (RA3 1.13 0x864560; docs/engine/production.md): 1 - (1 - min(1, supply / demand))
    x penalty, at least min, and while short at most max (retail: short of power is 0.3 to 0.5 whatever the
    shortfall); <= 0 -> 0.01. 1.0 with enough power."""
    r = 1.0 if demand == 0 else min(1.0, f32(supply / demand))
    f = 1.0 - (1.0 - r) * rules['penalty']
    f = max(f, rules['min'])
    if r < 1.0:
        f = min(f, rules['max'])
    return f32(f) if f > 0 else f32(0.01)


def mmss(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'


def seconds(s):
    s = str(s).strip()
    if ':' in s:
        m, sec = s.split(':')
        return 60 * float(m) + float(sec)
    return float(s)


class Ground:
    """The map's routing grids (GRID cells): ground (dry, not too steep, bridges over), water, both; paths by
    least cost, cached per surface and goal cell."""

    def __init__(self, mapmod):
        import platmap
        dims = getattr(mapmod, 'DIMS', platmap.CONTAINER)       # a retail map's own size (retail.Terrain)
        w, h, b = dims
        if hasattr(mapmod, 'LAYOUT'):
            e, _ = platmap.heights(mapmod.LAYOUT, w, h, b)
            walk = platmap.walkable(mapmod.LAYOUT, getattr(mapmod, 'OBJECTS', []), dims, e)
            bridge = walk & ~platmap.walkable(mapmod.LAYOUT, [], dims, e)    # walkable only for a bridge laid on it
        else:
            e = mapmod.ground().e
            import newmap
            walk = (e > getattr(mapmod, 'WATERLINE', newmap.WATERLINE) + 10) & (platmap.slope_of(e) <= platmap.STEEP)
            if hasattr(mapmod, 'impassable'):                   # a probe's field-0 cells (maps/probe_block.py)
                walk &= ~mapmod.impassable()
            bridge = np.zeros_like(walk)
        import newmap
        waterline = getattr(mapmod, 'WATERLINE', newmap.WATERLINE)
        water = e < waterline - 5
        d = int(GRID // platmap.CELL)
        hh, ww = h // d, w // d
        fold = lambda a: a[:hh * d, :ww * d].reshape(hh, d, ww, d)            # noqa: E731
        self.b, self.d = b, d
        self.e = e                                                          # ground height (CELL cells)
        self.zgrid = e[:hh * d:d, :ww * d:d]                                # the same at each GRID cell's corner
        self.grids ={'ground': fold(walk).all(axis=(1, 3)), 'water': fold(water).all(axis=(1, 3))}
        # the shore's shallows (between the water's edge and 'dry'): platmap.apply blocks only steep ground, so an
        # amphibian goes ashore through them; left out they cut every slip (a5, 2026-11-04)
        shallow = (e >= waterline - 5) & (e <= waterline + 10) & (platmap.slope_of(e) <= platmap.STEEP)
        # R7: an amphibian does not take a bridge -- its deck is up over the water, it swims under (bench 2026-11-07
        # engine_land: the A4 transport went straight at the quay, 89 frames to the shore area, where the simulator
        # had it drive out of the water onto the southern bridge's deck and round, 346)
        land = walk & ~bridge
        self.grids['both'] = (fold(land).all(axis=(1, 3)) | self.grids['water'] |
                              fold(land | water | shallow).all(axis=(1, 3)))
        self.cache = {}
        self.blocked = np.zeros(self.grids['ground'].shape, bool)
        self.version = 0
        # a bridge's deck: what stands on it blocks nobody (bench 2026-10-27, reroute: the warriors walked through an
        # ice wall on the deck)
        self.deck = np.zeros_like(self.blocked)
        objs = list(getattr(mapmod, 'OBJECTS', []))
        jj, ii = np.mgrid[0:self.blocked.shape[0], 0:self.blocked.shape[1]]
        self.xy = self.world((jj, ii))
        for o, q in zip(objs, objs[1:]):
            if getattr(o, 'flags', None) == platmap.BRIDGE_START and getattr(q, 'flags', None) == platmap.BRIDGE_END:
                self.deck |= self.strip((o.x, o.y), (q.x, q.y), platmap.BRIDGE_DECK, 0.0)

    def strip(self, p, q, width, over):
        """Cells within width / 2 of segment p-q, the segment `over` longer at both ends."""
        x, y = self.xy
        dx, dy = q[0] - p[0], q[1] - p[1]
        n = max(math.hypot(dx, dy), 1e-6)
        ux, uy = dx / n, dy / n
        u = (x - p[0]) * ux + (y - p[1]) * uy
        v = -(x - p[0]) * uy + (y - p[1]) * ux
        return (u >= -over) & (u <= n + over) & (abs(v) <= width / 2)

    def set_blocks(self, shapes):
        """What stands in the way now: [(x, y, angle, length, thick) a bar, or (x, y, r) a round building]; off a
        bridge's deck. Routes are worked out anew."""
        x, y = self.xy
        m = np.zeros_like(self.blocked)
        for s in shapes:
            if len(s) == 3:
                m |= (x - s[0]) ** 2 + (y - s[1]) ** 2 <= s[2] ** 2
            else:
                cx, cy, a, length, thick = s
                u = (x - cx) * math.cos(a) + (y - cy) * math.sin(a)
                v = -(x - cx) * math.sin(a) + (y - cy) * math.cos(a)
                m |= (abs(u) <= length / 2) & (abs(v) <= thick / 2)
        m &= ~self.deck
        if (m != self.blocked).any():
            self.blocked, self.version, self.cache = m, self.version + 1, {}
            return True
        return False

    def open(self, surface, x, y):
        """A world point a unit of that surface may stand on now (its routing cell walkable and not blocked)."""
        if surface == 'air':
            return True
        c, g = self.cell(x, y), self.grids[surface]
        return 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and bool(g[c]) and not self.blocked[c]

    def cell(self, x, y):
        import platmap
        return (int(round((y / platmap.CELL + self.b) / self.d)), int(round((x / platmap.CELL + self.b) / self.d)))

    def z(self, x, y):
        """The ground's height at a world point (the nearest CELL)."""
        import platmap
        j = min(max(int(round(y / platmap.CELL + self.b)), 0), self.e.shape[0] - 1)
        i = min(max(int(round(x / platmap.CELL + self.b)), 0), self.e.shape[1] - 1)
        return float(self.e[j, i])

    def world(self, c):
        import platmap
        return ((c[1] * self.d - self.b) * platmap.CELL, (c[0] * self.d - self.b) * platmap.CELL)


    def snap(self, g, c):
        if 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]:
            return c
        jj, ii = np.nonzero(g[max(0, c[0] - 15):c[0] + 16, max(0, c[1] - 15):c[1] + 16])
        if not len(jj):
            return None
        k = int(np.argmin((jj + max(0, c[0] - 15) - c[0]) ** 2 + (ii + max(0, c[1] - 15) - c[1]) ** 2))
        return (int(jj[k] + max(0, c[0] - 15)), int(ii[k] + max(0, c[1] - 15)))

    def route(self, surface, p, q, closest=False):
        """World points from p to q (None: no way); aircraft fly straight. closest: no way to q -- the way to the
        nearest point it can reach instead (a unit's move, R7; the static checks ask for q itself)."""
        if surface == 'air':
            return [q]
        got = self.way(surface, p, q, False)
        if got is None and surface == 'both':
            # R7: an amphibian on dry land may take a bridge from its end (the 'both' grid has no decks: from the
            # water nothing climbs onto one); one starting on land and not reaching q by water goes by land
            c, g = self.cell(*p), self.grids['ground'] & ~self.blocked
            if 0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]:
                got = self.way('ground', p, q, False)
        if got is None and closest:
            got = self.way(surface, p, q, True)
        return got

    def way(self, surface, p, q, closest):
        from skimage import graph
        g = self.grids[surface] & ~self.blocked
        a, z = self.snap(g, self.cell(*p)), self.snap(g, self.cell(*q))
        if a is None or z is None:
            return None
        key = (surface, z)
        if key not in self.cache:
            m = graph.MCP_Geometric(np.where(g, 1.0, np.inf))
            cost, _ = m.find_costs([z])
            self.cache[key] = (m, cost)
        m, cost = self.cache[key]
        if not np.isfinite(cost[a]):
            return self.closest(g, a, z) if closest else None
        cells = m.traceback(a)[::-1]                # traceback runs from the goal (the costs' source) to a
        pts = [self.world(c) for c in self.pull(g, cells)]
        if pts and math.hypot(pts[-1][0] - q[0], pts[-1][1] - q[1]) <= GRID:
            pts.pop()                               # the goal's own cell: q itself ends the way
        return pts + [q]

    def pull(self, g, cells):
        """Generals' Path::optimize (AIPathfind.cpp 474; work/re/generals-source-map.md): from each anchor the way
        goes straight to the farthest cell it can see over walkable cells, the cells between left out; the cells
        after the start, `cells[0]`. Without it a way ran on the grid's rows: a goal moved 30 aside (HOLD_SPOTS) put
        the unit on the next row from early on and kept it there the whole way, where the game goes in one slant
        line (a4's trucks 2 and 3 on the halt area's edges, 2026-11-09). Generals' extra cases (a diagonal
        neighbour, a straight run along a row or a 45 degree line taken as passable) need no rule here: the next cell
        is always kept."""
        out, a, n = [], 0, len(cells)
        while a < n - 1:
            j = a + 1
            while j + 1 < n and self.clear(g, cells[a], cells[j + 1]):
                j += 1
            out.append(cells[j])
            a = j
        return out

    @staticmethod
    def clear(g, c0, c1):
        """Every grid cell the straight line between the centres of cells c0 and c1 passes (sampled every quarter
        cell) walkable in g."""
        k = 4 * max(abs(c1[0] - c0[0]), abs(c1[1] - c0[1])) + 1
        jj = np.rint(np.linspace(c0[0], c1[0], k)).astype(int)
        ii = np.rint(np.linspace(c0[1], c1[1], k)).astype(int)
        return bool(g[jj, ii].all())

    def closest(self, g, a, z):
        """R7: the goal out of reach -- the way to the cell it can reach nearest the goal (bench 2026-11-07
        engine_land: the A4 transport sent to the quay's top went straight to its foot and stayed; the Generals
        pathfinder's closest path; bench 2026-11-08 engine_seal move: a peacekeeper walled in, sent 600 out, walked
        to the wall's inside nearest the goal and stood). [] when that is where it stands: it stays (not stuck)."""
        from skimage import graph
        m = graph.MCP_Geometric(np.where(g, 1.0, np.inf))
        cost, _ = m.find_costs([a])
        jj, ii = np.nonzero(np.isfinite(cost))
        k = int(np.argmin((jj - z[0]) ** 2 + (ii - z[1]) ** 2))
        end = (int(jj[k]), int(ii[k]))
        if end == tuple(a):
            return []
        return [self.world(c) for c in self.pull(g, m.traceback(end))] or [self.world(end)]

    def within(self, surface, p, q, reach):
        """R3: an attacker's way -- to the cell it reaches soonest from which q is within `reach` (Generals' attack
        path: the way to a spot in range, not to the target; bench 2026-11-07 a4 smash: the Ghost King at the ice wall
        12 s after landing, not round the wall to its far side). [] when p is in range already, None when no cell is."""
        import platmap
        if math.hypot(q[0] - p[0], q[1] - p[1]) <= reach:
            return []
        if surface == 'air':
            return [q]
        from skimage import graph
        g = self.grids[surface] & ~self.blocked
        a = self.snap(g, self.cell(*p))
        if a is None:
            return None
        m = graph.MCP_Geometric(np.where(g, 1.0, np.inf))
        cost, _ = m.find_costs([a])
        jj, ii = np.nonzero(np.isfinite(cost))
        x = (ii * self.d - self.b) * platmap.CELL
        y = (jj * self.d - self.b) * platmap.CELL
        ok = np.hypot(x - q[0], y - q[1]) <= reach
        if not ok.any():
            return None
        k = int(np.flatnonzero(ok)[np.argmin(cost[jj[ok], ii[ok]])])
        end = (int(jj[k]), int(ii[k]))
        return [self.world(c) for c in self.pull(g, m.traceback(end))] or [self.world(end)]


class Sim:
    shot_clock = False                  # opt-in frame clock: discrete shots and movement between script frames;
                                        # default movement retains its benched coarse tick (work/re/handoff-c.md)

    def __init__(self, mission, test=None, level='normal', script='', model=True):
        """model: run the scripts in the engine line's model where it is on this computer (False: the older loop)."""
        self.m = mission
        self.retail = getattr(mission, 'RETAIL', False)      # a retail campaign map (retail.py): its own scripts
        self.mm = mission.merged(test) if self.retail else parts.merged(mission, test)
        self.test = test
        self.level = LEVELS[level]
        self.t = 0.0
        self.log = []                       # (t, kind, text)
        self.box_log = []                   # [start, end, text]: the caption box holds one line; a new one ends the one up
        self.panel_log = []                 # groups of (t, text): the dialogue panel stacks subtitles, a group clears together
        self.asked, self.up = {}, []        # a 功能 caption asked for (flag -> t), and shown: (flag, asked, shown)
        self.scenes = []                    # [start, end] of each 过场 (end None while it runs)
        self.used = set()                   # ALIGN keys the run leaned on
        self.unknown = {}                   # condition / action names the simulator does not know: count
        self.unmodeled = {}                 # (kind, name) -> {'n', 't' first met, 'what'}: Sim.gap
        self.declared = {}                  # template -> the weapons its XML names (simunits.declared_weapons), asked once
        self.flags, self.counters, self.timers = {}, {}, {}
        self.objectives = {}                # name -> status (0 hidden, 1 shown, 2 done, 3 failed)
        self.markers = {}                   # objective -> {object / waypoint}
        self.done, self.disabled = set(), set()
        self.banned = set()                 # (player, template in lower case): ALLOW_DISALLOW_ONE_BUILDING 0
        self.banned_ups = set()             # (player, upgrade in lower case): ALLOW_DISALLOW_ONE_UPGRADE 0
        self.border = 0
        self.reveal_all = False             # the player's MAP_REVEAL_ALL
        self.revealed_to = set()            # other players given MAP_REVEAL_ALL (side_sees: they see everything)
        self.reveals = {}                   # name -> (x, y, r)
        self.peeks = []                     # (x, y, r, until frame): MAP_REVEAL_AT_WAYPOINT, back to fog at `until`
        self.reshroud = 10.0                # MAP_SHROUD_SET_RESHROUD_TIME seconds (retail default holds as 10)
        self.camera = None
        self.input = True
        self.countdowns = set()
        self.ending = None
        self.both = None                    # won and lost in one frame: (first, second)
        self.ra3_only = set()               # RA3-only action / condition names the run used
        self.last_change = 0.0
        self.ai = {}                        # player -> woken at
        self.handed = ()                    # skirmish_setup: players taken off their teams after the first frame
        self.ai_switches = {}               # player -> {AI_SWITCHES name: value} (simai.Brain reads them)
        self.audio_end = {}                 # sound event -> when HAS_FINISHED_AUDIO holds again (Sim.played)
        self.video_end = {}                 # clip -> when HAS_FINISHED_VIDEO holds (None: never, a full-screen one)
        self.money = {}
        self.nodes = {}                     # ore node name -> {'free': frame it takes a miner from, 'gathered', 'at'}
        self.mined_to = None                # the last frame mine_due ran
        self.relations = dict(getattr(mission, 'relations', {}))   # (a, b) -> Enemy / Neutral / Friend
        self.team_team_rel, self.team_player_rel, self.player_team_rel = {}, {}, {}   # the overrides (hostile)
        self.team_targets = {}                  # id(body) -> the team it was told to attack (TEAM_ATTACK_TEAM)
        self.players = dict(mission.map.PLAYERS)
        self.human = self.players['p1']
        self.foe = self.players.get('s1')
        import simtech
        sides = getattr(mission, 'sides', {}) if self.retail else {}
        self.books = {}                     # player -> simtech.Book: protocols, protocol points (a playable faction's)
        for p in dict.fromkeys(self.players.values()):
            f = simtech.faction_of(p, sides.get(p))
            if f:
                self.books[p] = simtech.Book(f, simunits.LIFE_FPS,    # its personality's PowerChoice lottery
                                             (sides.get(p) or {}).get('aiPersonality'))
        self.tech_to = 0                    # the last frame tech_due ran
        self.tech_read = False              # a script has read the points or the protocols (pending: a rank to come)
        self.ground = Ground(mission.map)
        self.own = {u.id: u.xml for u in self.mm.units}
        self.garrison = simgarrison.Garrisons(self)    # GarrisonContain / ContestableGarrisonContain
        self.bodies = {}                    # name -> Body (named ones), plus unnamed under '#k'
        self.topples = []                   # ToppleUpdate objects; neutral props can be knocked over too
        self.frame_movers = {}              # bodies whose current path crosses a topple object's footprint
        self.refs = {}                      # reference name (UNITRef - ...) -> the Body a SET_REF_TO_... pointed it at
        self.object_lists = {}              # OBJECTLIST_ADDOBJECTTYPE: list name -> {template}, both lower case
        self.base_power = {}                # PLAYER_SET_BASE_POWER: player -> supply added to its objects' (INFERRED)
        self.powers_off = {}                # PLAYER_SPECIAL_POWER_AVAILABILITY: (player, power lower) -> its word
                                            # (one table for every player, names any case: retail.SCOPED_ARGS)
        self.series = []                    # (t, counter values) for a check's counters
        self.threat = []                    # (t, enemies near, countdowns) every 10 s
        self.first_threat = None
        self.known = None                   # cells ever seen (GRID)
        self.known_at = []                  # (t, km2 known)
        self.guessed = set()
        self.walls = {u.id: u.params for u in self.mm.units if 'length' in u.params}   # our bars of ice, gates
        self.due = []                       # (frame, structure, owner, team, x, y, by): a builder's, to put down (R5)
        self.blasts = []                    # (frame, x, y, [(distance, damage)], owner, by): a superweapon's hits
        self.casts = []                     # (frame, owner, power, caster, (x, y) or None): PLAYER_TRIGGERED_SPECIAL_POWER
        self.queues = {}                    # factory name -> [job]: production (order_build, produce_due)
        self.produced_to = None             # the last frame produce_due ran
        self.energies = {}                  # template -> EnergyProduction (simunits.energy; power)
        self.player_ups = {}                # player -> upgrades GIVE_PLAYER_UPGRADE gave (a unit's NeededUpgrade)
        self.templates = getattr(self.mm, 'templates', None) or {}     # team templates (Sim.reinforce)
        self.instances = {}                 # team template -> instances made so far
        teams = getattr(mission.map, 'TEAMS', {})
        self.active = set(teams.values())               # teams with an instance: a whole-team order to any other is lost (E3)
        self.lost_orders = []                           # (t, script, order, team) given to a team nobody had joined
        for k, o in enumerate(list(getattr(mission.map, 'OBJECTS', [])) + self.mm.objects):
            b = self.add(o.name or f'#{k}', o.template, self.owner_of(o.side), o.x, o.y)
            b.team = teams.get(o.side, '')
            health = (getattr(o, 'props', None) or {}).get('objectInitialHealth')
            if isinstance(health, (int, float)) and 0 < health < 100:     # the map's starting health, in percent
                b.hp = b.max_hp * health / 100.0                            # (a7 win: the carrier placed at 1 %)
            crew = (getattr(o, 'props', None) or {}).get('originalOwner')
            if isinstance(crew, str):                   # placed in a team of the mission's own (K6): that team has a member
                b.team = crew
                self.active.add(crew)
            b.angle = facing(o)                         # as the built map puts it (the player's north, others' south)
        import platprops
        for k, o in enumerate(getattr(mission.map, 'SCENERY', [])):
            if o.template in platprops.STRUCTURE:
                b = self.add(f'#scenery {k}', o.template, CIV, o.x, o.y)
                b.scenery = True
                b.kinds = frozenset(b.kinds | {'STRUCTURE'})
        self.script = parse_script(script)
        self.auto_kill = next((e[2] for e in self.script if e[1] == '自动打掉'), None)
        self.combat = not any(e[1] == '不打' for e in self.script)
        self.high = not any(e[1] == '高地不挡' for e in self.script)
        # what nobody shoots unless ordered: our ice walls (units with a lifetime; bench 2026-10-28, a4 hold)
        self.unshot = {u.id for u in self.mm.units if 'lifetime' in (getattr(u, 'params', None) or {})}
        self.seen = {}                      # this tick: (side, id(body)) -> whether that side sees it
        self.firing = []                    # this tick's aimed fire: (target, damage per second, shooter) (fight, deal)
        self.first_death = None             # (t, body, killer): the fight's first death
        self.death_blasts = []              # (frame, x, y, damage, type, radius, affects, owner, by): FireWeaponWhenDead
        self.sweeps = simsweep.Sweeps(self)  # ActivateLinearDamageNugget + LinearDamageUpdate: the lines walking
        self.events = sorted((e for e in self.script if isinstance(e[0], float)), key=lambda e: e[0])
        self.anchored = [e for e in self.script if isinstance(e[0], tuple)]       # (('@', flag, delta), verb, ...)
        self.areas = Areas(self.mm.areas)
        self.waypoints = self.mm.waypoints
        self.reblock()
        self.eng = None
        got = engine_model() if model else None
        if got:
            # the scripts as the game runs them: the compiler's NOT flags (package.py writes unnot's), the inverted
            # bit ignored; one list, the run's difficulty; this Sim is the engine's World (condition / action)
            mod, cls = got
            self.fps = mod.FPS
            lists = mission.script_lists(mod) if self.retail else mod.from_cnv(parts.unnot(self.mm.scripts))
            if not self.retail:
                self.handed = skirmish_setup(mission.map, set(self.players.values()))
            # a retail map's own scripts keep their inverted bit (the engine model: honored for retail's compiled
            # scripts; a02's 'NOT units in the convention center' completed objective 1 at 0:04 with it ignored)
            self.eng = cls(lists, world=self, difficulty=self.level, honor_inverted=self.retail)
            self.flags, self.counters, self.timers = self.eng.flags, Counters(self.eng), Timers(self, mod.FPS)
            if any(c and c[-1] == parts.NOT for s in self.mm.scripts for c in s.when):
                self.used.add('inverted')

    def blocks(self, b):
        """What of the way a body takes up: a wall of ours its bar (or disc, square), a building its round."""
        if b.topple:
            return None                    # engine_topple: vehicles drive straight through, infantry can pass too
        if b.template in self.walls:
            p = self.walls[b.template]
            if p.get('shape') == 'disc':
                return (b.x, b.y, p['length'] / 2)
            return (b.x, b.y, b.angle, p['length'], p['length'] if p.get('shape') == 'square' else p['thick'])
        if 'STRUCTURE' in b.kinds and 'bridge' not in b.template.lower():
            import platprops
            return (b.x, b.y, platprops.radius(b.template) if b.template in platprops.CATALOG else 40.0)
        return None

    def reblock(self):
        """The way as it stands now, for the orders given from now on: whoever is on the move keeps the way it was
        given and goes through what came up since (docs/engine/pathing.md 6, bench 2026-11-04 engine_block wall: the
        IFV ordered a second before its row of bunkers was made drove straight through it, s4, not round by the gap).
        A new order goes round a building made in the run, infantry's as a vehicle's (bench 2026-11-08 engine_block
        foot: the IFV and a peacekeeper ordered 3 s after the row was made both went round by the gap, s13 / s22)."""
        self.ground.set_blocks([s for s in (self.blocks(b) for b in self.living()) if s])

    # ---- the world
    def owner_of(self, side):
        return self.players.get(side, CIV)

    def add(self, name, template, owner, x, y, by='', at=0.0):
        st = simunits.stats(template, self.own)
        b = Body(name, template, owner, float(x), float(y), st['speed'], st['surface'],
                 max(st['vision'] or 0.0, st['shroud'] or 0.0), frozenset(st['kinds']), made_by=by, made_at=at)
        b.guessed = st['guessed']
        b.clear_height = st['clear_height']
        b.radius = st.get('radius') or 0.0
        b.sight = st['vision'] or 0.0
        f = simunits.fight(template, self.own)
        b.immortal, immortal_hp = simunits.immortal_body(template, self.own)
        b.suppression_rule = simunits.suppression(template, self.own)
        hp = immortal_hp if b.immortal else (f['hp'] or simunits.max_health(template, self.own))
        if hp:
            b.max_hp = b.hp = hp
        else:                                   # no health in the data: a building's or a unit's usual (a guess)
            b.max_hp = b.hp = 2000.0 if 'STRUCTURE' in b.kinds else 300.0
        b.armor, b.weapons = f['armor'], f['weapons']
        if template not in self.__dict__.setdefault('_wsets', {}):
            self._wsets[template] = simunits.weapon_sets(template, self.own)
        b.slots = self._wsets[template] if b.weapons else None    # guns not read at all stay a gap (below)
        if b.slots:                           # the weapon lines name a status: the held one is chosen from it
            b.weapons = simunits.pick_weapons(b.slots, b.status)
        b.crusher, b.crushable = simunits.crush(template, self.own)
        b.lies = simunits.slow_death(template, self.own)
        b.linger = LINGER
        b.prop = simunits.prop_body(template, self.own)
        import simtopple
        b.topple = simtopple.rules(template, self.own)
        if b.topple:
            a, c, _, _ = simtopple.shape(template, self.own)
            b.radius = math.hypot(a, c)
            b.vision = b.sight = 0.0         # a prop has no sight (stats' unit-only table otherwise guesses 100)
            self.topples.append(b)
        if not b.weapons:                     # its XML names guns and none was read: a gap, not a unit without guns
            if template not in self.declared:
                self.declared[template] = simunits.declared_weapons(template, self.own)
            if self.declared[template]:
                self.gap(GAP_WEAPON, template, f'XML 有 {", ".join(self.declared[template])}，读成没有武器')
        b.acquire =frozenset(simunits.acquire(template, self.own)) if b.weapons else frozenset()
        frames, b.leaves = simunits.lifetime(template, self.own)
        if frames is not None:                  # made in this frame's scripts (or, by a run event, at its start)
            made = self.eng.frame if getattr(self, 'eng', None) else int(round(at * simunits.LIFE_FPS))
            b.life_end = made + frames
        unpack = simunits.unpack_frames(template, self.own) if by and 'STRUCTURE' in b.kinds else 0
        if unpack:                              # made in the run (a map's own skip it): unpacks first -- adds no power
            v = np.float32(power_factor(*self.power(owner)))       # and does not fire meanwhile; RA3 1.13 0x720100:
            extra = np.float32(np.float32(1.0) - v) * np.float32(unpack)   # trunc((1 - v) F + F), v the owner's
            b.unpack_end = self.frame_now() + int(np.float32(extra + np.float32(unpack)))   # factor then
        b.deposit = simunits.deposit(template, self.own)
        if b.deposit:                           # Generals: the first deposit an interval after it is made
            b.deposit_at = (self.eng.frame if getattr(self, 'eng', None) else int(round(at * simunits.LIFE_FPS))) \
                + b.deposit[2]
        self.bodies[name] = b
        return b

    def expire(self, frame):
        """R1: whatever's lifetime is up by `frame` dies (killed, as the game's LifetimeUpdate: NAMED_DESTROYED, gone
        from areas at once -- bench 2026-11-07 engine_life, no body lingers) and leaves what its death makes, made
        that frame (the ice core's wall)."""
        for b in self.living():
            if b.topple_end is not None and frame >= b.topple_end:
                self.destroy(b, '倒伏后消失', delete=True)     # PropBody never exposes NAMED_DYING, even for one frame
                continue
            if b.sell_end is not None and frame >= b.sell_end:
                self.destroy(b, '卖掉了', delete=True)          # StructureSellUpdate: deleted, no death, no ruin
                continue
            if b.life_end is None or frame < b.life_end:
                continue
            self.used.add('lifetime')
            self.destroy(b, '寿命到了')
            for tmpl in b.leaves:
                n = self.add(f'#left {len(self.bodies)} of {b.name}', tmpl, b.owner, b.x, b.y, by=b.name, at=self.t)
                n.team, n.angle = b.team, b.angle
                self.note('留下', f'{tmpl}（{self.label(b)} 寿命到了）')
                if self.blocks(n):
                    self.reblock()

    def living(self):
        return [b for b in self.bodies.values() if b.alive]

    # ---- orders: one unit's, and a team's (the same for each member: ctx.order gives teams only)
    def members(self, team):
        """A team's living members; a team template's (several instances: CREATE_REINFORCEMENT_TEAM) the OLDEST
        instance's that still has any (bench 11-10 engine_reinf old: the order by the name moved the first instance,
        not the one made since; an emptied instance giving the name to the next is INFERRED)."""
        crew = [b for b in self.living() if same_team(b.team, team)]
        first = min((b.instance for b in crew), default=0)
        return [b for b in crew if b.instance == first]

    def reinforce(self, team, waypoint, script):
        """CREATE_REINFORCEMENT_TEAM(team, waypoint): a new instance of the team template (mission.templates:
        {'Owner/name': {'units': [(template, min, max)], 'instances': n}}), every line's MAX count of its template, at
        the waypoint -- made again on every call, teamMaxInstances or not (bench 11-10 engine_reinf two: 3 A + 2 B of
        a min 2 / max 3, min 1 / max 2 template, a second call 6 / 4 with teamMaxInstances 1). The units stand on a
        grid of SPREAD round the waypoint (INFERRED: the bench counts them inside 250 of it)."""
        key = next((k for k in self.templates if same_team(k, team)), None)
        p = self.point(waypoint)
        if key is None or p is None:
            self.used.add('reinforcement team unknown' if key is None else 'reinforcement waypoint unknown')
            return
        owner = key.split('/')[0]
        self.instances[key] = k = self.instances.get(key, 0) + 1
        made = [t for t, _, hi in self.templates[key]['units'] for _ in range(hi)]
        side = math.ceil(math.sqrt(len(made)))
        for i, t in enumerate(made):
            dx, dy = (i % side - (side - 1) / 2) * SPREAD, (i // side - (side - 1) / 2) * SPREAD
            b = self.add(f'#reinforcement {len(self.bodies)} {t}', t, owner, p[0] + dx, p[1] + dy, by=script.name,
                         at=self.t)
            b.team, b.instance = key, k
            if self.blocks(b):
                self.reblock()
        self.active.add(key)
        self.note('出现', f'增援 {key.split("/", 1)[-1]} 第 {k} 队（{len(made)} 个，{self.who(owner)}）在 {waypoint}')
        self.change()

    def off_teams(self, players):
        """UNIT_AI_TRANSFER_ALL(p, 1): p's units now are taken off every team (its default one too); units made later
        join theirs as ever (bench 11-09 engine_scripts9 memb3: teamSoviet_1 counts 0 while its placed dummy lives;
        memb11 / memb12: with Lib_Skirmish_Setup the crews go empty, without it they die)."""
        for b in self.living():
            if b.owner in players:
                b.team = ''

    def team_active(self, team):
        return any(same_team(t, team) for t in self.active)

    def books_of(self, player):
        """The protocol books a script's player names (the game's player mask: work/re l2_scripts1.md 1); a player
        without one (civilian, neutral) or a name that is no player: none."""
        names = list(self.books) if player == '<All Players>' else \
            [self.human] if player in ('<All Human Players>', '<1st Human Player>') else [player]
        return [self.books[n] for n in names if n in self.books]

    def tech_due(self, frame):
        """Rank experience frame by frame up to `frame` (simtech.Book.frame); the player's rank goes on the timeline
        where the scripts deal in protocols."""
        for f in range(self.tech_to + 1, frame + 1):
            for p, book in self.books.items():
                n = len(book.log)
                book.frame(f)
                if p != self.human:
                    book.ai_buy(f)
                if p == self.human and 'protocols' in self.used:
                    for _, what in book.log[n:]:
                        self.note('协议', f'玩家：{what}')
        self.tech_to = max(self.tech_to, frame)

    def order_move(self, b, where, attacking, given=(), skip=()):
        """A plain move (attacking: an attack-move). The spot is adjusted first (free_spot: Generals'
        AIInternalMoveToState::onEnter adjusts every move's goal off the spots other units hold); `given` are spots
        already handed out to a group being ordered, `skip` that group (its members' old goals are dropped first)."""
        if b:
            b.flee = None                       # INFERRED: any move order takes the run over, as STOP does
            b.follow = None                     # ... and a waypoint path (order_follow sets it again after its legs)
            b.mode = 'attack' if attacking else 'move'
            p = self.point(where) if isinstance(where, str) else where
            if p is not None and b.alive and b.speed > 0:
                spot = self.free_spot(b, p, self.claims(b, skip) + list(given))
                where = where if spot == p else spot
            self.send(b, where)
            b.move_to = b.dest if not attacking else None

    def claims(self, b, skip=()):
        """The spots other mobile ground units hold (x, y, radius): where they are going, or where they stand (the
        pathfinder's goal cells, Pathfinder::updateGoal); none for aircraft in the air or for `skip`; none unless
        HOLD_SPOTS. Benched 11-09: the rule is the game's (a01, two infantry sent alone to one point stood ~22 apart),
        and the game's a4 gets all trucks to the 80-wide halt area (checks/a4.py hold PASS). The simulator's trucks
        2 and 3, their goals moved 30 aside, ran on grid rows 40 off the road's middle the whole way, on the halt
        area's edges, and drove past it: its ways were not pulled straight (Ground.pull since; now 2854,2479 and
        2794,2521 at the halt at s315, like the switch off). On since bench 11-09 checks/engine_spots.py: three
        trucks on teams of their own sent to one point (at once, or 20 s apart) end one on it, two 10-80 off (the
        simulator 0 / 50 / 44.7). With it the a4 proxy's army stands apart, beats the second wave at x~1950 (off: all
        three trucks shot there at s232-240, lost at s248), the convoy halts alive, and the run goes to the clock:
        the proxy has no base-vehicle deploy, builds nothing and never takes 北营's command post (the level line's
        to-do, docs/story/handoff-phase4.md). j7 / a3's compiled plays ended 0.5-3.6 s off their own scripts
        (j7 126.9 vs 130.5): the script's 派 went straight to `send`, past this; it is order_move now, as its compiled
        ATTACK_MOVE_NAMED_UNIT_TO (test_playcheck). The script's 走 is a group move (order_group) but compiles to one
        MOVE_NAMED_UNIT_TO per unit -- no play has 走 for several units yet."""
        if b.surface == 'air' or not HOLD_SPOTS:
            return []
        return [tuple(o.dest if o.path and o.dest else (o.x, o.y)) + (o.radius,) for o in self.living()
                if o is not b and o not in skip and o.speed > 0 and o.surface != 'air' and not o.scenery]

    def order_group(self, bodies, where, attacking):
        """A move order to several units at once (a team's MOVE_TEAM_TO, a selection's click): Generals'
        AIGroup::groupMoveToPosition without a formation (GL/AI/AIGroup.cpp; work/re/generals-source-map.md). The unit
        nearest the goal is the centre and walks to the point; the others, nearest first, each to the point plus where
        it stands from that centre, the offset cut to 6 times its radius (computeIndividualDestination), then moved
        off spots already held (free_spot). Bench 2026-11-08 acceptance question 1 (a01's squad, 4 Peacekeepers + 2
        dogs): the squad's middle ~18-23 short of the point, the units apart -- the simulator had all six on the point.
        INFERRED for RA3 (its group move not read, docs/engine/pathing.md 5: the script's MOVE_TEAM_TO hands the team
        to one group command): Generals' column march for a big, far group (friend_moveInfantryToPos) and the line
        check from the group's goal to the spot are left out."""
        movers = [b for b in bodies if b and b.alive and b.speed > 0 and 'IMMOBILE' not in b.status]
        p = self.point(where) if isinstance(where, str) else where
        if len(movers) < 2 or p is None:
            for b in bodies:
                self.order_move(b, where, attacking)
            return
        self.used.add('group move')
        movers.sort(key=lambda b: (b.x - p[0]) ** 2 + (b.y - p[1]) ** 2)
        given = []                                  # (x, y, radius) spots handed out to the group so far
        foot = [b for b in movers if 'INFANTRY' in b.kinds]
        if len(foot) >= 3 and math.hypot(movers[0].x - p[0], movers[0].y - p[1]) >= 100:
            self.used.add('column march')
            self.column_ends(foot, p, attacking, given, movers)
            movers = [b for b in movers if b not in foot]
        if not movers:
            return
        cx, cy = movers[0].x, movers[0].y
        for b in movers:
            vx, vy = b.x - cx, b.y - cy
            n = math.hypot(vx, vy)
            cap = 6 * b.radius
            if n > cap:
                vx, vy = vx * cap / n, vy * cap / n
            self.order_move(b, (p[0] + vx, p[1] + vy), attacking, given, movers)
            given.append(tuple(b.dest or (b.x, b.y)) + (b.radius,))

    def column_ends(self, foot, p, attacking, given, skip):
        """Generals' infantry column march (AIGroup::friend_moveInfantryToPos), its ends only: 3 columns (5 from 16
        men) across the way in, COLUMN_GAP apart, filled by where the men stand across it; in each column the front man
        at the point's row, the next COLUMN_GAP behind. Bench 2026-11-09 (testbench/retail_q1_spots.py, a01's squad):
        3 columns x 2 rows, ~44-50 across and ~48 back, no side step on the second row -- Generals' 2.2 cells and its
        every-other-one cell aside read as RA3 with 20-unit cells and no side step. The way in is taken straight from
        the man nearest the group's middle (Generals: the last leg of one wide ground path); the column's own way
        there and the conditions' constants (AIData MinDistanceForGroup, here 100; MinInfantryForGroup, here 3) are
        INFERRED. Bench 2026-11-08 question 1: the squad's middle ~18-23 short of the point."""
        mx, my = sum(b.x for b in foot) / len(foot), sum(b.y for b in foot) / len(foot)
        mid = min(foot, key=lambda b: (b.x - mx) ** 2 + (b.y - my) ** 2)
        ex, ey = p[0] - mid.x, p[1] - mid.y
        n = math.hypot(ex, ey) or 1.0
        ex, ey = ex / n, ey / n
        nx, ny = -ey, ex
        cols = 5 if len(foot) >= 16 else 3
        across = sorted(foot, key=lambda b: -((b.x - mid.x) * nx + (b.y - mid.y) * ny))
        size = max(len(foot) // cols if cols == 5 else (len(foot) + 1) // 3, 1)
        column = {id(b): min(k // size, cols - 1) - cols // 2 for k, b in enumerate(across)}
        rows = collections.Counter()
        for b in sorted(foot, key=lambda b: -((b.x - mid.x) * ex + (b.y - mid.y) * ey)):    # front first
            c = column[id(b)]
            r = rows[c]
            rows[c] += 1
            side = COLUMN_GAP * c
            want = (p[0] + side * nx - r * COLUMN_GAP * ex, p[1] + side * ny - r * COLUMN_GAP * ey)
            self.order_move(b, want, attacking, given, skip)
            given.append(tuple(b.dest or (b.x, b.y)) + (b.radius,))

    def free_spot(self, b, want, held):
        """Pathfinder::adjustDestination over 10-unit cells: `want` or the first spot of the spiral round it (400
        tries) on ground b may stand on and clear of the spots `held` (centres at least the two radii apart);
        aircraft in the air take `want` as it is. None found, or `want` off its ground (the way finder's closest
        point decides, R7): `want`."""
        if b.surface == 'air' or not held:
            return want
        step = 10.0

        def ok(x, y):
            return self.ground.open(b.surface, x, y) and \
                all(math.hypot(x - gx, y - gy) >= max(b.radius + gr, 1.0) for gx, gy, gr in held)
        if ok(*want) or not self.ground.open(b.surface, *want):
            return want
        i = j = 0
        delta, left = 1, 400
        while left > 0:
            for di, dj, k in ((1, 0, delta), (0, 1, delta), (-1, 0, delta + 1), (0, -1, delta + 1)):
                for _ in range(k):
                    i, j, left = i + di, j + dj, left - 1
                    x, y = want[0] + i * step, want[1] + j * step
                    if ok(x, y):
                        return (x, y)
            delta += 2
        return want

    def held_up(self, b):
        """A plain move whose way ended short of where it was sent (blocked: a wall across the street) is still on
        that move: it neither fires nor goes after anyone until its next order. Bench 2026-11-07 `a4 demoeng`: the
        opening demo's pair, sent to the engineer's clear mark and stopped by the ice ~157 from him (centre to centre,
        in the simulator), never shot him in the 2 s before their turn order; the simulator, counting them idle once
        stopped, had him dead at 61.7 s. INFERRED (RA3's AI move state not read); not told apart on the bench: that
        they stop farther off than the simulator's wall lets them (out of reach)."""
        return b.mode == 'move' and not b.path and b.goal is None and b.move_to is not None and \
            b.dest == b.move_to and math.hypot(b.dest[0] - b.x, b.dest[1] - b.y) > ARRIVE

    def order_attack(self, b, target_name):
        self.used.add('attack')
        target = self.body(target_name)
        if b and target and target.alive and b.alive and b.goal is not target:
            b.goal, b.mode, b.follow = target, 'attack', None
            self.send(b, (target.x, target.y), reach=self.reach(b, target))

    def order_capture(self, b, target_name):
        """R4: NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED with Command_CaptureBuilding: the engineer goes to the
        building; at its side it takes it (capture_due)."""
        self.used.add('capture')
        target = self.body(target_name)
        if b and b.alive and target and target.alive:
            b.goal, b.mode = target, 'capture'
            self.send(b, (target.x, target.y))

    def capture_due(self):
        """R4: an engineer at the side of the building it was told to take (within the building's round + CAPTURE_REACH,
        or stopped as near as the way lets it within twice that): the building is his player's from then, the
        engineer gone into it (a guess: RA3's engineer is used up), a deposit building pays its bonus now and its next
        deposit an interval on (Generals' AutoDepositUpdate.awardInitialCaptureBonus). Bench 2026-11-07 a4 derrick:
        the derrick the player's at the first reading after the order (s4), 500, then 15 every 2 s (s7 515 -> s46 800)."""
        for b in self.living():
            g = b.goal
            if b.mode != 'capture' or not isinstance(g, Body):
                continue
            if not g.alive:
                b.goal, b.mode, b.path = None, 'move', []
                continue
            shape = self.blocks(g)
            r = (shape[2] if shape and len(shape) == 3 else 40.0) + CAPTURE_REACH
            d = math.hypot(g.x - b.x, g.y - b.y)
            if d > r and (b.path or d > 2 * r):
                continue
            g.owner = b.owner
            self.note('占领', f'{self.label(b)} 占下 {self.label(g)}，归 {self.who(b.owner)}')
            if g.deposit:
                self.money[b.owner] = self.money.get(b.owner, 0) + g.deposit[0]
                g.deposit_at = self.frame_now() + g.deposit[2]
            self.destroy(b, '进楼占领', delete=True)
            self.change()

    def deposit_due(self, frame):
        """R4: the deposit buildings a player (not the neutral side) holds pay `amount` each `frames` (Generals'
        AutoDepositUpdate.update: the clock runs for the neutral too, it just pays nobody)."""
        for b in self.living():
            if b.deposit and b.deposit_at is not None and frame >= b.deposit_at:
                b.deposit_at = frame + b.deposit[2]
                if b.owner != CIV and b.deposit[1] > 0:
                    self.money[b.owner] = self.money.get(b.owner, 0) + b.deposit[1]

    # ---- mining: HOOKS 7 (simai: after the opening the AI lives on its miners' income)
    def mine_due(self, frame):
        """Every player's harvester (KindOf HARVESTER, not the neutral side's) up to `frame`, a frame at a time, the
        collector's loop of docs/engine/mining.md: locate a node -> drive -> dock (the node loads it MINE_DOCK frames,
        from the frame after it docked, once the node waits for a miner) -> the nearest unpacked refinery of its
        owner's -> drive -> unload MINE_DOCK frames into the owner's money, load // MINE_DOCK a frame and the rest on the
        last -> again. The node: its last one first (sticky), else the nearest (INFERRED: 'the first one found', the
        search order not read). A miner coming to a node where another is docked waits there for good (the retail node
        has no queue place: bench engine_mining b / e); one coming while the node plays its MINE_REST frames docks and
        waits for it. A refinery unloads one miner at a time, the next waiting (INFERRED: its queue places not read).
        A leg is straight distance at the miner's speed + MINE_DRIVE_EXTRA (fitted, no path finding); the miner is
        drawn along it. A harvester given a path (a script's move) drops its trip and starts over once it stands."""
        start = frame if self.mined_to is None else self.mined_to + 1
        self.mined_to = frame
        miners = [b for b in self.living() if 'HARVESTER' in b.kinds and b.owner != CIV and b.speed > 0]
        if not miners:
            return
        nodes = [b for b in self.living() if 'orenode' in b.template.lower()]
        for fr in range(start, frame + 1):
            for b in miners:
                if b.alive:
                    self._mine(b, fr, nodes)

    def _leg(self, b, fr, to, state):
        """Off to `to`: there MINE_DRIVE_EXTRA + distance / speed frames on, in `state` meanwhile."""
        d = math.hypot(to[0] - b.x, to[1] - b.y)
        frames = int(round(d / b.speed * simunits.LIFE_FPS)) + MINE_DRIVE_EXTRA
        b.mine.update(state=state, due=fr + frames, leg=((b.x, b.y), to, fr, fr + frames))

    def _mine(self, b, fr, nodes):
        """One frame of a harvester's trip (mine_due)."""
        m = b.mine
        if b.path:                                  # moved by someone else: start over once it stands
            if m is not None:
                self._undock(b)
                b.mine = None
            return
        if m is None:
            m = b.mine = {'state': 'locate', 'node': None, 'ref': None, 'due': fr, 'load': 0, 'n': 0, 'leg': None}
        if m['leg']:                                # drawn along its drive
            (x0, y0), (x1, y1), f0, f1 = m['leg']
            k = min(1.0, (fr - f0) / max(1, f1 - f0))
            b.x, b.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        if fr < m['due']:
            return
        st = m['state']
        if st == 'locate':
            node = self.bodies.get(m['node']) if m['node'] else None
            if node is None or not node.alive:
                node = min(nodes, key=lambda n: math.hypot(n.x - b.x, n.y - b.y), default=None)
            if node is None:
                m['due'] = fr + MINE_RETRY
                return
            m['node'] = node.name
            self._leg(b, fr, (node.x, node.y), 'to node')
        elif st == 'to node':
            m['leg'] = None
            n = self.nodes.setdefault(m['node'], {'free': 0, 'gathered': 0, 'at': None})
            if n['at'] is not None and n['at'] != b.name and self._docked(n['at'], m['node']):
                m['state'], m['due'] = 'stuck', 10 ** 9     # no queue place: it never gets in
                return
            n['at'] = b.name
            m['state'], m['due'] = 'docked', max(fr + 1, n['free'])
        elif st == 'docked':                        # the node's first loading frame
            n = self.nodes[m['node']]
            m['load'] = MINE_LOAD if n['gathered'] < MINE_FULL else MINE_EMPTY
            if n['gathered'] < MINE_FULL:
                n['gathered'] += MINE_LOAD
            m['state'], m['due'] = 'loading', fr + MINE_DOCK - 1
        elif st == 'loading':                       # full on its last loading frame: off the frame after (the trip
            n = self.nodes[m['node']]               # 2 x 104 + 61 = 269 of engine_mining a)
            n['at'], n['free'] = None, fr + MINE_REST + 1
            m['state'], m['due'] = 'find refinery', fr + 1
        elif st == 'find refinery':
            now = self.frame_now()
            refs = [r for r in self.living() if r.owner == b.owner and 'REFINERY' in r.kinds
                    and not (r.unpack_end is not None and now < r.unpack_end)]
            r = min(refs, key=lambda r: math.hypot(r.x - b.x, r.y - b.y), default=None)
            if r is None:
                m['due'] = fr + MINE_RETRY
                return
            m['ref'] = r.name
            self._leg(b, fr, (r.x, r.y), 'to refinery')
        elif st == 'to refinery':
            m['leg'] = None
            r = self.bodies.get(m['ref'])
            if r is None or not r.alive:
                m['state'] = 'find refinery'
                return
            busy = next((o for o in self.living() if o is not b and o.mine and o.mine['state'] == 'unloading'
                         and o.mine['ref'] == r.name), None)
            if busy is not None:                    # one at a time: wait for it to finish
                m['due'] = busy.mine['due'] + MINE_DOCK - busy.mine['n']
                return
            m['state'], m['n'] = 'unloading', 0
            self._mine(b, fr, nodes)
        elif st == 'unloading':                     # money on the arrival frame and the next MINE_DOCK - 1
            r = self.bodies.get(m['ref'])
            if r is None or not r.alive:
                m['state'] = 'find refinery'
                return
            m['n'] += 1
            step = m['load'] // MINE_DOCK
            give = step if m['n'] < MINE_DOCK else m['load'] - step * (MINE_DOCK - 1)
            self.money[b.owner] = self.money.get(b.owner, 0) + give
            m['due'] = fr + 1
            if m['n'] >= MINE_DOCK:
                m['state'] = 'locate'

    def _docked(self, miner, node):
        """Whether `miner` stands docked at (or is being loaded by) `node`."""
        o = self.bodies.get(miner)
        return o is not None and o.alive and o.mine is not None and o.mine['node'] == node \
            and o.mine['state'] in ('docked', 'loading')

    def _undock(self, b):
        n = self.nodes.get(b.mine['node']) if b.mine and b.mine['node'] else None
        if n and n['at'] == b.name:
            n['at'] = None

    # ---- production: the second hook for simproxy's player (docs/engine/production.md, bench 2026-11-05)
    def factories(self, owner):
        """The owner's living structures that build units (their CommandSet has UNIT_BUILD buttons)."""
        return [b for b in self.living() if b.owner == owner and 'STRUCTURE' in b.kinds and not b.scenery
                and simunits.menu(b.template, self.own)]

    def holds_upgrade(self, owner, up, factory=None):
        """Whether `factory` (else any of owner's structures) has the upgrade a unit's NeededUpgrade asks for. A PLAYER
        upgrade: owner holds it (GIVE_PLAYER_UPGRADE). An OBJECT upgrade (the tiers): a factory with a
        TechUpgradeReceiver for it (the Allied ones) has it while a yard / outpost of owner's holding it stands within
        the radius (600, RECTANGULAR: |dx| and |dy| both, an inference); one without (Japan's) holds it itself
        (bench 2026-11-07 engine_tech: GIVE_PLAYER_UPGRADE Tech2 builds no Guardian, the yard's Tech2 lets a factory
        300 off build and not one 750 off, the factory's own Tech2 builds nothing, with or without the yard's)."""
        low = up.lower()
        if simunits.upgrade_type(up) != 'OBJECT':
            return low in {u.lower() for u in self.player_ups.get(owner, ())}
        fs = [factory] if factory is not None else \
            [b for b in self.living() if b.owner == owner and 'STRUCTURE' in b.kinds and not b.scenery]
        return any(self._tier_held(owner, f, low) for f in fs)

    def _tier_held(self, owner, f, low):
        recv = [r for r in simunits.tech_receivers(f.template, self.own) if low in r[0]]
        if not recv:
            return low in {u.lower() for u in f.upgrades}
        for _, radius, rect, sources in recv:
            for b in self.living():
                if b.owner == owner and b.template.lower() in sources and low in {u.lower() for u in b.upgrades}:
                    dx, dy = abs(b.x - f.x), abs(b.y - f.y)
                    if (max(dx, dy) if rect else math.hypot(dx, dy)) <= radius:
                        return True
        return False

    def can_build(self, owner, template, factory=None, ban=True):
        """Whether owner's sidebar button for `template` is lit (at `factory`, else at any of owner's that builds it):
        not banned (ALLOW_DISALLOW_ONE_BUILDING; ban=False: the ban not asked), every RequiredObject standing, every
        NeededUpgrade held there (holds_upgrade; all of them is an inference)."""
        if ban and (owner, template.lower()) in self.banned:
            return False
        objs, ups = simunits.needs(template, self.own)
        have = {b.template.lower() for b in self.living() if b.owner == owner}
        if not all(o.lower() in have for o in objs):
            return False
        if not ups:
            return True
        fs = [factory] if factory is not None else \
            [f for f in self.factories(owner) if template in simunits.menu(f.template, self.own, f.upgrades)] or [None]
        return any(all(self.holds_upgrade(owner, u, f) for u in ups) for f in fs)

    def upgrade_sellers(self, owner, up):
        """The owner's living structures whose buttons buy `up` now: not banned (ALLOW_DISALLOW_ONE_UPGRADE 0), its
        GameDependency met (RequiredObject owned; NeededUpgrade held by the structure: inference), not held yet
        (OBJECT: by that structure; PLAYER: by the owner), not in any of the owner's queues already."""
        low = up.lower()
        if (owner, low) in self.banned_ups or ('<All Players>', low) in self.banned_ups:
            return []
        objs, ups = simunits.upgrade_needs(up)
        have = {b.template.lower() for b in self.living() if b.owner == owner}
        if not all(o.lower() in have for o in objs):
            return []
        queued = any(j.get('upgrade', '').lower() == low for q in self.queues.values() for j in q
                     if j['owner'] == owner)
        out = []
        for b in self.living():
            if b.owner != owner or 'STRUCTURE' not in b.kinds or b.scenery or queued:
                continue
            for u, kind in simunits.upgrade_menu(b.template, self.own, b.upgrades):
                if u.lower() == low and all(n in b.upgrades for n in ups) and not (
                        u in b.upgrades if kind == 'OBJECT' else u in self.player_ups.get(owner, ())):
                    out.append(b)
        return out

    def offers(self, owner):
        """[(template or upgrade, cost, seconds)] owner can build or buy now, each once: the factories' units in their
        sidebar order, then the upgrades its structures' buttons buy (Upgrade_AlliedTech2 at the yard)."""
        out = {}
        for f in self.factories(owner):
            for t in simunits.menu(f.template, self.own, f.upgrades):
                if t not in out and self.can_build(owner, t, f):
                    out[t] = (t,) + simunits.production(t, self.own)
        for b in self.living():
            if b.owner == owner and 'STRUCTURE' in b.kinds and not b.scenery:
                for u, _ in simunits.upgrade_menu(b.template, self.own, b.upgrades):
                    if u not in out and self.upgrade_sellers(owner, u):
                        out[u] = (u,) + simunits.upgrade_cost(u)
        return list(out.values())

    def order_build(self, owner, template, factory=None, press=False):
        """Queue `template` at the owner's factory that builds it with the shortest queue (`factory`: that one only, a
        Body -- a script's press of its build button, which bench 2026-11-08 engine_production e measured the same
        as the player's click: paid as it builds, 160 frames to the engineer) -- or an upgrade at the structure
        whose button buys it; nothing is paid now (produce_due pays frame by frame, an upgrade as a unit).
        press: a script's press, queued even while the unit is banned (ALLOW_DISALLOW_ONE_BUILDING 0) -- it waits
        unbuilt until let go (bench 2026-11-09 engine_production g); the player's click is not (the button is locked).
        False: nothing of the owner's builds / buys it now."""
        sellers = self.upgrade_sellers(owner, template)
        if sellers:
            b = min(sellers, key=lambda b: len(self.queues.get(b.name, [])))
            cost, secs = simunits.upgrade_cost(template)
            kind = dict(simunits.upgrade_menu(b.template, self.own, b.upgrades))[template]
            self.queues.setdefault(b.name, []).append(
                {'template': template, 'upgrade': template, 'kind': kind, 'owner': owner, 'cost': cost,
                 'secs': secs, 'progress': 0.0, 'paid': 0, 'full': None})
            self.used.add('production')
            self.note('生产', f'{self.who(owner)} 在 {self.label(b)} 买 {template}（{cost}，{secs:g} 秒）')
            return True
        fs = [f for f in self.factories(owner) if template in simunits.menu(f.template, self.own, f.upgrades)
              and self.can_build(owner, template, f, ban=not press) and (factory is None or f is factory)]
        if not fs:
            return False
        f = min(fs, key=lambda f: len(self.queues.get(f.name, [])))
        cost, secs = simunits.production(template, self.own)
        self.queues.setdefault(f.name, []).append(
            {'template': template, 'owner': owner, 'cost': cost, 'secs': secs, 'progress': 0.0, 'paid': 0,
             'full': None})
        self.used.add('production')
        self.note('生产', f'{self.who(owner)} 在 {self.label(f)} 排 {template}（{cost}，{secs:g} 秒）')
        return True

    def produce_due(self, frame):
        """Each factory's queue up to `frame`, a frame at a time: the first job not yet full goes on 100 / frames
        (single float, so a 150-frame build fills at the 151st), paying up to ceil(cost x progress / 100) -- a frame
        the owner cannot pay the difference stands still; the next job starts the frame after one fills; a full one
        comes out DoorOpeningTime later at the factory's UnitCreatePoint (turned with it), on the factory's team,
        and walks to its NaturalRallyPoint (bench 2026-11-05 engine_production a-d: 150 / 151 frames, 54 paid at
        the 16th, a 250 budget stalls at 3 left, out 10 frames after full). A banned unit's job
        (ALLOW_DISALLOW_ONE_BUILDING 0) stands, keeps what it paid and goes on when let go -- not cancelled, not
        refunded (bench 2026-11-09 engine_production g). A factory gone takes its queue along."""
        start = frame if self.produced_to is None else self.produced_to + 1
        self.produced_to = frame
        if not self.queues:
            return
        for fr in range(start, frame + 1):
            for name in list(self.queues):
                f, q = self.bodies.get(name), self.queues[name]
                if f is None or not f.alive or not q:
                    del self.queues[name]
                    continue
                create, rally, door = simunits.exit_of(f.template, self.own)
                for job in [j for j in q if j['full'] is not None and fr >= j['full'] + (0 if 'upgrade' in j else door)]:
                    q.remove(job)
                    if 'upgrade' in job:
                        self.upgrade_done(f, job)
                    else:
                        self.produce_out(f, job, create, rally)
                job = next((j for j in q if j['full'] is None), None)
                if job is None or 'upgrade' not in job and (job['owner'], job['template'].lower()) in self.banned:
                    continue                # banned: the first job stands, paid so far kept, the queue behind it too
                step = f32(100.0 / self.build_frames(job['secs'], job['owner']))
                nxt = f32(job['progress'] + step)
                owe = min(job['cost'], math.ceil(round(job['cost'] * nxt / 100.0, 9))) - job['paid']
                have = self.money.get(job['owner'], 0)
                if owe > have:
                    continue
                self.money[job['owner']] = have - owe
                job['paid'] += owe
                job['progress'] = nxt
                if nxt >= 100.0:
                    job['full'] = fr

    def upgrade_done(self, b, job):
        """A bought upgrade arrives: OBJECT on the structure that bought it, PLAYER on its owner."""
        up = job['upgrade']
        if job['kind'] == 'OBJECT':
            self.give_upgrade(b, up)
        else:
            self.player_ups.setdefault(job['owner'], set()).add(up)
        self.note('生产', f'{self.who(job["owner"])} 的 {self.label(b)} 买好 {up}')
        self.change()

    def give_upgrade(self, b, up):
        """An object upgrade on b (bought, or NAMED_RECEIVE_UPGRADE): a SPEED modifier acts on a unit."""
        self._upgrade(b, up, True)

    def _upgrade(self, b, up, on):
        (b.upgrades.add if on else b.upgrades.discard)(up)
        if on:
            b.up_since[up] = self.frame_now()
        else:
            b.up_since.pop(up, None)
        self.modify(b)

    def xml_of(self, template):
        """The template's XML (a mission's own, else retail; '' where none), kept."""
        cache = self.__dict__.setdefault('_xmls', {})
        if template not in cache:
            try:
                cache[template] = simunits._xml(template, self.own) or ''
            except (OSError, ValueError):
                cache[template] = ''
        return cache[template]

    def modify(self, b):
        """Sets b's acting values from the attribute modifiers on it (simunits.effect): the upgrades it holds (an
        AttributeModifierUpgrade's modifier, until its Duration runs out from the giving: bench upgrades.md 4; a
        StatusBitsUpgrade's bits) and what auras hung on it (aura_tick, each until its frame). SPEED x the speed,
        RANGE x the weapons' range only, VISION x vision and sight (upgrades.md 1, 2); the status = the script's bits
        + the modifiers', IN_STASIS meaning IMMOBILE NO_ATTACK UNATTACKABLE (INFERRED: the measured stasis modifier
        sets them all); shielded, ARMOR (taken), DAMAGE_MULT x RATE_OF_FIRE (dealt)."""
        now = self.frame_now()
        xml = self.xml_of(b.template)
        mods = []
        if b.suppression_rule and now < b.suppressed_until:
            mods.append(simunits.modifier(xml, b.suppression_rule['modifier']))
        for up, mid in simunits.upgrade_mods(xml, b.upgrades):
            m = simunits.modifier(xml, mid)
            if m and (m['frames'] is None or now < b.up_since.get(up, now) + m['frames']):
                mods.append(m)
        for mid, (until, src) in list(b.auras_on.items()):
            if now >= until:
                del b.auras_on[mid]
            else:
                mods.append(simunits.modifier(src, mid))
        step = self.cold_of(b)[0]['steps'][b.cold_step] if b.cold_step >= 0 else None
        if step and step[1]:
            mods.append(simunits.modifier(xml, step[1]))
        on, off = simunits.status_bits(xml, b.upgrades)
        e = simunits.effect(mods, on | b.script_status, off)
        if not mods and not on and not off and b.base is None:
            b.status = set(b.script_status)
            if b.slots:
                b.weapons = simunits.pick_weapons(b.slots, b.status)
            return
        if b.base is None:
            b.base = {'speed': b.speed, 'vision': b.vision, 'sight': b.sight, 'weapons': b.weapons, 'armor': b.armor}
        st = e['status']
        if 'IN_STASIS' in st:
            st = st | {'IMMOBILE', 'NO_ATTACK', 'UNATTACKABLE'}
        if 'UNDER_FROZEN' in st or (step and step[2]):          # frozen (OnEnterDisable): stopped and silent
            st = st | {'IMMOBILE', 'NO_ATTACK'}
        b.armor = self.cold_of(b)[1] if step and step[3] and self.cold_of(b)[1] else b.base['armor']
        b.status = st
        # Suppression SPEED75%:50->37.5 (bench44->59); retain fractional speed.
        b.speed = b.base['speed'] * e['SPEED']
        b.vision, b.sight = b.base['vision'] * e['VISION'], b.base['sight'] * e['VISION']
        held = simunits.pick_weapons(b.slots, st) if b.slots else b.base['weapons']       # the status picks the guns
        b.weapons = held if e['RANGE'] == 1.0 else [dict(w, range=w['range'] * e['RANGE']) for w in held]
        b.shielded = e['shielded']
        # Suppression ARMOR75%: EXPLOSIVE40 on150HP reads80%; UNRESISTABLE bypasses it.
        b.taken, b.dealt = e['ARMOR'], e['DAMAGE_MULT'] * e['RATE_OF_FIRE']
        if mods or on:
            self.used.add('modifier')
        for m in mods:
            for ty in sorted(set(m['types']) - simunits.ACTING_TYPES) if m else ():
                self.gap(GAP_UPGRADE, m['id'], f'修正类型 {ty} 没模拟')
        for bit in sorted(e['status'] - b.script_status - ACTED_STATUS - ({'UNDER_IRON_CURTAIN'} if b.shielded else set())):
            self.gap(GAP_STATUS, bit, f'{b.template} 身上的修正 / 升级给的，只记下来')

    def relation(self, a, b):
        """ENEMIES / NEUTRAL / ALLIES: how owner b stands to owner a (an aura's ObjectFilter Relationship)."""
        if self.enemy(a, b):
            return 'ENEMIES'
        if a != b and CIV in (a, b):
            return 'NEUTRAL'
        return 'ALLIES'

    def aura_tick(self):
        """Once a tick before the fight: every living aura object (simunits.auras, active, holding the bits it needs)
        hangs its modifier on what its filter takes within Range, centre to centre, once every RefreshDelay (the first
        at once), until then + the modifier's Duration (none: the refresh); then every body with a modifier is re-set
        (modify). Bench upgrades.md 5 / 5.1 (engine_stasis_edge / _leave): the edge is the unit's centre (a Guardian
        at 190 from a 200 zone held, at 205 not, though its box is 20 x 12); a unit out of the zone keeps it Duration
        after the last refresh (hold 2 s: 26 frames after the teleport); a hold shorter than the refresh flickers
        (refresh 1 s, hold 0.2 s: on 22 of 150 frames) -- a 0.5 s tick shows that only as on at a refresh tick."""
        now = self.frame_now()
        live = self.living()
        cache = self.__dict__.setdefault('_auras', {})
        for e in live:
            if e.template not in cache:
                cache[e.template] = simunits.auras(self.xml_of(e.template))
            for a in cache[e.template]:
                if not a['active'] or not a['needs'] <= e.status:
                    continue
                m = simunits.modifier(self.xml_of(e.template), a['mod'])
                if m is None:
                    continue
                beat = self.__dict__.setdefault('_aura_beat', {})
                k = (e.name, a['mod'])
                if k in beat and now - beat[k] < a['refresh']:
                    continue
                beat[k] = now if k not in beat else beat[k] + (now - beat[k]) // a['refresh'] * a['refresh']
                until = now + (m['frames'] or a['refresh'])
                for t in live:
                    if t is e and not a['self']:
                        continue
                    if t.scenery or (a['include'] and not a['include'] & t.kinds) or a['exclude'] & t.kinds:
                        continue
                    if self.relation(e.owner, t.owner) not in a['relation']:
                        continue
                    if math.hypot(t.x - e.x, t.y - e.y) <= a['range']:
                        t.auras_on[a['mod']] = (until, self.xml_of(e.template))
        for b in live:
            if b.auras_on or b.base is not None:
                self.modify(b)

    def power(self, owner):
        """(supply, demand) of the owner: its living objects' EnergyProduction, > 0 summed into the supply, < 0 into
        the demand (RA3 1.13 0x7424a0 leaves out an object under construction or powered down: the simulator has
        neither -- a building stands built from the frame it appears)."""
        sup, dem = self.base_power.get(owner, 0), 0
        now = self.frame_now()
        for b in self.living():
            if b.owner == owner and not (b.unpack_end is not None and now < b.unpack_end):
                e = self.energies.get(b.template)
                if e is None:
                    e = self.energies[b.template] = simunits.energy(b.template, self.own)
                sup, dem = (sup + e, dem) if e > 0 else (sup, dem - e)
        return sup, dem

    def short_of_power(self, owner):
        sup, dem = self.power(owner)
        return sup < dem

    def unpowered(self, b):
        """Holds its fire: still unpacking, or POWERED while its owner is short of power (bench 2026-11-07
        engine_powerdef: a Tesla coil of a player with supply 0 < 75 never fires; the plant deleted, it stops within a
        shot's interval; a plant made by script unpacks 255 frames short of power, the coil's next kill 70 frames
        after that)."""
        if b.unpack_end is not None and self.frame_now() < b.unpack_end:
            return True
        return 'POWERED' in b.kinds and self.short_of_power(b.owner)

    def build_frames(self, secs, owner):
        """A unit's build frames, worked out again every frame (RA3 1.13 0x71ddc0): BuildTime x 15 with enough power;
        short of it 15 x trunc(BuildTime / power_factor) -- the division and its truncation on the seconds (bench
        2026-11-05 engine_production c: supply 0, f 0.3, 10 s -> 495 frames; d: 50 / 75, f 0.5 -> 300)."""
        f = power_factor(*self.power(owner))
        if f >= 1.0:
            return max(1, int(round(secs * simunits.LIFE_FPS)))
        return max(1, math.trunc(secs / f) * simunits.LIFE_FPS)

    def produce_out(self, f, job, create, rally):
        c, s = math.cos(f.angle), math.sin(f.angle)

        def at(p):
            return f.x + p[0] * c - p[1] * s, f.y + p[0] * s + p[1] * c
        b = self.add(f'#made {len(self.bodies)} {job["template"]}', job['template'], job['owner'], *at(create),
                     by=f.name, at=self.t)
        b.team, b.angle = f.team, f.angle
        self.note('生产', f'{self.label(f)} 出 {job["template"]}')
        if rally is not None:
            b.mode = 'move'
            self.send(b, at(rally))
        self.change()

    def order_guard(self, b, area):
        self.used.add('guard')
        if b:
            b.follow = None
        if b and not inside(self.areas[area], b.x, b.y):
            self.send(b, area)

    def power_refusal(self, b, power, x, y):
        """Why the player's click of `power` on (x, y) for unit b would be refused, None if it goes (order_power). A
        script's cast (engine_skill a-c, w) skips all of this. The click, bench 2026-11-07 engine_skill d (clicked by
        hand, the ice engineer): its reload not over (ready_at: refused 8 s after his cast, went 21 s after); PATHABLE_ONLY
        and the spot not ground he can walk (a point in the sea and one on the cliff refused); within ForbiddenObjectRange
        (32) of the edge of an object that does not move (an ore node, box 33 x 41, refused 75 from its centre and not
        123: its bounding circle 53 + 32 lies between) -- a unit does not count (our own tank 20 / 40 / 60 from the spot,
        inside its 23 radius, the core came all the same; a click right on the tank's centre took nothing, left out);
        MaxCastRange with LIMIT_DISTANCE and the spot farther from him (not measured)."""
        rules = simunits.power_rules(b.template, power, self.own)
        if rules is None:
            return 'not a power of his'
        if b.ready_at.get(power, 0) > self.frame_now():
            return 'reloading'
        if any(self.powers_off.get((p, power.lower()), 'Available') != 'Available' for p in (b.owner, '<All Players>')):
            return 'disabled'                   # PLAYER_SPECIAL_POWER_AVAILABILITY (INFERRED)
        if 'PATHABLE_ONLY' in rules['flags']:
            g, c = self.ground.grids.get(b.surface, self.ground.grids['ground']), self.ground.cell(x, y)
            if not (0 <= c[0] < g.shape[0] and 0 <= c[1] < g.shape[1] and g[c]):
                return 'not pathable'
        if rules['forbidden'] and any(o is not b and not o.speed
                                      and math.hypot(o.x - x, o.y - y) - o.radius < rules['forbidden']
                                      for o in self.living()):
            return 'too near an object'
        if 'LIMIT_DISTANCE' in rules['flags'] and rules['reach'] and math.hypot(b.x - x, b.y - y) > rules['reach']:
            return 'out of reach'
        return None

    def order_power(self, b, power, pos):
        """The player's ground power (simproxy's): (True, None) and cast as the scripts' way does (at a waypoint of its
        own), or (False, why) -- power_refusal."""
        x, y = float(pos[0]), float(pos[1])
        why = self.power_refusal(b, power, x, y) if b and b.alive else 'gone'
        if why:
            self.note('技能', f'{self.label(b) if b else "?"} 用 {power} 不行：{why}')
            return False, why
        spot = f'SIM power spot {len(self.waypoints)}'
        self.waypoints[spot] = (x, y)
        self.act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', [b.name, power, spot], None)
        return True, None

    def order_stop(self, b):
        if b:
            b.path, b.goal, b.follow = [], None, None
            b.flee = None                       # a later order takes the run over (engine_runoffmap d; the status stays)

    def stand(self, b):
        """Its order dropped, nothing new: idle where it is (the AI's command 5: l2_scripts1 3, 6)."""
        b.path, b.goal, b.mode, b.move_to, b.follow = [], None, 'idle', None, None

    def path_start(self, label, at):
        """The waypoint a path is joined at: of the waypoints carrying `label`, the nearest to `at` (2D; strictly
        nearer replaces, so the first in map order wins a tie) -- Generals' TerrainLogic::getClosestWaypointOnPath.
        None if no waypoint carries it."""
        best, bd = None, None
        for n, labels in self.mm.labels.items():
            if label in labels and n in self.waypoints:
                x, y = self.waypoints[n]
                d = (x - at[0]) ** 2 + (y - at[1]) ** 2
                if bd is None or d < bd:
                    best, bd = n, d
        return best

    def path_next(self, at):
        """The waypoint after `at` on its path (the map's WaypointsList, one way), None at the path's end. INFERRED:
        Generals' AIFollowWaypointPathState::getNextWaypoint picks one of several links at random; this takes the
        first (the runs stay repeatable) and marks the run. A loop goes round and round (INFERRED, not benched)."""
        nxt = [z for a, z in self.mm.links if a == at]
        if len(nxt) > 1:
            self.used.add('path fork')
        return nxt[0] if nxt else None

    def order_follow(self, bodies, label, attacking, exact=False, start=None, as_team=False):
        """NAMED_ / TEAM_ (ATTACK_) FOLLOW_WAYPOINTS (_EXACT, _STARTING_AT_WAYPOINT): each unit goes waypoint by
        waypoint along the path `label`, from `start`, or else the path's waypoint nearest to it (a team: to its
        middle, Generals' doTeamFollowWaypoints joins at getClosestWaypointOnPath of the team's estimated position);
        at a waypoint it takes the next (path_next) and stops at the path's end. Each leg is a move (order_move;
        attacking: an attack-move, it stops to fight and goes on). as_team: the team's legs are group moves
        (order_group), the next leg once every member is there. INFERRED, to be benched: EXACT walks the same as
        the plain one (no corner cut either way); the team version's fourth flag and BiDirectional do nothing."""
        movers = [b for b in bodies if b and b.alive and b.speed > 0 and 'IMMOBILE' not in b.status]
        if not movers:
            return
        self.used.add('follow path')
        if start is None:
            n = len(movers)
            start = self.path_start(label, (sum(b.x for b in movers) / n, sum(b.y for b in movers) / n))
        if start is None or start not in self.waypoints:
            for b in movers:
                self.note('卡住', f'{self.label(b)} 找不到路 {label}')
            return
        self.follow_leg(movers, {'label': label, 'at': start, 'attacking': attacking, 'exact': exact,
                                 'team': as_team})

    def follow_leg(self, movers, how):
        """Sends `movers` to how['at'] and marks them as on the path (a team as one: one shared dict)."""
        if how['team'] and len(movers) > 1:
            self.order_group(movers, how['at'], how['attacking'])
            for b in movers:
                b.follow = how
        else:
            for b in movers:
                self.order_move(b, how['at'], how['attacking'])
                b.follow = dict(how, team=False)

    def follow_due(self):
        """The path followers that got where their leg went (no way left, not fighting): on to the next waypoint,
        or off the path at its end. One waypoint per tick at most."""
        done = set()
        for b in self.living():
            how = b.follow
            if how is None or id(how) in done:
                continue
            if how['team']:
                group = [o for o in self.living() if o.follow is how]
                if any(o.path or o.engaged or isinstance(o.goal, Body) for o in group):
                    continue
                done.add(id(how))
            else:
                if b.path or b.engaged or isinstance(b.goal, Body):
                    continue
                group = [b]
            nxt = self.path_next(how['at'])
            if nxt is None or nxt not in self.waypoints:
                for o in group:
                    o.follow = None
                continue
            leg = dict(how, at=nxt)
            done.add(id(leg))
            self.follow_leg(group, leg)

    def enemy(self, a, b):
        """Player a takes player b as an enemy."""
        if (a, b) in self.relations:
            return self.relations[(a, b)] == 'Enemy'
        # the container (Heidelberg, maps/island.py) has Soviet_1..6 all in Player_1's playerEnemies, and they fire
        # unprompted, woken or not (bench 11-09 engine_scripts9b rel 丁: Soviet_4's tank, no AI script, shoots at s1)
        players = set(self.players.values())
        return {a, b} == {self.human, self.foe} or (a != b and CIV not in (a, b) and self.human in (a, b)
                                                   and (a in self.ai or b in self.ai or {a, b} <= players))

    def hostile(self, a, t):
        """Body a takes body t as an enemy: the team overrides first, then the players (Generals Team::getRelationship:
        a's team to t's team, a's team to t's owner, a's owner to t's team, the players). INFERRED; pending_scripts9 rel"""
        at, tt = a.team or '', t.team or ''
        tests = ((self.team_team_rel, lambda x, y: same_team(at, x) and same_team(tt, y)),
                 (self.team_player_rel, lambda x, y: same_team(at, x) and t.owner == y),
                 (self.player_team_rel, lambda x, y: a.owner == x and same_team(tt, y)))
        for table, hit in tests:
            for (x, y), r in table.items():
                if hit(x, y):
                    return r == 'Enemy'
        return self.enemy(a.owner, t.owner)

    def point(self, name):
        """A waypoint, a trigger area's middle, a site, a mark, a named object, map coordinates '@x,y' (model.coord)."""
        c = coord(name)
        if c is not None:
            return c
        if name in self.waypoints:
            return self.waypoints[name]
        if name in self.areas:
            pts = self.areas[name]
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        if name in self.m.marks:
            return self.waypoints[self.m.marks[name]]
        sites = getattr(self.m.map, 'SITES', {})
        if name in sites:
            return (sites[name].x, sites[name].y)
        b = self.bodies.get(self.m.cast[name].name if name in self.m.cast else name)
        if b:
            return (b.x, b.y)
        return None

    def note(self, kind, text):
        self.log.append((self.t, kind, text))

    def gap(self, kind, name, what=''):
        """Records what this run met and the simulator does not act on -- one place for every such skip, so a gap shows
        when a play meets it instead of being passed over in silence (the user's rule 11-08: fix by class). kind: a
        GAP_* name; Sim.unmodeled[(kind, name)] = {'n' times, 't' the first time, 'what' the first note}."""
        g = self.unmodeled.get((kind, name))
        if g is None:
            self.unmodeled[(kind, name)] = {'n': 1, 't': self.t, 'what': what}
        else:
            g['n'] += 1

    def show_caption(self, text, secs):
        """The military caption box (E6): one line, replaced by the next, gone after its own seconds."""
        if self.box_log and self.box_log[-1][1] > self.t:
            self.box_log[-1][1] = self.t
        self.box_log.append([self.t, self.t + float(secs), text])

    def show_subtitle(self, text):
        """The dialogue panel (E6): a dubbed line's subtitle joins the stack; PANEL_CLEAR after the last the stack goes."""
        if not self.panel_log or self.t >= self.panel_log[-1][-1][0] + PANEL_CLEAR:
            self.panel_log.append([])
        self.panel_log[-1].append((self.t, text))

    def late_captions(self):
        """The 功能 captions that came up more than FUNC_LATE after their event (K1: none may), and the ones still waiting
        (the run ended, or a scene held them) as (flag, asked, None)."""
        def wait(a, b):                         # the seconds from a to b the player could see (no scene running)
            return (b - a) - sum(max(0.0, min(b, e if e is not None else b) - max(a, s)) for s, e in self.scenes)
        return [x for x in self.up if wait(x[1], x[2]) > FUNC_LATE + 1e-6] + \
            [(f, t, None) for f, t in self.asked.items() if wait(t, self.t) > FUNC_LATE]

    def box_at(self, t):
        """The caption up at t, or None."""
        return next((x for a, b, x in self.box_log if a <= t < b), None)

    def panel_at(self, t):
        """The subtitles stacked in the panel at t."""
        return [x for g in self.panel_log if g[0][0] <= t < g[-1][0] + PANEL_CLEAR for a, x in g if a <= t]

    def change(self):
        self.last_change = self.t

    def reach(self, b, target):
        """R3: how near (centre to centre) an attacker goes to its target: the longest range of its weapons that can
        hit it, plus both bounding radii (R8, `in_range`), less ATTACK_SLACK (0: it has none -- it goes to the target
        itself)."""
        r = [w['range'] for w in b.weapons if self.can_hit(w, target)]
        return max(max(r) + b.radius + target.radius - ATTACK_SLACK, 1.0) if r else 0.0

    @staticmethod
    def in_range(a, t, w, d=None):
        """R8: a weapon reaches when the 2D gap between the two bounding circles is within its range (Generals
        Weapon::isWithinAttackRange, FROM_BOUNDINGSPHERE_2D: the centre distance less both radii); `d` the centre
        distance when known. Bench 2026-11-07 engine_acquire: a Guardian (150, radius 23.3) fires at one 180 off."""
        if d is None:
            d = math.hypot(t.x - a.x, t.y - a.y)
        return d - a.radius - t.radius <= w['range']

    def send(self, b, target, by='', reach=0.0):
        if b.guessed:                               # its speed matters now: say when it is only a guess
            self.guessed.add(f'{b.template}: {", ".join(b.guessed)}')
        if not b.alive or b.speed <= 0:
            return
        p = self.point(target) if isinstance(target, str) else target
        if p is None:
            self.note('卡住', f'{self.label(b)} 找不到要去的地方 {target}')
            return
        path = self.ground.within(b.surface, (b.x, b.y), p, reach) if reach else None
        stands = False
        if path is None:
            path = self.ground.route(b.surface, (b.x, b.y), p, closest=True)
            stands = path == []
        b.dest = p
        if path is None:
            self.note('卡住', f'{self.label(b)} 到不了 {target if isinstance(target, str) else "目标"}'
                              f'（{b.surface} 没有路）')
            b.path = []
            return
        if stands and b.dest != b.stood_for:
            # walled in, where it stands is the nearest it gets: it stays (bench engine_seal move); not stuck
            self.note('够不着', f'{self.label(b)} 走不到 {target if isinstance(target, str) else "目标"}，'
                                f'原地就是能到的最近处，站着')
            b.stood_for = b.dest
        import simtopple
        points = [(b.x, b.y)] + path
        b.frame_move = self.eng is not None and any(o.alive and simtopple.crosses(b, o, a, z, self.own)
                                                  for o in self.topples if o is not b
                                                  for a, z in zip(points, points[1:]))
        if b.frame_move:
            if not b.path:
                b.drive_speed = 0.0
            self.frame_movers[b.name] = b
        else:
            self.frame_movers.pop(b.name, None)
        b.path = path
        self.change()

    def label(self, b):
        role = next((k for k, r in self.m.cast.items() if r.name == b.name and b.name), '')
        return role or b.name or b.template

    def present(self, b):
        """Still in the game's name cache: alive, dying (LINGER after its death, where it fell), or deleted this
        tick (removed at the frame's end: docs/engine/script-semantics.md 4.2)."""
        if b is None or b.alive:
            return b is not None
        if b.deleted:
            return self.t <= b.died_at
        self.used.add('death linger')
        return self.t - b.died_at <= b.linger + 1e-9

    def dying(self, b):
        """NAMED_DYING: killed (not deleted) and still lying -- the kill frame at least; a crushed infantryman its
        SlowDeath's DestructionDelay (bench 11-06 engine_crush: 127 frames; a plant killed by script: one frame)."""
        return b is not None and not b.alive and not b.deleted and self.t - b.died_at <= b.linger + 1e-9

    SELL_PERCENT, SELL_FRAMES = 0.5, 30          # SellPercentage (SDK default) and SellTime 2 s x 15 (BuildingBehavior)

    def sell(self, b):
        """SELL_OBJECT (bench 2026-11-06 engine_sell, docs/engine/sell.md): a living structure that is not unpacking
        and not already sold is paid at once -- round(round(cost x 50%) x health share) -- and carries SOLD; 30 frames
        later it is deleted (no death, no ruin); meanwhile it still counts as power and can still be killed (then the
        money stays paid and it is just dead). Anything else: nothing happens. Not read: a template's RefundValue,
        NOT_SELLABLE, the factory's queue. The garrison empties (simgarrison, INFERRED: Generals' onSelling)."""
        if b is None or not b.alive or 'STRUCTURE' not in b.kinds or b.sell_end is not None:
            return
        self.garrison.empty(b)
        if b.unpack_end is not None and self.frame_now() < b.unpack_end:
            return                                                  # engine_sell c: refused while it unpacks
        self.used.add('sell')
        cost = simunits.production(b.template, self.own)[0]
        refund = math.floor(math.floor(cost * self.SELL_PERCENT + 0.5) * (b.hp / b.max_hp if b.max_hp else 1.0) + 0.5)
        self.money[b.owner] = self.money.get(b.owner, 0) + refund
        b.script_status.add('SOLD')
        self.modify(b)
        b.sell_end = self.frame_now() + self.SELL_FRAMES
        self.note('出售', f'{self.label(b)}（退 {refund}）')

    def destroy(self, b, why, delete=False):
        if not b.alive:
            return
        if b.immortal and not delete:
            # Object::kill (also script KILL, crushing etc.) is lethal damage;
            # only direct deletion bypasses the body's internalChangeHealth.
            b.damage(b.max_hp)
            return
        if b.prop and not delete and (b.topple or b.prop == 'stays'):
            # engine_propbody b (bench 11-10): a killed topple prop falls where it stands (no fall time) and is gone
            # its delay later, never dying (expire; 61 / 121 frames counted with the kill's); a PropBody with nothing
            # to take its death stays for good
            if b.topple and b.topple_end is None:
                b.toppled, b.topple_end = True, self.frame_now() + b.topple['delay']
            return
        b.alive, b.deleted, b.path, b.died_at = False, delete, [], self.t
        self.garrison.died(b, delete)       # passengers out alive / killed with it (simgarrison, garrison.md 4)
        if not delete:
            b.hp = 0.0
            # FireWeaponWhenDead (simunits.death_weapons; bench 11-05 engine_spawn_refill): its weapon goes off where it
            # died; a deletion fires nothing (INFERRED, as Generals' destroyObject skips the die modules)
            for dmg, typ, reach, after, affects in simunits.death_weapons(b.template, self.own):
                self.used.add('death weapon')
                self.death_blasts.append((self.frame_now() + simunits._frames(after), b.x, b.y, dmg, typ, reach,
                                          affects, b.owner, b))
        self.note('删除' if delete else '摧毁', f'{self.label(b)}（{why}）')
        self.change()
        if self.blocks(b):
            self.reblock()

    # ---- the engine model's World: what its script engine asks of the objects (the rest it does itself)
    def condition(self, eng, name, args):
        if name in RA3_ONLY:
            self.ra3_only.add(name)
        return self.cond(name, self.this_player(eng, args))

    def action(self, eng, name, args):
        self.act(name, self.this_player(eng, args), eng.script)

    @staticmethod
    def this_player(eng, args):
        """'<This Player>' as the game reads it: the player whose script list the script is in (the engine's side;
        retail maps' lists are per player, ours have one unnamed list and never use it)."""
        side = getattr(eng, '_side', '')
        return [side if a == '<This Player>' and side else a for a in args]

    def update(self, eng):
        """Units move and fight in step(), once a DT tick."""

    def difficulty(self, side):
        return None                             # the run's level ('difficulty side')

    # ---- conditions
    def holds(self, c):
        c = list(c)
        neg = c and c[-1] == parts.NOT
        if neg:
            c = c[:-1]
            self.used.add('inverted')
        if c[0] in RA3_ONLY:
            self.ra3_only.add(c[0])
        v = self.cond(c[0], c[1:])
        return (not v) if neg else v

    def body(self, name):
        if name in self.refs:                       # R2: a reference reads as the object it points at, dead or not
            return self.refs[name]
        return self.bodies.get(name)

    def of_types(self, name):
        """A script's object type argument (type 61): an object list's types (any player's list, any case) or that
        one type, lower case."""
        return self.object_lists.get(str(name).lower()) or {str(name).lower()}

    def nearest_ref(self, template, owner, team, ref, unnamed=True):
        """R2: SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER -- point `ref` at the living `template` of
        `owner` nearest to `team`'s middle (its members' mean place; bench 2026-11-07 engine_ref a / a2: not the first
        member's nor any member's nearest, whatever order they were made in), objects with a script name skipped
        (ref_b); an empty team's middle reads (0, 0) (ref_c: the wall nearest the map's corner was picked -- a
        guess as to why). None of the type: `ref` left as it was (not read on the bench)."""
        self.used.add('nearest ref')
        crew = self.members(team)
        want = self.of_types(template)
        cands = [b for b in self.living() if b.owner == owner and b.template.lower() in want
                 and (b.name.startswith('#') or not unnamed)]
        if not cands:
            return
        mx = sum(m.x for m in crew) / len(crew) if crew else 0.0
        my = sum(m.y for m in crew) / len(crew) if crew else 0.0
        self.refs[ref] = min(cands, key=lambda c: math.hypot(c.x - mx, c.y - my))

    def cond(self, name, a):
        if name == 'FLAG':
            return int(self.flags.get(a[0], 0)) == int(a[1])
        if name == 'PLAYER_HAS_COMPARISON_POWER_POINTS':     # (player, comparison, n): the points to spend
            self.used.add('protocols')
            self.tech_read = True
            return int(a[1]) in CMP and any(CMP[int(a[1])](b.points, int(a[2])) for b in self.books_of(a[0]))
        if name == 'PLAYER_HAS_PLAYER_TECH':                 # (player, protocol): held (a rank's, bought, the default)
            self.used.add('protocols')
            self.tech_read = True
            return any(b.has(str(a[1])) for b in self.books_of(a[0]))
        if name == 'TIMER_EXPIRED':
            if a[0] not in self.timers:
                self.used.add('timer unset')
                return False
            return self.t >= self.timers[a[0]]
        if name == 'COUNTER':
            return CMP[a[1]](self.counters.get(a[0], 0), a[2])
        if name in ('PLAYER_TRIGGERED_SPECIAL_POWER', 'PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED',
                    'PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA'):
            # (player, power[, named / area]): a cast of the player's in the frame before (bench 11-09 engine_scripts8b
            # pfire: 施放数 1 -- seen for one frame; pdis: 2, the second cast hurt nobody). Which frame sees it is
            # INFERRED (the next frame's scripts, so a script after the caster's sees it once too); _FROM_NAMED /
            # _IN_AREA (the caster, the cast's point inside the area) are INFERRED, not on the bench
            now = self.frame_now()
            for f, owner, power, who, q in self.casts:
                if f != now - 1 or owner != a[0] or power != str(a[1]).lower():
                    continue
                if name.endswith('_FROM_NAMED') and who != a[2]:
                    continue
                if name.endswith('_IN_AREA') and not (q and inside(self.areas[a[2]], *q)):
                    continue
                return True
            return False
        if name in ('NAMED_DESTROYED', 'NAMED_NOT_DESTROYED'):
            b = self.body(a[0])
            if b is None:
                self.used.add('destroyed unborn')
                return False
            # killed: destroyed at once; deleted: only from the next frame (the game's destroy list at the frame's end)
            dead = not b.alive and not (b.deleted and self.t <= b.died_at)
            return dead if name == 'NAMED_DESTROYED' else not dead
        if name == 'NAMED_DYING':
            return self.dying(self.body(a[0]))
        if name in ('NAMED_INSIDE_AREA', 'NAMED_OUTSIDE_AREA'):
            # the game asks no question of life: a dying unit is where it fell; a removed one is outside every area
            b = self.body(a[0])
            within = bool(self.present(b) and inside(self.areas[a[1]], b.x, b.y))
            return within if name == 'NAMED_INSIDE_AREA' else not within
        if name == 'PLAYER_EXCESS_POWER_COMPARE_VALUE':    # (player, cmp, n): supply - demand (the engine model's
            sup, dem = self.power(a[0])                     # world.py reads it so; not measured)
            self.used.add('power')
            return CMP[a[1]](sup - dem, a[2])
        if name == 'PLAYER_HAS_OBJECT_COMPARISON':
            # the dying counted too (Team::countObjectsByThingTemplate, ignoreDead false); a type or an object list
            want = self.of_types(a[3])
            n = sum(1 for b in self.bodies.values() if b.owner == a[0] and b.template.lower() in want
                    and self.present(b))
            return CMP[a[1]](n, a[2])
        if name == 'TEAM_DESTROYED':
            # INFERRED (Generals evaluateIsDestroyed: the team has no object left; not read in RA3): the dying count
            # as there, as PLAYER_HAS_OBJECT_COMPARISON's; a team nobody was ever in is not destroyed
            self.used.add('team destroyed')
            if not self.team_active(a[0]):
                return False
            return not any(same_team(b.team, a[0]) and self.present(b) for b in self.bodies.values())
        if name == 'CURRENT_PLATFORM':          # the game we run is the PC one
            return str(a[0]).upper() == 'PC'
        if name == 'PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA':
            n = sum(1 for b in self.living() if b.owner == a[0] and b.template.lower() == a[3].lower()
                    and inside(self.areas[a[4]], b.x, b.y))
            return CMP[a[1]](n, a[2])
        if name == 'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA':
            self.used.add('kind all players')
            kind = a[3][2] if isinstance(a[3], tuple) else a[3]
            n = sum(1 for b in self.living() if kind in b.kinds and inside(self.areas[a[4]], b.x, b.y))
            return CMP[a[1]](n, a[2])
        if name == 'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA':
            self.used.add('units in area')
            return any(b.owner == a[0] and not b.scenery and inside(self.areas[a[1]], b.x, b.y) for b in self.living())
        if name == 'NAMED_OWNED_BY_PLAYER':
            b = self.body(a[1])
            return bool(self.present(b) and b.owner == a[0])
        if name == 'NAMED_ATTACKED_BY_PLAYER':
            # the last damage only (ActiveBody's m_lastDamageInfo): a script's kill or another's hit clears it; the game
            # reads its source's id and looks that object up, so a source that is gone (dead and removed, deleted, self-
            # destructed) makes it false, and one that changed hands counts for its new owner (E2, reference 2026-11-04)
            b = self.body(a[0])
            if not self.present(b):
                return False
            if b.last_by is None:               # a hit a run script made up (打 / 摧毁): taken as the player's, standing
                return b.last_hit == a[1]
            by = self.bodies.get(b.last_by)
            return bool(self.present(by) and by.owner == a[1])
        if name == 'UNIT_HEALTH':
            # whole percent, rounded down (int(health * 100 / max): 99.9 % reads 99, so "< 50" holds at 49.9 %); a dying
            # unit reads 0 (E4)
            b = self.body(a[0])
            pct = math.floor(b.health + 1e-6) if b is not None and b.alive else 0
            return bool(self.present(b) and CMP[a[1]](pct, a[2]))
        if name == 'NAMED_DISCOVERED':
            self.used.add('discovered')
            b = self.body(a[1])
            return bool(b and self.sees(b.x, b.y, b.surface == 'air'))
        if name == 'CAMERA_ENTERED_AREA':
            return bool(self.camera and inside(self.areas[a[0]], *self.camera))
        if name == 'PLAYER_IS_HUMAN_OR_AI_PERSONALITY':
            # (player, personality) l2_scripts1 2.1: "Human" = the player has no AI; else its AI's personality is the
            # name. Bench 11-08 engine_scripts1 cond: Player_1 Human holds, Soviet_1 (a campaign computer player, its
            # AI never woken) is not Human from the start -- every computer player has its AI object
            # The map keeps the personality as an asset reference ('AIPersonalityDefinition:AIP_A03_Coop_...'), the
            # script names it bare: compared by the name after the type, case aside (asset names)
            if a[1] == 'Human':
                return a[0] == self.human
            want = str(a[1]).split(':')[-1].lower()
            return a[0] != self.human and any(self.players.get(s) == a[0] and
                                              str(p.get('aiPersonality', '')).split(':')[-1].lower() == want
                                              for s, p in getattr(self.m, 'sides', {}).items())
        if name == 'UNIT_HAS_OBJECT_STATUS':
            # (unit, status) l2_scripts1 2.2: the object's status bit; no object, false. Bench 11-08 cond: a bit a
            # script set reads at once, cleared at once, and a killed unit reads false from the kill
            b = self.body(a[0])
            st = a[1][2] if isinstance(a[1], tuple) else a[1]
            if st not in ACTED_STATUS and st not in getattr(b, 'status', ()):
                self.gap(GAP_CONDITION, name, f'状态位 {st}：模拟器只知道脚本设的和 {"、".join(sorted(ACTED_STATUS))}')
            if b and not b.alive and b.read_until == self.frame_now():     # engine_sell e: a damage kill still reads
                return st in b.status                                      # its bits in that frame
            return bool(b and b.alive and st in b.status)
        if name == 'HAS_FINISHED_AUDIO':        # never played: true (l2_scripts1 2.3; bench 11-08 cond)
            return self.t >= self.audio_end.get(a[0], 0.0)
        if name == 'HAS_FINISHED_VIDEO':        # never played: false (bench 11-08 cond); full screen: never (movie.py)
            end = self.video_end.get(a[0])
            return end is not None and self.t >= end
        self.unknown[name] = self.unknown.get(name, 0) + 1
        self.gap(GAP_CONDITION, name, 'Sim.cond 不认识：当成不成立')
        return False

    def sees(self, x, y, air=False):
        """Whether the player sees a point (a body there, airborne or not)."""
        if self.reveal_all:
            return True
        if any(math.hypot(x - rx, y - ry) <= r for rx, ry, r in list(self.reveals.values()) + self.peeking()):
            return True
        return any(b.owner == self.human and self.looks(b, x, y, air) for b in self.living())

    def looks(self, v, x, y, air=False):
        """Whether body v sees the point: within its vision, and (the high-ground rule, 未对齐) not on ground
        HIGH_STEP above its own -- unless one of the two flies."""
        sight = v.vision or max((w['range'] for w in v.weapons), default=0.0)     # no vision of its own: its guns'
        if not sight or math.hypot(v.x - x, v.y - y) > sight:
            return False
        if not self.high or air or v.surface == 'air':
            return True
        self.used.add('high ground')
        return self.ground.z(x, y) <= self.ground.z(v.x, v.y) + v.clear_height

    def side_sees(self, side, t):
        """Whether a side (it or a friend of it) sees body t, this tick; the player's reveals count for the player."""
        key = (side, id(t))
        if key not in self.seen:
            air = t.surface == 'air'
            if t.fired_at is not None and self.t - t.fired_at <= FIRE_SEEN:
                ok = True
            elif side == self.human:
                ok = self.sees(t.x, t.y, air)
            elif side in self.revealed_to:
                ok = True
            else:
                ok = any(not self.enemy(side, v.owner) and v.owner != CIV and self.looks(v, t.x, t.y, air)
                         for v in self.living())
            self.seen[key] = ok
        return self.seen[key]

    # ---- actions
    def played(self, name, a):
        """A sound or a movie started: when HAS_FINISHED_AUDIO / _VIDEO will hold (AUDIO_LEAD ...)."""
        if name in SOUND_PLAYS:
            n = self.audio_len(a[0])
            if n is None:
                self.gap(GAP_ACTION, name, f'{a[0]} 时长读不到：按 {AUDIO_GUESS} 秒算播完')
                n = AUDIO_GUESS
            self.audio_end[a[0]] = self.t + AUDIO_LEAD + n
        elif name == 'MOVIE_PLAY_RADAR':
            n = self.video_len(a[0])
            if n is None:
                self.gap(GAP_ACTION, name, f'{a[0]} 时长读不到：按 {VIDEO_GUESS} 秒算播完')
                n = VIDEO_GUESS
            self.video_end[a[0]] = self.t + n
        elif name == 'MOVIE_PLAY_FULLSCREEN':
            self.video_end[a[0]] = None

    def audio_len(self, event):
        """Seconds one of our dubbed lines plays (its recording in the mission's voice pack), else None (a retail
        line, a unit's voice)."""
        items = getattr(getattr(self.m, 'voice', None), 'items', None) or ()
        wav = next((it[1] for it in items if it[0] == event and not it[3]), None)
        if not wav:
            return None
        import wave
        try:
            with wave.open(wav) as w:
                return w.getnframes() / w.getframerate()
        except (wave.Error, OSError, EOFError):
            return None

    def video_len(self, clip):
        """Seconds a radar clip plays: its VP6 header (frames, rate) -- ours from the mission's clips, a retail one
        from the game's loose <GAME>/Data/Movies/<clip>.vp6 -- else None. Bench 11-09 (checks/movie.py retail at x1):
        A02TH06 291 frames (header 18.9 s), J01TH05 169 (10.8 s): a retail clip reads finished after its own length
        (at x8 the shim's clock hook does not reach the clip: it plays in real time, 100+ mission s)."""
        path = (getattr(getattr(self.m, 'video', None), 'clips', None) or {}).get(clip)
        if not path:
            import labpaths
            path = os.path.join(labpaths.GAME, 'Data', 'Movies', f'{clip}.vp6')
        try:
            with open(path, 'rb') as f:
                head = f.read(32)
        except (OSError, TypeError):
            return None
        if head[:4] != b'MVhd':
            return None
        frames, _, den, num = struct.unpack('<IIII', head[16:32])
        return frames * num / den if den else None

    def act(self, name, a, script):
        if name in RA3_ONLY:
            self.ra3_only.add(name)
        if name in SOUND_PLAYS or name.startswith('MOVIE_PLAY_'):
            self.played(name, a)
        if name == 'SET_FLAG':
            if SCENE_FLAG.fullmatch(str(a[0])):         # the player's input is off: nothing is late for a scene's length
                if a[1]:
                    self.scenes.append([self.t, None])
                elif self.scenes and self.scenes[-1][1] is None:
                    self.scenes[-1][1] = self.t
            if SHOW_FLAG.fullmatch(str(a[0])):          # a 功能 line's caption: asked for, then up (ctx.Talk `Now k`)
                if a[1]:
                    self.asked.setdefault(a[0], self.t)
                elif a[0] in self.asked:
                    self.up.append((a[0], self.asked.pop(a[0]), self.t))
            if int(self.flags.get(a[0], 0)) != int(a[1]):
                self.flags[a[0]] = int(a[1])
                self.change()
                if a[0] == WON and a[1]:
                    self.end('赢', script)
                elif a[0] == LOST and a[1]:
                    self.end('输', script)
        elif name == 'SET_COUNTER':
            self.counters[a[0]] = a[1]
        elif name == 'SET_COUNTER_TO_COUNTER':
            self.counters[a[0]] = self.counters.get(a[1], 0)
        elif name == 'COUNTER_MATH_COUNTER':        # retail: 0 adds (a total of per-player kills), 1 takes away (what is
            dst, op, src = a                        # left of the transports spawned); other codes were never seen used
            if op not in (0, 1):
                self.used.add(f'COUNTER_MATH_COUNTER code {op}')
            self.counters[dst] = self.counters.get(dst, 0) + (-1 if op == 1 else 1) * self.counters.get(src, 0)
        elif name in ('INCREMENT_COUNTER', 'DECREMENT_COUNTER'):
            self.counters[a[1]] = self.counters.get(a[1], 0) + (a[0] if name == 'INCREMENT_COUNTER' else -a[0])
            self.change()
        elif name == 'SET_MILLISECOND_TIMER':
            self.timers[a[0]] = self.t + float(a[1])
            self.change()
        elif name == 'SET_RANDOM_MSEC_TIMER':       # [lo, hi] at random (源码): the latest, as the beat sheet counts
            self.timers[a[0]] = self.t + float(a[2])
            self.change()
        elif name in ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION'):
            p = self.point(a[3])
            if p is None:
                return
            old = self.bodies.get(a[0])
            if old and old.alive:
                return                                  # one object to a name (the game makes no second)
            b = self.add(a[0], a[1], a[2].split('/')[0], *p, by=script.name, at=self.t)
            b.team = a[2]
            self.active.add(a[2])
            b.angle = float(a[4]) if len(a) > 4 else 0.0
            if self.blocks(b):
                self.reblock()
            self.note('出现', f'{self.label(b)}（{a[1]}，{self.who(b.owner)}）在 {a[3]}'
                      + ('' if b.owner == self.human or self.sees(b.x, b.y, b.surface == 'air') else '，玩家看不见'))
            self.change()
        elif name in ('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION'):
            # (type, team, waypoint[, angle]): the named one's maker without a name (RA3 1.13: both run the same three
            # calls, work/re actions_map.json), a new object every time it runs, on the team; no name, so '#' (an
            # unnamed one for SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER) -- bench 2026-11-09 ref_d
            self.used.add('create unnamed')
            p = self.point(a[2])
            if p is None:
                return
            b = self.add(f'#created {len(self.bodies)} {a[0]}', a[0], a[1].split('/')[0], *p, by=script.name, at=self.t)
            b.team = a[1]
            self.active.add(a[1])
            b.angle = float(a[3]) if len(a) > 3 else 0.0
            if self.blocks(b):
                self.reblock()
            self.note('出现', f'{a[0]}（{self.who(b.owner)}）在 {a[2]}'
                      + ('' if b.owner == self.human or self.sees(b.x, b.y, b.surface == 'air') else '，玩家看不见'))
            self.change()
        elif name in ('CREATE_REINFORCEMENT_TEAM', 'CREATE_REINFORCEMENT_TEAM_AT_UNIT_POSITION'):
            # (team, waypoint) / (team, named unit): one handler 0x5b7f50 for both (work/re actions_map.json); the
            # unit's position as the waypoint is INFERRED (Sim.point reads a named object's)
            self.reinforce(a[0], a[1], script)
        elif name in ('MOVE_NAMED_UNIT_TO', 'ATTACK_MOVE_NAMED_UNIT_TO'):
            self.order_move(self.body(a[0]), a[1], name == 'ATTACK_MOVE_NAMED_UNIT_TO')
        elif name in ('NAMED_FOLLOW_WAYPOINTS', 'NAMED_FOLLOW_WAYPOINTS_EXACT', 'NAMED_ATTACK_FOLLOW_WAYPOINTS',
                      'NAMED_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT'):
            # (unit, path[, start waypoint])
            self.order_follow([self.body(a[0])], a[1], name == 'NAMED_ATTACK_FOLLOW_WAYPOINTS',
                              exact=name.endswith('_EXACT'), start=a[2] if name.endswith('_AT_WAYPOINT') else None)
        elif name == 'NAMED_ATTACK_NAMED':
            self.order_attack(self.body(a[0]), a[1])
        elif name == 'UNIT_GUARD_AREA':
            self.order_guard(self.body(a[0]), a[1])
        elif name == 'NAMED_STOP':
            self.order_stop(self.body(a[0]))
        elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED' and a[1] == 'Command_CaptureBuilding':
            self.order_capture(self.body(a[0]), a[2])
        elif name == 'SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER':
            self.nearest_ref(*a[:4])
        elif name == 'SET_REF_TO_NEREST_TEAM_OF_TYPE_OWNED_BY_PLAYER':     # INFERRED: the same, named ones too
            self.used.add('nearest ref any')
            self.nearest_ref(*a[:4], unnamed=False)
        elif name == 'OBJECTLIST_ADDOBJECTTYPE':    # (type, list): the list grows by that type (types read lower case)
            self.object_lists.setdefault(str(a[1]).lower(), set()).add(str(a[0]).lower())
        elif name == 'UNIT_SET_TEAM':               # the unit joins the team (K6: ctx.order does it before every whole-team order)
            b = self.body(a[0])
            self.active.add(a[1])                   # ... and the team has an instance from then on, the unit there or not (E3)
            if b and b.alive:
                b.team = a[1]
        elif name in TEAM_COMMANDS and not self.team_active(a[0]):
            # the game looks the team up without making it: nobody joined it, so the order does nothing (E3)
            self.lost_orders.append((self.t, script.name, name, a[0]))
            self.note('无效命令', f'{name} {a[0]}：这个队还没有人加入，命令落空')
        elif name in ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO'):
            self.order_group(self.members(a[0]), a[1], name == 'ATTACK_MOVE_TEAM_TO')
        elif name in TEAM_FOLLOWS:
            # (team, path, asTeam[, ?][, start waypoint]); the fourth flag (handler 0x5a4c40) not read: ignored
            self.order_follow(self.members(a[0]), a[1], name == 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS',
                              exact=name.endswith('_EXACT'), as_team=bool(int(a[2])),
                              start=a[-1] if name.endswith('_AT_WAYPOINT') else None)
        elif name == 'TEAM_ATTACK_NAMED':
            for b in self.members(a[0]):
                self.order_attack(b, a[1])
        elif name == 'TEAM_GUARD_AREA':
            for b in self.members(a[0]):
                self.order_guard(b, a[1])
        elif name == 'TEAM_STOP':
            for b in self.members(a[0]):
                self.order_stop(b)
        elif name == 'UNIT_TELEPORT_TO_WAYPOINT':
            b, p = self.body(a[0]), self.point(a[1])
            if b and p:
                b.x, b.y, b.path = p[0], p[1], []
                self.change()
        elif name == 'NAMED_TRANSFER_OWNERSHIP_PLAYER':
            b = self.body(a[0])
            if b and b.owner != a[1]:
                b.owner = a[1]
                self.note('易主', f'{self.label(b)} 归 {self.who(a[1])}')
                self.change()
        elif name in ('TEAM_DELETE', 'TEAM_KILL', 'TEAM_DELETE_LIVING'):
            # (team) INFERRED (Generals doTeamDelete / doTeamKill): every living member removed / killed, as
            # NAMED_DELETE / NAMED_KILL one by one; TEAM_DELETE_LIVING as TEAM_DELETE. engine_scripts8 team asks
            for b in self.members(a[0]):
                if name == 'TEAM_KILL':
                    b.last_hit = b.last_by = None
                self.destroy(b, '脚本' if name == 'TEAM_KILL' else '脚本删掉', delete=name != 'TEAM_KILL')
        elif name in ('TEAM_IDLE_FOR_SECONDS', 'TEAM_IDLE_FOR_FRAMECOUNT'):
            # (team, n) INFERRED: the unit version on every member (it drops the order: engine_scripts7 idle)
            for b in self.members(a[0]):
                if b.speed:
                    self.stand(b)
        elif name == 'TEAM_CHANGE_OBJECT_STATUS':     # (team, status, on) INFERRED: the unit version on every member
            for b in self.members(a[0]):
                self.act('UNIT_CHANGE_OBJECT_STATUS', [b.name, *a[1:]], script)
        elif name == 'TEAM_MERGE_INTO_TEAM':          # (source, target) INFERRED (Generals doMergeTeamIntoTeam): the
            for b in self.members(a[0]):              # source's members join the target, their orders kept
                b.team = a[1]
            self.active.add(a[1])
            self.change()
        elif name in ('TEAM_SET_OVERRIDE_RELATION_TO_TEAM', 'TEAM_SET_OVERRIDE_RELATION_TO_PLAYER',
                      'PLAYER_SET_OVERRIDE_RELATION_TO_TEAM'):
            # (team / player, team / player, Enemy / Neutral / Friend) INFERRED (Generals doTeam / doPlayer override
            # relation): how the first takes the second from then on, over the players' relation (hostile)
            table = {'TEAM_SET_OVERRIDE_RELATION_TO_TEAM': self.team_team_rel,
                     'TEAM_SET_OVERRIDE_RELATION_TO_PLAYER': self.team_player_rel}.get(name, self.player_team_rel)
            table[(a[0], a[1])] = a[2] if isinstance(a[2], str) else {0: 'Enemy', 1: 'Neutral', 2: 'Friend'}[a[2][0]]
            self.change()
        elif name in ('TEAM_ATTACK_TEAM', 'NAMED_ATTACK_TEAM'):
            # (team / unit, team) INFERRED (Generals groupAttackTeam): each attacker on the target team's nearest
            # living member; when that one dies the fight picks the next (auto target). pending_scripts9 atk
            crew = self.members(a[0]) if name == 'TEAM_ATTACK_TEAM' else [b for b in [self.body(a[0])] if b and b.alive]
            them = self.members(a[1])
            for b in crew:
                if them:
                    self.order_attack(b, min(them, key=lambda t: math.hypot(t.x - b.x, t.y - b.y)).name)
                    self.team_targets[id(b)] = a[1]     # the fight takes the next member when this one dies
        elif name == 'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION':
            # (name, type, team, object) INFERRED: CREATE_NAMED_ON_TEAM_AT_WAYPOINT at the object's place, its facing
            at = self.body(a[3])
            if at and self.present(at):
                spot = f'SIM spawn spot {len(self.waypoints)}'
                self.waypoints[spot] = (at.x, at.y)
                self.act('CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION', [a[0], a[1], a[2], spot, at.angle], script)
        elif name == 'PLAYER_SET_BASE_POWER':         # (player, n) INFERRED: n supply on top of its objects'
            self.base_power[a[0]] = int(a[1])
            self.change()
        elif name == 'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT':
            # (player, power, waypoint) INFERRED: the player's first living object that has the power casts it, as
            # NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT (a script's cast: no reload asked); none, nothing. Retail fires
            # protocols this way mostly (orbital refuse, final squadron): those have no source object, not simulated
            power = next((k for k in (*SUPERWEAPON_HITS, *CURTAIN) if k.lower() == str(a[1]).lower()), a[1])
            src = next((b for b in self.living() if b.owner == a[0]
                        and simunits.power_rules(b.template, power, self.own)), None)
            if src:
                self.act('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', [src.name, power, a[2]], script)
            else:
                self.gap(GAP_ACTION, refined(name, a), f'{a[0]} 没有带 {a[1]} 的物体（协议类不模拟）')
        elif name == 'PLAYER_SPECIAL_POWER_AVAILABILITY':
            # (player, power, Available / Disabled / Hidden) INFERRED: the player's click refused unless Available
            # (power_refusal); a script's cast goes all the same. engine_scripts8 pdis asks the bench
            self.powers_off[(a[0], str(a[1]).lower())] = str(a[2])
        elif name == 'TEAM_TRANSFER_TO_PLAYER':
            # (team, player) l2_scripts1 6: each member goes to the player's own team, its order cleared. Bench 11-08
            # engine_scripts1 xfer: owned by the new player at once, the move it was on dropped, the team left empty
            for b in self.members(a[0]):
                b.owner, b.team = a[1], f'{a[1]}/team{a[1]}'
                self.stand(b)
                self.note('易主', f'{self.label(b)} 归 {self.who(a[1])}（命令清掉）')
            self.change()
        elif name in ('UNIT_IDLE_FOR_FRAMECOUNT', 'UNIT_IDLE_FOR_SECONDS'):
            # (unit, n) l2_scripts1 3: a unit with an AI drops its order (command 5) and its idle count is set. Bench
            # 11-08 idle: UNIT_IDLE_FOR_SECONDS 3 on a moving tank -- it never went on (45 s), not a 3 s pause
            b = self.body(a[0])
            if b and b.alive and b.speed:
                self.stand(b)
        elif name in ('TEAM_HUNT', 'NAMED_HUNT'):
            # l2_scripts1 4: a flag bit on each unit and its AI woken; only an AI player's HuntTactic (TEAM_HUNT) and
            # its AI (NAMED_HUNT) read it. Bench 11-08 hunt: a computer player's team / unit (AI not woken) and the
            # player's own team stayed where they were for 60 s
            crew = self.members(a[0]) if name == 'TEAM_HUNT' else [b for b in [self.body(a[0])] if b and b.alive]
            if any(b.owner in self.ai for b in crew):
                self.gap(GAP_ACTION, name, 'AI 玩家的猎杀战术（HuntTactic）不模拟（引擎 B 的 AI）')
        elif name in ('UNIT_AI_TRANSFER', 'TEAM_AI_TRANSFER'):
            # (unit / team, on) l2_scripts1 7: a computer player's units into / out of its AI's hands (no order
            # cleared); a human player's: nothing. What the AI then does with them is engine B's (AI not simulated)
            crew = self.members(a[0]) if name == 'TEAM_AI_TRANSFER' else [b for b in [self.body(a[0])] if b and b.alive]
            if any(b.owner != self.human for b in crew):
                self.gap(GAP_ACTION, name, '交给 AI 后的行为不模拟（引擎 B 的 AI）')
        elif name == 'TEAM_USE_COMMANDBUTTON_ABILITY':
            # (team, button) l2_scripts1 8: the button on every living member, no target. Bench 11-08 button: both
            # Peacekeepers of the crew raised their shields
            for b in self.members(a[0]):
                self.act('NAMED_USE_COMMANDBUTTON_ABILITY', [b.name, a[1]], script)
        elif name == 'SELL_OBJECT':              # (object) engine_sell: sell(), refused while unpacking
            self.sell(self.body(a[0]))
        elif name == 'NAMED_DAMAGE':             # (object, amount) health points off, no armour; engine_sell b / e
            b = self.body(a[0])                  # the Indestructible panel flag does not stop it (engine_scripts7 panel)
            if b and b.alive:
                b.last_hit = b.last_by = None
                b.damage(float(a[1]))
                if b.hp <= 0.0:
                    self.destroy(b, '脚本伤害')
                    b.read_until = self.frame_now()
                else:                           # under REALLYDAMAGED: out in this frame (engine_garrison 伤争敌 1230)
                    self.garrison.hurt(b)
        elif name in ('NAMED_KILL', 'NAMED_DELETE'):
            b = self.body(a[0])
            if b:
                if name == 'NAMED_KILL':
                    b.last_hit = b.last_by = None   # the game's kill damage comes from nobody (INVALID_ID)
                self.destroy(b, '脚本' if name == 'NAMED_KILL' else '脚本删掉', delete=name == 'NAMED_DELETE')
        elif name == 'PLAYER_SET_ALL_UNITS_TO_FLEE':     # (player) engine_runoffmap: every one with RunOffMapBehavior runs
            for b in self.living():
                if b.owner == a[0]:
                    self.flee_start(b)
        elif name == 'UNIT_SET_STANCE':          # (name, stance): 3 is HOLD_FIRE; the others are not modelled
            b = self.body(a[0])
            if b and b.alive:
                b.hold_fire = int(a[1]) == 3
        elif name == 'UNIT_SET_HEALTH':
            b = self.body(a[0])
            if b and b.alive:
                b.health = float(a[1])
        elif name == 'NAMED_SET_MAX_HEALTH':
            b = self.body(a[0])                 # (name, max, full too): retail Iga's trucks by difficulty
            if b and b.alive:
                pct = b.health
                b.max_hp = float(a[1])
                b.health = 100.0 if a[2] else pct
        elif name == 'UNIT_CHANGE_OBJECT_STATUS':
            b = self.body(a[0])
            st = a[1][2] if isinstance(a[1], tuple) else a[1]
            if b:
                (b.script_status.add if a[2] else b.script_status.discard)(st)
                self.modify(b)
            if st not in ACTED_STATUS:
                self.gap(GAP_ACTION, refined(name, a), f'状态位 {st} 只记下来；模拟器只认 {"、".join(sorted(ACTED_STATUS))}')
        elif name in ('UNIT_AFFECT_OBJECT_PANEL_FLAGS', 'TEAM_AFFECT_OBJECT_PANEL_FLAGS'):
            # (unit or team, flag, on). Indestructible: the body takes no damage at all (Generals ScriptActions
            # changeObjectPanelFlagForSingleObject -> ActiveBody::setIndestructible; attemptDamage returns at once;
            # not read in RA3). Bench 2026-11-09 engine_scripts7 panel: NAMED_DAMAGE and NAMED_KILL go through it (UNIT
            # and TEAM alike); a weapon's damage not measured -- still refused here (INFERRED).
            # Retail s01 keeps Natasha alive so ('Emergency - Natasha Indestructible'); the other
            # flags (Selectable, Enabled, AI Recruitable ...) are only noted
            flag = str(a[1][2] if isinstance(a[1], tuple) else a[1])
            if flag.lower() == 'indestructible':
                bodies = [self.body(a[0])] if name.startswith('UNIT') else self.members(a[0])
                for b in bodies:
                    if b:
                        b.indestructible = bool(a[2])
            else:
                self.gap(GAP_ACTION, f'{name}:{flag}', f'面板标志 {flag} 没模拟（只认 Indestructible）')
        elif name in ('NAMED_RECEIVE_UPGRADE', 'NAMED_REMOVE_UPGRADE'):     # (upgrade, object): recorded; of what an upgrade
            b = self.body(a[1])                                              # does to a unit only the SPEED modifier is
            if b:                                                            # simulated (units/pace.py's 齐步); a range,
                self._upgrade(b, a[0], name == 'NAMED_RECEIVE_UPGRADE')     # a shield are not; a tier (can_build) is
        elif name == 'ALLOW_DISALLOW_ONE_UPGRADE':      # (player, upgrade, allow): retail campaigns ban Tech2/3 with 0
            (self.banned_ups.discard if a[2] else self.banned_ups.add)((a[0], str(a[1]).lower()))
        elif name == 'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER':
            b = self.body(a[0])
            if b:
                self.used.add('health of the dead')
                if b.alive:                     # whole percent, rounded down (engine_garrison hp: 200 of 3000 reads 6)
                    self.counters[a[1]] = math.floor(b.health + 1e-6)
                elif b.died_at == self.t and not b.deleted:
                    # killed by a script earlier this frame: it is still there, at 0 (a NAMED_DELETE leaves the last
                    # value: engine_immortal b, bench 11-09, health 1 beside gone 1)
                    self.counters[a[1]] = 0
                # dead before this frame (a weapon's kill lands after the frame's scripts): the counter keeps the last
                # value read (bench 11-09 pend_scripts9 rel: 12 to the end, the tank gone on the minimap; engine_float,
                # engine_spawn, engine_super saw the same freeze)
        elif name == 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER':
            self.counters[a[2]] = sum(1 for b in self.living() if b.owner == a[1] and
                                      b.template.lower() == a[0].lower())
        elif name == 'SET_PLAYER_MONEY_TO_COUNTER':
            self.counters[a[1]] = int(self.money.get(a[0], 0))
        elif name == 'PLAYER_SET_MONEY':
            self.money[a[0]] = a[1]
        elif name == 'PLAYER_GIVE_MONEY':
            self.money[a[0]] = self.money.get(a[0], 0) + a[1]
        elif name == 'NAMED_GARRISON_SPECIFIC_BUILDING':
            b, g = self.body(a[0]), self.body(a[1])
            if b and g and self.garrison.spec(g) is not None:      # walks to it, in if it may (simgarrison; INFERRED)
                self.garrison.send(b, g)
            elif b and g:
                self.send(b, a[1])
        elif name == 'NAMED_GARRISON_SPECIFIC_BUILDING_INSTANTLY':      # (unit, building) engine_garrison: no
            self.garrison.put(self.body(a[0]), self.body(a[1]), script=True)    # relation, no room (garrison.md 1)
        elif name == 'NAMED_EXIT_BUILDING':      # (unit) engine_garrison base: out where the building stands
            self.garrison.out(self.body(a[0]))
        elif name == 'SET_MISSION_OBJECTIVE_STATUS':
            if a[1] not in (0, 1, 2, 3):                # script-semantics.md 8: only 0..3, any other does nothing
                return                                  # (inferred; checks/engine_scripts5.py goals O5 asks the bench)
            old = self.objectives.get(a[0], 0)
            self.objectives[a[0]] = a[1]
            if a[1] != old and a[1]:
                g = next((g for g in self.m.objectives if g.name == a[0]), None)
                title = self.text(g.title) if g else a[0]
                self.note('目标', f'{"奖励" if g and g.bonus else ""}目标{["", "亮出", "完成", "失败"][a[1]]}：{title}')
                self.change()
        elif name in ('LINK_MISSION_OBJECTIVE_TO_OBJECT', 'LINK_MISSION_OBJECTIVE_TO_WAYPOINT'):
            s = self.markers.setdefault(a[0], set())
            (s.add if a[2] else s.discard)(a[1])
        elif name == 'ALLOW_DISALLOW_ONE_BUILDING':     # the AI's production is not simulated; the player's 造 is
            (self.banned.discard if a[2] else self.banned.add)((a[0], str(a[1]).lower()))
        elif name == 'GIVE_PLAYER_UPGRADE':             # (player, upgrade): a PLAYER upgrade; an OBJECT one (the tiers)
                                                        # it gives unlocks nothing (bench 11-07 engine_tech b)
            self.player_ups.setdefault(a[0], set()).add(a[1])
        elif name == 'PLAYER_RELATES_PLAYER':           # (index, 0, name): the game reads the index (plan.relates)
            r = a[2]
            self.relations[(a[0], a[1])] = r if isinstance(r, str) else \
                {0: 'Enemy', 1: 'Neutral', 2: 'Friend'}[r[0]]
        elif name in ('PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'PLAYER_SET_PLAYER_POWER_POINTS', 'PLAYER_LOCK_PLAYER_TECH'):
            self.used.add('protocols')                  # (player, n) / (player, protocol, on): simtech.Book
            for book in self.books_of(a[0]):
                if name == 'PLAYER_SET_MAX_PLAYER_POWER_POINTS':
                    book.set_cap(a[1])
                elif name == 'PLAYER_SET_PLAYER_POWER_POINTS':
                    book.set_points(a[1])
                elif not book.lock(str(a[1]), bool(int(a[2]))):
                    self.gap(GAP_ACTION, name, f'{a[1]} 不是协议：游戏也不管')
        elif name in AI_SWITCHES:                       # (player, value): the skirmish AI's script switches; what
            self.ai_switches.setdefault(a[0], {})[name] = int(a[1])     # they do is simai's (engine line B)
        elif name in ('UNIT_AI_TRANSFER_ALL', 'SKIRMISH_AI_MAKE_BASE'):
            self.used.add('ai')
            if name == 'UNIT_AI_TRANSFER_ALL' and int(a[1]):
                self.off_teams((a[0],))
            if a[0] not in self.ai:
                self.ai[a[0]] = self.t
                self.note('AI', f'{self.who(a[0])} 交给遭遇战 AI（造兵、进攻不模拟）')
        elif name == 'MAP_SWITCH_BORDER':
            if self.reveal_all or self.reveals:
                self.used.add('border reveal')
            self.border = int(a[0])
            names = list(getattr(self.m.map, 'BORDERS', {}))
            self.note('边界', f'可玩区换成 {names[self.border] if self.border < len(names) else self.border}')
            self.change()
        elif name in ('MAP_REVEAL_ALL', 'MAP_REVEAL_ALL_PERM'):
            if a and a[0] != self.human and a[0] in self.players.values():   # another side's: its own sight
                self.revealed_to.add(a[0])
            else:
                self.reveal_all = True
                self.note('揭图', '全图')
        elif name == 'MAP_REVEAL_ALL_UNDO_PERM':
            if a and a[0] != self.human and a[0] in self.players.values():
                self.revealed_to.discard(a[0])
            else:
                self.reveal_all = False
                self.note('揭图', '全图收回')
        elif name in ('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', 'MAP_REVEAL_AT_WAYPOINT'):
            p = self.point(a[0])
            if p:
                if name == 'MAP_REVEAL_AT_WAYPOINT':
                    # docs/engine/vision.md 2 (bench 11-06 engine_vision resh*): it holds 15 x N - 13 frames
                    hold = max(0, int(round(self.reshroud * 15)) - 13)
                    self.peeks.append((p[0], p[1], float(a[1]), self.frame_now() + hold))
                else:
                    self.reveals[a[3]] = (p[0], p[1], float(a[1]))
                self.note('揭图', f'{a[0]} 半径 {a[1]:g}')
        elif name == 'MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT':
            # bench 11-09 engine_vision undo: back to fog at once (no reshroud delay), by the reveal's name
            self.reveals.pop(a[0], None)
        elif name == 'MAP_SHROUD_SET_RESHROUD_TIME':
            self.reshroud = float(a[0])
        elif name in ('MOVE_CAMERA_TO', 'MOVE_CAMERA_TO_NAMED', 'CAMERA_FOLLOW_NAMED'):
            p = self.point(a[0])
            if p:
                self.camera = p
                self.note('镜头', f'到 {a[0]}')
        elif name in ('DISABLE_INPUT', 'ENABLE_INPUT'):
            self.input = name == 'ENABLE_INPUT'
            self.note('过场', '交还控制' if self.input else '锁住操作')
        elif name == 'DISPLAY_COUNTDOWN_TIMER':
            if a[0] not in self.countdowns:
                self.countdowns.add(a[0])
                left = self.timers.get(a[0], self.t) - self.t
                self.note('倒计时', f'{self.text(a[1])} {mmss(max(0.0, left))}')
        elif name == 'HIDE_COUNTDOWN_TIMER':
            self.countdowns.discard(a[0])
        elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and self.body(a[0]) and self.body(a[0]).alive and \
                simunits.built(self.body(a[0]).template, a[1], self.own, self.body(a[0]).upgrades):
            # a factory's build button: queued there as the player's click (bench engine_production e); a banned unit
            # queued all the same and waits (g); refused where the player's click would be for the rest (can_build:
            # tier, a factory still unpacking -- INFERRED, not measured)
            f = self.body(a[0])
            tmpl = simunits.built(f.template, a[1], self.own, f.upgrades)
            if not self.order_build(f.owner, tmpl, factory=f, press=True):
                self.note('生产', f'{self.label(f)} 按 {a[1]}：现在造不了 {tmpl}')
        elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and \
                simunits.command_power(a[1], self.own) == UNPACK_POWER:
            # an MCV / a Japanese egg deploys at the point: drives there, then turns into its replacement (bench
            # engine_unpack mcv / egg: the yard stands on the point, the name passes on)
            b, p = self.body(a[0]), self.point(a[2])
            got = b and b.alive and p is not None and simunits.replace_self(b.template, a[1], self.own)
            if not got:
                self.note('技能', f'{a[0]} 按 {a[1]}：没有能展开的单位或路点')
            else:
                stand, into = got
                self.used.add('unpack')
                b.building, b.replace, b.goal, b.mode = (into, p, stand), True, None, 'move'
                self.note('技能', f'{self.label(b)} 去 {a[2]} 展开成 {into}')
                if not self.at_site(b, 0.0):
                    self.send(b, p)
        elif name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY'):
            b = self.body(a[0])
            if b and b.alive and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT':
                # bench 11-09 engine_scripts8b pfire / pdis: every script cast (the player-level one too, a second
                # one in the reload that hurts nobody) is seen by PLAYER_TRIGGERED_SPECIAL_POWER for one frame
                self.casts.append((self.frame_now(), b.owner, str(a[1]).lower(), b.name,
                                   self.point(a[2]) if len(a) > 2 else None))
            got = b and b.alive and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' and \
                simunits.assemble(b.template, a[1], self.own)
            p = self.point(a[2]) if got and got[1] else None
            if p is not None:                       # R5: he walks there and builds (the ice engineer's core)
                self.used.add('assemble')           # a script's cast heeds neither reload nor placing rules
                rules = simunits.power_rules(b.template, a[1], self.own)    # (bench engine_skill a-c, w); it
                if rules and rules['reload']:                               # starts the reload all the same
                    b.ready_at[a[1]] = self.frame_now() + rules['reload']   # (RA3 1.13 0x7dea80, read)
                b.building, b.goal, b.mode = (got[1], p, got[0]), None, 'move'
                self.note('技能', f'{self.label(b)} 去 {a[2]} 造 {got[1]}')
                if not self.at_site(b, 0.0):
                    self.send(b, p)
            else:
                self.used.add('special power')
                self.note('技能', f'{a[0]} 用 {a[1]}' + (f' 打 {a[2]}' if len(a) > 2 else ''))
                q = self.point(a[2]) if len(a) > 2 and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' else None
                rules = simunits.power_rules(b.template, a[1], self.own) if b and b.alive else None
                # bench 11-09 engine_scripts8b pdis: a second script cast ~20 s after the first (the collider's
                # reload, set by that cast, not over) is seen as triggered but hurts nobody; the first cast of a
                # collider never cast went though its power was not charged (engine_super p / q). INFERRED: a cast
                # in the reload a cast started brings no blast
                cooling = bool(b and b.alive and b.ready_at.get(a[1], 0) > self.frame_now())
                if rules and rules['reload']:       # every cast starts the reload anew (RA3 1.13 0x7dea80, read;
                    b.ready_at[a[1]] = self.frame_now() + rules['reload'] + RELOAD_LAG.get(a[1], 0)   # SDK GlobalData)
                hits = SUPERWEAPON_HITS.get(a[1]) if b and b.alive else None
                if hits and q is not None and cooling:
                    self.used.add('superweapon')
                    self.note('技能', f'{self.label(b)} 的 {a[1]} 还在重装：没打出来')
                elif hits and q is not None:       # a script's cast fires though the power is not ready
                    self.used.add('superweapon')
                    now = self.frame_now()
                    for after, table in hits:
                        self.blasts.append((now + after, q[0], q[1], table, b.owner, b))
                if a[1] in CURTAIN and q is not None and b and b.alive:
                    self.used.add('superweapon')
                    reach, lasts, kinds = CURTAIN[a[1]]
                    for t in self.living():
                        # the reach to the object's bounding circle (bench engine_super o: a tank 807 off covered,
                        # 832 not; 800 + its 23.3 radius -- INFERRED, R8's measure)
                        if (kinds is None or t.kinds & kinds) and \
                                math.hypot(t.x - q[0], t.y - q[1]) - t.radius <= reach:
                            t.immune_until = self.frame_now() + lasts
                if b and b.alive and not ((hits or a[1] in CURTAIN) and q is not None):
                    self.gap(GAP_ACTION, refined(name, a), f'{a[1]} 只记进时间线（special power），没有效果')
        elif name in ('ENABLE_SCRIPT', 'DISABLE_SCRIPT'):
            # a once-script that fired is only switched off: ENABLE_SCRIPT arms it again (SE enableScript)
            if name == 'ENABLE_SCRIPT':
                self.disabled.discard(a[0])
                self.done.discard(a[0])
            else:
                self.disabled.add(a[0])
        elif name in SHOWN:
            text = self.text(a[0]) if isinstance(a[0], str) else str(a[0])
            self.note(SHOWN[name], text)
            if name == 'SHOW_MILITARY_CAPTION':
                self.show_caption(text, a[1])
            elif name == 'PLAY_SOUND_EFFECT' and a[0] in self.mm.subtitles:
                self.show_subtitle(self.text(self.mm.subtitles[a[0]]))
        elif name in IGNORED or name == 'CAMERA_STOP_FOLLOW':
            pass
        else:
            self.unknown[name] = self.unknown.get(name, 0) + 1
            self.gap(GAP_ACTION, refined(name, a), 'Sim.act 不认识：没效果')

    def text(self, key):
        return self.mm.strings.get(key, key)

    def who(self, player):
        if player == self.human:
            return '玩家'
        side = next((s for s, p in self.players.items() if p == player), player)
        return {'s1': '敌人'}.get(side, side)

    def end(self, how, script):
        """The rest of the frame's scripts still run (Generals' VICTORY: the scripts stop from the next frame; RA3's
        flag, unknown): a second ending in the same frame is a warning -- the game may take either."""
        if self.ending is None:
            self.ending = (how, self.t, script.name)
            self.note('结局', f'{how}（{script.name}）')
        elif self.ending[1] == self.t and self.ending[0] != how:
            self.both = (self.ending, (how, self.t, script.name))
            self.note('警告', f'同一帧里又{how}了（{script.name}）：赢和输都满足，游戏里算哪个要实测')
            self.used.add('both endings')

    # ---- the player's script
    def pick(self, who):
        """The bodies a script event names."""
        who = who.strip()
        if who.startswith('名字含 '):
            part = who[4:].strip()
            return [b for b in self.living() if part in b.name]
        if who.startswith('队 '):                    # a team's living members ('player/team' or the bare name)
            return self.members(who[2:].strip())
        if who.startswith('敌人 在 '):
            p = self.point(who[5:].strip())
            sites = getattr(self.m.map, 'SITES', {})
            r = sites[who[5:].strip()].r if who[5:].strip() in sites and sites[who[5:].strip()].r else 400.0
            return [b for b in self.living() if p and self.enemy(self.human, b.owner) and not b.scenery
                    and math.hypot(b.x - p[0], b.y - p[1]) <= r]
        names = [self.m.cast[who].name] if who in self.m.cast else \
            [r.name for k, r in self.m.cast.items() if re.fullmatch(re.escape(who) + r' \d+', k)]
        if not names and who in self.bodies:
            names = [who]
        out = [self.bodies[n] for n in names if n in self.bodies]
        if not out:
            self.note('剧本', f'找不到 {who}（还没出现，或者不是角色、物体名）')
        return out

    def happen(self, e):
        t, verb, *rest = e
        self.note('剧本', ' '.join([verb] + [str(x) for x in rest]))
        if verb == '派':
            who, where = rest
            for b in self.pick(who):                # the player's units go attack-moving, fighting on the way: one
                self.order_move(b, where, True)     # unit's order as ATTACK_MOVE_NAMED_UNIT_TO (its goal off held spots)
        elif verb == '走':
            who, where = rest
            self.order_group(self.pick(who), where, False)  # as MOVE_NAMED_UNIT_TO; several at once, a group move
        elif verb == '攻击':
            who, target = rest                      # an attack order on a thing (NAMED_ATTACK_NAMED): units take no building by themselves
            targets = self.pick(target)
            if targets:
                for b in self.pick(who):
                    self.order_attack(b, targets[0].name)
        elif verb in ('摧毁', '删除'):
            for b in self.pick(rest[0]):
                if verb == '摧毁' and 'UNATTACKABLE' in b.status:
                    self.note('剧本', f'{self.label(b)} 打不动（UNATTACKABLE），没摧毁')
                    continue
                b.last_hit, b.last_by = self.human, None
                self.destroy(b, '剧本', delete=verb == '删除')
        elif verb == '血量':
            for b in self.pick(rest[0]):
                b.health = float(rest[1])
                b.last_hit, b.last_by = self.human, None
        elif verb == '买':                          # the player buys a protocol (simtech.Book.buy: points, not locked)
            book = self.books.get(self.human)
            if book and book.buy(rest[0], self.frame_now()):
                self.note('协议', f'玩家买了 {rest[0]}（剩 {book.points} 点）')
                self.change()
            else:
                self.note('剧本', f'买不了 {rest[0]}' + (f'（{book.points} 点）' if book else '（玩家没有协议）'))
        elif verb == '打':
            for b in self.pick(rest[0]):
                b.last_hit, b.last_by = self.human, None
        elif verb == '放':
            who, ability, where = rest              # a ground power of the player's (order_power): `放 engineer freeze 在 inside 1`
            p = self.point(where)
            for b in self.pick(who):
                u = next((u for u in self.mm.units if u.id == b.template), None)
                if p is None:
                    self.note('剧本', f'找不到地点 {where}')
                else:
                    self.order_power(b, (u.abilities.get(ability) if u else None) or ability, p)
        elif verb == '占领' and len(rest) == 2:
            targets = self.pick(rest[1])            # the player's order: the engineer goes and takes it (capture_due)
            if targets:
                for b in self.pick(rest[0]):
                    self.order_capture(b, targets[0].name)
        elif verb == '占领':
            for b in self.pick(rest[0]):
                b.owner = self.human
        elif verb == '旗标':
            self.flags[rest[0]] = int(rest[1])
        elif verb == '生产':                         # the player's build order at a named factory: paid as it builds, the
            what, where = rest                      # build time, out at the factory's door (order_build / produce_due)
            tmpl = next((u.id for u in self.mm.units if u.id == what), None) or \
                next((r.template for k, r in self.m.cast.items() if k == what), what)
            f = next(iter(self.pick(where)), None)
            if f is None:
                self.note('剧本', f'找不到工厂 {where}')
            elif not self.order_build(self.human, tmpl, factory=f):
                self.note('剧本', f'{self.label(f)} 现在造不了 {tmpl}（不是玩家的、不造它、科技或禁造）')
        elif verb == '造':
            what, where, angle = rest
            tmpl = next((u.id for u in self.mm.units if u.id == what), None) or \
                next((r.template for k, r in self.m.cast.items() if k == what), what)
            p = self.point(where)
            if p is None and self.point(f'{where} {angle:g}'):    # 'inside 2': the number was the site's
                where, angle = f'{where} {angle:g}', 0.0
                p = self.point(where)
            if (self.human, tmpl.lower()) in self.banned:
                self.note('剧本', f'{tmpl} 现在不许造（禁造），没造出来')
            elif p is None:
                self.note('剧本', f'找不到地点 {where}')
            else:
                b = self.add(f'UNIT - SIM Made {len(self.bodies)}', tmpl, self.human, *p, by='剧本', at=self.t)
                b.angle = angle
                if self.blocks(b):
                    self.reblock()
        self.change()

    # ---- running
    def step(self):
        """One DT tick from self.t (the caller moves self.t on). With the engine model: the tick's frames (those
        before self.t + DT, 7 or 8), the run script's events at the first frame at or after their second, a check's
        counters read on each whole second's frame. Default movement and acquisition run
        after the tick's first frame. The opt-in shot_clock integrates movement each frame:
        suppression controls ceil(145 / speed * 15) = 44 (50), 40 (55)."""
        if self.eng is None:
            return self.step_old()
        t0, eng = self.t, self.eng
        last = math.ceil(round((t0 + DT) * self.fps, 6))
        moved = False
        while eng.frame < last and self.ending is None:
            self.t = eng.frame / self.fps
            self.release()
            while self.events and self.events[0][0] <= self.t + 1e-9:
                self.happen(self.events.pop(0))
            self.tech_due(eng.frame + 1)        # before the frame's scripts (bench 11-08 engine_protocol rank: rank
            eng.step()                          # 2 read by the scripts of frame 5400 = 360 s x 15)
            if self.handed:                     # the container's Lib_Skirmish_Setup, after the first frame's scripts
                self.off_teams(self.handed)
                self.handed = ()
            self.autoheal(eng.frame)
            self.suppression_tick()
            self.flee_due(eng.frame)
            self.expire(eng.frame)
            self.garrison.due()
            if self.frame_movers:
                self.move(1.0 / self.fps, precise=True)
            self.build_due(eng.frame)
            self.blast_due(eng.frame)
            self.death_blast_due(eng.frame)
            self.sweeps.due(eng.frame)
            self.deposit_due(eng.frame)
            self.mine_due(eng.frame)
            self.produce_due(eng.frame)
            if self.test and self.test.counters and (eng.frame - 1) % self.fps == 0 and self.t >= LAG:
                self.series.append((int(round(self.t - LAG)), [self.counters.get(c, 0) for c, _ in self.test.counters]))
            if not moved and self.ending is None and self.t >= t0 - 1e-9:
                moved = True
                self.aura_tick()
                if self.combat:
                    self.fight()
                if not self.shot_clock:
                    self.move()
            if self.shot_clock:
                self.move(1.0 / self.fps)
            if self.combat and self.ending is None:
                self.deal(1.0 / self.fps)       # R6: the aimed fire frame by frame, after the frame's scripts
        self.t = t0

    FLEE_GONE = 3

    def flee_start(self, b):
        """RunOffMapBehavior (simunits.run_off_map; engine line C round 8, engine_runoffmap a-d, bench 11-06): from the
        order's frame the body walks straight to the waypoint named `RunOffMap` (none: 1000 along its facing), at its
        speed, carrying FLEE_OFF_MAP, and FLEE_GONE frames after it arrives it is removed without a death (not dying).
        The counting scripts' frames give 64064 / 304304 and the 15 frames in the end's area at lag 0, gone 3 (a grid
        of lag 0-4 x gone 0-5 had that one fit). Not modelled: the path (a straight line),
        a way that cannot be walked, flying off."""
        name = simunits.run_off_map(b.template, self.own)
        if name is None or not b.alive or b.speed <= 0:
            return
        goal = self.waypoints.get(name or 'RunOffMap')
        if goal is None:
            goal = (b.x + 1000.0 * math.cos(b.angle), b.y + 1000.0 * math.sin(b.angle))
        d = math.hypot(goal[0] - b.x, goal[1] - b.y)
        b.flee = (self.frame_now(), b.x, b.y, goal[0], goal[1], d, b.speed / simunits.LIFE_FPS)
        b.path, b.goal, b.mode, b.move_to = [], None, 'idle', None
        b.script_status.add('FLEE_OFF_MAP')
        self.modify(b)
        self.used.add('flee off map')
        self.change()

    def flee_due(self, frame):
        """One frame of every runner: its place on the straight line, the removal when its time comes."""
        for b in self.living():
            f = getattr(b, 'flee', None)
            if not f:
                continue
            f0, x0, y0, x1, y1, d, step = f
            k = frame - f0
            walked = min(d, max(0, k) * step) / d if d else 1.0
            b.x, b.y = x0 + (x1 - x0) * walked, y0 + (y1 - y0) * walked
            if walked >= 1.0 and k - math.ceil(d / step - 1e-9) >= self.FLEE_GONE:
                b.flee = None
                self.destroy(b, '逃出地图', delete=True)
            else:
                self.change()

    def autoheal(self, frame):
        """AutoHealBehavior (simunits.autoheal; engine line C round 7, engine_heal a / b): a hurt body (health below
        what it was last frame) is mended `amount` every `every` frames, the first `wait` frames after the latest hurt;
        full health stops it. The state- and rank-gated ones are not modelled."""
        cache = self.__dict__.setdefault('_heal_of', {})
        for b in self.bodies.values():
            if not b.alive:
                continue
            if b.template not in cache:
                cache[b.template] = simunits.autoheal(b.template, self.own)
            rule = cache[b.template]
            if not rule or not rule[0]:
                continue
            amount, every, wait = rule
            seen = getattr(b, 'heal_seen', None)
            if seen is not None and b.hp < seen - 1e-9:
                b.heal_at = frame + max(wait, 1)
            if b.hp < b.max_hp - 1e-9:
                if getattr(b, 'heal_at', None) is None:
                    b.heal_at = frame + every
                if frame >= b.heal_at:
                    b.hp = min(b.max_hp, b.hp + amount)
                    b.heal_at = frame + every
            else:
                b.heal_at = None
            b.heal_seen = b.hp
            self.used.add('autoheal')

    def release(self):
        """The script events anchored to a flag that is up now: due `delta` after this moment."""
        for e in list(self.anchored):
            if self.flags.get(e[0][1]) == 1:
                self.anchored.remove(e)
                self.events.append((round(self.t + e[0][2], 6),) + tuple(e[1:]))
                self.events.sort(key=lambda x: x[0])

    def step_old(self):
        self.release()
        while self.events and self.events[0][0] <= self.t:
            self.happen(self.events.pop(0))
        for s in self.mm.scripts:
            if s.name in self.done or s.name in self.disabled or not s.levels[self.level]:
                continue
            if all(self.holds(c) for c in s.when):
                for name, *a in s.do:
                    self.act(name, a, s)
                if s.once:
                    self.done.add(s.name)
        self.expire(self.frame_now())
        self.garrison.due()
        self.suppression_tick()
        self.build_due(self.frame_now())
        self.deposit_due(self.frame_now())
        self.mine_due(self.frame_now())
        self.produce_due(self.frame_now())
        self.tech_due(self.frame_now())
        if self.ending:
            return
        self.aura_tick()
        if self.combat:
            self.fight()
        self.move()

    def can_hit(self, w, t):
        """A weapon's anti mask against a target: aircraft need ANTI_AIRBORNE, buildings ANTI_STRUCTURE (or
        ground), the rest ground or water. A weapon that does nothing to the target's armour (its damage type at 0 %:
        Tanya's pistol, SNIPER, at every faction building) cannot take it at all, ordered or not (Generals
        WeaponSet::getAbleToUseWeaponAgainstTarget: estimateWeaponDamage 0 -> ATTACKRESULT_INVALID_SHOT; the a6
        Tanya who stood firing at a building, 2026-11-08)."""
        if simunits.percent(t.armor, w['type']) <= 0:
            return False
        anti = w['anti']
        if not anti:
            return True
        if t.surface == 'air':
            return any(a.startswith('ANTI_AIRBORNE') for a in anti)
        if 'STRUCTURE' in t.kinds:
            return 'ANTI_STRUCTURE' in anti or 'ANTI_GROUND' in anti
        return 'ANTI_GROUND' in anti or 'ANTI_WATER' in anti

    def takes_by_itself(self, a, t):
        """Whether `a` may take `t` with no order naming it (idle, firing on a plain move, attack-moving, going after:
        Generals AIUpdateInterface::getNextMoodTarget -> AI::findClosestEnemy, every such path): never a structure
        (PartitionFilterRejectBuildings) unless `a` is ATTACK_BUILDINGS or `t` a base defence (FS_BASE_DEFENSE; a
        garrisoned building that can fire is the other exception, not modelled: no garrisons here), never a
        NOT_AUTOACQUIRABLE one (INFERRED by its name). Bench 2026-11-08 engine_seal: the player's idle peacekeeper
        leaves the enemy's bunkers alone (erow), the enemy's (a computer player's: Generals would let it take
        buildings) idle and attack-moving past leaves the player's bunker and plant alone (ebld / ebldam) -- RA3 drops
        Generals' computer exception; the a4 ice nobody shoots (2026-10-28) is the same rule. An order naming the
        target (`a.goal`) is not filtered here. A side run by the skirmish AI (`self.ai`, woken) keeps Generals'
        exception and takes buildings (INFERRED: the bench's s1 had no AI; a skirmish AI's attack does pull down
        buildings -- tests/test_simai)."""
        if 'NOT_AUTOACQUIRABLE' in t.kinds:
            return False
        if 'STRUCTURE' in t.kinds:
            return ('ATTACK_BUILDINGS' in a.acquire or 'FS_BASE_DEFENSE' in t.kinds
                    or a.owner in getattr(self, 'ai', ()))
        return True

    def auto_acquires(self, a):
        """Whether `a` takes targets by itself now: an attack-mover always; idle or on a plain move (Generals'
        calledDuringIdle: the idle state and the turret's scan) only with AutoAcquireEnemiesWhenIdle YES."""
        return a.mode == 'attack' or 'YES' in a.acquire

    def shot_blocked(self, a, t, w):
        """Line of fire (docs/engine/pathing.md 7c; bench 2026-11-08 engine_seal idle / row / cut): a weapon with
        ATTACK_NEEDS_LINE_OF_SIGHT in its Flags (simunits `los`: the peacekeeper's shotgun, tank cannons, the IFV's
        missiles; not the Athena's lob) does not shoot through a structure's footprint, whoever owns it; terrain in
        between does not stop it. Generals Pathfinder::isAttackViewBlockedByObstacle walks the pathfinding cells along
        the line: an obstacle cell blocks unless it is the shooter's own, the target's, or one the shooter or the
        target stands inside (its container; a target within another's bounds). Here the footprints are `blocks`'s
        shapes and the line is tested against them exactly (INFERRED: the cell walk, not read in RA3's program).
        A target in the air is never blocked (bench 2026-11-08 engine_seal aa / aaopen: an IFV's missiles at a
        Twinblade over the player's row the same as with no row)."""
        if not w.get('los') or t.surface == 'air':
            return False
        return self.line_blocked(a.x, a.y, t, a)

    def line_blocked(self, x, y, t, a=None):
        """A structure's footprint on the line from (x, y) to t (shot_blocked's test from any point)."""
        if getattr(self, '_fire_obstacles', None) is None:
            self._fire_obstacles = [(b, s) for b in self.living() for s in (self.blocks(b),) if s]
        for b, s in self._fire_obstacles:
            if b is a or b is t or _in_shape(s, x, y) or _in_shape(s, t.x, t.y):
                continue
            if _line_hits(s, x, y, t.x, t.y):
                return True
        return False

    def fire_spot(self, a, t):
        """Where an attacker told to attack t goes when every weapon of its that can hit t has its line blocked (bench
        2026-11-08 engine_seal attack: a peacekeeper ordered onto an MCV behind the player's row walks round the
        row's north end and fires from there, s10; the row's far side never reached). Generals AIAttackState asks
        Pathfinder::findAttackPath for a cell in range with a clear view. Here: points on rings round t inside its
        longest such weapon's reach, the line clear and a way there, the shortest way taken (INFERRED: rings, 10
        degree steps; a tie goes north). None: no such point."""
        ws = [w for w in a.weapons if self.can_hit(w, t) and w.get('los')]
        if not ws or t.surface == 'air':
            return None
        far = max(w['range'] for w in ws) + a.radius + t.radius - 1.0
        cands = []
        for f in (1.0, 0.8, 0.6, 0.4):
            r = max(far * f, t.radius + a.radius + 1.0)
            for k in range(36):
                x, y = t.x + r * math.cos(math.radians(10 * k)), t.y + r * math.sin(math.radians(10 * k))
                if not self.line_blocked(x, y, t, a) and \
                        not any(b is not t and _in_shape(sh, x, y) for b, sh in self._fire_obstacles):
                    cands.append((math.hypot(x - a.x, y - a.y), -y, x, y))
        best = None
        for _, _, x, y in sorted(cands)[:12]:
            way = self.ground.route(a.surface, (a.x, a.y), (x, y))
            if way is None:
                continue
            n = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip([(a.x, a.y)] + way[:-1], way))
            if best is None or (round(n / 10.0), -y) < best[0]:
                best = ((round(n / 10.0), -y), (x, y))
        return best and best[1]

    def on_map(self, b):
        """Within the active border (MAP_SWITCH_BORDER). Bench 2026-11-09 engine_scripts4 border: while the border is
        the west half, a Guardian pair across its edge (ours inside, theirs 60 outside) and a pair both outside hold
        their fire, a pair inside fights; the border opened, both pairs fight at once. An object off the border is
        neither a shooter nor a target (the Generals source marks it OFF_MAP); it lives on and the area conditions
        see it. Taken by its centre (INFERRED: the pairs stood well clear of the edge)."""
        if not self.border:
            return True
        rect = list(getattr(self.m.map, 'BORDERS', {}).values())
        if self.border >= len(rect):
            return True
        x0, y0, x1, y1 = rect[self.border]
        return x0 <= b.x <= x1 and y0 <= b.y <= y1

    def fight(self):
        """One tick of the fight model (未对齐, docs: the 'combat' align entry): every armed body fires each of its
        weapons at the nearest enemy in that weapon's range it can hit (its NAMED_ATTACK target first, when in
        range); the damage rate = the weapon's damage per second x the target's armour percent for its damage type;
        an attack-mover with an enemy in range holds while it fights; a plain move goes on firing; an idle unit goes
        after an enemy within its sight and comes back (`idle_chase`, R8). The reach is measured between the bounding
        circles (`in_range`, R8). The aim is taken once a tick; the damage is dealt frame by frame (`deal`, R6)."""
        self.seen = {}
        self.firing = []
        self.volleys = []
        self.chilling = []
        self._fire_obstacles = None             # `shot_blocked`'s footprints, taken once a tick when first asked
        live = [b for b in self.living() if not b.scenery and self.on_map(b)]     # off the border: out of the fight
        armed = [b for b in live if b.weapons and 'NO_ATTACK' not in b.status    # NO_ATTACK: holds its fire
                 and not self.unpowered(b) and not (b.hold_fire and not isinstance(b.goal, Body))]
        cloaked = self.cloaked(live)
        targets = [b for b in live if 'UNATTACKABLE' not in b.status and id(b) not in cloaked]
        if not armed or not targets:
            return
        aimable = {id(t) for t in targets}
        tx = np.array([b.x for b in targets])
        ty = np.array([b.y for b in targets])
        for a in armed:                         # an attack on a team goes on to its next member (TEAM_ATTACK_TEAM)
            if id(a) in self.team_targets and not (isinstance(a.goal, Body) and a.goal.alive):
                them = self.members(self.team_targets[id(a)])
                if them:
                    self.order_attack(a, min(them, key=lambda t: math.hypot(t.x - a.x, t.y - a.y)).name)
                else:
                    del self.team_targets[id(a)]
        for a in armed:
            a.engaged = False
            if self.held_up(a):                 # stopped short on a plain move: still moving (DEMO_KILL)
                continue
            foes =[k for k, t in enumerate(targets) if t is not a and self.hostile(a, t)]
            if not foes:
                self.idle_chase(a, False, [])
                continue
            idx = np.array(foes)
            d = np.hypot(tx[idx] - a.x, ty[idx] - a.y)
            pad = max(targets[k].radius for k in foes)          # the biggest foe's radius: the scan's cut-off (R8)
            fired = False
            for w in a.weapons:
                order = np.argsort(d, kind='stable')    # ties (two foes made on one point) by list order: the
                pick = None                              # default quicksort broke them by the array's length (a4 r121)
                if isinstance(a.goal, Body) and a.goal.alive and id(a.goal) in aimable and \
                        self.in_range(a, a.goal, w) and self.can_hit(w, a.goal) and \
                        self.side_sees(a.owner, a.goal) and not self.shot_blocked(a, a.goal, w):
                    pick = a.goal
                elif self.auto_acquires(a):
                    for j in order:
                        if d[j] - a.radius - pad > w['range']:      # sorted by centre: nobody nearer after this
                            break
                        t = targets[idx[j]]
                        if not self.in_range(a, t, w, d[j]):
                            continue
                        if t.template in self.unshot or not self.takes_by_itself(a, t) or \
                                'NON_AUTOACQUIRABLE' in t.status:
                            continue                # a building / our ice: only when ordered (takes_by_itself)
                        if self.can_hit(w, t) and self.side_sees(a.owner, t) and not self.shot_blocked(a, t, w):
                            pick = t
                            break
                if pick is None:
                    continue
                if a.vision and w['range'] > a.vision:
                    a.fired_at = self.t                 # a bombarder firing shows itself
                for effect in w.get('unmodeled_effects', []):
                    self.gap(GAP_WEAPON, effect, '武器第1轮尚未解释此效果的筛选、几何或时序')
                if not self.shot_clock and (w.get('hit_modifiers') or w.get('line') or w.get('strip_max_health') or w.get('emp_seconds')
                                           or w.get('sweep')):
                    self.gap(GAP_WEAPON, 'weapon effects', '逐发武器效果仅在离散命中时钟中模拟')
                if w['dps'] or w.get('suppression'):
                    if 'sched' in w and self.shot_clock:
                        self.volleys.append((pick, w, a))
                    else:
                        # Continuous DPS has no individual hit events. Do not run a second
                        # clip clock just for pressure (A4 guardians falsely suppressed at F1980).
                        if w.get('suppression'):
                            self.gap(GAP_WEAPON, 'SuppressionNugget',
                                     '连续DPS没有逐发命中事件；压制贡献仅在离散命中时钟中模拟')
                        self.firing.append((pick, w['dps'] * a.dealt * (1.0 if w['type'] == 'UNRESISTABLE' else
                                            simunits.percent(pick.armor, w['type']) / 100.0 * pick.taken), a))
                if w.get('sdps'):
                    self.chilling.append((pick, w['sdps'] * a.dealt, a))
                fired = True
                if a.mode == 'attack':
                    a.engaged = True
            g = a.goal
            if not fired and isinstance(g, Body) and g.alive and not a.path and id(g) in aimable and \
                    (a.spot is None or a.spot[0] != id(g) or math.hypot(g.x - a.spot[1], g.y - a.spot[2]) > 150) and \
                    any(self.can_hit(w, g) and self.shot_blocked(a, g, w) for w in a.weapons) and \
                    not any(self.can_hit(w, g) and self.in_range(a, g, w) and not self.shot_blocked(a, g, w)
                            for w in a.weapons):
                a.spot = (id(g), g.x, g.y)          # told to attack, the line blocked: round to a clear spot
                p = self.fire_spot(a, g)
                if p is not None:
                    self.note('绕位', f'{self.label(a)} 打不着 {self.label(g)}（中间有建筑），绕到 ({p[0]:.0f},{p[1]:.0f})')
                    self.send(a, p)
            self.idle_chase(a, fired, [(d[j], targets[idx[j]]) for j in np.argsort(d, kind='stable')])
        if self.firing or self.volleys:
            self.used.add('combat')
        if self.chilling:
            self.used.add('freeze')
        if self.eng is None:                    # no frames: the tick's damage at once
            self.deal(DT)

    def cloaked(self, live):
        """ids of the bodies an InvisibilityBroadcastUpdate hides this tick (simunits.invis_broadcast; engine line C
        round 9, engine_stealth a / b, bench 11-05, docs/engine/stealth.md 1-2): a broadcaster carrying the status its
        ObjectStatusValidation wants (the mirage tank: GENERIC_TOGGLE_STATE, which a script gives) hides what its filter
        takes within BroadcastRange, centre to centre (relation, KindOf, status exclusions; not itself unless AffectsSelf).
        A hidden body is no target for the other side while the aura holds -- an attack order on it stays, fire starts
        the moment it shows and stops the moment it hides (bench 开关血 / 后隐血). Taken every tick, not on the
        UpdatePeriod (0.2 s, finer than the tick; the entry's own lifetime not read). Not modelled: a detector's
        reveal (StealthDetectorUpdate, ~6 s in on the bench), the garrison's stealth template."""
        cache = self.__dict__.setdefault('_invis', {})
        out = set()
        for e in live:
            if e.template not in cache:
                cache[e.template] = simunits.invis_broadcast(e.template, self.own)
            r = cache[e.template]
            if not r or not r['needs'] <= e.status:
                continue
            for t in live:
                if (t is e and not r['self']) or t.scenery or (r['include'] and not r['include'] & t.kinds) \
                        or r['exclude'] & t.status or self.relation(e.owner, t.owner) not in r['relation']:
                    continue
                if math.hypot(t.x - e.x, t.y - e.y) <= r['range']:
                    out.add(id(t))
        if out:
            self.used.add('stealth')
        return out

    def idle_chase(self, a, fired, near):
        """R8, bench 2026-11-07 engine_acquire (a Guardian, weapon 150, VisionRange 200, both tanks radius 23.3): an
        idle unit fires where it stands at 180 (centre to centre); at 200 and 220 it walks up, fires, and once its
        target is done walks back to where it stood (within 15); at 240 and beyond, nothing -- likewise when guarding
        (260) or attack-moving past (260 / 400). Read as: an idle unit takes the nearest enemy it can hit and its side
        sees, when the centre distance less the target's radius is within its own VisionRange (220 < limit < 240:
        200 + 23.3; INFERRED, the scan itself not read), walks to `reach` of it, and goes home when it has none left.
        Idle = not building, no goal, no way of its own (a way this rule gave it does not count); any order since
        (another way) drops the chase and the home. `near`: [(centre distance, enemy)] nearest first."""
        mine = a.path and a.dest is not None and a.dest == a.auto_to
        if a.path and not mine:                 # an order of its own since: not idle, nothing of ours to keep
            a.chase = a.home = a.auto_to = None
            return
        if a.goal is not None or a.building or a.speed <= 0 or 'IMMOBILE' in a.status:
            return
        if a.home is not None and a.chase is None and not a.path:
            a.home = a.auto_to = None           # back home
        if fired:
            return
        sight = a.sight
        c = a.chase
        if c is not None and c.alive and self.side_sees(a.owner, c) and \
                math.hypot(c.x - a.x, c.y - a.y) - c.radius <= sight:
            if not a.path:                      # got there and it is still out of reach: after it again
                self.send(a, (c.x, c.y), reach=self.reach(a, c))
                a.auto_to = a.dest
            return
        a.chase = None
        if 'YES' not in a.acquire:              # AutoAcquireEnemiesWhenIdle NO / none: idle, it takes nothing
            near = []
        for dist, t in near:
            if dist - t.radius > sight:
                break                           # sorted by centre; a radius over 0 only cuts more
            if t.template in self.unshot or not self.takes_by_itself(a, t) or not self.side_sees(a.owner, t) or \
                    'NON_AUTOACQUIRABLE' in t.status:
                continue
            if not any(self.can_hit(w, t) and not self.shot_blocked(a, t, w) for w in a.weapons):
                continue                        # bench engine_seal row: a target behind a structure is not gone after
            if a.home is None:
                a.home = (a.x, a.y)
            a.chase = t
            self.used.add('acquire')
            self.send(a, (t.x, t.y), reach=self.reach(a, t))
            a.auto_to = a.dest
            return
        if a.home is not None and (a.path or math.hypot(a.home[0] - a.x, a.home[1] - a.y) > 1.0):
            if a.dest != a.home:
                self.send(a, a.home)
                a.auto_to = a.dest

    def deal(self, dt):
        """R6: `dt` seconds of the aimed fire (`fight`) from shooters and at targets still alive. With the engine model
        once a frame, after that frame's scripts (Generals GameLogic::update runs the script engine before the objects'
        updates): a script's health top-up (UNIT_SET_HEALTH every frame, the a4 checks' trucks) lands before the
        frame's damage, so only a frame's fire of the whole maximum kills (A4 win: bench 2026-11-07 against the 0.5 s
        tick that killed the trucks at 4:23). Bodies at 0 die, the last hit their killer's."""
        hurt = {}
        pending = self.__dict__.setdefault('projectile_hits', [])
        due = [hit for hit in pending if self.frame_now() >= hit[0]]
        pending[:] = [hit for hit in pending if self.frame_now() < hit[0]]
        for when, target, damage, attacker in due:
            if target.alive:
                h = hurt.setdefault(id(target), [target, 0.0, attacker])
                h[1] += damage
        for t, rate, by in self.firing:
            if t.alive and by.alive:
                h = hurt.setdefault(id(t), [t, 0.0, by])
                h[1] += rate * dt
                h[2] = by
        for t, w, by in self.volleys:           # engine line C round 2: a shot lands when its clock says (shots_due)
            if t.alive and by.alive:
                n = self.shots_due(by, w, dt)
                if n:
                    projectile = w.get('projectile')
                    if projectile:
                        speeds = self.__dict__.setdefault('projectile_speeds', {})
                        if projectile not in speeds:
                            try:
                                xml = simunits._xml(projectile, self.own)
                                update = next(simunits._blocks(xml or '', 'ProjectileUpdate'), ('', ''))
                                movement = next(simunits._blocks(update[1] or '', 'MoveInStraightLine'), ('', ''))
                                speeds[projectile] = (simunits._num(simunits._attr(movement[0], 'MuzzleVelocity'))
                                    if simunits._attr(update[0], 'StateMachine') == 'StraightLineProjectile' else 0)
                            except (OSError, ValueError):
                                speeds[projectile] = 0
                        speed = speeds[projectile]
                        complex_effect = any(w.get(k) for k in ('suppression', 'hit_modifiers', 'line', 'emp_seconds', 'strip_max_health'))
                        if speed > 0 and not complex_effect:
                            # GUESSED collision boundary, rechecked for the two probe distances: full
                            # distance steps before impact. No fitted per-distance delays.
                            frames = int(math.hypot(t.x - by.x, t.y - by.y) / speed)
                            armor = 1.0 if w['type'] == 'UNRESISTABLE' else simunits.percent(t.armor, w['type']) / 100 * t.taken
                            # GUESSED until dynamic-armor bench: snapshot scalars at launch.
                            damage = n * w['dmg'] * by.dealt * armor
                            if frames:
                                pending.append((self.frame_now() + frames, t, damage, by))
                            else:
                                h = hurt.setdefault(id(t), [t, 0.0, by])
                                h[1] += damage
                            continue
                        self.gap(GAP_WEAPON, 'ProjectileNugget', '仅无复合效果的直线弹飞行已建模；曲线弹/复合弹/自制弹体待核')
                    for radius, value, seconds in w.get('suppression', []):
                        for target in self.living():
                            if target.suppression_rule and math.hypot(target.x - t.x, target.y - t.y) <= radius:
                                target.suppression_hits.append((self.frame_now() + simunits._frames(seconds), n * value))
                    for seconds in w.get('emp_seconds', []):
                        deadlines = self.__dict__.setdefault('emp_until', {})
                        deadlines[id(t)] = max(deadlines.get(id(t), 0), self.frame_now() + simunits._frames(seconds))
                    if w.get('sweep'):
                        self.sweeps.fire(by, t, w['sweep'])
                    victims = [t]
                    # GUESSED edge geometry: circle extent; round 1 centres avoid edges.
                    line = w.get('line')
                    if line and line['dynamic']:
                        dx, dy = t.x - by.x, t.y - by.y
                        length = math.hypot(dx, dy)
                        if length:
                            ux, uy = dx / length, dy / length
                            victims = []
                            for candidate in self.living():
                                if candidate is by or not self.hostile(by, candidate) or not self.can_hit(w, candidate):
                                    continue
                                cx, cy = candidate.x - by.x, candidate.y - by.y
                                along, across = cx * ux + cy * uy, abs(cx * uy - cy * ux)
                                if -line['lead'] <= along <= length + line['out'] and across <= line['width'] / 2 + candidate.radius:
                                    victims.append(candidate)
                    for victim in victims:
                        h = hurt.setdefault(id(victim), [victim, 0.0, by])
                        armor = 1.0 if w['type'] == 'UNRESISTABLE' else simunits.percent(victim.armor, w['type']) / 100.0 * victim.taken
                        h[1] += n * w['dmg'] * by.dealt * armor
                        for fraction, damage_type in w.get('strip_max_health', []):
                            scalar = 1.0 if damage_type == 'UNRESISTABLE' else simunits.percent(victim.armor, damage_type) / 100 * victim.taken
                            h[1] += n * victim.max_hp * fraction * by.dealt * scalar
                        h[2] = by
                    for mid in w.get('hit_modifiers', []):
                        xml = self.xml_of(by.template)
                        modifier = simunits.modifier(xml, mid)
                        if modifier and modifier['frames'] is not None:
                            t.auras_on[mid] = (self.frame_now() + modifier['frames'], xml)
                            self.modify(t)
                        else:
                            self.gap(GAP_WEAPON, mid, '命中修正未找到或缺少已解释的Duration')
        for t, dmg, by in hurt.values():
            if self.frame_now() < t.immune_until or t.shielded or t.indestructible:
                continue
            t.damage(dmg)
            t.last_hit, t.last_by = by.owner, by.name
            if t.hp <= 0 and t.alive:
                if self.first_death is None:
                    self.first_death = (self.t, t, by)
                self.destroy(t, f'被 {self.label(by)} 打掉')
        self.chill(dt)

    def suppression_tick(self):
        """Suppressability is inclusive: bench24x2=48 normal,25x2=50 suppressed.

        UNCONFIRMED timing: per-hit DurationSeconds expiry and UpdateDelay phase.
        Short1s contributions / late recovery56 are not explained by this model.
        INFERRED: each above-threshold sample refreshes SuppressionDuration.
        SUPPRESSED is a model condition; do not invent a script object status.
        """
        now = self.frame_now()
        for b in self.living():
            rule = b.suppression_rule
            if not rule:
                continue
            b.suppression_hits[:] = [(end, v) for end, v in b.suppression_hits if now < end]
            before = now - 1 < b.suppressed_until
            if now >= b.suppression_next:
                b.suppression_next = now + rule['every']
                if sum(v for _, v in b.suppression_hits) >= rule['threshold']:
                    b.suppressed_until = now + rule['duration']
            if before or now < b.suppressed_until:
                self.modify(b)

    def shots_due(self, b, w, dt):
        """How many of weapon `w`'s clip-clock shots of body `b` land in [self.t, self.t + dt): the clip is a
        schedule (simunits._shot_times, then the reload), each cycle `w['cycle']` long, one shot after another as
        long as the weapon has a target every window. After an idle gap (no target in the previous window) a
        cycle that has run out starts anew now, pre-attack first; one still running (a reload, a part-spent clip)
        goes on by the clock. Round 2 of engine line C (bench: the coil one tank per ~125 frames)."""
        t0, t1 = self.t, self.t + dt
        eps = 1e-6
        clocks = self.__dict__.setdefault('clocks', {})
        key = (id(b), id(w))
        c = clocks.get(key)
        cycle = w['cycle']
        if c is None or (t0 - c[1] > dt * 1.5 and c[0] + cycle <= t0 + eps):
            c = [t0 + 1 / 15, t0]                       # [this cycle's start, the last window with a target]; the first
            #                                             object hit is1 frame after order; scripts observe it next frame (engine_emp)
        else:
            c[1] = t0
            while c[0] + cycle <= t0 + eps:             # chained: the next cycle starts where this one ends
                c[0] += cycle
        clocks[key] = c
        n = 0
        while True:
            for at in w['sched']:
                when = c[0] + at
                if t0 - eps <= when < t1 - eps:
                    n += 1
            if c[0] + cycle < t1 - eps:                 # the window reaches into the next cycle
                c[0] += cycle
                continue
            break
        return n

    def cold_of(self, b):
        """(simunits.freeze tracker, frozen armour) of b's template, read once a template."""
        cache = self.__dict__.setdefault('_cold', {})
        if b.template not in cache:
            cache[b.template] = simunits.freeze(b.template, self.own)
        return cache[b.template]

    def chill(self, dt):
        """`dt` seconds of the cryo beams aimed this tick (fight's `chilling`) and of melting (ALIGN 'freeze'): the
        cold goes up by the beams' rate, down by DissipateAmount / UpdateDuration, stays within 0 .. cap x max health;
        a change of the highest step reached re-sets the body (modify); a DIE_ON_ENTER step kills."""
        cold = self.__dict__.setdefault('_cold_on', {})
        for t, rate, by in getattr(self, 'chilling', ()):
            if not (t.alive and by.alive) or t.shielded:     # shielded: the Iron Curtain (the nugget's filter)
                continue
            if self.cold_of(t)[0] is None:
                continue
            t.cold += rate * dt
            cold[id(t)] = (t, by)
        for k, (t, by) in list(cold.items()):
            tr = self.cold_of(t)[0]
            if not t.alive:
                del cold[k]
                continue
            t.cold = min(max(t.cold - tr['melt'] / max(tr['every'], 1e-6) * dt, 0.0), tr['cap'] * t.max_hp)
            step = max((i for i, st in enumerate(tr['steps']) if t.cold >= st[0] * t.max_hp), default=-1)
            if t.cold <= 0:
                del cold[k]
            if step != t.cold_step:
                t.cold_step = step
                self.modify(t)
                if step >= 0:
                    self.note('冷冻', f'{self.label(t)} 冷冻到第 {step + 1} 档（{tr["steps"][step][0]:.0%} 生命值）')
                if step >= 0 and tr['steps'][step][4] and t.alive:
                    self.destroy(t, f'被 {self.label(by)} 冻死')

    def peeking(self):
        """The MAP_REVEAL_AT_WAYPOINT reveals still open this frame, as (x, y, r)."""
        now = self.frame_now()
        self.peeks = [q for q in self.peeks if now < q[3]]
        return [q[:3] for q in self.peeks]

    def frame_now(self):
        return self.eng.frame if self.eng else int(round(self.t * simunits.LIFE_FPS))

    def at_site(self, b, walked):
        """R5: a builder within his stand of the spot he was told to build at stops; the structure is made there the
        frame after he got there (`walked` this tick before that: bench 2026-11-07 engine_life, the ice core one frame
        after an order given within range). False while he is still short of it."""
        structure, (x, y), stand = b.building
        if math.hypot(b.x - x, b.y - y) > stand + 1e-6:
            return False
        got = self.frame_now() + (math.ceil(round(walked / b.speed * simunits.LIFE_FPS, 6)) if walked else 0)
        self.due.append((got + (REPLACE_FRAMES if b.replace else 1), structure, b.owner, b.team, x, y, b.name))
        b.building, b.path, b.dest = None, [], None
        self.note('技能', f'{self.label(b)} 到位，造 {structure}')
        return True

    def build_due(self, frame):
        """The structures builders put down by `frame` (at_site)."""
        for d in [d for d in self.due if d[0] <= frame]:
            self.due.remove(d)
            _, structure, owner, team, x, y, by = d
            was = self.bodies.get(by)
            if was is not None and was.replace:     # engine_unpack: the replacement takes its name and health share
                if not was.alive:
                    continue
                share = was.hp / was.max_hp if was.max_hp else 1.0
                self.destroy(was, f'展开成 {structure}', delete=True)
                self.bodies[f'#packed {len(self.bodies)} {by}'] = self.bodies.pop(by)
                n = self.add(by, structure, owner, was.x, was.y, by=by, at=self.t)
                n.hp = n.max_hp * share
            else:
                n = self.add(f'#built {len(self.bodies)} by {by}', structure, owner, x, y, by=by, at=self.t)
            n.team = team
            if self.blocks(n):
                self.reblock()

    def blast_due(self, frame):
        """A superweapon's hits landing by `frame` (SUPERWEAPON_HITS): every living object, friend or foe, within the
        table's reach loses the damage read off its centre distance (linear between the measured distances)."""
        for d in [d for d in self.blasts if d[0] <= frame]:
            self.blasts.remove(d)
            _, x, y, table, owner, by = d
            for t in self.living():
                dmg = hit_at(table, math.hypot(t.x - x, t.y - y))
                if dmg <= 0 or frame < t.immune_until or t.shielded or t.indestructible:
                    continue
                t.damage(dmg)
                t.last_hit, t.last_by = owner, by.name
                if t.hp <= 0 and t.alive:
                    if self.first_death is None:
                        self.first_death = (self.t, t, by)
                    self.destroy(t, f'被 {self.label(by)} 的超武打掉')

    def death_blast_due(self, frame):
        """A death weapon going off by `frame` (destroy, simunits.death_weapons): every living object within its
        radius, centre to centre, whose owner stands to the dead one's as the weapon's RadiusDamageAffects takes
        (ENEMIES / NEUTRALS / ALLIES, its own owner counted an ally), loses the damage through its armor. A death it
        causes fires that one's weapon in turn (a chain of exploding props)."""
        for d in [d for d in self.death_blasts if d[0] <= frame]:
            self.death_blasts.remove(d)
            _, x, y, dmg, typ, reach, affects, owner, by = d
            for t in self.living():
                if math.hypot(t.x - x, t.y - y) > reach or frame < t.immune_until or t.shielded or t.indestructible:
                    continue
                rel = self.relation(owner, t.owner)
                if (rel + 'S' if rel == 'NEUTRAL' else rel) not in affects:
                    continue
                armor = 1.0 if typ == 'UNRESISTABLE' else simunits.percent(t.armor, typ) / 100.0 * t.taken
                if dmg * armor <= 0:
                    continue
                t.damage(dmg * armor)
                t.last_hit, t.last_by = owner, by.name
                if t.hp <= 0 and t.alive:
                    if self.first_death is None:
                        self.first_death = (self.t, t, by)
                    self.destroy(t, f'被 {self.label(by)} 的死亡武器炸掉')

    def crush_along(self, b, x0, y0):
        """R9: a driving crusher kills what its footprint passes over that is a lower level (docs/engine/crush.md,
        bench 11-06 engine_crush: strictly greater kills, 20 against 20 and 30 against 30 live; the crushed does not
        step aside; the dead lie their SlowDeath out). The segment this tick passing within the CRUSHED's own radius
        of its centre (FITTED to two readings: Hammer / conscript at frame 43, Apocalypse / guardian at 69 -- touching
        at the radii's sum would be ~12 and ~30 frames earlier still; the simulator has no acceleration). Whose
        units: the crusher's enemies' only (INFERRED: crushing one's own / neutral units was not measured)."""
        dx, dy = b.x - x0, b.y - y0
        seg = dx * dx + dy * dy
        pool = self._crushable_pool
        if pool is None:                        # once a tick: the crushable ones, as arrays (a big map's tanks all drive)
            low = [o for o in self.living() if o.crushable is not None and not o.scenery and not o.topple
                   and o.surface == 'ground']
            pool = self._crushable_pool = (low, np.array([o.x for o in low]), np.array([o.y for o in low]),
                                           np.array([o.radius for o in low]), np.array([o.crushable for o in low]))
        low, ox, oy, orad, olevel = pool
        if not low:
            return
        k = np.clip(((ox - x0) * dx + (oy - y0) * dy) / seg, 0.0, 1.0) if seg else np.zeros(len(low))
        near = np.hypot(ox - (x0 + k * dx), oy - (y0 + k * dy)) <= orad
        for j in np.nonzero(near & (olevel < b.crusher))[0]:
            o = low[j]
            if o is b or not o.alive or not self.enemy(b.owner, o.owner):
                continue
            self.used.add('crush')
            o.last_hit, o.last_by = b.owner, b.name
            o.linger = o.lies
            self.destroy(o, f'被 {self.label(b)} 压死')

    _crushable_pool = None

    def move(self, dt=DT, precise=False):
        """Move one coarse tick, or one frame on paths crossing ToppleUpdate props (collision / removal timing)."""
        self._crushable_pool = None
        for b in list(self.frame_movers.values()) if precise else self.living():
            if not b.alive or b.frame_move != precise:
                continue
            if isinstance(b.goal, Body):
                g = b.goal
                if not g.alive:
                    b.goal, b.path = None, []
                elif b.spot and b.spot[0] == id(g) and math.hypot(g.x - b.spot[1], g.y - b.spot[2]) <= 150:
                    pass                            # at / on the way to its fire_spot while the goal stays near it
                elif not b.path or math.hypot(b.path[-1][0] - g.x, b.path[-1][1] - g.y) > 150:
                    if int(self.t / DT) % 8 == 0:                    # re-aimed every 4 s
                        self.send(b, (g.x, g.y), reach=self.reach(b, g) if b.mode == 'attack' else 0.0)
            if b.building and self.at_site(b, 0.0):
                continue
            if b.frame_move != precise:          # chasing a moving target may have replanned into / out of prop contact
                continue
            if not b.path or 'IMMOBILE' in b.status or b.engaged or self.frame_now() < self.__dict__.get('emp_until', {}).get(id(b), 0):
                continue
            left = b.speed * dt
            if precise:
                import simtopple
                speed, acceleration = simtopple.motion(b.template, self.own)
                base = simunits.stats(b.template, self.own)['speed']
                speed = speed * b.speed / base if speed is not None and base else b.speed
                b.drive_speed = min(speed, b.drive_speed + speed * dt / acceleration) if acceleration else speed
                left = b.drive_speed * dt
            walked = left
            x0, y0 = b.x, b.y
            while left > 0 and b.path:
                tx, ty = b.path[0]
                d = math.hypot(tx - b.x, ty - b.y)
                step = min(BUILD_STEP, left)
                if b.building and d > step:                 # a builder: in short steps, to see where he reaches it
                    b.x += (tx - b.x) * step / d
                    b.y += (ty - b.y) * step / d
                    left -= step
                    if self.at_site(b, walked - left):
                        break
                    continue
                if d <= left:
                    b.x, b.y, left = tx, ty, left - d
                    b.path.pop(0)
                else:
                    b.x += (tx - b.x) * left / d
                    b.y += (ty - b.y) * left / d
                    left = 0
            if b.building:
                self.at_site(b, walked - left)
            if b.crusher > 0 and b.surface == 'ground' and (b.x, b.y) != (x0, y0):
                self.crush_along(b, x0, y0)
                if precise or self.eng is None:
                    import simtopple
                    for o in self.topples:
                        if not o.alive or o.toppled or o.crushable is None or b.crusher <= o.crushable:
                            continue
                        if not simtopple.crosses(b, o, (x0, y0), (b.x, b.y), self.own):
                            continue
                        o.toppled = True
                        speed = b.drive_speed if precise else b.speed
                        fall = simtopple.fall_frames(speed / simunits.LIFE_FPS, o.topple)
                        if fall is not None and (o.topple['start'] or o.topple['finish']):
                            o.topple_end = self.frame_now() + fall + o.topple['delay']
            self.change()
        if precise:
            return
        self.follow_due()
        self.capture_due()
        if self.auto_kill is not None:
            mine = [b for b in self.living() if b.owner == self.human]
            for b in self.living():
                if not self.enemy(self.human, b.owner) or b.scenery or b.speed <= 0 or 'UNATTACKABLE' in b.status:
                    continue
                close = any(math.hypot(b.x - o.x, b.y - o.y) <= REACH for o in mine)
                b.close_since = (b.close_since if b.close_since is not None else self.t) if close else None
                if close and self.t - b.close_since >= self.auto_kill:
                    b.last_hit, b.last_by = self.human, None
                    self.destroy(b, f'自动打掉：在玩家 {REACH:g} 以内 {self.auto_kill:g} 秒')

    def sample(self):
        """Every second: a check's counters; every 10: the threat; every 30: what the player has seen."""
        if self.eng is None and self.test and self.test.counters and self.t >= LAG:     # the model's: in step
            self.series.append((int(round(self.t - LAG)), [self.counters.get(c, 0) for c, _ in self.test.counters]))
        if int(round(self.t)) % 10 == 0:
            # can the player hold: the enemy's fire within NEAR of the player's things against the player's own
            # there, and how much of the player's units' health is left (of all they ever had: the dead at 0,
            # units given later count from then)
            mine = [b for b in self.living() if b.owner == self.human]
            near = [b for b in self.living() if self.enemy(self.human, b.owner) and not b.scenery and b.speed > 0
                    and any(math.hypot(b.x - o.x, b.y - o.y) <= NEAR for o in mine)]
            foe = sum(w['dps'] for b in near for w in b.weapons)
            ours = sum(w['dps'] for b in mine for w in b.weapons
                       if any(math.hypot(b.x - e.x, b.y - e.y) <= NEAR for e in near))
            ever = [b for b in self.bodies.values() if b.owner == self.human and b.speed > 0]
            alive = {id(b) for b in mine}
            left = sum(b.hp for b in ever if id(b) in alive) /(sum(b.max_hp for b in ever) or 1.0)
            self.threat.append((self.t, len(near), foe, ours, left))
            if near and self.first_threat is None:
                b = min(near, key=lambda b: b.made_at)
                self.first_threat = (self.t, b)
        if int(round(self.t)) % 30 == 0:
            self.see()

    def see(self):
        g = self.ground.grids['both'] | self.ground.grids['ground'] | ~self.ground.grids['both']
        if self.known is None:
            self.known = np.zeros(g.shape, bool)
            jj, ii = np.mgrid[0:g.shape[0], 0:g.shape[1]]
            self._xy = self.ground.world((jj, ii))
        x, y = self._xy
        if self.reveal_all:
            self.known[:] = True
        for rx, ry, r in list(self.reveals.values()) + self.peeking():
            self.known |= (x - rx) ** 2 + (y - ry) ** 2 <= r * r
        for b in self.living():
            if b.owner == self.human and b.vision:
                seen = (x - b.x) ** 2 + (y - b.y) ** 2 <= b.vision ** 2
                if self.high and b.surface != 'air':
                    seen &= self.ground.zgrid[:seen.shape[0], :seen.shape[1]] <= self.ground.z(b.x, b.y) + b.clear_height
                self.known |= seen
        rect = list(getattr(self.m.map, 'BORDERS', {'': (0, 0, 1e9, 1e9)}).values())
        x0, y0, x1, y1 = rect[self.border] if self.border < len(rect) else rect[0]
        inb = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        self.known_at.append((self.t, round(float((self.known & inb).sum()) * GRID * GRID / 1e6, 2)))

    def pending(self):
        """Something still to come: a timer running, a unit moving, a script event, a rank to come where a script
        reads the points or the protocols."""
        return bool(self.events) or bool(self.anchored) or any(v > self.t for v in self.timers.values()) or \
            bool(self.due) or any(b.path or b.building or b.life_end is not None or b.topple_end is not None
                                 for b in self.living()) or \
            (self.tech_read and any(b.grows() for b in self.books.values()))

    def run(self, until=UNTIL):
        self.used |= {'engine model' if self.eng else 'frame rate', 'difficulty side'}
        while self.t <= until and self.ending is None:
            self.step()
            if abs(self.t - round(self.t)) < 1e-6:
                self.sample()
            if not self.pending() and self.t - self.last_change >= QUIET:
                self.note('卡住', f'{QUIET:g} 秒没有任何变化，也没有在等的计时、移动和剧本事件')
                break
            self.t = round(self.t + DT, 3)
        if self.ending and self.test and self.test.counters:   # the counters go with the mission
            self.series += [(int(self.t - LAG) + k, [None] * len(self.test.counters)) for k in range(1, 4)]
        return self

    def advance(self, frames):
        """The mission `frames` frames on, for a caller that plays it a slice at a time (simproxy's player gives its
        orders between slices): run's DT ticks (step, each whole second's sample) up to the first tick at or past them,
        stopping at the mission's end. No quiet check and no end-of-run counters (run's). Returns self."""
        fps = self.fps if self.eng is not None else simunits.LIFE_FPS
        target = round(self.t + frames / fps, 6)
        while self.t < target - 1e-9 and self.ending is None:
            self.step()
            if abs(self.t - round(self.t)) < 1e-6:
                self.sample()
            self.t = round(self.t + DT, 3)
        return self

    # ---- the report
    def ending_line(self):
        if self.ending:
            how, t, by = self.ending
            return f'结局：{how}，{mmss(t)}（{by}）'
        head = f'结局：{mmss(self.t)} 内没有结束' if self.pending() else \
            f'结局：卡住，{mmss(self.t)} 以后什么都不会再发生'
        return head + '；还差：' + '；'.join(self.missing())

    def missing(self):
        """What each ending (win / lose script) still waits for: its conditions false now."""
        out = []
        for s in self.mm.scripts:
            if s.name in self.m.endings and s.levels[self.level]:
                false = [c for c in s.when if not self.holds(c)]
                out.append(f'{s.name} ← ' + ', '.join(describe(c) for c in false))
        return out or ['（这一关没有写输赢）']

    def report(self, every=False):
        """The ending, the timeline (units made in one tick folded into one line, a line said again and again
        given once with how often), the measures, what the run assumed."""
        out = [self.ending_line()]
        if every:
            out += [f'{mmss(t)} [{k}] {x}' for t, k, x in self.log]
        else:
            rows, made, again = [], {}, {}
            for t, k, x in self.log:
                if k == '出现':
                    if t not in made:
                        made[t] = []
                        rows.append([t, k, made[t]])
                    made[t].append(x)
                elif (k, x) in again:
                    again[(k, x)].append(t)
                else:
                    again[(k, x)] = [t]
                    rows.append([t, k, x])
            for t, k, x in rows:
                if k == '出现':
                    out.append(f'{mmss(t)} [出现] {len(x)} 个：{x[0]}' + ('……' if len(x) > 1 else ''))
                    continue
                ts = again[(k, x)]
                more = f'（又 {len(ts) - 1} 次，到 {mmss(ts[-1])}）' if len(ts) > 1 else ''
                out.append(f'{mmss(t)} [{k}] {x}{more}')
        out.append(self.metrics())
        if self.ra3_only:
            self.used.add('ra3 only')
        if self.used:
            out.append('待对齐（这次推演用到的假设）：' + '；'.join(
                ALIGN[k] + (', '.join(sorted(self.ra3_only)) if k == 'ra3 only' else '') for k in sorted(self.used)))
        if self.unmodeled:                  # Sim.unknown's names are among them
            out.append('这次碰到、模拟器没模拟的（Sim.unmodeled）：' + '；'.join(
                f'[{k}] {n}×{g["n"]}（{mmss(g["t"])} 起）{g["what"]}' for (k, n), g in self.unmodeled.items()))
        if self.areas.missing:
            self.guessed.add('地图里没有的区域（按空区域算）：' + ', '.join(sorted(self.areas.missing)))
        if self.guessed:
            out.append('数据里没有、用了默认值：' + '；'.join(sorted(self.guessed)))
        return out

    def metrics(self):
        def ratio(foe, ours):
            return '—' if not foe else ('∞' if not ours else f'{foe / ours:.1f}')
        peak = max(self.threat, key=lambda x: x[2], default=(0, 0, 0, 0, 1))
        curve = ' '.join(f'{mmss(t)}:{n}个/{ratio(foe, ours)}/{left:.0%}' for t, n, foe, ours, left in self.threat
                         if int(t) % 60 == 0)
        known = ' '.join(f'{mmss(t)}:{v:g}' for t, v in self.known_at if int(t) % 120 == 0)
        if self.first_death:
            t, b, by = self.first_death
            dead = f'第一次有单位阵亡 {mmss(t)}：{self.label(b)}（{self.who(b.owner)}），{self.label(by)} 打的'
        else:
            dead = '没有单位在交战里阵亡' + ('（不打）' if not self.combat else '')
        if self.first_threat:
            t, b = self.first_threat
            s = next((s for s in self.mm.scripts if s.name == b.made_by), None)
            why = f'由 {b.made_by} 造出（条件 {s.when}）' if s else '开局就在图上'
            first = f'第一股敌人 {mmss(t)} 到玩家 {NEAR:g} 以内：{self.label(b)}，{why}'
        else:
            first = '没有敌人走到玩家附近'
        return (f'张力（每分钟：玩家 {NEAR:g} 以内的敌人数 / 敌我火力比 / 玩家剩余血量）：{curve or "—"}；'
                f'敌方火力最猛 {mmss(peak[0])}，{peak[1]} 个、火力比 {ratio(peak[2], peak[3])}\n'
                f'已知区域（km²，每 2 分钟）：{known or "—"}\n{first}\n{dead}')


def describe(c):
    """A condition as one short line: FLAG(CNV_A4_Phase_2=1), NOT NAMED_DESTROYED(x)."""
    c = list(c)
    neg = c and c[-1] == parts.NOT
    args = [a[2] if isinstance(a, tuple) and len(a) == 3 else a for a in (c[1:-1] if neg else c[1:])]
    return ('NOT ' if neg else '') + f'{c[0]}(' + ', '.join(str(a) for a in args) + ')'


def parse_script(text):
    """Events (t, verb, args...) from a script's text; 自动打掉 as (None, '自动打掉', seconds)."""
    if text and os.path.exists(text):
        text = open(text, encoding='utf-8').read()
    out = []

    def when(t):
        """A time: seconds or m:ss, or `<flag>+<time>` -- that long after the flag first reads 1 (an event of the plan: a
        phase's flag, a scene's), so a script follows the level when an opening gets longer (ADR 0015)."""
        if '+' in t and not re.fullmatch(r'[\d:.]+', t):
            flag, _, delta = t.rpartition('+')
            return ('@', flag, seconds(delta))
        return seconds(t)
    for line in re.split(r'[;\n]', text or ''):
        line = line.split('#')[0].strip()
        if not line or line == '不动':
            continue
        if line.startswith('自动打掉'):
            out.append((None, '自动打掉', seconds(line.split()[1])))
            continue
        if line in ('不打', '高地不挡'):
            out.append((None, line))
            continue
        t, rest = line.split(None, 1)
        if rest.startswith('派 '):
            who, _, where = rest[2:].rpartition(' 去 ')
            out.append((when(t), '派', who.strip(), where.strip()))
        elif rest.startswith('走 ') and ' 去 ' in rest:
            who, _, where = rest[2:].rpartition(' 去 ')
            out.append((when(t), '走', who.strip(), where.strip()))
        elif rest.startswith('攻击 '):
            who, _, target = rest[3:].rpartition(' 打 ')
            out.append((when(t), '攻击', who.strip(), target.strip()))
        elif rest.startswith('放 ') and ' 在 ' in rest:
            who_power, _, where = rest[2:].rpartition(' 在 ')
            who, _, power = who_power.strip().rpartition(' ')
            out.append((when(t), '放', who.strip(), power.strip(), where.strip()))
        elif rest.startswith('占领 ') and ' 进 ' in rest:
            who, _, target = rest[3:].rpartition(' 进 ')
            out.append((when(t), '占领', who.strip(), target.strip()))
        elif rest.startswith('血量 '):
            who, pct = rest[3:].rsplit(None, 1)
            out.append((when(t), '血量', who.strip(), float(pct.rstrip('%'))))
        elif rest.startswith('旗标 '):
            name, v = rest[3:].rsplit(None, 1)
            out.append((when(t), '旗标', name.strip(), int(v)))
        elif rest.startswith('生产 ') and ' 在 ' in rest:
            what, _, where = rest[3:].rpartition(' 在 ')
            out.append((when(t), '生产', what.strip(), where.strip()))
        elif rest.startswith('造 '):
            what, _, where = rest[2:].partition(' 在 ')
            angle = 0.0
            if re.fullmatch(r'-?[\d.]+', where.split()[-1]) and len(where.split()) > 1:
                where, angle = where.rsplit(None, 1)[0], float(where.split()[-1])
            out.append((when(t), '造', what.strip(), where.strip(), angle))
        else:
            verb, _, who = rest.partition(' ')
            if verb not in ('摧毁', '删除', '打', '占领', '买'):
                raise ValueError(f'剧本 {line!r}: 动作是 派 / 攻击 / 放 / 摧毁 / 删除 / 血量 / 打 / 占领 / 旗标 / 生产 / 造 / 买 之一')
            out.append((when(t), verb, who.strip()))
    return out


def simulate(name, check='', script='', level='normal', until=UNTIL):
    import build
    m, t, _ = build.resolve(name, check)
    return Sim(m, t, level, script).run(until)


def main():
    if sys.argv[1:] == ['--align']:             # the list of what the bench must still settle
        print('\n'.join(f'- {k}: {v}' for k, v in ALIGN.items()))
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--check', default='')
    ap.add_argument('--script', default='')
    ap.add_argument('--level', default='normal', choices=list(LEVELS))
    ap.add_argument('--until', type=float, default=UNTIL)
    ap.add_argument('--all', action='store_true', help='every line of the timeline (units made one by one)')
    a = ap.parse_args()
    import simchecks
    own = simchecks.CHECKS.get((a.name, a.check)) if a.check else None
    s = simulate(a.name, a.check, a.script or (own or {}).get('script', ''), a.level, a.until)
    print('\n'.join(s.report(a.all)))
    if own and not a.script:                    # the check's simulator version: its ending, its wiring counters
        ok, lines = simchecks.run(a.name, a.check)
        print('\n'.join(['模拟器版检查：' + ('PASS' if ok else 'FAIL')] + [x for x in lines[1:]]))
        sys.exit(0 if ok else 1)
    if s.test and s.test.expect:
        import build
        lines, _ = build.report(s.test, s.series)
        print('测试台版的期望（这个检查没有模拟器版，多半靠引擎行为：只作参考）：')
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
