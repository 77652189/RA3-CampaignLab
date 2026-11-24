"""L6 script conditions on what is seen (ADR 0029, docs/engine/sim-layers.md; L3): a viewer or a team sighting an
enemy or a type, an object or a team discovered.

Each condition is `fn(sim, name, a)`, moved verbatim out of Sim.cond's chain; simcond.cond looks them up in
CONDITIONS. None back: not taken (a gap)."""
import math

from engine.script.common import RELATION_OF, players_of, team_crew


def _stands(sim, a, b, want):
    """How player a takes b is `want` (RELATION_OF's; None: any)."""
    return want is None or sim.relation(a, b) == want


def enemy_sighted(sim, name, a):
    # (viewer, relation, player): the viewer finds an object of the player's that stands to it as asked, within
    # its sight (engine_levelvision a: a range query, no shroud). Bench 11-14 engine_eyes all 看见 45 -> 47: the
    # third argument is the sighted object's owner (watch's Enemy Soviet_5 only once far came in); Friend
    # takes the viewer's own side and the viewer itself (lone, nobody near: on); Enemy of its own player and
    # Neutral of an enemy never. Stealth and the exact edge INFERRED
    viewer = sim.body(a[0])
    want = RELATION_OF.get(a[1])
    live = list(sim.living())
    hidden = sim.cloaked(live, mark=False)
    return bool(viewer and viewer.alive and want and any(
        target.owner == a[2] and _stands(sim, viewer.owner, target.owner, want)
        and target.serial not in hidden
        # Centre-distance boundary/combined modifiers remain INFERRED.
        and math.hypot(target.x - viewer.x, target.y - viewer.y) <= viewer.sight * viewer.level_vision
        for target in live))


def named_discovered(sim, name, a):
    sim.used.add('discovered')
    b = sim.body(a[1])
    return bool(b and (any(sim.infiltrators.unit_discovered(p, b) for p in players_of(sim, a[0]))
                       or sim.sees(b.x, b.y, b.surface == 'air')))


def enemy_sighted_by_team(sim, name, a):
    # retail batch 2 (round 210, checks/engine_conds.py sight; d115_script_semantics.md 4-6)
    # 码 (team, relation, player): a member with sight finds an object of the player's, not INERT / MOVE_ONLY,
    # the member's relation to it the one asked, within its sight. A range query: no fog, no stealth. Bench
    # 11-13 engine_conds sight 视野: the member itself counts (&4 all along); a Guardian 230 from the member
    # unseen, 180 seen (sight 200: centre to centre, as ENEMY_SIGHTED -- not D 115's sight + both radii; the
    # edge between 200 and 223 INFERRED); a killed one seen while it lies (&1 ~11 s after NAMED_KILL; the
    # simulator's Guardian lies 0 s -- its SlowDeath time is not this condition's). View angle not modelled
    crew = team_crew(sim, a[0])
    if crew is None:
        return False
    rel = a[1][2] or a[1][0] if isinstance(a[1], tuple) else a[1]
    want = RELATION_OF.get(rel)
    them = [t for t in sim.bodies.values() if t.owner == a[2] and (t.alive or sim.dying(t))
            and not ({'INERT', 'MOVE_ONLY'} & set(t.kinds))]
    return any(_stands(sim, m.owner, t.owner, want)
               and math.hypot(t.x - m.x, t.y - m.y) <= m.sight * m.level_vision
               for m in crew if m.sight > 0 for t in them)


def team_discovered(sim, name, a):
    # retail batch 2 (round 210, checks/engine_conds.py sight; d115_script_semantics.md 4-6)
    # 码 (player, team): a member the player sees (the fog clear or partly so, INFERRED: as Sim.sees / looks) and
    # not hidden from it; the player's own members always. Bench 11-13 engine_conds sight 发现&1: a member on
    # the move is not (near, in plain sight, off the second or two it moved; INFERRED: its fog status is
    # re-read once it stands, Generals' partition data)
    crew = team_crew(sim, a[1])
    if not crew:
        return False
    live = list(sim.living())
    hidden = sim.cloaked(live, mark=False)
    for m in crew:
        air = m.surface == 'air'
        if m.owner == a[0]:
            return True
        if 'SHROUD_REVEAL_TO_ALL' in m.status:  # bench 11-13 engine_acts flow 旗&1: the bit set on a standing
            return True                          # unit far from all the player's, discovered from that second
        if m.serial in hidden or sim.on_the_move(m):
            continue
        if (sim.sees(m.x, m.y, air) if a[0] == sim.human else
                any(b.owner == a[0] and sim.looks(b, m.x, m.y, air) for b in live)):
            return True
    return False


def type_sighted(sim, name, a):
    # retail batch 4 (round 238, checks/engine_sighted.py all)
    # (viewer, type, player): ENEMY_SIGHTED's range query with a type in place of the relation -- 看见 37 -> 39:
    # the Peacekeeper only once it came within watch's sight, the viewer itself counts (lone, alone: on), the
    # type in any case. A list made by OBJECTLIST_ADDOBJECTTYPE never matched (&16 off all run, the same list
    # PLAYER_HAS_OBJECT_COMPARISON reads); a map's own object list (retail ep01) INFERRED to match
    viewer = sim.body(a[0])
    want = str(a[1]).lower()
    live = list(sim.living())
    hidden = sim.cloaked(live, mark=False)
    return bool(viewer and viewer.alive and any(
        target.owner == a[2] and target.template.lower() == want and target.serial not in hidden
        and math.hypot(target.x - viewer.x, target.y - viewer.y) <= viewer.sight * viewer.level_vision
        for target in live))


CONDITIONS = {
    'ENEMY_SIGHTED': enemy_sighted,
    'NAMED_DISCOVERED': named_discovered,
    'ENEMY_SIGHTED_BY_TEAM': enemy_sighted_by_team,
    'TEAM_DISCOVERED': team_discovered,
    'TYPE_SIGHTED': type_sighted,
}
