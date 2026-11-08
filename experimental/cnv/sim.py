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
  <t> 派 <谁> 去 <地点>     move (a map site, a mark, a trigger area, a named object)
  <t> 摧毁 <谁>             destroyed (killed by the player)
  <t> 删除 <谁>             gone without dying
  <t> 血量 <谁> <百分比>     health set
  <t> 打 <谁>               attacked by the player (NAMED_ATTACKED_BY_PLAYER)
  <t> 占领 <谁>             now the player's
  <t> 旗标 <名字> <值>       a flag set outright (a check's or a device's)
  <t> 造 <单位> 在 <地点> [角度]  the player makes one (a unit id of the mission's, a cast part's template, a retail
                            template): an engineer's ice -- '40 造 CNV_IceWall 在 inside 1 1.57'
  自动打掉 <秒>             every enemy that has been that long within REACH (300) of something of the player's is
                            destroyed (the player fights back where the enemy comes to them)
  不打                      the fight model off (a check of the wiring alone)
  高地不挡                  the high-ground rule off: low ground sees high ground (the Generals way)
  <谁>: a cast part ('yuriko'), a group of them ('tank' = tank 1, tank 2 ...), an object's name, 名字含 <text>
  (every object whose name holds it: '名字含 W1-' a plan's first wave), 敌人 在 <地点> (the enemy's there).
