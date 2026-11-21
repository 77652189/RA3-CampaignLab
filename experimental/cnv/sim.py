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
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import parts  # noqa: E402
import engine.script.act as simact  # noqa: E402
import engine.script.cond as simcond  # noqa: E402
import engine.combat.host as simdamage  # noqa: E402
import engine.objects.garrison as simgarrison  # noqa: E402
import engine.objects.heal as simheal  # noqa: E402
import engine.world.living as simliving  # noqa: E402
import engine.objects.locomotion as simlocomotion  # noqa: E402
import engine.objects.body as simbody  # noqa: E402
import engine.objects.mine as simmine  # noqa: E402
import engine.objects.path as simpath  # noqa: E402
from engine.objects.path import Ground  # noqa: E402,F401  (the routing world, M1; tests and simstatic read sim.Ground)
import engine.objects.modifier as simmodifier  # noqa: E402
import engine.players.money as simmoney  # noqa: E402
import engine.objects.infiltrator as siminfiltrator  # noqa: E402
from engine.orders import order as simorder, ability as simability, target as simtarget, hunt as simhunt, seq as simseq  # noqa: E402
import engine.objects.power as simpower  # noqa: E402
import engine.players.production as simproduce  # noqa: E402
import engine.combat.range as simrange  # noqa: E402
import engine.objects.special as simspecial  # noqa: E402
import engine.combat.sweeps as simsweep  # noqa: E402
import engine.players.tech as simtech  # noqa: E402
import engine.objects.toggle as simtoggle  # noqa: E402
import engine.data.units as simunits  # noqa: E402
import engine.objects.level as simlevel  # noqa: E402
from engine.kernel import factory as kernel_factory, interfaces as kernel_interfaces  # noqa: E402
from engine.kernel import module as kernel_module, world as kernel_world  # noqa: E402
from engine.ports import command as command_port  # noqa: E402  (happen gives the player's orders through it)
import engine.modules  # noqa: E402,F401  (imports, so registers, every module file in it)
from engine.modules import aiupdate, locomotor  # noqa: E402
from engine.modules import slowdeath as kernel_slowdeath, weaponset as kernel_weaponset  # noqa: E402
import engine.loop.frame as simloop  # noqa: E402
import engine.world.handle as simworld  # noqa: E402
import engine.script.host as simexec  # noqa: E402
import scriptplugin  # noqa: E402
from ctx import FUNC_LATE, PANEL_CLEAR  # noqa: E402
from model import coord, facing  # noqa: E402
from engine.script.common import TEAM_FOLLOWS, TEAM_COMMANDS  # noqa: E402,F401  (the script vocabulary, L6)
from engine.script.common import SHOW_FLAG, SCENE_FLAG, WON, LOST  # noqa: E402,F401  (flags SET_FLAG reads, L6)

DT = simloop.DT                 # seconds a tick (the frame loop's, simloop.DT)
UNTIL = 1800.0                  # a run stops here at the latest (30 minutes)
QUIET = 120.0                   # nothing pending this long and no ending: stuck

from engine.objects.power import SUPERWEAPON_HITS, RELOAD_LAG, CURTAIN, hit_at, UNPACK_POWER, PACK_POWER, PACK_FRAMES  # noqa: E402,F401  (special powers, L2)
CIV = simworld.CIV
# The container's (Heidelberg, retail a03's SidesList) sides with aiTactical 255 (aiTeamBuilder alike); StartingUnits
# and Soviet_5 are 240 (retail data read 11-14, round 216): Sim.tactical
TACTICAL_SIDES = {'Player_1', 'Player_2', 'Soviet_1', 'Soviet_2', 'Soviet_3', 'Soviet_4', 'Soviet_6'}
from engine.script.common import CMP, SURFACES, RELATION_OF  # noqa: E402,F401  (a condition's comparison / surface / relation, L6)
LEVELS = {'easy': 0, 'normal': 1, 'hard': 2}
NEAR = 800.0                    # an enemy this close to something of the player's is a threat (the tension curve)
ATTACK_SLACK = 10.0             # R3: an attacker stops this far inside its range of the target (a guess)
from engine.objects.modifier import UNDERSIZE  # noqa: E402,F401  (a weapon reach less this, L2)
REACH = 300.0                  # 自动打掉: an enemy this close to something of the player's is being fought
SPREAD = 30.0                   # a reinforcement team's units this far apart round its waypoint (Sim.reinforce, INFERRED)
from engine.world.handle import GRID  # noqa: E402,F401  (routing cells, world units; L0)
HOLD_SPOTS = True              # every move's goal kept off other units' spots (Sim.claims): the game's (bench 11-09,
                               # a01's two infantry; checks/engine_spots.py, three trucks sent alone to one point)
ORE_PLATE = (60.0, 45.0)        # an ore node's base plate, half-extents (OreNode.xml's last BOX): Sim.goal_off_nodes
RALLY_PUSH = 40.0              # a new unit stops this far beyond its factory's NaturalRallyPoint, on the line from
                               # the factory's centre through it: INFERRED, fitted to bench 11-11 engine_production
                               # h / i (barracks, (40, 18): stops ~(75-80, 24-33)) and engine_rally tank (war
                               # factory, (80, 20): ~(112-127, 25-34); x 1.9 from the centre would be (152, 38))
from engine.objects.special import WFIRE_LAG, WFIRE_REAIM, NONE_TARGET_LAG  # noqa: E402,F401  (weapon-fire abilities, L2)
HIGH_STEP = 50.0                # ShroudClearingHeight's default: a viewer does not discover a cell this much above its own
                                # (bench, docs/engine/vision.md; a unit's own value is Body.clear_height). Cell by cell,
                                # no line of sight; ENEMY_SIGHTED is a range query and ignores it
FIRE_SEEN = 3.0                 # a bombarder (a weapon longer than its own vision) that fired this lately is seen
LAG = simloop.LAG               # the readings' clock (simloop.LAG)

