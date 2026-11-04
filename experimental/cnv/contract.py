"""Layer L5, the rule checks on the product: contract() says, before any build, which script argument names something
nobody published (a map's SITES, a mission's cast, a unit's abilities ...).

Imports model.py at most, never package.py (tests/test_architecture.py, G-layers). The campaign folder must already be
on sys.path (package.py / parts.py put it there) for mapscript. Split out of parts.py (ADR 0016).
"""
import collections


AREA_ARG = 9                            # script argument type of a trigger area name (script_catalog.json)
# the other argument types contract() holds against what was published
TEAM_ARG, WAYPOINT_ARG, PLAYER_ARG, OBJECT_ARG, STRING_ARG, POWER_ARG, TEMPLATE_ARG = 3, 7, 11, 14, 25, 31, 61
COMMAND_ARG = 34                        # a command button (NAMED_USE_COMMANDBUTTON_ABILITY)
# retail units' own command buttons a script may press (SageXML GlobalData/LogicCommandSet.xml): ours publish theirs
RETAIL_COMMANDS = {'Command_CaptureBuilding'}           # an engineer takes a building (AlliedEngineerCommandSet)
OBJECTIVE_ARG = 91                      # a mission objective's name (SET_MISSION_OBJECTIVE_STATUS ...)
MUSIC_EVENT_ARG = 96                    # a Pathfinder event's name (PATH_MUSIC_PLAY_EVENT): held to Mission.music
SOUND_ARG = 12                          # a sound event (PLAY_SOUND_EFFECT, HAS_FINISHED_AUDIO): ours (CNV_*) held to
                                        # Mission.voice, retail's free
CREATES_NAMED = ('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION',
                 'UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION')


POINTS_AT_UNNAMED = 'SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER'    # (kind, player, team, name)


def missing_areas(mission):
    """Trigger areas the scripts name but nobody declared (the map's own areas are replaced by the mission's)."""
    return [p for p in contract(mission) if ' area ' in p]


def contract(mission):
    """What the mission (merged with its check) uses that nobody published -- checked before any build:
    objects placed by raw coordinates or on a site the map lacks; cast parts naming no object; script arguments
    naming an object, waypoint, trigger area, team, player, string or special power nobody declared, a template
    that is neither cast nor one of the mission's units; a named object fired with a power its unit does not
    publish."""
    import mapscript
    m, cat, out = mission, mapscript.catalog(), []
    sites = getattr(m.map, 'SITES', {})
    named = {o.name: o for o in m.objects if o.name}
    named.update({o.name: o for o in getattr(m.map, 'STRONGPOINTS', {}).values()})     # the map's, published
    out += [f'object {o.template} at ({o.x:g}, {o.y:g}): placed by raw coordinates, not by a map site'
            for o in m.objects if not o.site]
    out += [f'object {o.template}: map has no site {o.site!r}' for o in m.objects if o.site and o.site not in sites]
    # an object a script creates by name is declared by that script (the first argument of the CREATE_NAMED_* ones)
    created = {args[0] for s in m.scripts for name, *args in s.do if name in CREATES_NAMED}
    # ... and so is a name a script points at an unnamed unit of a kind (the retail campaign names a building so)
    created |= {args[3] for s in m.scripts for name, *args in s.do if name == POINTS_AT_UNNAMED}
    out += [f'cast {k}: no object named {r.name!r}' for k, r in m.cast.items()
            if r.name and r.name not in named and r.name not in created]
    out += [f'mark {k}: no waypoint {w!r}' for k, w in m.marks.items() if w not in m.waypoints]
    powers = {p: u for u in m.units for p in u.abilities.values()}
    known = {AREA_ARG: ('area', m.areas), TEAM_ARG: ('team', set(getattr(m.map, 'TEAMS', {}).values())),
             WAYPOINT_ARG: ('waypoint', m.waypoints), PLAYER_ARG: ('player', set(getattr(m.map, 'PLAYERS', {}).values())),
             OBJECT_ARG: ('object', set(named) | created), STRING_ARG: ('string', m.strings), POWER_ARG: ('power', powers),
             COMMAND_ARG: ('command button', set(powers) | RETAIL_COMMANDS), OBJECTIVE_ARG: ('objective', {g.name for g in m.objectives}),
             TEMPLATE_ARG: ('template', {r.template for r in m.cast.values()} | {u.id for u in m.units} | m.spawns)}
    if m.music:
        known[MUSIC_EVENT_ARG] = ('music event', m.music.events)

    def latin(v):
        try:
            v.encode('latin-1')
            return True
        except UnicodeEncodeError:
            return False
    # the map stores names and script arguments as Latin-1 (only the string table's texts are Unicode): a plan's
    # Chinese in a script name would crash the build (2026-10-24)
    out += [f'script name {s.name!r}: not Latin-1' for s in m.scripts if not latin(s.name)]
    seen = collections.Counter(s.name for s in m.scripts)
    out += [f'script name {k!r}: {n} scripts have it' for k, n in seen.items() if n > 1]
    out += [f'{kind} {v!r}: not Latin-1' for kind, vs in (('object', named), ('waypoint', m.waypoints),
                                                          ('area', m.areas)) for v in vs if not latin(v)]
    out += [f'{s.name}: {name} argument {v!r}: not Latin-1' for s in m.scripts for name, *args in s.when + s.do
            for v in args if isinstance(v, str) and not latin(v)]
    for s in m.scripts:
        for name, *args in s.when + s.do:
            types = cat[name]['args']
            for t, v in zip(types, args):
                if t in known and v not in known[t][1]:
                    out.append(f'{s.name}: {name} {known[t][0]} {v!r} not published')
                if t == SOUND_ARG and str(v).startswith('CNV_') and v not in (m.voice.events if m.voice else ()):
                    out.append(f'{s.name}: {name} voice line {v!r} not in the voice pack')
            own = POWER_ARG if POWER_ARG in types else COMMAND_ARG
            if OBJECT_ARG in types and own in types:                # NAMED_FIRE_SPECIAL_POWER_* / _USE_COMMANDBUTTON_*
                who, power = args[types.index(OBJECT_ARG)], args[types.index(own)]
                if who in named and power in powers and powers[power].id != named[who].template:
                    out.append(f'{s.name}: {who} ({named[who].template}) fired {power}, an ability of {powers[power].id}')
    return out
