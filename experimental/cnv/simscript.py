"""L6 script vocabulary (ADR 0029, docs/engine/sim-layers.md): the name sets and spellings the script actions and
conditions share, moved out of sim.py so the action files (simact_*) can read them without importing sim. sim
re-exports each (`sim.TEAM_COMMANDS` still works)."""

TEAM_FOLLOWS = ('TEAM_FOLLOW_WAYPOINTS', 'TEAM_FOLLOW_WAYPOINTS_EXACT', 'TEAM_ATTACK_MOVE_FOLLOW_WAYPOINTS',
                'TEAM_FOLLOW_WAYPOINTS_STARTING_AT_WAYPOINT')      # Sim.order_follow
TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP') \
    + TEAM_FOLLOWS                                                  # E3: need a live team