# what the simulator assumes of the engine ("待对齐清单"): printed with every run that leans on one of them. Settled
# by the Generals / Zero Hour source (docs/engine/script-semantics.md, the section given) unless marked 未对齐: those
# the source cannot tell for RA3, for the bench to settle last
ALIGN = {**kernel_factory.align(), **simheal.ALIGN,     # the kernel modules' own lines, the area heal's
    'levelup': '部分对齐：创建升级触发升阶、移除重给、等级伤害/血量、英雄射程RANGE125%及幻影英雄离散射速120%有效周期25→20帧（engine_levelup a/b/c、engine_leveldamage a、engine_levelhealth a/b、engine_levelrange a、engine_levelrate a）；其他武器射速、计时分段、其余等级属性与经验成长未模拟',
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
    'column march': '3+ infantry sent together stop in a block, ceil(sqrt(n)) files 40 apart, rows 40 back from the '
                    'point, turned with the way in (bench 2026-11-17 engine_column; simpath.block)',
    'death linger': 'a killed unit is gone from areas and counts from the next reading: LINGER 0 (bench 2026-10-28, '
                    'probe death; the Generals source keeps it while it dies, 源码 4.2)',
    'both endings': '未对齐: won and lost in one frame: Generals runs the frame\'s later scripts and takes the last; '
                    'RA3\'s "Mission Won" / "Mission Lost" flags are its own (源码 4.5)',
    'inverted': 'a NOT condition is read off a flag two every-frame scripts first in the list keep (parts.unnot), so '
                'it sees the frame\'s top (bench engine_toggle 第四行 1001) -- the game ignores the inverted bit of a .map\'s own scripts (bench 2026-10-29, '
                'probe align; retail\'s scripts are compiled into the stream)',
    'frame rate': 'the scripts run in the public executor (engine/script/executor.py, script-semantics.md): 15 frames a '
                  'second (bench 10-28 probe align), a timer ceil(seconds x 15) frames counted down before the scripts, '
                  'counters and timers in one table (源码 3); units move and fight once a DT tick, on its first frame',
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
    'freeze': 'the cryo beam (SecondaryDamageNugget, engine/modules/freeze.py): its Amount a shot (x RATE_OF_FIRE) adds to '
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
from engine.script.common import RA3_ONLY  # noqa: E402,F401  (RA3's own actions and conditions, L6)

from engine.world.handle import GAP_WEAPON, GAP_UPGRADE, GAP_ACTION, GAP_CONDITION, GAP_COMMAND, GAP_STATUS  # noqa: E402,F401
from engine.objects.status import ACTED_STATUS, AI_ONLY_STATUS  # noqa: E402,F401  (status bits acted on, L2)
from engine.script.common import BUTTON_ACTIONS, refined  # noqa: E402,F401  (an action's refined name, L6)


from engine.script.common import SHOWN, IGNORED  # noqa: E402,F401  (logged-only / dropped actions, L6)
# HAS_FINISHED_AUDIO / _VIDEO (work/re/l2_scripts1.md 2.3 / 2.4): the game waits for the clients' end-of-play report,
# not a time; we place it. A dubbed line, x1 as a player hears it (bench 11-04 checks/engine_dialog.py): heard
# AUDIO_LEAD s after the play, done at its length after that (4.34 s line -> 5.3 s). A radar clip (bench movie.py
# play): done its own length after the play (CNVTEST01, 95 frames at 23.976 = 3.96 s: 63 game frames, 4.2 s);
# a full-screen one never reads done. Lengths we cannot read (a retail line, a retail clip) take the guesses below.
AUDIO_LEAD, AUDIO_GUESS, VIDEO_GUESS = 0.9, 2.5, 4.0
SOUND_PLAYS = ('PLAY_SOUND_EFFECT', 'PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT')
from engine.script.act_player import AI_SWITCHES  # noqa: E402,F401  (simai reads sim.AI_SWITCHES)

# ---- the engine line's script engine (ADR 0019 layer 1). Where it is not on this computer (a clean clone) the
# public executor runs the scripts (engine/script/executor.py): once a frame, timers in frames, NOT as a plain negation.
from engine.script.host import SEEN_CORE, CHANGES  # noqa: E402,F401  (what the world watches of the plug-in's core actions, L6)
_MODEL = {}


def engine_model():
    """RA3-EngineModel's ra3model/scripts.py (labpaths.ENGINE_MODEL, CNV_ENGINE_MODEL overrides it) as a module, or
    None where it is not there. Loaded by file: this adds nothing to sys.path, and the model's code stays in its own
    private repository (ADR 0018). Only the commit inventory_model.rev pins loads (modelpin.check, ADR 0030)."""
    import labpaths
    import modelpin
    path = os.path.join(labpaths.ENGINE_MODEL, 'ra3model', 'scripts.py')
    if os.path.isfile(path):
        modelpin.check(labpaths.ENGINE_MODEL)
    if path not in _MODEL:
        mod = None
        if os.path.isfile(path):
            name = 'ra3model_scripts'
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod             # dataclasses look their module up while the file runs
            spec.loader.exec_module(mod)
        _MODEL[path] = mod and (mod, scriptplugin.plug(mod))
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


@dataclasses.dataclass
class Body(kernel_module.Thing):
    """An object in the simulated world."""
    name: str
    template: str
    owner: str
    x: float
    y: float
    vision: float = 0.0
    kinds: frozenset = frozenset()
    immune_until: int = -1          # the frame an Iron Curtain's protection ends (weapons and superweapons, not scripts)
    armor: dict = dataclasses.field(default_factory=dict)      # damage type -> percent taken (simunits.fight)
    radius: float = 0.0                                         # R8: Geometry's bounding circle (simunits.radius)
    sight: float = 0.0                                          # R8: its VisionRange alone (vision: with the shroud)
    alive: bool = simliving.Alive()
    deleted: bool = False
    close_since: float = None                                   # since the enemy came within the player's REACH (自动打掉)
    made_by: str = ''                                           # the script that created it
    made_at: float = 0.0
    scenery: bool = False
    team: str = ''
    instance: int = 0                   # which instance of a team template (CREATE_REINFORCEMENT_TEAM: 1, 2, ...)
    guessed: list = dataclasses.field(default_factory=list)    # what of its numbers simunits only guessed
    clear_height: float = HIGH_STEP                             # its ShroudClearingHeight (simunits: 50 unless written)
    angle: float = 0.0
    status: set = dataclasses.field(default_factory=set)       # IMMOBILE (stays put), UNATTACKABLE (the player
                                                                # cannot destroy it) ...
    attachment_status: set = dataclasses.field(default_factory=set)  # owned by direct attachment links, not scripts
    lift_status: set = dataclasses.field(default_factory=set)  # survives timer release; landing is unresolved
    upgrades: set = dataclasses.field(default_factory=set)     # NAMED_RECEIVE_UPGRADE / _REMOVE_UPGRADE (modify)
    up_since: dict = dataclasses.field(default_factory=dict)   # upgrade -> the frame it was given (a Duration runs)
    level_rank: int = 1                                      # LevelUpUpgrade creation grants; not combat XP (the Object's ExperienceTracker, no module's: M12)
    script_status: set = dataclasses.field(default_factory=set)  # persistent script/startup bits; `status` is these
                                                                # + the modifiers' (modify)
    auras_on: dict = dataclasses.field(default_factory=dict)   # modifier id -> (until frame, xml) an aura hung on it
    shielded: bool = False                                      # INVULNERABLE + Iron Curtain bits on it (simunits.effect)
    taken: float = 1.0                                          # ARMOR factor: damage taken x (INFERRED)
    model_conditions: dict = dataclasses.field(default_factory=dict)  # condition -> expiry frame or None
    dealt: float = 1.0                                          # DAMAGE_MULT x RATE_OF_FIRE: damage dealt x (INFERRED)
    level_rate: float = 1.0                                     # measured heroic Mirage clip rate; never per-hit damage
    level_vision: float = 1.0                                   # ENEMY_SIGHTED only; heroic auto-acquire not benched
    base: dict = None                                           # speed, vision, sight, weapons before modifiers
    died_at: float = None                                       # killed or deleted then
    fired_at: float = None                                      # a bombarder's last shot (seen by all a while)
    building: tuple = None                                      # (structure, (x, y), stand): told to build there (R5)
    replace: bool = False                                       # building = its ReplaceSelfSpecialAbility: it turns into it
    drive_speed: float = 0.0
    jet_started: bool = False
    z: float = None                                         # None: on terrain; airborne MetaImpact sets world z
    unpack_parent: object = None                                # SpawnOnUnpack's producer, outlived and never replaced (M10)

    def _require_body(self):
        body = self.find(kernel_interfaces.Body)
        if body is None:
            raise RuntimeError(f'{self.name!r} is missing a Body module')
        return body

    def damage(self, amount):     # the Body module's (engine/modules/body.py, step B2b): down to its floor, a prop none
        self._require_body().attempt_damage(amount)

    def mend(self, amount):     # up by `amount`, at most the maximum (math.inf: to full); every heal (step K2)
        self._require_body().attempt_healing(amount)

    @property
    def health(self):           # percent of its maximum, what the scripts read; a PropBody's 0 (engine_propbody a)
        body = self.find(kernel_interfaces.Body)
        return 100.0 if body is None else body.percent()   # the bare body's 100 HP / 100 MaxHP defaults

    @health.setter
    def health(self, pct):
        self.find(kernel_interfaces.Body).set_percent(pct)

    def set_hp(self, hp, max_hp=None, tell=True):     # the one write (B1, the module's set_health since B2b)
        self._require_body().set_health(hp, max_hp, tell)

    def set_last_damage(self, player, by=None):     # every hit names its source (step B3: the Body module's)
        self.find(kernel_interfaces.Body).set_last_damage(player, by)
    FORWARDS = ('hp', 'max_hp', 'health_floor', 'immortal', 'prop', 'last_hit', 'last_by', 'indestructible',  # read only
                'read_until', 'life_end', 'topple', 'toppled', 'topple_end', 'crusher', 'crushable', 'deposit', 'deposit_at',
                'toggle_at', 'armor_up', 'suppression_rule', 'suppression_hits', 'suppressed', 'suppressed_until',
                'suppression_next', 'attachment_rules', 'spawned_children', 'spawn_refills', 'spawn_parent',
                'spawn_module', 'ready_at', 'mine', 'unpack_end', 'sell_end', 'cold', 'cold_step', 'level_modules',
                'lies', 'linger', 'weapons', 'slots', 'speed', 'surface', 'turn_rate', 'turn_first', 'path', 'dest', 'face',
                'hold_fire', 'hold_paused', 'stance', 'ai_acquire', 'acquire', 'goal', 'mode', 'set_off', 'stood_for', 'frame_move', 'jet_motion', 'rolling', 'carry', 'stops_at',
                'chase', 'home', 'auto_to', 'resume', 'spot', 'engaged', 'follow', 'move_to')
    hp = kernel_module.forward(kernel_interfaces.Body, lambda m: m.health(), 100.0)     # step B2b: the Body
    max_hp = kernel_module.forward(kernel_interfaces.Body, lambda m: m.max_health(), 100.0)     # module's
    health_floor = kernel_module.forward(kernel_interfaces.Body, lambda m: m.floor(), 1.0)
    immortal = kernel_module.forward(kernel_interfaces.Body, lambda m: m.is_immortal(), False)
    prop = kernel_module.forward(kernel_interfaces.Body, lambda m: m.prop_death())    # None / 'stays' / 'dies'
    last_hit = kernel_module.forward(kernel_interfaces.Body, lambda m: m.last_damage()[0])  # B3: player (None for script kills or no hit)
    last_by = kernel_module.forward(kernel_interfaces.Body, lambda m: m.last_damage()[1])  # attacking object (None for script hits)
    indestructible = kernel_module.forward(kernel_interfaces.Body, lambda m: m.is_indestructible(), False)
    read_until = kernel_module.forward(kernel_interfaces.Body, lambda m: m.bits_read_until())     # step B4a
    life_end = kernel_module.forward(kernel_interfaces.Lifetime, lambda m: m.die_frame())     # step M1
    topple = kernel_module.forward(kernel_interfaces.Topple, lambda m: m.rules())           # step M2: its rules
    toppled = kernel_module.forward(kernel_interfaces.Topple, lambda m: m.is_toppled(), False)
    topple_end = kernel_module.forward(kernel_interfaces.Topple, lambda m: m.gone_frame())
    crusher = kernel_module.forward(kernel_interfaces.Crush, lambda m: m.crusher_level(), 0)    # step M3: drives over
    crushable = kernel_module.forward(kernel_interfaces.Crush, lambda m: m.crushable_level())  # a lower level
    deposit = kernel_module.forward(kernel_interfaces.Deposit, lambda m: m.rules())     # step M4: (bonus, amount, frames)
    deposit_at = kernel_module.forward(kernel_interfaces.Deposit, lambda m: m.next_frame())
    toggle_at = kernel_module.forward(kernel_interfaces.Toggle, simtoggle.toggle_at, {})   # step M5: {index: state}
    armor_up = kernel_module.forward(kernel_interfaces.Toggle, simtoggle.armor_up, False)  # the miner's armour
    suppression_rule = kernel_module.forward(kernel_interfaces.Suppression, lambda m: m.rules())    # step M6
    suppression_hits = kernel_module.forward(kernel_interfaces.Suppression, lambda m: m.hits(), ())  # (end, value)
    suppressed = kernel_module.forward(kernel_interfaces.Suppression, lambda m: m.is_suppressed(), False)  # a model
    suppressed_until = kernel_module.forward(kernel_interfaces.Suppression, lambda m: m.until(), -1)  # condition
    suppression_next = kernel_module.forward(kernel_interfaces.Suppression, lambda m: m.next_sample(), 0)
    attachment_rules = kernel_module.forward(kernel_interfaces.Attach,      # step M7: {module id: rule or False}
                                             lambda ms: {m.module_id(): m.rule() for m in ms}, {})
    spawned_children = kernel_module.forward(kernel_interfaces.Spawn, lambda ms: [c for m in ms for c in m.children()],
                                             [])                            # what its SpawnBehaviors made
    spawn_refills = kernel_module.forward(kernel_interfaces.Spawn, lambda ms: [r for m in ms for r in m.refills()], [])
    spawn_parent = kernel_module.forward(kernel_interfaces.Slaved, lambda m: m.slaver())   # its SlavedUpdate's maker
    spawn_module = kernel_module.forward(kernel_interfaces.Slaved, lambda m: m.slaver_module(), '')
    ready_at = kernel_module.forward(kernel_interfaces.SpecialPower, simpower.ready_at, {})  # step M8: {power: frame}
    mine = kernel_module.forward(kernel_interfaces.OreMiner, lambda m: m.trip())    # step M9: a miner's trip
    unpack_end = kernel_module.forward(kernel_interfaces.Unpack, lambda m: m.end_frame())   # step M10: unpacking
    sell_end = kernel_module.forward(kernel_interfaces.Sell, lambda m: m.gone_frame())      # till; a sale's delete
    cold = kernel_module.forward(kernel_interfaces.Freeze, lambda m: m.held(), 0.0)    # step M11: the cryo beam's cold
    cold_step = kernel_module.forward(kernel_interfaces.Freeze, lambda m: m.stage(), -1)     # its highest EffectInfo
    level_modules = kernel_module.forward(kernel_interfaces.LevelUp, lambda ms: {m.module_id() for m in ms if m.active()}, set())  # M12: ids in force
    lies = kernel_module.forward(kernel_interfaces.SlowDeath, kernel_slowdeath.lies, 0.0)   # step B5a: its SlowDeath's
    linger = kernel_module.forward(kernel_interfaces.SlowDeath, kernel_slowdeath.linger,    # delay; how long this
                                   kernel_slowdeath.LINGER)                                 # death lies (a crush: it)
    weapons = kernel_module.forward(kernel_interfaces.WeaponSet, lambda m: m.held(), [])    # step W2: its guns; the
    slots = kernel_module.forward(kernel_interfaces.WeaponSet, lambda m: m.choices())   # ones by status (None: fixed)
    speed = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.speed, 0.0)    # M2 step 2: its
    surface = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.surface, 'ground')    # LocomotorState
    turn_rate = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.turn_rate)
    turn_first = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.turn_first, False)
    path = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.path, [], locomotor.writer('path'))  # M2 3:
    dest = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.dest, None, locomotor.writer('dest'))  # the
    face = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.face, None, locomotor.writer('face'))  # way
    hold_fire = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.hold_fire, False)  # C2a: its
    hold_paused = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.hold_paused, False)  # AIOrderState
    stance = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.stance, 0)
    ai_acquire = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.ai_acquire, False)
    acquire = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.acquire, frozenset(), aiupdate.writer('acquire'))
    goal = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.goal, None, aiupdate.writer('goal'))  # C2b
    mode = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.mode, 'idle', aiupdate.writer('mode'))
    chase = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.chase)      # C3: fight_step's
    home = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.home)
    auto_to = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.auto_to)
    resume = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.resume)
    spot = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.spot)
    engaged = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.engaged, False)
    follow = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.follow)    # C4: order.py's
    move_to = kernel_module.forward(kernel_interfaces.AIUpdate, lambda m: m.move_to)
    ground_fire = aiupdate.ground_fire                  # no forward: in the record only once written
    aiupdate = property(aiupdate.of)                    # the module itself (attached at its first setting)
    set_off = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.set_off, -1)      # M3 1: go_to's
    stood_for = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.stood_for)     # (Sim.on_the_move,
    frame_move = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.frame_move, False)    # Sim.move,
    jet_motion = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.jet_motion)   # simjet read them)
    rolling = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.rolling, False)  # M3 3: drive's
    carry = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.carry, 0.0)
    stops_at = kernel_module.forward(kernel_interfaces.Locomotor, lambda m: m.stops_at, -1.0)

from engine.world.handle import inside, same_team  # noqa: E402,F401  (point in polygon, a team as a script names it, L0)


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
    """A player's low-power speed (RA3 1.13, work/re/l2_production.md; docs/engine/production.md): 1 - (1 - min(1, supply / demand))
    x penalty, at least min, and while short at most max (retail: short of power is 0.3 to 0.5 whatever the
    shortfall); <= 0 -> 0.01. 1.0 with enough power."""
    r = 1.0 if demand == 0 else min(1.0, f32(supply / demand))
    f = 1.0 - (1.0 - r) * rules['penalty']
    f = max(f, rules['min'])
    if r < 1.0:
        f = min(f, rules['max'])
    return f32(f) if f > 0 else f32(0.01)


from engine.world.handle import mmss  # noqa: E402,F401  (m:ss, L0; autoplay / offline / batch read sim.mmss)


def seconds(s):
    s = str(s).strip()
    if ':' in s:
        m, sec = s.split(':')
        return 60 * float(m) + float(sec)
    return float(s)


def _late(sim, f):
    """Sim.LATE's part f, made on first use (a Sim built without __init__ has none yet)."""
    m = sim.__dict__.get(f)
    if m is None:
        m = type(sim).LATE[f]()
        setattr(sim, f, m)
    return m


