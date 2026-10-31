"""The game's own dynamic music (its combat states: sdk SageXML/PathMusic) driving our A4 music
(experimental/music/a4.py): the mission turns the system on and stages a fight the player first loses, then wins,
then no more fighting. A recording of the game (experimental/music/bench_listen.py --nav) then says which section
played when: listen.identify against a4.STREAMS (index.npz there).

  0 s        a4's start event (prep) and the dynamic system on (a4.DYNAMIC_SYSTEM)
  ENEMY_AT   enemy tanks and infantry attack-move onto the player's infantry, in the start camera's view: combat
             (-> fierce); they kill many and lose few (-> SetAdvantageEnemy -> tense, after 20 s of combat)
  HELP_AT    a strong player force arrives and kills them (-> ResetAdvantage -> fierce)
  then quiet (-> Threat1_1 -> escort)

Facts: enemy at, help at (mission seconds).
"""
import os
import sys

from maps import island
from parts import Mission, Script

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from experimental.music import a4, pack  # noqa: E402

ENEMY_AT, HELP_AT = 5.0, 80.0
ENEMY = {'JapanAntiVehicleVehicleTech1': 6, 'JapanAntiInfantryInfantry': 8}      # tsunami tanks, imperial warriors
PLAYER = {'AlliedAntiInfantryInfantry': 16}                                       # peacekeepers
# guardian tanks: 12 killed the enemy but never got the game to fire ResetAdvantage (bench 2026-10-26: it wants
# twice as many kills as losses over 20 s, and 3 kills), so many more, to lose few
HELP = {'AlliedAntiVehicleVehicleTech1': 24}


SPY_VAR_CASES = ('UpYoursSoviet', 'UpYoursEmpire')     # spy: Threat1_1 plays the first's tracer if a4.PHASE_VAR
                                                       # holds 1, else the second's (what does the variable start at?)


def _spy_pack():
    """Every event plays a tracer of its own, at once (ownmap.spy): the recording says which events the game's
    dynamic system fired when (bench_listen prints the tracer runs: stream = event index)."""
    from experimental.music import extract, ownmap
    b, lengths = ownmap.spy(extract.retail_map())
    secs = {e.name: s for e, s in zip(b.m.events, b.sections)}
    b.act(a4.EVENTS['calm'][0], ownmap.switch(a4.PHASE_VAR, {1: ownmap.goto(secs[SPY_VAR_CASES[0]], True)},
                                              ownmap.goto(secs[SPY_VAR_CASES[1]], True)))
    return pack.make(b.m, pack.tracer_tracks(b.m, lengths))


def _tracer_pack():
    """a4's own map, every stream a tracer (stream k plays tracer k): the recording says which stream the game
    played when, with no doubt between sections that sound alike."""
    from experimental.music import extract
    b, secs, lengths = a4.music_map(extract.retail_map())
    ours = lengths[:len(lengths) - len(b.kept)]                 # the shell's retail streams stay retail
    return pack.make(b.m, pack.tracer_tracks(b.m, ours, extract.retail_streams(b.kept)))


def mission(name='CampMusDyn', spy=False, tracer=False):
    start = a4.EVENTS['start'][0]
    m = Mission(name=name, map=island, facts={'enemy at': ENEMY_AT, 'help at': HELP_AT},
                music=pack.Later(_spy_pack if spy else _tracer_pack if tracer else a4.pack, {start}))
    m.waypoint('fight', 'CNV Music Fight', 'west field')
    m.waypoint('help', 'CNV Music Help', 'west shore')
    k = 0
    for tmpl, n in PLAYER.items():
        for j in range(n):
            m.put(tmpl, 'west field', -60 + 40 * (j % 4), -60 + 40 * (j // 4))
    enemy = []
    for tmpl, n in ENEMY.items():
        for j in range(n):
            k += 1
            enemy.append(f'UNIT - CNV Music Enemy {k}')
            m.put(tmpl, 'east field', -100 + 50 * (j % 4), -60 + 60 * (j // 4), side='s1', name=enemy[-1],
                  role=f'enemy {k}')
    help_ = []
    for tmpl, n in HELP.items():
        m.spawns.add(tmpl)
        for j in range(n):
            help_.append((f'UNIT - CNV Music Help {j + 1}', tmpl))
    m.scripts += [
        Script('CNV Music - Start', [], [('PATH_MUSIC_PLAY_EVENT', start),
                                         ('PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM', a4.DYNAMIC_SYSTEM),
                                         ('SET_MILLISECOND_TIMER', 'CNV Music Enemy', ENEMY_AT),
                                         ('SET_MILLISECOND_TIMER', 'CNV Music Help', HELP_AT)]),
        Script('CNV Music - Enemy', [('TIMER_EXPIRED', 'CNV Music Enemy')],
               [('ATTACK_MOVE_NAMED_UNIT_TO', n, m.mark('fight')) for n in enemy]),
        Script('CNV Music - Help', [('TIMER_EXPIRED', 'CNV Music Help')],
               [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', n, t, m.team('p1'), m.mark('help')) for n, t in help_] +
               [('ATTACK_MOVE_NAMED_UNIT_TO', n, m.mark('fight')) for n, _ in help_]),
    ]
    return m
