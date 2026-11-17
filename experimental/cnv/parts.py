"""The decoupled build: units, maps, missions and tests declared apart, assembled into a mod by one call.

A unit is a function of its options returning Unit parts (the XML text and what the map compile must know about
it); a map gives the terrain and the start; a mission places objects and writes scripts; a test adds its own
objects, scripts, on-screen counters, the bench steps that run it and the readings it expects. assemble() feeds
them through the CampNew7 pipeline (experimental/campaign: mission slot, map cache, linked map stream, lint) --
the old make_camp*.py chain stays as it was (user 2026-10-21: only new work is written this way).

Each layer talks to the next only through what that one publishes (user 2026-10-22: interface to interface, no
reaching in): a map its SITES (named places) and PLAYERS / TEAMS; a unit its abilities; a mission its cast (who
plays which part, on which sites), its endings, its marks (waypoints by part) and facts (timings). A check asks the
mission (m.site, m.role, m.ability, m.point, m.player), never a mission module's constants or a coordinate of its own; contract() says, before any build, which
script argument names something nobody published.

This file is now a facade (ADR 0016): the names live in model.py (L2, mission data), contract.py (L5, rule checks)
and package.py (L3, packaging); new code should import those.

  python -I -X utf8 experimental/cnv/build.py a8 [--test liberty_jump] [--name CampX]
"""

from contract import (AREA_ARG, COMMAND_ARG, CREATES_NAMED, MUSIC_EVENT_ARG, OBJECT_ARG, OBJECTIVE_ARG, PLAYER_ARG,  # noqa: F401
                      POINTS_AT_UNNAMED, POWER_ARG, RETAIL_COMMANDS, SOUND_ARG, STRING_ARG, TEAM_ARG, TEMPLATE_ARG,
                      WAYPOINT_ARG, contract, missing_areas)
from model import (COUNTER_LINES, MAX_NAME, NOT, Goal, Mission, Obj, Part, Role, Script, Site, Test, Unit,  # noqa: F401
                   _enum, counted, kindof, merged, side_by_side, square, status, unnot)
from package import (CAMPAIGN, HERE, SIDECAR, assemble, game_running, mod_busy, preview, sdk_build_lock,  # noqa: F401
                     write_map, write_sidecar)
