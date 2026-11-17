"""Engine probe: the skirmish AI's script switches our levels send at its wake (plan.py 敌方AI: priorities 20, repairs
and rebuild 0) -- SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES, SKIRMISH_AI_USE_REPAIRS, SKIRMISH_AI_USE_REBUILD_SYSTEM
(engine line B, layer 4; read back by checks/engine_aiswitch.py; program: work/re l4_aiswitches.md; model:
RA3-EngineModel ra3model/ai/player.py set_enemy_priorities / repairs / use_rebuild, simai.Brain.switches).

The map, AI and the player's structures are aitarget_bench's (one always-on state sends 2-4 Peacekeepers by
SimpleAttack); only the wake's switches differ, plus for the repair / rebuild builds a power plant of the AI's own
north of its yard:
  aisw0near  aitargetnear (ClosestStructureHeuristic) with priorities 0: read, the enemy table is emptied -> no
             enemy player -> no target, no team leaves (the control aitargetnear went to the near plant at s13)
  aisw0far   ainmfar (NamedObject, the far plant) with priorities 0: does a named target look at the enemy table?
             (the program, work/re/l4_states.md, reads no relationship tier: the model says the team still goes)
  aiswrep1 / aiswrep0  the AI's plant at 50 % health from the start, repairs 1 / 0: read, repairing needs the switch
             and the personality's RepairBuildingsAtDifficulty (MEDIUM HARD BRUTAL); the model says 1 heals, 0 not
  aiswreb1 / aiswreb0  the AI's plant killed 5 s after the wake, 5000 money at the wake, rebuild 1 / 0: is it put
             back, how soon? (who reads the rebuild list is NOT READ; the model rebuilds nothing)
Facts: wake at, own plant (name), kill at (rebuild builds).
"""
from missions import ainamed_bench as an
from missions import aitarget_bench as at
from parts import Script

OWN = 'UNIT - CNV AI Own Plant'
KILL_AFTER = 5.0
MONEY = 5000


def switches(m, prio=20, repairs=0, rebuild=0, money=0):
    """The wake script's switches set to these (the rest of aitarget_bench's wake kept)."""
    s1 = m.player('s1')
    (wake,) = [s for s in m.scripts if s.name == 'CNV AI - Wake']
    vals = {'SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES': prio, 'SKIRMISH_AI_USE_REPAIRS': repairs,
            'SKIRMISH_AI_USE_REBUILD_SYSTEM': rebuild, 'PLAYER_SET_MONEY': money}
    wake.do = [(a[0], s1, vals[a[0]]) if a[0] in vals else a for a in wake.do]
    return m


def own_plant(m):
    m.put('AlliedPowerPlant', 'east base', 0.0, 300.0, side='s1', name=OWN, role='ai plant')
    m.facts['own plant'] = OWN
    return m


def repair(mod, on):
    m = own_plant(switches(at.mission(mod, 'ClosestStructureHeuristic', 'SimpleAttack'), repairs=on))
    m.scripts.append(Script('CNV AI - Hurt', [], [('UNIT_SET_HEALTH', OWN, 50.0)]))
    return m


def rebuild(mod, on):
    m = own_plant(switches(at.mission(mod, 'ClosestStructureHeuristic', 'SimpleAttack'), rebuild=on, money=MONEY))
    m.facts['kill at'] = m.facts['wake at'] + KILL_AFTER
    m.scripts.append(Script('CNV AI - Kill own plant', [('TIMER_EXPIRED', 'CNV AI Kill')], [('NAMED_KILL', OWN)]))
    (wake,) = [s for s in m.scripts if s.name == 'CNV AI - Wake']
    wake.do = list(wake.do) +[('SET_MILLISECOND_TIMER', 'CNV AI Kill', KILL_AFTER)]
    return m


MISSION = {
    'aisw0near': lambda: switches(at.mission('CampAISw0Near', 'ClosestStructureHeuristic', 'SimpleAttack'), prio=0),
    'aisw0far': lambda: switches(an.mission('CampAISw0Far', 'NamedObject', an.FAR_NAME), prio=0),
    'aiswrep1': lambda: repair('CampAISwRep1', 1),
    'aiswrep0': lambda: repair('CampAISwRep0', 0),
    'aiswreb1': lambda: rebuild('CampAISwReb1', 1),
    'aiswreb0': lambda: rebuild('CampAISwReb0', 0),
}