"""
import argparse
import collections.abc
import dataclasses
import importlib.util
import math
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import simunits  # noqa: E402
from ctx import FUNC_LATE, PANEL_CLEAR  # noqa: E402

TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP')   # E3: need a live team
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
LINGER = 0.0                    # a killed unit's death (its slow death): still in the game's name cache, where it fell
                                # (docs/engine/script-semantics.md 4.2) -- the bench (2026-10-28, probe death): out of
                                # the area from the reading the kill shows in; the guess was 3 s
GRID = 20.0                     # routing cells (world units)
ARRIVE = 1.5 * GRID             # a plain move that ends farther than this from where it was sent stopped short (held_up)
BUILD_STEP = 5.0                # a builder on his way (R5) moves in steps this long, to see where he gets within range
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
    'special power': 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT / NAMED_USE_COMMANDBUTTON_ABILITY: logged, no effect '
                     '(a jump, a carrier\'s drop: the device\'s own scripts say what follows)',
    'ai': 'a skirmish AI (UNIT_AI_TRANSFER_ALL, SKIRMISH_AI_*): woken and logged; what it builds and when it '
          'attacks is not simulated (bench 2026-10-27 aistep: it may never build a kind it is let to)',
    'lifetime': 'an object with a LifetimeUpdate (our ice walls, cores, smoke) is killed seconds x 15 frames (cut '
                'down) after the frame it was made, and its CreateObjectDie for that death type makes what it lists '
                'there that frame (bench 2026-11-07 engine_life: a 30 s wall lived 450 frames, a 5.5 s core 82, the '
                'core\'s wall there at once; nothing of the dead lingers in an area). Min and Max apart: their '
                'middle (a guess); retail templates\' lifetimes are not read',
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
    'health of the dead': 'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER of a dead object: 0 (bench 2026-10-28, probe death)',
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

# actions that change nothing the scripts ask about: logged on the timeline (the player sees or hears them)
SHOWN = {'SHOW_MILITARY_CAPTION': '通报', 'CAMPAIGN_CREATE_AUTO_SAVE': '存档', 'PATH_MUSIC_PLAY_EVENT': '音乐',
         'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM': '战况音乐', 'NAMED_FLASH': '闪烁', 'NAMED_SHOW_INFOBOX': '信息框',
         'OBJECT_CREATE_RADAR_EVENT': '小地图闪点', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT': '原版播报',
         'PLAY_SOUND_EFFECT': '配音', 'MOVIE_PLAY_RADAR': '头像'}
IGNORED = {'PLAYER_SET_MAX_PLAYER_POWER_POINTS', 'PLAYER_SET_PLAYER_POWER_POINTS', 'DISPLAY_COUNTER', 'HIDE_COUNTER',
           'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES',
           'SKIRMISH_AI_USE_REPAIRS', 'SKIRMISH_AI_USE_REBUILD_SYSTEM', 'CAMERA_LETTERBOX_BEGIN', 'CAMERA_LETTERBOX_END',
           'CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', 'SET_COOP_AI_COMMAND_UI_ENABLED'}

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
    max_hp: float = 100.0
    hp: float = 100.0
    immune_until: int = -1          # the frame an Iron Curtain's protection ends (weapons and superweapons, not scripts)
    armor: dict = dataclasses.field(default_factory=dict)      # damage type -> percent taken (simunits.fight)
    weapons: list = dataclasses.field(default_factory=list)    # [{range, dps, type, anti}]
    radius: float = 0.0                                         # R8: Geometry's bounding circle (simunits.radius)
    sight: float = 0.0                                          # R8: its VisionRange alone (vision: with the shroud)
    chase: object = None                                        # R8 idle_chase: the enemy it went after by itself,
    home: tuple = None                                          # where it stood then (it walks back),
    auto_to: tuple = None                                       # and the way's end that rule gave it
    stood_for: tuple = None                                     # the goal it was told and stands short of (send)
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
    guessed: list = dataclasses.field(default_factory=list)    # what of its numbers simunits only guessed
    clear_height: float = HIGH_STEP                             # its ShroudClearingHeight (simunits: 50 unless written)
    angle: float = 0.0
    dest: object = None                                         # where it was sent (rerouted when the way changes)
    status: set = dataclasses.field(default_factory=set)       # IMMOBILE (stays put), UNATTACKABLE (the player
                                                                # cannot destroy it) ...
    upgrades: set = dataclasses.field(default_factory=set)     # NAMED_RECEIVE_UPGRADE / _REMOVE_UPGRADE (a SPEED modifier acts)
    base_speed: float = None                                    # its speed before upgrades (set at the first one)
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
    unpack_end: int = None                                      # a structure made in the run: unpacking until then
    mine: dict = None                                           # a harvester's trip (mine_due): state, node,
                                                                # refinery, due frame, load, paid, leg
    ready_at: dict = dataclasses.field(default_factory=dict)   # special power -> the frame its reload ends (a cast,
                                                                # the script's too, starts it anew: order_power)

    @property
    def health(self):
        """Health in percent of its maximum (what the scripts read)."""
        return 100.0 * self.hp / self.max_hp if self.max_hp else 0.0

    @health.setter
    def health(self, pct):
        self.hp = self.max_hp * float(pct) / 100.0


def inside(pts, x, y):
    """Point in polygon (even-odd)."""
    c, n = False, len(pts)
    for k in range(n):
        (x0, y0), (x1, y1) = pts[k], pts[(k + 1) % n]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


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
        dims = platmap.CONTAINER
        w, h, b = dims
        if hasattr(mapmod, 'LAYOUT'):
            e, _ = platmap.heights(mapmod.LAYOUT, w, h, b)
            walk = platmap.walkable(mapmod.LAYOUT, getattr(mapmod, 'OBJECTS', []), dims, e)
            bridge = walk & ~platmap.walkable(mapmod.LAYOUT, [], dims, e)    # walkable only for a bridge laid on it
        else:
            e = mapmod.ground().e
            import newmap
            walk = (e > newmap.WATERLINE + 10) & (platmap.slope_of(e) <= platmap.STEEP)
            if hasattr(mapmod, 'impassable'):                   # a probe's field-0 cells (maps/probe_block.py)
                walk &= ~mapmod.impassable()
            bridge = np.zeros_like(walk)
        import newmap
        water = e < newmap.WATERLINE - 5
        d = int(GRID // platmap.CELL)
        hh, ww = h // d, w // d
        fold = lambda a: a[:hh * d, :ww * d].reshape(hh, d, ww, d)            # noqa: E731
        self.b, self.d = b, d
        self.e = e                                                          # ground height (CELL cells)
        self.zgrid = e[:hh * d:d, :ww * d:d]                                # the same at each GRID cell's corner
        self.grids ={'ground': fold(walk).all(axis=(1, 3)), 'water': fold(water).all(axis=(1, 3))}
        # the shore's shallows (between the water's edge and 'dry'): platmap.apply blocks only steep ground, so an
        # amphibian goes ashore through them; left out they cut every slip (a5, 2026-11-04)
        shallow = (e >= newmap.WATERLINE - 5) & (e <= newmap.WATERLINE + 10) & (platmap.slope_of(e) <= platmap.STEEP)
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
        pts = [self.world(c) for c in cells]
        return pts[1::3] + [q] if len(pts) > 3 else [q]

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
        pts = [self.world(c) for c in m.traceback(end)]
        return pts[1::3] + [pts[-1]] if len(pts) > 3 else [pts[-1]]

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
        pts = [self.world(c) for c in m.traceback((int(jj[k]), int(ii[k])))]
        return pts[1::3] + [pts[-1]] if len(pts) > 3 else [pts[-1]]


class Sim:
    def __init__(self, mission, test=None, level='normal', script='', model=True):
        """model: run the scripts in the engine line's model where it is on this computer (False: the older loop)."""
        self.m = mission
        self.mm = parts.merged(mission, test)
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
        self.peeks = []                     # (x, y, r): a reveal that is not permanent (taken as for this tick on)
        self.camera = None
        self.input = True
        self.countdowns = set()
        self.ending = None
        self.both = None                    # won and lost in one frame: (first, second)
        self.ra3_only = set()               # RA3-only action / condition names the run used
        self.last_change = 0.0
        self.ai = {}                        # player -> woken at
        self.money = {}
        self.nodes = {}                     # ore node name -> {'free': frame it takes a miner from, 'gathered', 'at'}
        self.mined_to = None                # the last frame mine_due ran
        self.relations = {}
        self.players = dict(mission.map.PLAYERS)
        self.human = self.players['p1']
        self.foe = self.players.get('s1')
        self.ground = Ground(mission.map)
        self.own = {u.id: u.xml for u in self.mm.units}
        self.bodies = {}                    # name -> Body (named ones), plus unnamed under '#k'
        self.refs = {}                      # reference name (UNITRef - ...) -> the Body a SET_REF_TO_... pointed it at
        self.series = []                    # (t, counter values) for a check's counters
        self.threat = []                    # (t, enemies near, countdowns) every 10 s
        self.first_threat = None
        self.known = None                   # cells ever seen (GRID)
        self.known_at = []                  # (t, km2 known)
        self.guessed = set()
        self.walls = {u.id: u.params for u in self.mm.units if 'length' in u.params}   # our bars of ice, gates
        self.due = []                       # (frame, structure, owner, team, x, y, by): a builder's, to put down (R5)
        self.blasts = []                    # (frame, x, y, [(distance, damage)], owner, by): a superweapon's hits
        self.queues = {}                    # factory name -> [job]: production (order_build, produce_due)
        self.produced_to = None             # the last frame produce_due ran
        self.energies = {}                  # template -> EnergyProduction (simunits.energy; power)
        self.player_ups = {}                # player -> upgrades GIVE_PLAYER_UPGRADE gave (a unit's NeededUpgrade)
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
            b.angle = o.angle or 0.0
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
        self.events = sorted((e for e in self.script if isinstance(e[0], float)), key=lambda e: e[0])
        self.anchored = [e for e in self.script if isinstance(e[0], tuple)]       # (('@', flag, delta), verb, ...)
        self.areas = self.mm.areas
        self.waypoints = self.mm.waypoints
        self.reblock()
        self.eng = None
        got = engine_model() if model else None
        if got:
            # the scripts as the game runs them: the compiler's NOT flags (package.py writes unnot's), the inverted
            # bit ignored; one list, the run's difficulty; this Sim is the engine's World (condition / action)
            mod, cls = got
            self.fps = mod.FPS
            self.eng = cls(mod.from_cnv(parts.unnot(self.mm.scripts)), world=self, difficulty=self.level,
                           honor_inverted=False)
            self.flags, self.counters, self.timers = self.eng.flags, Counters(self.eng), Timers(self, mod.FPS)
            if any(c and c[-1] == parts.NOT for s in self.mm.scripts for c in s.when):
                self.used.add('inverted')

    def blocks(self, b):
        """What of the way a body takes up: a wall of ours its bar (or disc, square), a building its round."""
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
        if f['hp']:
            b.max_hp = b.hp = f['hp']
        else:                                   # no health in the data: a building's or a unit's usual (a guess)
            b.max_hp = b.hp = 2000.0 if 'STRUCTURE' in b.kinds else 300.0
        b.armor, b.weapons = f['armor'], f['weapons']
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
        return [b for b in self.living() if b.team == team]

    def order_move(self, b, where, attacking):
        if b:
            b.mode = 'attack' if attacking else 'move'
            self.send(b, where)
            b.move_to = b.dest if not attacking else None

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
            b.goal, b.mode = target, 'attack'
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

    def can_build(self, owner, template, factory=None):
        """Whether owner's sidebar button for `template` is lit (at `factory`, else at any of owner's that builds it):
        not banned (ALLOW_DISALLOW_ONE_BUILDING), every RequiredObject standing, every NeededUpgrade held there
        (holds_upgrade; all of them is an inference)."""
        if (owner, template.lower()) in self.banned:
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

    def order_build(self, owner, template):
        """Queue `template` at the owner's factory that builds it with the shortest queue -- or an upgrade at the
        structure whose button buys it; nothing is paid now (produce_due pays frame by frame, an upgrade as a unit).
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
              and self.can_build(owner, template, f)]
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
        the 16th, a 250 budget stalls at 3 left, out 10 frames after full). A factory gone takes its queue along."""
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
                if job is None:
                    continue
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
        if b.base_speed is None:
            b.base_speed = b.speed
        b.speed = b.base_speed * simunits.speed_scale(self.own.get(b.template), b.upgrades)

    def power(self, owner):
        """(supply, demand) of the owner: its living objects' EnergyProduction, > 0 summed into the supply, < 0 into
        the demand (RA3 1.13 0x7424a0 leaves out an object under construction or powered down: the simulator has
        neither -- a building stands built from the frame it appears)."""
        sup = dem = 0
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
            b.path, b.goal = [], None

    def enemy(self, a, b):
        """Player a takes player b as an enemy."""
        if (a, b) in self.relations:
            return self.relations[(a, b)] == 'Enemy'
        return {a, b} == {self.human, self.foe} or (a != b and CIV not in (a, b) and self.human in (a, b)
                                                   and (a in self.ai or b in self.ai))

    def point(self, name):
        """A waypoint, a trigger area's middle, a site, a mark, a named object."""
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
        return self.t - b.died_at <= LINGER

    def destroy(self, b, why, delete=False):
        if not b.alive:
            return
        b.alive, b.deleted, b.path, b.died_at = False, delete, [], self.t
        if not delete:
            b.hp = 0.0
        self.note('删除' if delete else '摧毁', f'{self.label(b)}（{why}）')
        self.change()
        if self.blocks(b):
            self.reblock()

    # ---- the engine model's World: what its script engine asks of the objects (the rest it does itself)
    def condition(self, eng, name, args):
        if name in RA3_ONLY:
            self.ra3_only.add(name)
        return self.cond(name, list(args))

    def action(self, eng, name, args):
        self.act(name, list(args), eng.script)

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

    def nearest_ref(self, template, owner, team, ref):
        """R2: SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER -- point `ref` at the living `template` of
        `owner` nearest to `team`'s middle (its members' mean place; bench 2026-11-07 engine_ref a / a2: not the first
        member's nor any member's nearest, whatever order they were made in), objects with a script name skipped
        (ref_b); an empty team's middle reads (0, 0) (ref_c: the wall nearest the map's corner was picked -- a
        guess as to why). None of the type: `ref` left as it was (not read on the bench)."""
        self.used.add('nearest ref')
        crew = self.members(team)
        cands = [b for b in self.living() if b.owner == owner and b.template.lower() == template.lower()
                 and b.name.startswith('#')]
        if not cands:
            return
        mx = sum(m.x for m in crew) / len(crew) if crew else 0.0
        my = sum(m.y for m in crew) / len(crew) if crew else 0.0
        self.refs[ref] = min(cands, key=lambda c: math.hypot(c.x - mx, c.y - my))

    def cond(self, name, a):
        if name == 'FLAG':
            return int(self.flags.get(a[0], 0)) == int(a[1])
        if name == 'TIMER_EXPIRED':
            if a[0] not in self.timers:
                self.used.add('timer unset')
                return False
            return self.t >= self.timers[a[0]]
        if name == 'COUNTER':
            return CMP[a[1]](self.counters.get(a[0], 0), a[2])
        if name in ('NAMED_DESTROYED', 'NAMED_NOT_DESTROYED'):
            b = self.body(a[0])
            if b is None:
                self.used.add('destroyed unborn')
                return False
            # killed: destroyed at once; deleted: only from the next frame (the game's destroy list at the frame's end)
            dead = not b.alive and not (b.deleted and self.t <= b.died_at)
            return dead if name == 'NAMED_DESTROYED' else not dead
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
            # the dying counted too (Team::countObjectsByThingTemplate, ignoreDead false)
            want = a[3].lower()
            n = sum(1 for b in self.bodies.values() if b.owner == a[0] and b.template.lower() == want
                    and self.present(b))
            return CMP[a[1]](n, a[2])
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
        self.unknown[name] = self.unknown.get(name, 0) + 1
        return False

    def sees(self, x, y, air=False):
        """Whether the player sees a point (a body there, airborne or not)."""
        if self.reveal_all:
            return True
        if any(math.hypot(x - rx, y - ry) <= r for rx, ry, r in list(self.reveals.values()) + self.peeks):
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
    def act(self, name, a, script):
        if name in RA3_ONLY:
            self.ra3_only.add(name)
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
        elif name in ('MOVE_NAMED_UNIT_TO', 'ATTACK_MOVE_NAMED_UNIT_TO'):
            self.order_move(self.body(a[0]), a[1], name == 'ATTACK_MOVE_NAMED_UNIT_TO')
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
        elif name == 'UNIT_SET_TEAM':               # the unit joins the team (K6: ctx.order does it before every whole-team order)
            b = self.body(a[0])
            self.active.add(a[1])                   # ... and the team has an instance from then on, the unit there or not (E3)
            if b and b.alive:
                b.team = a[1]
        elif name in TEAM_COMMANDS and a[0] not in self.active:
            # the game looks the team up without making it: nobody joined it, so the order does nothing (E3)
            self.lost_orders.append((self.t, script.name, name, a[0]))
            self.note('无效命令', f'{name} {a[0]}：这个队还没有人加入，命令落空')
        elif name in ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO'):
            for b in self.members(a[0]):
                self.order_move(b, a[1], name == 'ATTACK_MOVE_TEAM_TO')
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
        elif name in ('NAMED_KILL', 'NAMED_DELETE'):
            b = self.body(a[0])
            if b:
                if name == 'NAMED_KILL':
                    b.last_hit = b.last_by = None   # the game's kill damage comes from nobody (INVALID_ID)
                self.destroy(b, '脚本' if name == 'NAMED_KILL' else '脚本删掉', delete=name == 'NAMED_DELETE')
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
                (b.status.add if a[2] else b.status.discard)(st)
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
                self.counters[a[1]] = int(round(b.health)) if b.alive else 0
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
            b = self.body(a[0])
            if b and self.body(a[1]):
                self.send(b, a[1])
        elif name == 'SET_MISSION_OBJECTIVE_STATUS':
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
        elif name in ('UNIT_AI_TRANSFER_ALL', 'SKIRMISH_AI_MAKE_BASE'):
            self.used.add('ai')
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
                    self.peeks.append((p[0], p[1], float(a[1])))
                else:
                    self.reveals[a[3]] = (p[0], p[1], float(a[1]))
                self.note('揭图', f'{a[0]} 半径 {a[1]:g}')
        elif name == 'MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT':
            self.reveals.pop(a[0], None)
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
        elif name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY'):
            b = self.body(a[0])
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
                if rules and rules['reload']:       # every cast starts the reload anew (RA3 1.13 0x7dea80, read;
                    b.ready_at[a[1]] = self.frame_now() + rules['reload'] + RELOAD_LAG.get(a[1], 0)   # SDK GlobalData)
                hits = SUPERWEAPON_HITS.get(a[1]) if b and b.alive else None
                if hits and q is not None:         # a script's cast fires though the power is not ready
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
            for b in self.pick(who):
                b.mode = 'attack'                   # the player's units go attack-moving, fighting on the way
                self.send(b, where)
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
        elif verb == '打':
            for b in self.pick(rest[0]):
                b.last_hit, b.last_by = self.human, None
        elif verb == '占领':
            for b in self.pick(rest[0]):
                b.owner = self.human
        elif verb == '旗标':
            self.flags[rest[0]] = int(rest[1])
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
        counters read on each whole second's frame; units move and fight after the tick's first frame."""
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
            eng.step()
            self.expire(eng.frame)
            self.build_due(eng.frame)
            self.blast_due(eng.frame)
            self.deposit_due(eng.frame)
            self.mine_due(eng.frame)
            self.produce_due(eng.frame)
            if self.test and self.test.counters and (eng.frame - 1) % self.fps == 0 and self.t >= LAG:
                self.series.append((int(round(self.t - LAG)), [self.counters.get(c, 0) for c, _ in self.test.counters]))
            if not moved and self.ending is None and self.t >= t0 - 1e-9:
                moved = True
                if self.combat:
                    self.fight()
                self.move()
            if self.combat and self.ending is None:
                self.deal(1.0 / self.fps)       # R6: the aimed fire frame by frame, after the frame's scripts
        self.t = t0

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
        self.build_due(self.frame_now())
        self.deposit_due(self.frame_now())
        self.mine_due(self.frame_now())
        self.produce_due(self.frame_now())
        if self.ending:
            return
        if self.combat:
            self.fight()
        self.move()

    def can_hit(self, w, t):
        """A weapon's anti mask against a target: aircraft need ANTI_AIRBORNE, buildings ANTI_STRUCTURE (or
        ground), the rest ground or water."""
        anti = w['anti']
        if not anti:
            return True
        if t.surface == 'air':
            return any(a.startswith('ANTI_AIRBORNE') for a in anti)
        if 'STRUCTURE' in t.kinds:
            return 'ANTI_STRUCTURE' in anti or 'ANTI_GROUND' in anti
        return 'ANTI_GROUND' in anti or 'ANTI_WATER' in anti

    def fight(self):
        """One tick of the fight model (未对齐, docs: the 'combat' align entry): every armed body fires each of its
        weapons at the nearest enemy in that weapon's range it can hit (its NAMED_ATTACK target first, when in
        range); the damage rate = the weapon's damage per second x the target's armour percent for its damage type;
        an attack-mover with an enemy in range holds while it fights; a plain move goes on firing; an idle unit goes
        after an enemy within its sight and comes back (`idle_chase`, R8). The reach is measured between the bounding
        circles (`in_range`, R8). The aim is taken once a tick; the damage is dealt frame by frame (`deal`, R6)."""
        self.seen = {}
        self.firing = []
        live = [b for b in self.living() if not b.scenery]
        armed = [b for b in live if b.weapons and 'NO_ATTACK' not in b.status    # NO_ATTACK: holds its fire
                 and not self.unpowered(b)]
        targets = [b for b in live if 'UNATTACKABLE' not in b.status]
        if not armed or not targets:
            return
        aimable = {id(t) for t in targets}
        tx = np.array([b.x for b in targets])
        ty = np.array([b.y for b in targets])
        for a in armed:
            a.engaged = False
            if self.held_up(a):                 # stopped short on a plain move: still moving (DEMO_KILL)
                continue
            foes =[k for k, t in enumerate(targets) if t is not a and self.enemy(a.owner, t.owner)]
            if not foes:
                self.idle_chase(a, False, [])
                continue
            idx = np.array(foes)
            d = np.hypot(tx[idx] - a.x, ty[idx] - a.y)
            pad = max(targets[k].radius for k in foes)          # the biggest foe's radius: the scan's cut-off (R8)
            fired = False
            for w in a.weapons:
                order = np.argsort(d)
                pick = None
                if isinstance(a.goal, Body) and a.goal.alive and id(a.goal) in aimable and \
                        self.in_range(a, a.goal, w) and self.can_hit(w, a.goal) and \
                        self.side_sees(a.owner, a.goal):
                    pick = a.goal
                else:
                    for j in order:
                        if d[j] - a.radius - pad > w['range']:      # sorted by centre: nobody nearer after this
                            break
                        t = targets[idx[j]]
                        if not self.in_range(a, t, w, d[j]):
                            continue
                        if t.template in self.unshot:       # our ice: only when ordered (the bench, a4 hold)
                            continue
                        if self.can_hit(w, t) and self.side_sees(a.owner, t):
                            pick = t
                            break
                if pick is None:
                    continue
                if a.vision and w['range'] > a.vision:
                    a.fired_at = self.t                 # a bombarder firing shows itself
                self.firing.append((pick, w['dps'] * pick.armor.get(w['type'], simunits.ARMOR_DEFAULT) / 100.0, a))
                fired = True
                if a.mode == 'attack':
                    a.engaged = True
            self.idle_chase(a, fired, [(d[j], targets[idx[j]]) for j in np.argsort(d)])
        if self.firing:
            self.used.add('combat')
        if self.eng is None:                    # no frames: the tick's damage at once
            self.deal(DT)

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
        for dist, t in near:
            if dist - t.radius > sight:
                break                           # sorted by centre; a radius over 0 only cuts more
            if t.template in self.unshot or not self.side_sees(a.owner, t):
                continue
            if not any(self.can_hit(w, t) for w in a.weapons):
                continue
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
        for t, rate, by in self.firing:
            if t.alive and by.alive:
                h = hurt.setdefault(id(t), [t, 0.0, by])
                h[1] += rate * dt
                h[2] = by
        for t, dmg, by in hurt.values():
            if self.frame_now() < t.immune_until:
                continue
            t.hp -= dmg
            t.last_hit, t.last_by = by.owner, by.name
            if t.hp <= 0 and t.alive:
                if self.first_death is None:
                    self.first_death = (self.t, t, by)
                self.destroy(t, f'被 {self.label(by)} 打掉')

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
        self.due.append((got + 1, structure, b.owner, b.team, x, y, b.name))
        b.building, b.path, b.dest = None, [], None
        self.note('技能', f'{self.label(b)} 到位，造 {structure}')
        return True

    def build_due(self, frame):
        """The structures builders put down by `frame` (at_site)."""
        for d in [d for d in self.due if d[0] <= frame]:
            self.due.remove(d)
            _, structure, owner, team, x, y, by = d
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
                if dmg <= 0 or frame < t.immune_until:
                    continue
                t.hp -= dmg
                t.last_hit, t.last_by = owner, by.name
                if t.hp <= 0 and t.alive:
                    if self.first_death is None:
                        self.first_death = (self.t, t, by)
                    self.destroy(t, f'被 {self.label(by)} 的超武打掉')

    def move(self):
        for b in self.living():
            if isinstance(b.goal, Body):
                g = b.goal
                if not g.alive:
                    b.goal, b.path = None, []
                elif not b.path or math.hypot(b.path[-1][0] - g.x, b.path[-1][1] - g.y) > 150:
                    if int(self.t / DT) % 8 == 0:                    # re-aimed every 4 s
                        self.send(b, (g.x, g.y), reach=self.reach(b, g) if b.mode == 'attack' else 0.0)
            if b.building and self.at_site(b, 0.0):
                continue
            if not b.path or 'IMMOBILE' in b.status or b.engaged:
                continue
            left = b.speed * DT
            while left > 0 and b.path:
                tx, ty = b.path[0]
                d = math.hypot(tx - b.x, ty - b.y)
                step = min(BUILD_STEP, left)
                if b.building and d > step:                 # a builder: in short steps, to see where he reaches it
                    b.x += (tx - b.x) * step / d
                    b.y += (ty - b.y) * step / d
                    left -= step
                    if self.at_site(b, b.speed * DT - left):
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
                self.at_site(b, b.speed * DT - left)
            self.change()
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
        for rx, ry, r in list(self.reveals.values()) + self.peeks:
            self.known |= (x - rx) ** 2 + (y - ry) ** 2 <= r * r
        for b in self.living():
            if b.owner == self.human and b.vision:
                seen = (x - b.x) ** 2 + (y - b.y) ** 2 <= b.vision ** 2
                if self.high and b.surface != 'air':
                    seen &= self.ground.zgrid[:seen.shape[0], :seen.shape[1]] <= self.ground.z(b.x, b.y) + b.clear_height
                self.known |= seen
        self.peeks = []
        rect = list(getattr(self.m.map, 'BORDERS', {'': (0, 0, 1e9, 1e9)}).values())
        x0, y0, x1, y1 = rect[self.border] if self.border < len(rect) else rect[0]
        inb = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        self.known_at.append((self.t, round(float((self.known & inb).sum()) * GRID * GRID / 1e6, 2)))

    def pending(self):
        """Something still to come: a timer running, a unit moving, a script event."""
        return bool(self.events) or bool(self.anchored) or any(v > self.t for v in self.timers.values()) or \
            bool(self.due) or any(b.path or b.building or b.life_end is not None for b in self.living())

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
        if self.unknown:
            out.append('不认识的条件 / 动作（当成不成立 / 没效果）：' + ', '.join(f'{k}×{v}' for k, v in self.unknown.items()))
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
        elif rest.startswith('血量 '):
            who, pct = rest[3:].rsplit(None, 1)
            out.append((when(t), '血量', who.strip(), float(pct.rstrip('%'))))
        elif rest.startswith('旗标 '):
            name, v = rest[3:].rsplit(None, 1)
            out.append((when(t), '旗标', name.strip(), int(v)))
        elif rest.startswith('造 '):
            what, _, where = rest[2:].partition(' 在 ')
            angle = 0.0
            if re.fullmatch(r'-?[\d.]+', where.split()[-1]) and len(where.split()) > 1:
                where, angle = where.rsplit(None, 1)[0], float(where.split()[-1])
            out.append((when(t), '造', what.strip(), where.strip(), angle))
        else:
            verb, _, who = rest.partition(' ')
            if verb not in ('摧毁', '删除', '打', '占领'):
                raise ValueError(f'剧本 {line!r}: 动作是 派 / 摧毁 / 删除 / 血量 / 打 / 占领 / 旗标 / 造 之一')
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