class Sim:
    LATE = {'modifiers': simmodifier.Modifiers, 'life': simbody.Life, 'specials': simspecial.Specials,   # the parts
            'harm': simdamage.Damage}       # made on first use (_late); simsnap.check makes one a snapshot has by it
    model_scripts = False               # the model's plug-in runs the scripts (its tables): simexec.attach
    shot_clock = False                  # opt-in frame clock: discrete shots and movement between script frames;
                                        # default movement retains its benched coarse tick (work/re/handoff-c.md)
    player_ups = types.MappingProxyType({})     # read-only "nothing granted" for a Sim built without __init__ (the
                                                # tests' bare worlds); __init__ gives each Sim its own dict

    def __init__(self, mission, test=None, level='normal', script='', model=True, executor=None):
        """model: run the scripts in the engine line's model where it is on this computer (False: the older loop).
        executor 'public': the public executor on the model's world all the same (simexec.attach)."""
        self.m = mission
        self.retail = getattr(mission, 'RETAIL', False)      # a retail campaign map (retail.py): its own scripts
        self.mm = mission.merged(test) if self.retail else parts.merged(mission, test)
        self.test = test
        self.level = LEVELS[level]
        self.t, self.clock = 0.0, simworld.FrameClock()  # the frame now: its clock (the model's: simexec.attach)
        self.log = []                       # (t, kind, text)
        self.box_log = []                   # [start, end, text]: the caption box holds one line; a new one ends the one up
        self.panel_log = []                 # groups of (t, text): the dialogue panel stacks subtitles, a group clears together
        self.asked, self.up = {}, []        # a 功能 caption asked for (flag -> t), and shown: (flag, asked, shown)
        self.scenes = []                    # [start, end] of each 过场 (end None while it runs)
        self.world = kernel_world.World(lambda t, tag: simunits.module_blocks(t, tag, self.own),   # engine/kernel
                                        kill=lambda b, why, death, cause: self.destroy(b, why, death, cause),
                                        create=lambda b, ocl, air: self._life().create(
                                            self, b, ocl, air, self.death_blasts,
                                            lambda x, y: simdamage.impact_ground_z(self, x, y)),
                                        fire=lambda b, weapon: self._life().fire(self, b, weapon, self.death_blasts),
                                        remove=lambda b, why: self.delete(b, why), modify=lambda b: self.modify(b),
                                        pay=lambda b, amount: self.wallet.deposit(b.owner, amount),
                                        toggled=lambda b, m: simtoggle.entered(self, b, m, self.modify),
                                        suppression_at=lambda b, f: simdamage.suppression_at(
                                            self.suppression_fields, b, f),
                                        spawn=lambda b, m, template: self.spawn_child(b, m, template, self.t),
                                        vacate=lambda b, delete: self.garrison.died(b, delete))
        self.used = self.world.used         # ALIGN keys the run leaned on
        self.unknown = {}                   # condition / action names the simulator does not know: count
        self.unmodeled = self.world.gaps    # (kind, name) -> {'n', 't' first met, 'what'}: Sim.gap
        self.declared = {}                  # template -> the weapons its XML names (simunits.declared_weapons), asked once
        self.flags, self.counters, self.timers = {}, {}, {}
        self.objectives = {}                # name -> status (0 hidden, 1 shown, 2 done, 3 failed)
        self.markers = {}                   # objective -> {object / waypoint}
        self.banned = set()                 # (player, template in lower case): ALLOW_DISALLOW_ONE_BUILDING 0
        self.unit_construction_disabled = set()  # named players; engine_unitban a/b native engineer queues
        self.base_construction_disabled = set()  # named players; aibgate:a the skirmish AI's structure orders (simai)
        self.ai_paused = set()              # named players PLAYER_TOGGLE_SKIRMISH_AI(p, 0) paused (simai Brain.tick)
        self.buildable = {}                 # template lower -> BuildableStatus 0-3: TECHTREE_MODIFY_BUILDABILITY_OBJECT (all players)
        self.banned_ups = set()             # (player, upgrade in lower case): ALLOW_DISALLOW_ONE_UPGRADE 0
        self.border = 0
        self.reveal_all = False             # the player's MAP_REVEAL_ALL_PERM
        self.reveal_all_until = -1          # the player's MAP_REVEAL_ALL: the whole map open until this frame
        self.revealed_to = set()            # other players given MAP_REVEAL_ALL (side_sees: they see everything)
        self.reveals = {}                   # name -> (x, y, r)
        self.peeks = []                     # (x, y, r, until frame): MAP_REVEAL_AT_WAYPOINT, back to fog at `until`
        self.reveal_areas = {}              # reveal name -> area: the player's MAP_REVEAL_PERMANENTLY_IN_TRIGGER
        self.seq = []                       # UNIT_EXECUTE_SEQUENTIAL_SCRIPT records, in queue order (seq_due)
        self.reshroud = 10.0                # MAP_SHROUD_SET_RESHROUD_TIME seconds (retail default holds as 10)
        self.camera = None
        self.camera_been = set()            # areas the camera's point has been in (CAMERA_ENTERED_AREA latches)
        self.personality_of = {}            # player -> the personality its AI took when not the map's aiPersonality
        #                                     (simai SimAI.assigned, work/re d123 1.2: an open skirmish gate)
        self.input = True
        self.countdowns = set()
        self.ending = None
        self.both = None                    # won and lost in one frame: (first, second)
        self.ra3_only = set()               # RA3-only action / condition names the run used
        self.last_change = 0.0
        self.ai = {}                        # player -> woken at
        self.handed = ()                    # skirmish_setup: players taken off their teams after the first frame
        self.library_ai = frozenset()       # the same players, kept (the wake: Sim.act SKIRMISH_AI_MAKE_BASE)
        self.ai_switches = {}               # player -> {AI_SWITCHES name: value} (simai.Brain reads them)
        self.ai_priorities = {}             # player -> [(enemy, n)] SET_ENEMY_PLAYER_PRIORITY calls (simai.Brain)
        self.hidden_home = set()            # players whose hidden object SKIRMISH_AI_TRANSFER_ALL(p, 0) put on the
                                            # map default team (one more member there; engine_acts_z all)
        self.audio_end = {}                 # sound event -> when HAS_FINISHED_AUDIO holds again (Sim.played)
        self.video_end = {}                 # clip -> when HAS_FINISHED_VIDEO holds (None: never, a full-screen one)
        self.wallet = simmoney.Money()      # the players' money (L4); the four names below are its dicts, shared
        self.money, self.income = self.wallet.money, self.wallet.income
        self.sharing, self.money_cap = self.wallet.sharing, self.wallet.money_cap
        self.selected = None                # the object SELECT_OBJECT selected last (NAMED_SELECTED)
        self.script_disabled = {}           # body.serial -> NAMED_SET_DISABLED types on (emp_disabled)
        self.kills = []                     # (killer's player, killer's name, template, name) by weapon (cond_retail)
        self.attacked_by = set()            # (player hit, player hitting): SKIRMISH_PLAYER_HAS_BEEN_ATTACKED_BY_PLAYER
        self.cond_memory = {}               # a condition's reading the frame before (NAMED_EXITED_AREA)
        self.made_frame = {}                # team template -> frame its last instance was made by a script (TEAM_CREATED)
        self._engineer_rules = {}           # template -> EngineerContain rule (mission XML is fixed)
        self.mining = simmine.Mining()      # ore nodes and the harvesters' trips (L2)
        self.relations = dict(getattr(mission, 'relations', {}))   # (a, b) -> Enemy / Neutral / Friend
        self.team_team_rel, self.team_player_rel, self.player_team_rel = {}, {}, {}   # the overrides (hostile)
        self.team_targets = {}                  # body.serial -> the team it was told to attack (TEAM_ATTACK_TEAM)
        self.players = dict(mission.map.PLAYERS)
        self.human = self.players['p1']
        self.foe = self.players.get('s1')
        import engine.players.tech as simtech
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
        # Retail objects replaced by linked assets must use the same XML as
        # the built mod (E167 removes only the factory's Tech2 receiver).
        for _, xml, link in getattr(self.mm, 'assets', ()):    # a retail map (Merged) links none
            if link.startswith('GameObject:'):
                self.own[link.split(':', 1)[1]] = xml
        import engine.objects.repair as simrepair
        self.repairs = simrepair.Repairs(self, self.wallet, self.ai_switches, self.level)
        import engine.objects.assign as simassign
        self.assignments = simassign.Assignments(self)
        self.heal = simheal.Heal()          # AutoHeal / PassiveAreaEffect (L2)
        self.hunts = []                     # TEAM_HUNT's crews: [movers, target, frame to re-pick at] (Sim.hunt_due)
        self.garrison = simgarrison.Garrisons(self, simgarrison.Peers(self))    # GarrisonContain / ContestableGarrisonContain
        self.infiltrators = siminfiltrator.Infiltrators(self, siminfiltrator.Peers(self), self.wallet)
        self.bodies = {}                    # name -> Body (named ones), plus unnamed under '#k'
        self.attachments = {}              # child serial -> (child, parent, module rule): by the thing (11-19 sweep)
        self.lift_timers = simunits.LiftTimers()
        self._attachment_marked = {}       # serial -> the thing its attachment status was set on
        self.attachment_known_status = {'ATTACHED'}
        self.suppression_fields = []        # (end, value, x, y, radius): stationary hit contributions
        self.topples = []                   # ToppleUpdate objects; neutral props can be knocked over too
        self.frame_movers = {}              # topple contact paths and measured Jet startup
        self.refs, self.acting = {}, {}     # UNITRef name -> the Body SET_REF_TO_... set; acting: simseq._as_itself
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
        self.blasts = []                    # (frame, x, y, [(distance, damage)], owner, by): a superweapon's hits
        self.casts = []                     # (frame, owner, power, caster's serial, (x, y) or None): PLAYER_TRIGGERED_SPECIAL_POWER
        self.power_at = {}                  # (player, spellbook power lower) -> the frame it is ready from (spellbook_ready)
        self.production = simproduce.Production(self, simproduce.Peers(self))     # the factories' queues, run (S7b)
        self.energies = {}                  # template -> EnergyProduction (simunits.energy; power)
        self.player_ups = {}                # player -> upgrades GIVE_PLAYER_UPGRADE gave (a unit's NeededUpgrade)
        self.templates = getattr(self.mm, 'templates', None) or {}     # team templates (Sim.reinforce)
        self.instances = {}                 # team template -> instances made so far
        # callables name -> (exists, [Body]) or None (not theirs): teams scripts read by a name no map gives -- the
        # AI's strategic-state teams and its pool (simai.Brain.team_named); the first that answers is the team
        self.team_names = []
        teams = getattr(mission.map, 'TEAMS', {})
        self.active = set(teams.values())               # teams with an instance: a whole-team order to any other is lost (E3)
        self.lost_orders = []                           # (t, script, order, team) given to a team nobody had joined
        for o, key in simworld.load_keys(self, list(getattr(mission.map, 'OBJECTS', [])) + self.mm.objects):
            b = self.add(key, o.template, self.owner_of(o.side), o.x, o.y, shadow=True)  # simliving
            # a bare object is on its player's default team (island.like writes 'Soviet_5/teamSoviet_5'; the container
            # has teamSoviet_2 .. 6 too): bench 11-14 engine_acts_x own, PLAYER_TRANSFER_OWNERSHIP_PLAYER leaves it
            b.team = teams.get(o.side) or (self.mm.team(o.side) if hasattr(self.mm, 'team')    # a retail map (Merged)
                                           and o.side in getattr(mission.map, 'PLAYERS', {}) else '')  # names no teams
            health = (getattr(o, 'props', None) or {}).get('objectInitialHealth')
            if isinstance(health, (int, float)) and 0 < health < 100:     # the map's starting health, in percent
                b.set_hp(b.max_hp * health / 100.0, tell=False)             # (a7 win: the carrier placed at 1 %)
            crew = (getattr(o, 'props', None) or {}).get('originalOwner')
            if isinstance(crew, str):                   # placed in a team of the mission's own (K6): that team has a member
                b.team = crew
                self.active.add(crew)
            b.angle = facing(o)                         # as the built map puts it (the player's north, others' south)
        import platprops
        for k, o in enumerate(getattr(mission.map, 'SCENERY', [])):
            if o.template in platprops.STRUCTURE:
                b = self.add(simworld.free_key(self, '#scenery {}'.format, k), o.template, CIV, o.x, o.y)
                b.scenery = True
                b.kinds = frozenset(b.kinds | {'STRUCTURE'})
        self.script = parse_script(script)
        self.auto_kill = next((e[2] for e in self.script if e[1] == '自动打掉'), None)
        self.combat = not any(e[1] == '不打' for e in self.script)
        self.high = not any(e[1] == '高地不挡' for e in self.script)
        # what nobody shoots unless ordered: our ice walls (units with a lifetime; bench 2026-10-28, a4 hold)
        self.unshot = {u.id for u in self.mm.units if 'lifetime' in (getattr(u, 'params', None) or {})}
        self.seen = {}                      # this tick: (side, body.serial) -> whether that side sees it
        self.firing = []                    # this tick's aimed fire: (target, damage per second, shooter) (fight, deal)
        self.mid_aims = {}                  # id -> (second, body): an attack-mover that got in range mid-tick (move)
        self._field = ((), (), ())          # this tick's fight_field (fight)
        self.first_death = None             # (t, body, killer): the fight's first death
        self.death_blasts = []              # (frame, x, y, damage, type, radius, affects, owner, by): FireWeaponWhenDead
        self.sweeps = simsweep.Sweeps(self, simsweep.Peers(self))  # ActivateLinearDamageNugget + LinearDamageUpdate: the lines walking
        self.events = sorted((e for e in self.script if isinstance(e[0], float)), key=lambda e: e[0])
        self.anchored = [e for e in self.script if isinstance(e[0], tuple)]       # (('@', flag, delta), verb, ...)
        self.commands = command_port.Commands(self)     # the command port: one per run (happen's orders, the givers')
        self.areas = Areas(self.mm.areas)
        # the map's hot spots (MissionHotSpots): name -> on; off at the start, only SET_..._ACTIVENESS (and the player's
        # popup, not simulated) turns one on or off (d115_script_semantics.md 4). The name as written: bench 11-13
        # engine_conds sight 热点&8, the lower-case name never on
        self.hotspots = {str(k): False for k in getattr(self.mm, 'hotspots', {}) or {}}
        self.waypoints = dict(self.mm.waypoints)    # the run's own: a waypoint moved in it is not the mission's
        self.reblock()
        # the script executor port (engine/ports/scripts.py): the model's plug-in where it is, else the public one
        simexec.attach(self, engine_model() if model else None, executor, skirmish_setup, parts)

    def blocks(self, b, place=False):
        """What of the way a body takes up: a wall of ours its bar (or disc, square), a building its round. place:
        what a new structure's placement keeps clear of instead (an ore node's round, not its routing plate)."""
        if b.topple:
            return None                    # engine_topple: vehicles drive straight through, infantry can pass too
        if b.template in self.walls:
            p = self.walls[b.template]
            if p.get('shape') == 'disc':
                return (b.x, b.y, p['length'] / 2)
            return (b.x, b.y, b.angle, p['length'], p['length'] if p.get('shape') == 'square' else p['thick'])
        if 'ORE_NODE' in b.kinds and b.radius:
            # its own bounding circle (box 33 x 41 -> 52.6), not the 40 a building out of platprops gets: with 40 the
            # SimpleExpansion miner's way to its slot 67 behind the node slid past it 45 off and unpacked inside
            # Distance 50 (aiexpb50); the bench miner goes round, never nearer than 89 (D round 168/169). D176: its
            # base plate (ORE_PLATE) grown by GRID, a 2-cell unit's half footprint (goal_off_nodes' rule on the
            # routing grid's corners); with the circle aiexpb200's miner came at the node from the south and
            # unpacked at (4127, 2788), with the plate from the west, (4014, 2847) -- the bench (4012, 2903).
            # INFERRED: one clearance for every unit's size. A structure's placement keeps the round (place): with
            # the plate the refinery search found no third refinery's spot (test_simai_bench_b third_refinery)
            if place:
                return (b.x, b.y, b.radius)
            return (b.x, b.y, b.angle, 2 * (ORE_PLATE[0] + GRID), 2 * (ORE_PLATE[1] + GRID))
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
        bodies = self.living()
        self.ground.set_blocks([s for s in (self.blocks(b) for b in bodies) if s],
                               [s for s in (self.blocks(b, place=True) for b in bodies) if s])

    # ---- the world
    def owner_of(self, side):
        return self.players.get(side, CIV)

    def proto(self, template, owner):
        """A Body of the template that is not in the world (made by add, then taken out of the registry again):
        what the skirmish AI reads a template's figures off (simai Brain._proto)."""
        name = simworld.free_key(self, lambda n: f'__proto_{owner}_{template}' + '#' * n, 0)
        b = self.add(name, template, owner, -1e6, -1e6)
        self.world.drop(self.bodies.pop(name))
        return b

    def add(self, name, template, owner, x, y, by='', at=0.0, team='', shadow=False):
        if not shadow:                          # a living one's name: refused (ValueError); the map load's: shadowed
            simliving.refuse_living(self.bodies, name)
        st = simunits.stats(template, self.own)
        b = Body(name, template, owner, float(x), float(y), max(st['vision'] or 0.0, st['shroud'] or 0.0),
                 frozenset(st['kinds']), made_by=by, made_at=at)
        b.guessed, b.clear_height = st['guessed'], st['clear_height']
        b.radius, b.sight = st.get('radius') or 0.0, st['vision'] or 0.0
        f = simunits.fight(template, self.own)
        proxy_hp = None                         # the Body module's health is made below, once the modules are
        if self.world.blocks_of(template, 'ManagerBody'):
            proxy_hp = simunits.manager_proxy_health(template, self.own)
            self.gap('ManagerBody', template, '仅HB_Bridge_02整体代理脚本伤害已量；有效HP/内部下限映射INFERRED，其他配置、桥段生成、共享血量与维修未建模')
        wall_start = simunits.wall_builder_start(template, self.own)
        if wall_start:
            if not by and wall_start['secondary'] and wall_start['status'] == 'WALL_SEGMENT':
                b.script_status.add('WALL_SEGMENT')
                b.status.add('WALL_SEGMENT')
            self.gap('WallBuilderBehavior', template,
                     '仅预摆墙默认WALL_SEGMENT初始状态已量；运行时生成/建墙/连接/段数上限/生死联动、自定义状态与模型条件未建模；其他继承覆盖默认值INFERRED，脚本改位交互未测')
        b.armor, weapons = f['armor'], f['weapons']     # held by its WeaponSet module (step W2), armed below
        if template not in self.__dict__.setdefault('_wsets', {}):
            self._wsets[template] = simunits.weapon_sets(template, self.own)
        slots = self._wsets[template] if weapons else None    # guns not read at all stay a gap (below)
        for tm in self.toggles_of(b):         # a first ToggleState's bits hold from the start (engine_toggle c / e;
            b.status = set(b.status) | tm['states'][0]['status']      # Sim.modify keeps them; retail first states
                                                                      # have no AttributeModifier)
        if slots:                             # the weapon lines name a status: the held one is chosen from it
            weapons = simunits.pick_weapons(slots, b.status, self.weapon_upgrades(b))
        if not weapons:                       # its XML names guns and none was read: a gap, not a unit without guns
            if template not in self.declared:
                self.declared[template] = simunits.declared_weapons(template, self.own)
            if self.declared[template]:
                self.gap(GAP_WEAPON, template, f'XML 有 {", ".join(self.declared[template])}，读成没有武器')
        b.modules = self.world.build(b, self.clock.frame)     # none: the setter keeps it unset
        rate, first = locomotor.turns(simunits.turning(template, self.own), st['speed'], st['surface'])
        locomotor.write(self.world, b, speed=st['speed'], surface=st['surface'], turn_rate=rate, turn_first=first)
        kernel_weaponset.equip(self.world, b, weapons, slots, self.clock.frame)
        body = b.find(kernel_interfaces.Body) or self.world.attach(b, 'ActiveBody', self.clock.frame)  # no block: one
        b.acquire = frozenset(simunits.acquire(template, self.own)) if weapons else frozenset()    # AIOrderState
        hp = proxy_hp or (body.data.max_health if body.is_immortal() else f['hp'] or body.data.max_health)
        body.make(hp or (2000.0 if 'STRUCTURE' in b.kinds else 300.0), proxy_hp * 0.01 if proxy_hp else None,
                  body.kind() == 'PropBody' and simunits.prop_death(template, self.own))
        unpack = b.find(kernel_interfaces.Unpack) if by and 'STRUCTURE' in b.kinds else None
        if unpack and unpack.frames():          # made in the run (a map's own skip it): unpacks first -- adds no power
            v = np.float32(power_factor(*self.power(owner)))       # and does not fire meanwhile; RA3 1.13, work/re/l2_construction.md:
            extra = np.float32(np.float32(1.0) - v) * np.float32(unpack.frames())   # trunc((1 - v) F + F), v the
            unpack.set_end(self.frame_now() + int(np.float32(extra + np.float32(unpack.frames()))))  # owner's factor
        for m in b.find(kernel_interfaces.Attach):    # AttachUpdate (engine/modules/attach.py): the statuses its
            if m.rule():                              # links may set are known ones (simcond_object)
                self.attachment_known_status.update(m.rule()['child'] | m.rule()['parent'])
        if b.topple:                            # a ToppleUpdate (engine/modules/topple.py)
            import engine.objects.topple as simtopple
            a, c, _, _ = simtopple.shape(template, self.own)
            b.radius = math.hypot(a, c)
            b.vision = b.sight = 0.0         # a prop has no sight (stats' unit-only table otherwise guesses 100)
            self.topples.append(b)
        self.world.drop(self.bodies.get(name))  # a dead one under the same name leaves the world (a living one: above)
        self.bodies[name] = b
        spawns = b.find(kernel_interfaces.Spawn)    # SpawnBehavior (engine/modules/spawn.py)
        for m in spawns:
            if not m.unpack_child():
                continue
            if by:                      # built (simai gives the AI's its own, put) or a script's: not benched here
                self.gap('SpawnBehavior', template, '建成或脚本创建的矿场自带矿车（SpawnOnUnpack）出车时机未对拍')
                continue
            self.unpack_child(b, m.unpack_child(), at)
        for m in spawns:
            if m.unpack_child():
                continue
            self.gap('SpawnBehavior', template,
                     '仅盟军战车工厂配置开局3架、死亡10秒补充、母体清随从及缺电保持3架已量；子体直接删除、真正禁用、占领、缺电时死亡补充、'
                     '展开时机、其他配置未建模；生成位置INFERRED；不含SlavedUpdate/AttachUpdate维修')
            if not m.child() or by:     # construction/unpack and scripted creation have not been measured
                continue
            for i in range(3):
                self.spawn_child(b, m, m.child(), at)
        b.team = team                   # the team it is made into, set last (its spawn and unpack children keep '')
        return b

    def spawn_child(self, parent, spawner, template, at):
        """One thing a parent's Spawn module (engine/modules/spawn.py) makes: the measured drone group only; centre
        placement remains INFERRED (no autonomous repair flight). A child template without SlavedUpdate is given
        one (World.attach), so every child knows its maker."""
        k = len(parent.spawned_children)
        name = simworld.free_key(self, lambda n: f'#spawn {parent.name} {spawner.module_id()} {k}' + '#' * n, 0, self.bodies)
        child = self.add(name, template, parent.owner, parent.x, parent.y, by=parent.name, at=at)
        self.world.bind_slave(child, parent, spawner)
        spawner.adopt(child)
        return child

    def unpack_child(self, parent, template, at):
        """SpawnOnUnpack (engine/modules/spawn.py): a refinery the map places gives its one collector at the start, on
        its own spot (bench 2026-11-12 mineturn<k> / mineniag p: the first money by the drive from there; the spot and
        the 1 s fade INFERRED). Its own unit: it outlives the refinery (no SpawnedRequireSpawner)."""
        name = simworld.free_key(self, lambda n: f'#unpack {parent.name}' + '#' * n, 0, self.bodies)
        child = self.add(name, template, parent.owner, parent.x, parent.y, by=parent.name, at=at)
        child.unpack_parent = parent                # the owner's default team, as Generals' createSpawn (team '')
        return child

    def living(self, *, unspawned=False):
        return simliving.living(self.world, self.bodies, unspawned)

    # ---- orders: one unit's, and a team's (the same for each member: ctx.order gives teams only)
    def members(self, team):
        """A team's living members; a team template's (several instances: CREATE_REINFORCEMENT_TEAM) the OLDEST
        instance's that still has any (bench 11-10 engine_reinf old: the order by the name moved the first instance,
        not the one made since; an emptied instance giving the name to the next is INFERRED)."""
        named = self.named_team(team)
        if named is not None:
            return named[1]
        crew = [b for b in self.living() if same_team(b.team, team)]
        first = min((b.instance for b in crew), default=0)
        return [b for b in crew if b.instance == first]

    def add_team_lookup(self, look):
        """An AI's team-name lookup (team -> (exists, living members) or None), asked by named_team (simai Brain)."""
        self.team_names.append(look)

    def take_personality(self, player, personality):
        """The personality an AI player took when not the map's aiPersonality (simai; PLAYER_HAS_PERSONALITY reads it)."""
        self.personality_of[player] = personality

    def forget_sight(self):
        """This moment's sight cleared (side_sees' per-tick cache; fight clears it each tick too): the proxy's look."""
        self.seen = {}

    def named_team(self, team):
        """(exists, living members) of a team only a name gives (self.team_names: an AI's), None for any other."""
        for look in self.team_names:
            got = look(team)
            if got is not None:
                return got
        return None

    def absent_team(self, team):
        """A named AI team with no instance now: the game finds no team by that name and the team conditions read
        false (bench 11-11 aiskirm:m, CampAISkirmM_mcp_1111_221811: BalancedCleanup_SimpleAttack_0_0's
        TEAM_COMPARE_NUM_MEMBERS == n holds for no n -- the counter stays 99 -- until the team is made; the same
        name's TEAM_HAS_FEWER_THAN_X_UNITS_WITH_KINDOF likewise, checks/engine_aiskirm.py _kind_members)."""
        named = self.named_team(team)
        if named is not None and not named[0]:
            self.used.add('ai team absent')
            return True
        return False

    def reinforce(self, team, waypoint, script, at=None):
        """CREATE_REINFORCEMENT_TEAM(team, waypoint): a new instance of the team template (mission.templates:
        {'Owner/name': {'units': [(template, min, max)], 'instances': n}}), every line's MAX count of its template, at
        the waypoint -- made again on every call, teamMaxInstances or not (bench 11-10 engine_reinf two: 3 A + 2 B of
        a min 2 / max 3, min 1 / max 2 template, a second call 6 / 4 with teamMaxInstances 1). On a grid of SPREAD
        round the waypoint, or `at` (a unit's spot, the caller's pick; INFERRED: the bench counts inside 250 of it)."""
        key = next((k for k in self.templates if same_team(k, team)), None)
        p = at if at is not None else self.point(waypoint)
        if key is None or p is None:
            self.used.add('reinforcement team unknown' if key is None else 'reinforcement waypoint unknown')
            return
        owner = key.split('/')[0]
        self.instances[key] = k = self.instances.get(key, 0) + 1
        self.made_frame[key] = self.frame_now()
        made = [t for t, _, hi in self.templates[key]['units'] for _ in range(hi)]
        side = math.ceil(math.sqrt(len(made)))
        for i, t in enumerate(made):
            dx, dy = (i % side - (side - 1) / 2) * SPREAD, (i // side - (side - 1) / 2) * SPREAD
            b = self.add(simworld.free_name(self, '#reinforcement', t), t, owner, p[0] + dx, p[1] + dy, by=script.name,
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
        self.hidden_home -= set(players)

    def hidden_members(self, team):
        """The hidden objects on a map default team (Sim.hidden_home), for the member counts."""
        return sum(1 for s, p in self.players.items() if p in self.hidden_home and same_team(self.mm.team(s), team))

    def tactical(self, player):
        """The player's SidesList aiTactical switch is on (255): its TEAM_HUNT hunts (bench 11-14 engine_acts_w). A
        retail map's own sides; ours: the mission's side props (Mission.sides) over the container's (TACTICAL_SIDES)."""
        if player == self.human:            # bench 11-08 engine_scripts1 hunt: the player's own team stayed
            return False
        sides = getattr(self.m, 'sides', None) or {}
        key = player if self.retail else next((s for s, p in self.players.items() if p == player), None)
        got = (sides.get(key) or {}).get('aiTactical')
        if got is not None:
            return int(got) == 255
        return not self.retail and player in TACTICAL_SIDES

    def team_active(self, team):
        return any(same_team(t, team) for t in self.active)

    def books_of(self, player):
        """The protocol books a script's player names (the game's player mask: work/re l2_scripts1.md 1); a player
        without one (civilian, neutral) or a name that is no player: none."""
        names = list(self.books) if player == '<All Players>' else \
            [self.human] if player in ('<All Human Players>', '<1st Human Player>') else [player]
        return [self.books[n] for n in names if n in self.books]

    def book_players(self, player):
        """The players (with a protocol book) a script's player argument names, as books_of."""
        names = list(self.books) if player == '<All Players>' else \
            [self.human] if player in ('<All Human Players>', '<1st Human Player>') else [player]
        return [n for n in names if n in self.books]

    def spellbook_ready(self, player, power):
        """SKIRMISH_SPECIAL_POWER_READY for a PlayerSpellBook power (its RequiredPlayerTech, simtech.power_needs): held,
        its countdown run out, its GameDependency's RequiredObject standing. Bench 11-13 engine_acts_u: ready the
        frame PLAYER_GRANT_SPECIAL_POWER gives it; false once the player's SovietConstructionYard was deleted (the
        protocol kept); a countdown of 5 s false for 5 s. A protocol bought or held from the start: ready (INFERRED)."""
        tech, objs = simtech.power_needs(power)
        for p in self.book_players(player):
            have = {b.template.lower() for b in self.living() if b.owner == p}
            if self.books[p].has(tech) and self.frame_now() >= self.power_at.get((p, power.lower()), 0) and \
                    all(o in have for o in objs):
                return True
        return False

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

    def order_move(self, b, where, attacking, given=(), skip=(), face=None, on_grid=False):
        """simorder.order_move (L5)."""
        return simorder.order_move(self, self._order_peers(), b, where, attacking, given, skip, face, on_grid)

    def _order_peers(self):
        """simorder.Peers: what the unit orders (L5) may reach on this Sim beyond the world, made on first use."""
        p = self.__dict__.get('order_peers')
        if p is None:
            p = self.order_peers = simorder.Peers(self)
        return p

    def claims(self, b, skip=()):
        """The spots other mobile ground units hold (x, y, radius): where they are going, or where they stand; none for
        aircraft in the air or for `skip`; none unless HOLD_SPOTS. free_spot (simpath.spot) keeps a move's goal off
        them (bench 2026-11-17 checks/engine_drop.py: allies sent one after another to one point stood in the rings'
        order, each off every one before it -- all of them there already; that a goal is held while its unit is
        still on its way is from engine_spots 'same' below). Benched 11-09: the rule is the game's (a01, two
        infantry sent alone to one point stood ~22 apart),
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
        MOVE_NAMED_UNIT_TO per unit -- no play has 走 for several units yet.
        Whose spots: an ally's (own units too) goal always; an enemy's or a neutral's only where it stands still and b
        cannot crush it -- a moving enemy's goal and a crushable one's spot are b's to take (INFERRED: no bench sent a
        unit onto an enemy's spot yet; the crush case is aicrush1's, below). Until 11-11 every unit's spot was held:
        aicrush1's first Crush move (checks/engine_aicrush.py, work/re/c_crush_path_report.md) had its goal, the
        guard's own spot, moved 31.6 aside, and the tank drove past the guard it was sent over."""
        if b.surface == 'air' or not HOLD_SPOTS:
            return []
        out = []
        for o in self.living():
            if o is b or o in skip or o.speed <= 0 or o.surface == 'air' or o.scenery:
                continue
            moving = bool(o.path and o.dest)
            if self.relation(b.owner, o.owner) != 'ALLIES' and (
                    moving or (b.crusher is not None and o.crushable is not None and b.crusher > o.crushable)):
                continue
            out.append(tuple(o.dest if moving else (o.x, o.y)) + (o.radius,))
        return out

    def order_group(self, bodies, where, attacking, on_grid=False):
        """simorder.order_group (L5)."""
        return simorder.order_group(self, self._order_peers(), bodies, where, attacking, on_grid)

    def column_ends(self, foot, p, attacking, given, skip, on_grid=False):
        """An infantry group's ends (simpath.block, bench engine_column): each man sent to his spot in the block, a
        move's goal like any other (snapped by order_move's free_spot when on_grid)."""
        for b, q in zip(foot, simpath.block([(b.x, b.y) for b in foot], p)):
            self.order_move(b, q, attacking, given, skip, on_grid=on_grid)
            given.append(tuple(b.dest or (b.x, b.y)) + (b.radius,))

    def goal_off_nodes(self, b, want):
        """A ground move's goal whose footprint touches an ore node's: the nearest goal clear of every node, on the
        pathfinder's GRID cells (D round 176). The footprint is simpath.footprint, floor(2 r / GRID + 0.3) cells, an
        even one round a cell corner, an odd one round a cell centre (bench 2026-11-17 checks/engine_drop.py: Guardians
        2 cells, Peacekeepers 1, snapped so); a node's is its base plate (OreNode.xml's 60 x 45 half-extent box, every other shape of it inside),
        turned with the node, and a cell touching it is shut. Bench aiexpb50n (only node 44 by the slot, D175): the
        miner sent to its slot (4215, 3039), 7 off the plate's edge, turned off its straight way 37 short and stood
        at (4221, 3061) -- this rule's (4220, 3060), the nearest corner whose four cells clear the plate. Not yet
        explained: aiexpb50 (node 45 too) stood at (4201, 3081), the rule's (4180, 3060)."""
        if b.surface == 'air' or 'ORE_NODE' in b.kinds:
            return want
        nodes = [(o.x, o.y, o.angle) for o in self.living() if 'ORE_NODE' in o.kinds]
        if not nodes:
            return want
        hx, hy = ORE_PLATE
        diam = max(1, math.floor(2 * b.radius / GRID + 0.3))
        m, off = diam * GRID / 2, 0.0 if diam % 2 == 0 else GRID / 2

        def clear(x, y):
            for nx, ny, a in nodes:
                u = (x - nx) * math.cos(a) + (y - ny) * math.sin(a)
                v = -(x - nx) * math.sin(a) + (y - ny) * math.cos(a)
                if abs(u) < hx + m and abs(v) < hy + m:
                    return False
            return True
        if clear(*want):
            return want
        cx, cy = round((want[0] - off) / GRID), round((want[1] - off) / GRID)
        spots = [((cx + i) * GRID + off, (cy + j) * GRID + off) for i in range(-8, 9) for j in range(-8, 9)]
        spots = [s for s in spots if clear(*s) and self.ground.open(b.surface, *s)]
        if not spots:
            return want
        return min(spots, key=lambda s: (s[0] - want[0]) ** 2 + (s[1] - want[1]) ** 2)

    def free_spot(self, b, want, held, on_grid=False):
        """simpath.spot (L2: the goal snapped to the grid by b's footprint, off the spots `held`; bench engine_drop):
        aircraft in the air, or no spot (none free, or `want` off its ground: the way finder's closest point decides,
        R7) -> `want`."""
        if b.surface == 'air':
            return want
        at = simpath.spot(want, b.radius, held, lambda x, y: self.ground.open(b.surface, x, y), GRID, on_grid)
        return want if at is None else at

    def order_attack(self, b, target_name, force=False):
        """simorder.order_attack (L5)."""
        return simorder.order_attack(self, self._order_peers(), b, target_name, force)

    def order_capture(self, b, target_name):
        """simorder.order_capture (L5)."""
        return simorder.order_capture(self, self._order_peers(), b, target_name)

    def engineer_entry(self, b, target):
        """The target building's EngineerContain admits the entering template/relation.
        Unmeasured replacement/filters are gaps, never unconditional captures."""
        cache = self._engineer_rules
        if target.template not in cache:
            cache[target.template] = simunits.engineer_contain(target.template, self.own)
        rule = cache[target.template]
        if rule is None or not rule['enabled']:
            return None
        if not rule['supported']:
            self.gap('EngineerContain', target.template, '替换或复杂进入筛选未对拍')
            return None
        if b.template.lower() not in rule['allowed']:
            return None
        if rule['relations'] and self.relation(target.owner, b.owner) not in rule['relations']:
            return None
        return rule

    def capture_due(self):
        """simorder.capture_due (L5)."""
        return simorder.capture_due(self, self._order_peers())

    # ---- production: the second hook for simproxy's player (docs/engine/production.md, bench 2026-11-05)
    def factories(self, owner):
        """The owner's living structures that build units (their CommandSet has UNIT_BUILD buttons)."""
        return [b for b in self.living() if b.owner == owner and 'STRUCTURE' in b.kinds and not b.scenery
                and simunits.menu(b.template, self.own, b.upgrades)]

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
        status = self.buildable.get(template.lower(), 0)
        if status == 1:                     # IGNORE_PREREQUISITES (bench 11-13 engine_acts_u: the press built a spy
            return True                     # without Upgrade_AlliedTech2, the press before it refused)
        if ban and status in (2, 3):        # NO / ONLY_BY_AI: a script's press builds all the same (bench, same run);
            return False                    # the player's button refused (INFERRED, not benched)
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
        queued = self.production.buying(owner, low)
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
        whose button buys it; nothing is paid now (production.due pays frame by frame, an upgrade as a unit).
        press: a script's press, queued even while the unit is banned (ALLOW_DISALLOW_ONE_BUILDING 0) -- it waits
        unbuilt until let go (bench 2026-11-09 engine_production g); the player's click is not (the button is locked).
        False: nothing of the owner's builds / buys it now (`factory`: that one does not, review 1120cc P2 #3)."""
        sellers = [b for b in self.upgrade_sellers(owner, template) if factory is None or b is factory]
        if sellers:
            b = min(sellers, key=lambda b: len(self.production.jobs(b.serial)))
            cost, secs = simunits.upgrade_cost(template)
            kind = dict(simunits.upgrade_menu(b.template, self.own, b.upgrades))[template]
            self.production.queue(b.serial,
                {'template': template, 'upgrade': template, 'kind': kind, 'owner': owner, 'cost': cost,
                 'secs': secs, 'progress': 0.0, 'paid': 0, 'full': None})
            self.used.add('production')
            self.note('生产', f'{self.who(owner)} 在 {self.label(b)} 买 {template}（{cost}，{secs:g} 秒）')
            return True
        fs = [f for f in self.factories(owner) if template in simunits.menu(f.template, self.own, f.upgrades)
              and self.can_build(owner, template, f, ban=not press) and (factory is None or f is factory)]
        if not fs:
            return False
        f = min(fs, key=lambda f: len(self.production.jobs(f.serial)))
        cost, secs = simunits.production(template, self.own)
        self.production.queue(f.serial,
            {'template': template, 'owner': owner, 'cost': cost, 'secs': secs, 'progress': 0.0, 'paid': 0,
             'full': None})
        self.used.add('production')
        self.note('生产', f'{self.who(owner)} 在 {self.label(f)} 排 {template}（{cost}，{secs:g} 秒）')
        return True

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
        newly_held = up not in b.upgrades
        (b.upgrades.add if on else b.upgrades.discard)(up)
        if on:
            b.up_since[up] = self.frame_now()
        else:
            b.up_since.pop(up, None)
        simlevel.receive(self, b, up, on, newly_held)
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

    def weapon_upgrades(self, b):
        """The upgrade names a <Weapon Upgrade="X"> line tests (simunits.pick_weapons): the object's and its
        player's (INFERRED: the engine's object test also takes the player's upgrades, as Generals').
        simgarrison handles the bounded single-passenger SecondaryObjectListener grant."""
        return set(b.upgrades) | set(getattr(self, 'player_ups', {}).get(b.owner, ()))

    def modify(self, b):
        """simmodifier.Modifiers.modify (L2): b's acting values from the attribute modifiers on it."""
        self._modifiers().modify(self, b, self.toggles_of, self.cold_of, self.weapon_upgrades, self.player_ups)

    def _modifiers(self):
        return _late(self, 'modifiers')

    def relation(self, a, b):
        """ENEMIES / NEUTRAL / ALLIES: how owner b stands to owner a (an aura's ObjectFilter Relationship)."""
        if self.enemy(a, b):
            return 'ENEMIES'
        if a != b and CIV in (a, b):
            return 'NEUTRAL'
        return 'ALLIES'

    def aura_tick(self):
        """simmodifier.Modifiers.aura_tick (L2): the auras hang their modifiers, then every modified body is re-set."""
        self._modifiers().aura_tick(self, self.relation, self.modify)

    def power(self, owner):
        """(supply, demand) of the owner: its living objects' EnergyProduction, > 0 summed into the supply, < 0 into
        the demand (RA3 1.13 (work/re/l2_construction.md) leaves out an object under construction or powered down: the simulator has
        neither -- a building stands built from the frame it appears)."""
        sup, dem = self.base_power.get(owner, 0), 0
        now = self.frame_now()
        for b in self.living():
            if b.owner == owner and not (b.unpack_end is not None and now < b.unpack_end):
                e = self.energies.get(b.template)
                if e is None:
                    e = self.energies[b.template] = simunits.energy(b.template, self.own)
                sup, dem = (sup + e, dem) if e > 0 else (sup, dem - e)
        return (0 if self.infiltrators.disabled(owner) else sup), dem

    def short_of_power(self, owner):
        sup, dem = self.power(owner)
        return self.infiltrators.disabled(owner) or sup < dem

    def unpowered(self, b):
        """Holds its fire: still unpacking, or POWERED while its owner is short of power (bench 2026-11-07
        engine_powerdef: a Tesla coil of a player with supply 0 < 75 never fires; the plant deleted, it stops within a
        shot's interval; a plant made by script unpacks 255 frames short of power, the coil's next kill 70 frames
        after that)."""
        if b.unpack_end is not None and self.frame_now() < b.unpack_end:
            return True
        return 'POWERED' in b.kinds and self.short_of_power(b.owner)

    def build_frames(self, secs, owner):
        """A unit's build frames, worked out again every frame (RA3 1.13, work/re/l2_construction.md): BuildTime x 15 with enough power;
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
        b = self.add(simworld.free_name(self, '#made', job['template']), job['template'], job['owner'], *at(create),
                     by=f.name, at=self.t)
        b.team, b.angle = f.team, f.angle
        self.note('生产', f'{self.label(f)} 出 {job["template"]}')
        if rally is not None:               # pushed out RALLY_PUSH along the factory's centre -> rally line
            r = math.hypot(*rally)
            k = (r + RALLY_PUSH) / r if r else 1.0
            b.mode = 'move'
            self.send(b, at((rally[0] * k, rally[1] * k)))
        self.change()

    def order_guard(self, b, area):
        """simorder.order_guard (L5)."""
        return simorder.order_guard(self, self._order_peers(), b, area)

    def order_power(self, b, power, pos):
        """simability.order_power (L5)."""
        return simability.order_power(self, self._order_peers(), b, power, pos)

    def player_power(self, units, power, pos, via):
        """simability.player_power (L5)."""
        return simability.player_power(self, self._order_peers(), units, power, pos, via)

    def order_stop(self, b):
        """simorder.order_stop (L5)."""
        return simorder.order_stop(b)

    def stand(self, b):
        """simorder.stand (L5)."""
        return simorder.stand(b)

    def seq_due(self):
        """simseq.seq_due (L5)."""
        return simseq.seq_due(self, self._order_peers())

    def order_follow(self, bodies, label, attacking, exact=False, start=None, as_team=False):
        """simorder.order_follow (L5)."""
        return simorder.order_follow(self, self._order_peers(), bodies, label, attacking, exact, start, as_team)

    def follow_due(self):
        """simorder.follow_due (L5)."""
        return simorder.follow_due(self, self._order_peers())

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

    def start_camera(self):
        """Where the camera looks before a script moves it: the map's start site (contract K5), else the middle."""
        start = (getattr(self.m.map, 'SITES', None) or {}).get('start')
        return (start.x, start.y) if start is not None else (2500.0, 2500.0)

    def point(self, name):
        """A waypoint, an area's middle, a mark, a site, a named object, '@x,y' (simseq.AS_WRITTEN: places by name)."""
        c = coord(name)
        if c is not None:
            return c
        place = name[:-len(simseq.AS_WRITTEN)] if name in self.acting and name.endswith(simseq.AS_WRITTEN) else name
        if place in self.waypoints:
            return self.waypoints[place]
        if place in self.areas:
            pts = self.areas[place]
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        if place in self.m.marks:
            return self.waypoints[self.m.marks[place]]
        if place in (sites := getattr(self.m.map, 'SITES', {})):
            return (sites[place].x, sites[place].y)
        b = self.acting.get(name) or self.bodies.get(self.m.cast[name].name if name in self.m.cast else name)
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
        r = [self.reach_of(w) for w in b.weapons if self.can_hit(w, target)]
        return max(max(r) + b.radius + target.radius - ATTACK_SLACK, 1.0) if r else 0.0

    # R8 weapon reach: the rules are L3 simrange's (R3 13f-2b: the AI imports them there, not through the host)
    reach_of = staticmethod(simrange.reach_of)
    in_range = staticmethod(simrange.in_range)

    def send(self, b, target, by='', reach=0.0, face=None):
        """Put b on a way to target: simlocomotion.go_to (L2) says how; `by` is unused."""
        simlocomotion.go_to(self, b, target, reach, face, self.frame_movers, self.topples)

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

    def sell(self, b):
        """simbody.Life.sell (L2): SELL_OBJECT -- the refund paid at once (simmoney.Money.credit), deleted 30 frames on."""
        self._life().sell(self, b, self.garrison, self.modify, self.wallet.credit)

    def destroy(self, b, why, death='NORMAL', cause=''):
        """simbody.Life.kill (L2), the one death entry: b killed, its Die modules told its death type and cause."""
        self._life().kill(self, b, why, death, cause)

    def delete(self, b, why):
        """simbody.Life.delete (L2), the one deletion entry: b taken out, no death (children, passengers with it)."""
        self._life().delete(self, b, why)

    def _life(self):
        return _late(self, 'life')

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
        if name in self.acting or name in self.refs:    # a step's own unit; R2: a reference, dead or not
            return self.acting[name] if name in self.acting else self.refs[name]
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
        return simcond.cond(self, name, a)             # the conditions as a lookup table (ADR 0029 step 3)

    def team_entered(self, a):
        """TEAM_ENTERED_AREA_PARTIALLY (team, area, k): one frame as a member (living, not INERT / MOVE_ONLY, on
        surface k) comes into the area (Generals Team::didPartialEnter). engine_enter all, 进入 10000 / 20000 / 30001 /
        30002 / 30003: the Guardians count on the first frame (placed inside Home), AGAIN on the frame each leaves Home
        -- but not on leaving F, entered later. INFERRED: an entry seen on the first frame stays marked until the
        member leaves (the program's area record of a placed unit; a 'stale mark' rule, every exit counting once after an
        entry, needs go 1's exit from F and go 2's entry to share a frame: the hypothesis table, round 245)."""
        key = ('entered', a[0], a[1], int(a[2]))
        st = self.cond_memory.setdefault(key, {'frame': None, 'val': False, 'was': {}, 'start': set()})
        now = self.frame_now()
        if st['frame'] == now:
            return st['val']
        face = SURFACES[int(a[2])] if 0 <= int(a[2]) < len(SURFACES) else None
        crew = [b for b in self.members(a[0]) if not ({'INERT', 'MOVE_ONLY'} & set(b.kinds)) and face in self.surfaces(b)]
        val = False
        for b in crew:
            ins = inside(self.areas[a[1]], b.x, b.y)
            was = st['was'].get(b.serial)
            if was is None:
                hit = ins
                if ins:
                    st['start'].add(b.serial)
            else:
                hit = (ins and not was) or (was and not ins and b.serial in st['start'])
                if was and not ins:
                    st['start'].discard(b.serial)
            st['was'][b.serial] = ins
            val = val or hit
        st['frame'], st['val'] = now, val
        return val

    def surfaces(self, b):
        """The Locomotor Surfaces of a body's NORMAL set (TEAM_INSIDE_AREA_*'s k reads their bits, D 119); a body
        without one (a building) the ground only."""
        cache = self.__dict__.setdefault('_surfaces', {})
        if b.template not in cache:
            try:
                got = simunits.resolve(b.template, self.own, simunits._surfaces())['surf']
            except (OSError, ValueError, KeyError, TypeError):
                got = None
            # an amphibious one's NORMAL set reads GROUND only (the Bullfrog): its water INFERRED from the KindOf
            cache[b.template] = (frozenset(got) if got else frozenset({'GROUND'})) | (
                {'WATER'} if 'AMPHIBIOUS' in b.kinds else set())
        return cache[b.template]

    def all_revealed(self):
        """Whether the whole map is open to the player this frame (MAP_REVEAL_ALL_PERM, or a MAP_REVEAL_ALL not lapsed)."""
        return self.reveal_all or self.frame_now() < self.reveal_all_until

    def sees(self, x, y, air=False):
        """Whether the player sees a point (a body there, airborne or not)."""
        if self.all_revealed():
            return True
        if any(math.hypot(x - rx, y - ry) <= r for rx, ry, r in list(self.reveals.values()) + self.peeking()):
            return True
        if any(inside(self.areas[k], x, y) for k in self.reveal_areas.values() if k in self.areas):
            return True
        if self.infiltrators.sees(self.human, x, y, air):
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
        key = (side, t.serial)
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

    def act(self, name, a, script, unit=None):
        if name in RA3_ONLY:
            self.ra3_only.add(name)
        if name in SOUND_PLAYS or name.startswith('MOVIE_PLAY_'):
            self.played(name, a)
        simact.act(self, name, a, script, unit)        # the actions as a lookup table (ADR 0029 step 3)

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
        cmd = self.commands.command(e, 'player')    # 派 走 攻击 放 占领 X 进 Y 生产 买: the player's orders, given
        if e[1] == command_port.ORDER:              # through the command port (its routes are these verbs' order
            e = command_port.event(cmd, e[0])       # calls); a posted command noted as its line's event
        t, verb, *rest = e
        self.note('剧本', ' '.join([verb] + [str(x) for x in rest]))
        if cmd is not None:
            self.commands.do(cmd)
        elif verb in ('摧毁', '删除'):              # the rest: the god's hand (a test's shortcuts, not orders)
            for b in self.pick(rest[0]):
                if verb == '摧毁' and 'UNATTACKABLE' in b.status:
                    self.note('剧本', f'{self.label(b)} 打不动（UNATTACKABLE），没摧毁')
                    continue
                b.set_last_damage(self.human, None)
                (self.delete if verb == '删除' else self.destroy)(b, '剧本')
        elif verb == '血量':
            for b in self.pick(rest[0]):
                b.health = float(rest[1])
                b.set_last_damage(self.human, None)
        elif verb == '打':
            for b in self.pick(rest[0]):
                b.set_last_damage(self.human, None)
        elif verb == '占领':                        # one name: it is the player's now (占领 X 进 Y is an order)
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
                b = self.add(simworld.free_key(self, 'UNIT - SIM Made {}'.format, len(self.bodies)), tmpl, self.human, *p, by='剧本', at=self.t)
                b.angle = angle
                if self.blocks(b):
                    self.reblock()
        self.change()

    # ---- running
    def step(self):
        """One DT tick from self.t (the caller moves self.t on): the frame loop's table (simloop.FRAME, frame by
        frame, with the engine model or without it)."""
        return simloop.step(self)

    def flee_start(self, b):
        """simability.flee_start (L5)."""
        return simability.flee_start(self, self._order_peers(), b)

    def hunt_due(self, frame, crew=None):
        """simhunt.hunt_due (L5)."""
        return simhunt.hunt_due(self, self._order_peers(), frame, crew)

    def flee_due(self, frame):
        """simability.flee_due (L5)."""
        return simability.flee_due(self, self._order_peers(), frame)

    def lose_health(self, frame):
        """simbody.Life.lose_health (L2): LoseHealthUpdate while the body's own toggle carries its statuses."""
        self._life().lose_health(self, frame, self.toggles_of)

    def release(self):
        """The script events anchored to a flag that is up now: due `delta` after this moment."""
        for e in list(self.anchored):
            if self.flags.get(e[0][1]) == 1:
                self.anchored.remove(e)
                self.events.append((round(self.t + e[0][2], 6),) + tuple(e[1:]))
                self.events.sort(key=lambda x: x[0])

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
        far = max(self.reach_of(w) for w in ws) + a.radius + t.radius - 1.0
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
        """simorder.fight (L5)."""
        return simorder.fight(self, self._order_peers())

    def fight_field(self):
        """(live, armed, targets) for this moment's fight: who is in it, who can fire, who can be shot."""
        live = [b for b in self.living() if not b.scenery and self.on_map(b)]     # off the border: out of the fight
        flying = self.__dict__.get('impact_flights', {})
        # a knocked body fires its kept order lying (landing hold: feet only), not in the air (Physics P4, bench 11-11
        # engine_knock_probe fire: first hit ~300-316, the landing 300; bench 11-11 engine_knock_water farfire: ~20 up
        # and in 2-D reach for frames ~182..196, no fire in the air)
        armed = [b for b in live if b.weapons and 'NO_ATTACK' not in b.status    # NO_ATTACK: holds its fire
                 and b.serial not in flying
                 and not getattr(b, 'ground_fire', None)     # NAMED_FORCE_ATTACK_WAYPOINT: busy at the ground
                 and not self.emp_disabled(b) and not self.unpowered(b)
                 and not self.infiltrators.attack_blocked(b)
                 and not (b.hold_fire and (b.hold_paused or not isinstance(b.goal, Body)))]
        cloaked = self.cloaked(live)
        targets = [b for b in live if 'UNATTACKABLE' not in b.status and b.serial not in cloaked]
        return live, armed, targets

    def aim(self, a, targets, aimable, tx, ty):
        """`a`'s pick for each of its weapons where it stands (fight): the aimed fire into self.firing / volleys /
        chilling, engaged when it is attack-moving. None: no foe at all; else (fired, the foes' centre distances,
        their indexes in targets). The picks are engine.orders.target's."""
        got = simtarget.picks(a, targets, aimable, tx, ty, self)
        if got is None:
            return None
        fired = False
        for w, pick in zip(a.weapons, got[2]):
            if pick is None:
                continue
            if a.vision and w['range'] > a.vision:
                a.fired_at = self.t                 # a bombarder firing shows itself
            for effect in w.get('unmodeled_effects', []):
                self.gap(GAP_WEAPON, effect, '武器第1轮尚未解释此效果的筛选、几何或时序')
            if not self.shot_clock and (w.get('hit_modifiers') or w.get('line') or w.get('strip_max_health') or w.get('emp_seconds')
                                       or w.get('sweep') or w.get('contained') or w.get('dot') or w.get('special_powers') or w.get('attach') or w.get('lift') or w.get('meta_impacts')):
                self.gap(GAP_WEAPON, 'weapon effects', '逐发武器效果仅在离散命中时钟中模拟')
            self.first_shot(a, w, pick)
            if w['dps'] or w.get('suppression') or (self.shot_clock and (w.get('sdps') or w.get('dot') or w.get('special_powers') or w.get('attach') or w.get('lift') or w.get('meta_impacts'))):
                if 'sched' in w and self.shot_clock:
                    self.volleys.append((pick, w, a))
                else:
                    # Continuous DPS has no individual hit events. Do not run a second
                    # clip clock just for pressure (A4 guardians falsely suppressed at F1980).
                    if w.get('suppression'):
                        self.gap(GAP_WEAPON, 'SuppressionNugget',
                                 '连续DPS没有逐发命中事件；压制贡献仅在离散命中时钟中模拟')
                    self.firing.append((pick, w['dps'] * a.dealt * (1.0 if w['type'] == 'UNRESISTABLE' else
                                        simunits.percent(pick.armor, w['type']) / 100.0 * pick.taken)
                                        * simdamage.flank_of(pick, a), a))
            if w.get('sdps') and not self.shot_clock:
                self.chilling.append((pick, w['sdps'] * a.dealt, a))
            fired = True
            a.aiupdate.engage()
        return fired, got[0], got[1]

    def first_shot(self, a, w, pick):
        """A PreAttackType PER_TARGET weapon waits its PreAttackDelay (whole frames, simunits._frames) before its first
        shot at a new target, not before every shot (simunits._pre_per_clip keeps it out of the cycle; Generals
        Weapon::getPreAttackDelay). Bench 2026-11-07 `cnv_check a4 smash`: the King Oni's beam (PER_TARGET 0.75 s,
        a 175 shot every 1.8 s, 11.7 % of the wall) took it 100 -> 76 -> 53 -> 41 -> 18 -> 6 at s67 / 70 / 73 / 76 /
        79 / 82: its first shot falls in s67.0-67.6, more than the delay after it had the wall in range (A round 233).
        INFERRED: the gate is per shooter and target (deal), a shooter's other weapons on that target wait with it.
        The last target and the gate are the shooter's WeaponSet's (step W3: WeaponSet.lock_on)."""
        wt = simunits.weapon_table(self.own).get(w.get('weapon_key'), {})
        if wt.get('pretype') != 'PER_TARGET' or not wt.get('pre'):
            return
        m = kernel_weaponset.of(self.world, a, self.clock.frame)
        held = m.pre_lock(w.get('weapon_key'))
        if held is None or held[0] is not pick:
            m.lock_on(w.get('weapon_key'), pick, self.t + simunits._frames(wt['pre']) / simunits.FPS)

    def range_targets(self, b):
        """For move: the foes an attack-mover on its way would stop for, [(foe, the centre distance it fires
        from)], out of reach where it stands (the tick's fight found nothing for it); None when it does not stop
        for any (not attack-moving, not in the tick's fight). Bench 2026-11-10 engine_wayatk team (A
        round 230): the tanks get in range mid-tick; held for the next tick's fight they hit a tick late (s7, the
        bench s4: LAG 2). Generals AIAttackMoveToState looks for a target every frame its attack machine is idle.
        The same picks as aim's (the order's target, or one it takes by itself); INFERRED: the foe stands still for
        the tick, the line of fire is taken where it would stop."""
        if (not self.combat or b.mode != 'attack' or b.engaged or b.speed <= 0
                or not any(a is b for a in self._field[1])):
            return None
        out = []
        for t in self._field[2]:
            if t is b or not t.alive or not self.hostile(b, t) or not self.side_sees(b.owner, t) or \
                    (b.goal is not t and (not simtarget.takes_by_itself(b, t, self)       # the order's, or one
                                          or 'NON_AUTOACQUIRABLE' in t.status)):          # it takes by itself
                continue
            for w in b.weapons:
                if self.can_hit(w, t) and not self.in_range(b, t, w):
                    out.append((t, w, self.reach_of(w) + b.radius + t.radius))
        return out

    def range_entry(self, b, reach, tx, ty, length):
        """How far b goes toward (tx, ty), at most `length`, before a foe of range_targets is in range and its line
        of fire is clear from there; None: none on this stretch. It stops a hair inside (fight's in_range holds)."""
        dx, dy = (tx - b.x) / math.hypot(tx - b.x, ty - b.y), (ty - b.y) / math.hypot(tx - b.x, ty - b.y)
        hits = []
        for t, w, r in reach:
            r -= 1e-6
            fx, fy = b.x - t.x, b.y - t.y
            half = fx * dx + fy * dy                    # |f + s u| = r: s^2 + 2 half s + (|f|^2 - r^2) = 0
            c = fx * fx + fy * fy - r * r
            disc = half * half - c
            if c <= 0 or disc < 0:
                continue
            s = -half - math.sqrt(disc)
            if 0 <= s <= length:
                hits.append((s, t, w))
        x, y = b.x, b.y
        try:
            for s, t, w in sorted(hits, key=lambda h: h[0]):
                b.x, b.y = x + dx * s, y + dy * s
                if not self.shot_blocked(b, t, w):
                    return s
        finally:
            b.x, b.y = x, y
        return None

    def aim_due(self):
        """The attack-movers move stopped in range mid-tick aim from their frame (aim), not the next tick's."""
        for key, (at, b) in list(self.mid_aims.items()):
            if self.t < at - 1e-9:
                continue
            del self.mid_aims[key]
            if not b.alive or b.engaged or any(a is b for _, _, a in self.firing + self.volleys):
                continue                        # already firing this tick (a plain mover fires on its way)
            targets = [t for t in self._field[2] if t.alive]
            if not targets:
                continue
            self.aim(b, targets, {t.serial for t in targets},
                     np.array([t.x for t in targets]), np.array([t.y for t in targets]))
            if self.firing or self.volleys:
                self.used.add('combat')

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
                    out.add(t.serial)
        if out:
            self.used.add('stealth')
        return out

    @property
    def incoming(self):
        """{target.serial: [(source, weapon key, damage, hit frame, expiry frame)]}: simdamage.Damage's notifications."""
        return self._harm().incoming

    @property
    def projectile_hits(self):
        """[(frame, target, damage, attacker, weapon, centre)]: simdamage.Damage's projectile arrivals to come."""
        return self._harm().projectile_hits

    def _harm(self):
        return _late(self, 'harm')

    def expected_damage(self, target, behind, ahead, now=None):
        """simdamage.Damage.expected_damage (L3): the micro's incoming-damage callback."""
        return self._harm().expected_damage(self, target, behind, ahead, now)

    def toggles_of(self, b):
        """The rules of b's template's toggle modules (engine/modules/toggle.py, step M5), in their blocks' order --
        the data its modules get (World.data_of), kept: Sim.add reads the first states before the modules are made.
        A Sim built without __init__ reads them through a world of its own."""
        cache = self.__dict__.setdefault('_toggles', {})
        if b.template not in cache:
            world = self.__dict__.get('world') or kernel_world.World(
                lambda t, tag: simunits.module_blocks(t, tag, self.own))
            cache[b.template] = [d.rules() for d in world.data_of(b.template, 'ToggleStatusSpecialAbilityUpdate')]
        return cache[b.template]

    def toggle_press(self, b, command):
        """simtoggle.press (L2): a toggle button steps b's toggle module to its next ToggleState. False when b has no
        toggle for that button."""
        return simtoggle.press(self, b, command, self.short_of_power)

    toggle_miner_armor = toggle_press           # simai's name (the AI micro's toggles)

    def queue_projectile_hit(self, when, target, damage, attacker, weapon, centre=None):
        """simdamage.Damage.queue_projectile_hit (L3): a projectile's arrival event."""
        self._harm().queue_projectile_hit(when, target, damage, attacker, weapon, centre)

    def projectile_detonate(self, weapon, target, centre=None, attacker=None):
        """simdamage.Damage.projectile_detonate (L3): the non-damage payload of a projectile arrival."""
        self._harm().projectile_detonate(self, weapon, target, centre, attacker, simdamage.Peers(self))

    def deal(self, dt):
        """simdamage.Damage.deal (L3, R6): `dt` seconds of aimed fire, projectiles and DOTs dealt; bodies at 0 die."""
        self._harm().deal(self, dt, simdamage.Peers(self))

    def attachment_tick(self):
        """engine_attach a: teleport the child and keep it with its moving parent.

        engine_attach_parent a confirms a script-killed simple parent leaves
        its child alive and clears the link. engine_attach_child a confirms
        script-killing the simple child clears VEHICLE_ATTACHED on its living
        parent (ENCLOSED/UNATTACKABLE fixture). engine_attach_child_delete a
        confirms the same survivor status after NAMED_DELETE of that child.
        engine_attach_parent_delete a confirms its surviving child clears
        ATTACHED/ENCLOSED/UNATTACKABLE after NAMED_DELETE of the parent.
        Other child-status combinations and deletion without a survivor remain gaps;
        no detach/leech/repair contract is claimed.
        Extending these script-kill results to other lethal causes is INFERRED;
        a dead parent's queried status does not reveal its internal bits.
        NO_COLLISIONS visibility remains a separate strict-xfail gap.
        Attachment status has its own owner so ordinary
        modifier recalculation cannot erase it or pollute script-set bits.
        """
        if not self.attachments and not self._attachment_marked:
            return
        bits = {}
        for key, (child, parent, rule) in list(self.attachments.items()):
            if not child.alive or not parent.alive:
                del self.attachments[key]
                measured_delete = (rule['child'] == {'ATTACHED', 'ENCLOSED', 'UNATTACKABLE'}
                                   and rule['parent'] == {'VEHICLE_ATTACHED'}
                                   and ((child.deleted and parent.alive)
                                        or (parent.deleted and child.alive)))
                if (parent.deleted or child.deleted) and not measured_delete:
                    self.gap(GAP_WEAPON, 'AttachNugget', '仅ENCLOSED/UNATTACKABLE简单模块单端直接删除后的存活另一端状态已量；其他删除清理INFERRED')
                continue
            child.x, child.y, child.path = parent.x, parent.y, []
            bits.setdefault(child.serial, (child, set()))[1].update(rule['child'])
            bits.setdefault(parent.serial, (parent, set()))[1].update(rule['parent'])
        for key, b in {**self._attachment_marked, **{k: v[0] for k, v in bits.items()}}.items():
            want = bits[key][1] if key in bits else set()
            if self.bodies.get(b.name) is b and b.attachment_status != want:
                b.attachment_status = want
                self.modify(b)
        self._attachment_marked = {k: v[0] for k, v in bits.items()}

    def suppression_tick(self):
        """simdamage.suppression_tick (L3): after the bodies' modules sampled (engine/modules/suppression.py, step
        M6), the fields whose lifetime is out leave."""
        simdamage.suppression_tick(self, simdamage.Peers(self))

    def shots_due(self, b, w, dt):
        """How many of weapon `w`'s clip-clock shots of body `b` land in [self.t, self.t + dt): the clip is a
        schedule (simunits._shot_times, then the reload), each cycle `w['cycle']` long, one shot after another as
        long as the weapon has a target every window. After an idle gap (no target in the previous window) a
        cycle that has run out starts anew now, pre-attack first; one still running (a reload, a part-spent clip)
        goes on by the clock. Round 2 of engine line C (bench: the coil one tank per ~125 frames). The clock is the
        body's WeaponSet's (step W3: WeaponSet.clip_clock)."""
        t0, t1 = self.t, self.t + dt
        eps = 1e-6
        m = kernel_weaponset.of(self.world, b, self.clock.frame)
        # Attribute refresh may copy a weapon to scale its range. Keep that
        # weapon's clip running across copies; distinct retail guns stay apart (a keyless one, made by hand: its slot).
        key = w.get('weapon_key') or next((k for k, x in enumerate(b.weapons) if x is w), -1)
        c = m.clip_clock(key)
        cycle = w['cycle']
        if b.level_rate != 1.0:
            if (w.get('weapon_key') == 'AlliedAntiVehicleVehicleTech3PrismCannon_Veteran'
                    and w['sched'] == [0.0] and abs(cycle * 15 - 25) < eps):
                # engine_levelrate a measures the effective cycle only. The
                # 25 -> 20 frames does not identify which sub-timer scales or
                # how it rounds. Pre-delays, other clips and mid-cycle changes
                # are unmeasured; do not extrapolate a general rounding rule.
                cycle = 20 / 15
            else:
                self.gap(GAP_UPGRADE, 'LevelUpUpgrade/rate-clock', '该武器的等级射速计时未对拍')
        if c is None or (t0 - c[1] > dt * 1.5 and c[0] + cycle <= t0 + eps):
            c = [t0 + 1 / 15, t0]                       # [this cycle's start, the last window with a target]; the first
            #                                             object hit is1 frame after order; scripts observe it next frame (engine_emp)
        else:
            c[1] = t0
            while c[0] + cycle <= t0 + eps:             # chained: the next cycle starts where this one ends
                c[0] += cycle
        m.set_clip_clock(key, c)
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
        """(b's SecondaryDamageTracker rules, engine/modules/freeze.py -- None: none; simunits.frozen_armor, a template)."""
        m = b.find(kernel_interfaces.Freeze) if b.modules else None
        if b.template not in self.__dict__.setdefault('_cold', {}):
            self._cold[b.template] = simunits.frozen_armor(b.template, self.own)
        return (m and m.rules()), self._cold[b.template]

    def peeking(self):
        """The MAP_REVEAL_AT_WAYPOINT reveals still open this frame, as (x, y, r)."""
        now = self.frame_now()
        self.peeks = [q for q in self.peeks if now < q[3]]
        return [q[:3] for q in self.peeks]

    def set_model_condition(self, b, condition, seconds=None):
        """Shared minimal script/consumer store; separate from ObjectStatus.

        engine_spndisguise measures DISGUISED held for 20s. INFERRED: expiry
        at the first frame at/after duration, zero duration holds until cleared.
        Other native producers (including suppression) are not merged here.
        """
        b.model_conditions[condition] = (self.frame_now() + math.ceil(seconds * simunits.LIFE_FPS)
                                         if seconds and seconds > 0 else None)

    def has_model_condition(self, b, condition):
        if not self.present(b) or condition not in b.model_conditions:
            return False
        until = b.model_conditions[condition]
        if until is not None and self.frame_now() >= until:
            b.model_conditions.pop(condition, None)
            return False
        return True

    def frame_now(self):
        return self.clock.frame

    def on_the_move(self, b):
        """b physically moves this frame, as the program's own clock has it (TEAM_DISCOVERED): from the frame after
        the order that set it off from standing (its locomotor's first update) until one frame after the moment
        within the tick its way ended -- the simulator moves a whole tick at the tick's first frame, so its path is
        empty up to a tick early. Bench 11-13 engine_conds sight 发现&1 (A round 232; the bench's sN is the
        simulator's s(N+2) sample, as its hot spot / kill / sight readings line up): near off at one sample after its
        180 deg turn + 70 (order 60, off 75, on 90; 13 at the order's own frame) and at two after the turn + 120 (off
        150 and 165 -- the turn 0.5 s, 1.5 s driving: its way ends at 11.0, the frame of 165 still moving)."""
        if b.path and b.dest:
            return self.frame_now() > b.set_off
        return self.t < b.stops_at + 1.0 / self.fps - 1e-9

    def emp_disabled(self, b):
        """EMP pauses movement and new fire (engine_emp phase / engine_empfire a).

        Recheck at each damage frame too: fight's cached aim may predate the hit.
        Already launched projectiles and DOTs keep their own delivery events.
        """
        return (self.frame_now() < self.__dict__.get('emp_until', {}).get(b.serial, 0)
                or b.serial in self.__dict__.get('script_disabled', {}))

    def order_unpack(self, b, p, button=None, where=None, stand=None, here=False, send=True):
        """simability.order_unpack (L5)."""
        return simability.order_unpack(self, self._order_peers(), b, p, button, where, stand, here, send)

    def blast_due(self, frame):
        """simspecial.Specials.blast_due (L2): a superweapon's hits landing by `frame` (SUPERWEAPON_HITS)."""
        self._specials().blast_due(self, frame, self.blasts, self.mark_first_death, self.destroy)

    def mark_first_death(self, t, by):
        """The fight's first death (first_death: run time, body, killer), kept once."""
        if self.first_death is None:
            self.first_death = (self.t, t, by)

    def emp_book(self):
        """{body.serial: frame}: who stands still (EMP'd, casting, leaping) till when, made on first use."""
        return self.__dict__.setdefault('emp_until', {})

    def _specials(self):
        return _late(self, 'specials')

    def movement_power_press(self, b, button, point):
        """simspecial.Specials.movement_power_press (L2): a MovementSpecialPower's rush to a point in range."""
        return self._specials().movement_power_press(self, b, button, point, self.modify, self.send)

    def self_power_press(self, b, button):
        """simspecial.Specials.self_power_press (L2): an ActivateModuleSpecialPower on self."""
        return self._specials().self_power_press(self, b, button, self.modify)

    def leap_press(self, b, button, p):
        """simspecial.Specials.leap_press (L2): a ProjectileSelf leap (the Sickle's) to a point."""
        return self._specials().leap_press(self, b, button, p, self.send, self.emp_book)

    def self_power_due(self, frame):
        """simspecial.Specials.self_power_due (L2): leaps landing, rushes and self powers' bits running out."""
        self._specials().self_power_due(self, frame, self.modify, self.projectile_detonate,
                                        lambda x, y: simdamage.impact_ground_z(self, x, y))

    def wfire_press(self, b, button, target=None):
        """simspecial.Specials.wfire_press (L2): a WeaponFireSpecialAbilityUpdate's button."""
        return self._specials().wfire_press(self, b, button, target, self.send, self.emp_book)

    def wfire_due(self, frame):
        """simspecial.Specials.wfire_due (L2): the weapon-fire abilities going off by `frame`."""
        self._specials().wfire_due(self, frame, self.casts, self.death_blasts, self.player_ups, self.relation,
                                   self.send, self.emp_book)

    def death_blast_due(self, frame):
        """simdamage.death_blast_due (L3): the death weapons going off by `frame`."""
        simdamage.death_blast_due(self, frame, simdamage.Peers(self))

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
                   and o.surface == 'ground' and o.serial not in self.attachments]
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
            o.set_last_damage(b.owner, b)
            self.destroy(o, f'被 {self.label(b)} 压死', death='CRUSHED')    # lies its SlowDeath out (B5a)

    _crushable_pool = None

    def move(self, dt=DT, precise=False):
        """Move a coarse tick, or one frame for topple collisions / measured Jet startup."""
        self._crushable_pool = None
        for b in list(self.frame_movers.values()) if precise else self.living():
            if not b.alive or b.frame_move != precise:
                continue
            if b.serial in self.__dict__.get('impact_flights', {}):
                continue
            hold = self.__dict__.get('knock_hold', {}).get(b.serial)
            if hold is not None and self.frame_now() < hold + (simunits.KNOCK_ATTACK_WAIT
                                                               if isinstance(b.goal, Body) else 0):
                continue
            if 'ATTACHED' in b.status and b.serial in self.attachments:
                continue
            if isinstance(b.goal, Body):
                g = b.goal
                if not g.alive:
                    b.goal, b.path = None, []
                elif b.spot and b.spot[0] == g.serial and math.hypot(g.x - b.spot[1], g.y - b.spot[2]) <= 150:
                    pass                            # at / on the way to its fire_spot while the goal stays near it
                elif not b.path or math.hypot(b.path[-1][0] - g.x, b.path[-1][1] - g.y) > 150:
                    if int(self.t / DT) % 8 == 0:                    # re-aimed every 4 s
                        self.send(b, (g.x, g.y), reach=self.reach(b, g) if b.mode == 'attack' else 0.0)
            if b.building and self.production.at_site(b, 0.0):
                continue
            if b.frame_move != precise:          # chasing a moving target may have replanned into / out of prop contact
                continue
            if ('IMMOBILE' in b.status or b.engaged or self.emp_disabled(b)
                    or self.infiltrators.movement_blocked(b)):
                locomotor.write(self, b, rolling=False, carry=0.0)
                continue
            moved = simlocomotion.drive(self, b, dt, precise, self.range_targets, self.range_entry,
                                        self.production.at_site)
            if moved is None:
                continue
            x0, y0, at, stopped = moved
            if at is not None and (stopped or not precise and self.combat and b.serial not in self.mid_aims
                                   and any(a is b for a in self._field[1])):
                # stopped with a foe in range, or its way ended mid-tick (an idle chase, an order's end): it aims
                # from that frame, not the next tick's fight (bench engine_acquire idle220, A round 231)
                self.mid_aims[b.serial] = (self.t + at, b)
            if b.crusher > 0 and b.surface == 'ground' and (b.x, b.y) != (x0, y0):
                self.crush_along(b, x0, y0)
                if precise:                    # toppled only frame by frame: a way across one is a frame mover's
                    import engine.objects.topple as simtopple           # (simlocomotion.go_to), with or without the model (bench engine_crush)
                    for o in self.topples:
                        if not o.alive or o.toppled or o.crushable is None or b.crusher <= o.crushable:
                            continue
                        if not simtopple.crosses(b, o, (x0, y0), (b.x, b.y), self.own):
                            continue
                        o.find(kernel_interfaces.Topple).knock(self.frame_now(), b.drive_speed / simunits.LIFE_FPS)
            self.change()
        self.attachment_tick()
        # what follows a coarse move in the frame (follow_due, capture_due, infiltrators.tick, auto_kill_due) are
        # simloop's cells right after the moving cell (sim layers step 8c), no longer this method's tail

    def auto_kill_due(self):
        """A check's '自动打掉' (auto_kill s): an enemy unit within REACH of the player's things that long dies.
        After each coarse move (simloop cell auto_kill)."""
        if self.auto_kill is None:
            return
        mine = [b for b in self.living() if b.owner == self.human]
        for b in self.living():
            if not self.enemy(self.human, b.owner) or b.scenery or b.speed <= 0 or 'UNATTACKABLE' in b.status:
                continue
            close = any(math.hypot(b.x - o.x, b.y - o.y) <= REACH for o in mine)
            b.close_since = (b.close_since if b.close_since is not None else self.t) if close else None
            if close and self.t - b.close_since >= self.auto_kill:
                b.set_last_damage(self.human, None)
                self.destroy(b, f'自动打掉：在玩家 {REACH:g} 以内 {self.auto_kill:g} 秒')

    def sample(self):
        """Every 10 seconds: the threat; every 30: what the player has seen (a check's counters: simloop.counters)."""
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
            alive = {b.serial for b in mine}
            left = sum(b.hp for b in ever if b.serial in alive) /(sum(b.max_hp for b in ever) or 1.0)
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
        if '_xy' not in self.__dict__:      # a cache (a run written back from a snapshot makes its own)
            self._xy = self.ground.world(tuple(np.mgrid[0:g.shape[0], 0:g.shape[1]]))
        x, y = self._xy
        if self.all_revealed():
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
            bool(self.production.placing) or \
            any(b.path or b.building or b.life_end is not None or b.topple_end is not None for b in self.living()) or \
            (self.tech_read and any(b.grows() for b in self.books.values()))

    def run(self, until=UNTIL):
        self.used |= {'engine model' if self.model_scripts else 'frame rate', 'difficulty side'}
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
        target = round(self.t + frames / self.fps, 6)
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
                ALIGN.get(k, k + '（未写说明）') + (', '.join(sorted(self.ra3_only)) if k == 'ra3 only' else '')
                for k in sorted(self.used)))        # an unwritten key still prints (tests/guards/test_align.py)
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
        if rest.startswith('派 ') or (rest.startswith('走 ') and ' 去 ' in rest):
            who, _, where = rest[2:].rpartition(' 去 ')
            out.append((when(t), rest[0], who.strip(), where.strip()))
        elif rest.startswith('攻击 '):              # `... 强制`: a forced attack -- kept in the word group, the
            who, _, target = rest[3:].rpartition(' 打 ')     # command port's split reads it (a whole name first: i #4)
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
            what, _, where = rest[3:].rpartition(' 在 ')     # `... 由 P`: in that player's name (kept whole, as 攻击's)
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
