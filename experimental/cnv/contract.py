"""Layer L5, the rule checks on the product: contract() says, before any build, which script argument names something
nobody published (a map's SITES, a mission's cast, a unit's abilities ...).

Imports model.py at most, never package.py (tests/test_architecture.py, G-layers). The campaign folder must already be
on sys.path (package.py / parts.py put it there) for mapscript. Split out of parts.py (ADR 0016).
"""
import collections
import math
import re


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


OUTLET_SCRIPTS = re.compile(r'CNV \w+ - (Say \d+( chat)?|Now \d+|Phase \d+ line \d+)')    # ctx.talk's: a queued line, a scene's
QUEUE_SCRIPTS = re.compile(r'CNV \w+ - (Say|Drop) (\d+)( chat)?')
PENDING_FLAG = re.compile(r'CNV_\w+_Say_\d+')
TALKING_FLAG = re.compile(r'CNV_\w+_Talking')


def said_outside_the_outlet(m, cat):
    """G3b (K1): everything the player sees said or hears said -- a caption, an announcer line, one of our voice lines,
    a talking head -- is done by a script of the one queue (ctx.say: `CNV <tag> - Say k`, or a scene's `Phase n line k`,
    which wait for the floor), or by the ending's own script (ctx.final: the ending line, which waits for the floor),
    never by a script of its own, where two lines would come up together. Test scripts (`Test - ...`, a check's own)
    are not the level's."""
    talk = {n for n in cat if 'MILITARY_CAPTION' in n or 'EVA_EVENT' in n} | {'MOVIE_PLAY_RADAR'}
    ends = set(m.endings)
    return [f'{s.name}: {name} outside the dialogue outlet (ctx.say queues every line, one at a time)'
            for s in m.scripts if not s.name.startswith('Test') and not OUTLET_SCRIPTS.fullmatch(s.name)
            and s.name not in ends
            for name, *args in s.do
            if name in talk or (name == 'PLAY_SOUND_EFFECT' and str(args[0]).startswith('CNV_'))]


def said_lines_kept(m):
    """K2 (2026-11-04): what must be said is never lost. A line is dropped only by its own `Drop k` script, and only
    a 闲话 line (its `Say k chat`) has one; nothing else puts a queued line's flag down; an ending script that shows
    its line waits for the floor (the flag `Talking` is down), so it comes after the line being said and is said in
    the frame the mission ends."""
    names, out = {s.name for s in m.scripts}, []
    for s in m.scripts:
        q = QUEUE_SCRIPTS.fullmatch(s.name)
        if q and q[1] == 'Drop' and s.name.replace('Drop', 'Say') + ' chat' not in names:
            out.append(f'{s.name}: drops a line that is not 闲话 (a 功能 line is never dropped)')
        if q:
            continue
        out += [f'{s.name}: puts the queued line flag {a[0]!r} down (only its own Say / Drop may)'
                for name, *a in s.do if name == 'SET_FLAG' and PENDING_FLAG.fullmatch(str(a[0])) and not a[1]]
    for s in m.scripts:
        if s.name in m.endings and any('MILITARY_CAPTION' in x[0] for x in s.do) \
                and not (any(c[0] == 'FLAG' and TALKING_FLAG.fullmatch(str(c[1])) and not c[2] for c in s.when)
                         and any(x[0] == 'SET_FLAG' and TALKING_FLAG.fullmatch(str(x[1])) and x[2] for x in s.do)):
            out.append(f'{s.name}: an ending that says its line must wait for the floor and then take it '
                       f'(ctx.ending_gate, ctx.ending_begin)')
    return out


NOW_SCRIPTS = re.compile(r'CNV \w+ - Now \d+')            # a 功能 line's caption (ctx.Talk): shown the frame its event came
FUNC_SAY = re.compile(r'CNV \w+ - Say \d+')               # the 功能 queue's (a 闲话 line's has ' chat' after the number)
SHOW_FLAG = re.compile(r'CNV_\w+_Show_\d+')
SCENE_FLAG = re.compile(r'CNV_\w+_InScene')
FRESH_FLAG = re.compile(r'CNV_\w+_Fresh')                 # a 功能 caption went up FUNC_HOLD ago (it is not cut short)


def said_once_and_on_time(m):
    """E6 (2026-11-04, the engine's two channels: one caption box that holds a line, one dialogue panel that stacks the
    subtitles of dubbed lines) and K1's "a 功能 line is never late": (a) no line is shown in both places: a script that
    plays a recording carrying its own subtitle shows no caption, and no caption has the words of such a subtitle;
    (b) the recordings the voice pack gives a subtitle are exactly the ones the mission counts; (c) a 功能 line's
    caption is a script of its own that waits for nothing but its event, a scene's end and the 功能 caption before it
    (ctx.FUNC_HOLD), so it is up within ctx.FUNC_LATE of the event (the sim holds the run to that: late_captions), and
    never sits in the queue; (d) nothing but that script shows a caption in the 功能 queue's scripts."""
    out = []
    texts = {m.strings.get(k, k) for k in m.subtitles.values()}
    for s in m.scripts:
        if s.name.startswith('Test'):
            continue
        plays = [a[0] for name, *a in s.do if name == 'PLAY_SOUND_EFFECT' and a and a[0] in m.subtitles]
        caps = [a for name, *a in s.do if 'MILITARY_CAPTION' in name]
        if plays and caps:
            out.append(f'{s.name}: plays {plays[0]}, which carries its own subtitle, and shows a caption: one channel')
        out += [f'{s.name}: caption {m.strings.get(c[0], c[0])!r} says what a recording\'s own subtitle shows (one channel)'
                for c in caps if m.strings.get(c[0], c[0]) in texts]
        if NOW_SCRIPTS.fullmatch(s.name):
            late = [c for c in s.when if not ((c[0] == 'FLAG' and SHOW_FLAG.fullmatch(str(c[1])) and c[2])
                                              or (c[0] == 'FLAG' and SCENE_FLAG.fullmatch(str(c[1])) and not c[2])
                                              or (c[0] == 'FLAG' and FRESH_FLAG.fullmatch(str(c[1])) and not c[2]))]
            out += [f'{s.name}: a 功能 caption that waits for {c[:2]} is late (it waits for its event only)' for c in late]
        elif FUNC_SAY.fullmatch(s.name) and caps:
            out.append(f'{s.name}: a caption in the 功能 queue is late (a 功能 line shows its caption at once, ctx.Talk)')
    have = set(getattr(m.voice, 'subtitled', ())) if m.voice else set()
    if have != set(m.subtitles):
        out.append(f'the voice pack gives {sorted(have ^ set(m.subtitles))} a subtitle the mission does not count (or the '
                   f'other way): plan.py and voice_link.Later.subtitled must agree')
    return out


# G6b (E3): the game finds a team by name without making it, so an order to a team nobody joined does nothing. A team
# of the mission's own gets an instance when a unit is put on it (UNIT_SET_TEAM, even a unit that is not there; a
# CREATE_*_ON_TEAM) or one placed in the map is its member.
TEAM_COMMANDS = ('MOVE_TEAM_TO', 'ATTACK_MOVE_TEAM_TO', 'TEAM_ATTACK_NAMED', 'TEAM_GUARD_AREA', 'TEAM_STOP', 'TEAM_HUNT')
JOINS_TEAM = {'UNIT_SET_TEAM': 1, 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT': 2,
              'CREATE_NAMED_ON_TEAM_AT_WAYPOINT_WITH_ORIENTATION': 2}      # action -> the index of the team it names


# E7 (2026-11-04, ra3-script-reference E7-6, E7-7). PATH_MUSIC_PLAY_EVENT suspends the game's combat music (the dynamic
# system) and nothing brings it back, so every cue after it was switched on must switch it on again in the same action
# list (the order the bench heard work: cue, then ENABLE, the same frame). And the library's Mission Won / Mission Lost
# (Lib_End_Mission) play S_EndMissionWin / S_EndMissionLose themselves, then take the player's input away, show the
# victory screen after 2 s and end in 5 s (QUICKVICTORY()) or end in 3 s (DEFEAT()): a caption set in the same script
# is on screen that long at most.
MUSIC_CUE, MUSIC_DYNAMIC = 'PATH_MUSIC_PLAY_EVENT', 'PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM'
ENDING_EVENTS = 'S_EndMission'                      # the library plays these; the shell's own end-of-mission music
PHASE_SCRIPT = re.compile(r'CNV \w+ - Phase (\d+)( \(\d+\))?')      # phase n's own script (its 开场 acts)
PHASE_FLAG = re.compile(r'CNV_\w+_Phase_(\d+)')                     # raised when phase n begins, stays up
ENDING_LIBRARY_AT = {'Mission Won': 5.0, 'Mission Lost': 3.0}       # seconds from the flag to QUICKVICTORY() / DEFEAT()
                                                                    # (the victory screen comes at 2 s, whether the caption
                                                                    # shows under it is not known)
CJK_CPS, LATIN_CPS = 9.0, 17.0                      # characters a player reads in a second: the subtitle norm (Netflix
                                                    # timed-text style guide: Chinese 9, English 17)


def read_seconds(text):
    """Seconds a player needs to read a caption."""
    return sum(1 / CJK_CPS if ord(c) >= 0x2e80 else 1 / LATIN_CPS for c in text)


def script_phase(s):
    """The latest phase a script is certain to run in (or after): phase n's own script, or one whose condition holds
    a phase's flag up. None: nothing ties it to a phase (a rule waiting for a device's event, say)."""
    n = None
    own = PHASE_SCRIPT.fullmatch(s.name)
    if own:
        n = int(own[1])
    for c in s.when:
        f = PHASE_FLAG.fullmatch(str(c[1])) if c[0] == 'FLAG' and len(c) > 2 and c[2] == 1 else None
        if f:
            n = max(n or 0, int(f[1]))
    return n


def unresumed_cues(scripts):
    """[(script, index of the last cue)]: scripts that play a (non-ending) music cue in or after the phase that switches
    the combat music on, with no switch-on after the cue."""
    on = [script_phase(s) for s in scripts if any(a[0] == MUSIC_DYNAMIC for a in s.do)]
    on = [n for n in on if n is not None]
    if not on:
        return []
    out = []
    for s in scripts:
        n = script_phase(s)
        if n is None or n < min(on):
            continue
        cues = [i for i, a in enumerate(s.do) if a[0] == MUSIC_CUE and not str(a[1]).startswith(ENDING_EVENTS)]
        if cues and not any(a[0] == MUSIC_DYNAMIC for a in s.do[cues[-1]:]):
            out.append((s, cues[-1]))
    return out


def music_resumes(m):
    """E7: once the combat music is on, a cue switches it on again (see MUSIC_CUE above); the ending's cues are the
    library's, so a script that sets Mission Won / Mission Lost plays none of its own."""
    out = [f'{s.name}: plays a music cue after the combat music was switched on and does not switch it on again '
           f'(it stays suspended: PATH_MUSIC_PLAY_EVENT, E7-6)' for s, _ in unresumed_cues(m.scripts)]
    out += [f'{s.name}: plays {a[1]} itself; the library plays it when {flag!r} is set (E7-7)' for s in m.scripts
            for flag in ENDING_LIBRARY_AT if ('SET_FLAG', flag, 1) in s.do
            for a in s.do if a[0] == MUSIC_CUE and str(a[1]).startswith(ENDING_EVENTS)]
    return out


def ending_line_fits(m):
    """E7: the caption of a script that sets Mission Won / Mission Lost stays on the screen only until the library's
    QUICKVICTORY() / DEFEAT() (ENDING_LIBRARY_AT), and has the words a player reads in that time (read_seconds)."""
    out = []
    for s in m.scripts:
        for flag, until in ENDING_LIBRARY_AT.items():
            if ('SET_FLAG', flag, 1) not in s.do:
                continue
            for name, *a in s.do:
                if 'MILITARY_CAPTION' not in name:
                    continue
                text = m.strings.get(a[0], a[0])
                if a[1] > until:
                    out.append(f'{s.name}: the ending caption stays {a[1]:g} s, {flag!r} ends it in {until:g} s')
                if read_seconds(text) > until:
                    out.append(f'{s.name}: the ending caption {text!r} takes {read_seconds(text):.1f} s to read, '
                               f'{flag!r} ends it in {until:g} s')
    return out


def team_orders_land(m):
    """G6b: every whole-team order of the level (a check's `Test ...` own are not) goes to a team that has an instance
    when it runs: the same script put a unit on that team before it (ctx.order does: UNIT_SET_TEAM for each name, then
    the order), or the team is one of the map's own or has a member placed in the map. A TEAM_STOP only needs the team
    to be joined by some script of the level (it adds nobody, so it follows an order given before)."""
    placed = {o.props.get('originalOwner') for o in m.objects if isinstance(getattr(o, 'props', {}).get('originalOwner'), str)}
    own = set(getattr(m.map, 'TEAMS', {}).values()) | placed
    joined = {a[JOINS_TEAM[name]] for s in m.scripts if not s.name.startswith('Test')
              for name, *a in s.do if name in JOINS_TEAM}
    out = []
    for s in m.scripts:
        if s.name.startswith('Test'):
            continue
        here = set()
        for name, *a in s.do:
            if name in JOINS_TEAM:
                here.add(a[JOINS_TEAM[name]])
            elif name in TEAM_COMMANDS and a[0] not in own | here and not (name == 'TEAM_STOP' and a[0] in joined):
                out.append(f'{s.name}: {name} {a[0]}: nobody joined this team before the order (UNIT_SET_TEAM first, or '
                           f'place a member in the map): the game ignores an order to a team without an instance')
    return out


KIND_IN_AREA = 'PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA'


def kind_counts_in_area(m):
    """E1 (the engine reads one table for every player, bench 2026-11-04): a count of a unit kind in a trigger area is a
    count of everyone's, whatever player the condition names, so a level's own script (a check's `Test ...` own are not)
    never uses it. Ask SKIRMISH_PLAYER_HAS_UNITS_IN_AREA (per player), or count a template
    (PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA, per player)."""
    return [f'{s.name}: {KIND_IN_AREA} counts every player\'s units of a kind (the engine ignores the player): ask '
            f'SKIRMISH_PLAYER_HAS_UNITS_IN_AREA or count a template'
            for s in m.scripts if not s.name.startswith('Test') for c in s.when if c[0] == KIND_IN_AREA]


def camera_outside_the_view(m):
    """K5 (G10): a level's camera move aims at a view point (ctx.camera: the site held inside the playable area in
    force, a screen's half-size from its edge), so no frame shows the black beyond the border. Every MOVE_CAMERA_TO of
    the level's scripts (a check's `Test ...` own are not) names a waypoint the compiler published a view rect for,
    and the waypoint lies inside it."""
    out = []
    for s in m.scripts:
        if s.name.startswith('Test'):
            continue
        for name, *a in s.do:
            if name != 'MOVE_CAMERA_TO':
                continue
            rect, at = m.views.get(a[0]), m.waypoints.get(a[0])
            if rect is None or at is None:
                out.append(f'{s.name}: camera aims at {a[0]!r}, which is no view point (ctx.camera makes them)')
            elif not (rect[0] - 1e-6 <= at[0] <= rect[2] + 1e-6 and rect[1] - 1e-6 <= at[1] <= rect[3] + 1e-6):
                out.append(f'{s.name}: camera aims at {a[0]!r} {at}, outside where the screen stays on the map {rect}')
    return out


# G6 (K6): the commands that give one named unit an order. A level never uses them: a group is a team of the map's own
# and is ordered as one (ctx.order / Mission.order: the units join the team in the same script, so a member lost leaves
# the rest all going and one made later takes the order too, I7).
SINGLE_ORDERS = ('NAMED_ATTACK_NAMED', 'UNIT_GUARD_AREA', 'NAMED_HUNT', 'ATTACK_MOVE_NAMED_UNIT_TO',
                 'MOVE_NAMED_UNIT_TO', 'NAMED_STOP')
# scripts still allowed one (regexes on the script name, matched from its start): only ever deleted from
# (tests/test_architecture G6). Empty: every level goes through the outlet.
SINGLE_ORDERS_LEFT = ()


def single_orders(m, allow=SINGLE_ORDERS_LEFT):
    """G6: no script of the level (a check's `Test ...` own are not) orders one unit by name, except the scripts the
    list `allow` still holds."""
    return [f'{s.name}: {name} orders one unit (ctx.order gives the whole team the order)'
            for s in m.scripts if not s.name.startswith('Test') and not any(re.match(p, s.name) for p in allow)
            for name, *_ in s.do if name in SINGLE_ORDERS]


# K4 (G12): ore, refineries and oil stand in the relations retail's maps keep (resources.py holds the measures; every
# check here reads the finished objects, so a node typed into a map by hand is held to them too).
def _placed(m):
    """Everything standing on the ground: the map's own objects and the mission's."""
    return list(getattr(m.map, 'OBJECTS', ())) + list(m.objects)


def _pads(m):
    """{site name: (x, y, facing radians)}: the refinery pads the map publishes (resources.sites)."""
    return {k: (s.x, s.y, s.facing) for k, s in getattr(m.map, 'SITES', {}).items() if s.facing is not None}


def ore_faces_refinery(m):
    """Every refinery -- a pad the map publishes, one the mission places -- has the ore node it mines straight ahead,
    resources.AXIS away (retail: 138 of 171 exactly there). A placed refinery stands at the pad's facing (Mission.put
    turns it), so a refinery put by raw coordinates, or turned away from its ore, fails here."""
    import resources
    ore = [(o.x, o.y) for o in _placed(m) if o.template == 'OreNode']
    spots = {f'pad {k}': v for k, v in _pads(m).items()}
    spots.update({f'{o.template} at ({o.x:g}, {o.y:g})': (o.x, o.y, o.angle) for o in _placed(m)
                  if o.template.endswith('Refinery')})
    out = []
    for what, (x, y, a) in spots.items():
        if a is None:
            out.append(f'{what}: no facing (a refinery stands facing its ore: place it on a pad, resources.Field)')
            continue
        want = (x + resources.AXIS * math.cos(a), y + resources.AXIS * math.sin(a))
        near = min((math.dist(want, n) for n in ore), default=None)
        if near is None or near > resources.AXIS_SLACK:
            out.append(f'{what}: no ore node {resources.AXIS:g} straight ahead of it'
                       + ('' if near is None else f' (nearest {near:.0f} off the spot)'))
    return out


def ore_in_groups(m):
    """Ore comes as retail has it: one node or a pair (never a field of three), and every node is one a Field makes --
    the front node of a pad or the one beside it -- not a coordinate typed into the map."""
    import resources
    ore = [(o.x, o.y) for o in _placed(m) if o.template == 'OreNode']
    made = []
    for x, y, a in _pads(m).values():
        fx, fy = x + resources.AXIS * math.cos(a), y + resources.AXIS * math.sin(a)
        made += [(fx, fy)] + [(fx - s * resources.PAIR_GAP * math.sin(a), fy + s * resources.PAIR_GAP * math.cos(a))
                              for s in (-1, 1)]
    out = [f'OreNode at ({x:g}, {y:g}): not made by a resources.Field (no pad has it ahead or beside)'
           for x, y in ore if min((math.dist((x, y), p) for p in made), default=1e9) > 5.0]
    left = list(ore)
    while left:
        group = [left.pop()]
        for n in left[:]:
            if any(math.dist(n, g) <= resources.PAIR_MAX for g in group):
                group.append(n)
                left.remove(n)
        if len(group) > resources.GROUP_MAX:
            out.append(f'{len(group)} ore nodes together near ({group[0][0]:g}, {group[0][1]:g}): '
                       f'at most {resources.GROUP_MAX} (one or a pair)')
    return out


def _bases(m):
    """[(site name, owner, x, y)]: the bases the map's fields serve (resources.Field.base)."""
    sites = getattr(m.map, 'SITES', {})
    return [(f.base, f.owner, sites[f.base].x, sites[f.base].y) for f in getattr(m.map, 'FIELDS', ())
            if f.base in sites]


def oil_off_the_camps(m):
    """Oil is a prize outside the camps: every derrick stands resources.OIL_CLEAR from each enemy base the map's fields
    name and from anything an enemy (s1) of the mission stands on (retail: 96% of derricks, I9: the derrick was in the
    enemy camp)."""
    import resources
    enemy = [(f'base {k}', x, y) for k, owner, x, y in _bases(m) if owner == 's1']
    enemy += [(f'{o.template} at ({o.x:g}, {o.y:g})', o.x, o.y) for o in m.objects if o.side == 's1']
    return [f'OilDerrick at ({d.x:g}, {d.y:g}): {math.dist((d.x, d.y), (x, y)):.0f} from {what} (at least '
            f'{resources.OIL_CLEAR:g}: oil is outside the camps)'
            for d in _placed(m) if d.template.startswith('OilDerrick')
            for what, x, y in enemy if math.dist((d.x, d.y), (x, y)) < resources.OIL_CLEAR]


def base_has_ore(m):
    """A base has ore to mine within resources.BASE_ORE of it (map-language.md: 开局 1000 以内有一组矿)."""
    import resources
    ore = [(o.x, o.y) for o in _placed(m) if o.template == 'OreNode']
    return [f'base {k}: no ore within {resources.BASE_ORE:g}' for k, _, x, y in _bases(m)
            if min((math.dist((x, y), n) for n in ore), default=1e9) > resources.BASE_ORE]


def cast_points_clear(m):
    """K3: every place the player casts a spell (Mission.spells: a device's ice marks) is a map site made for it
    (Site.cast > 0; platmap.cast_lint holds the ground and the map's objects off its circle, platprops keeps scenery off),
    the mark is the site itself, and nothing the mission stands on the ground comes within its circle."""
    import platmap
    sites = getattr(m.map, 'SITES', {})
    out = []
    for wp, site in m.spells.items():
        s = sites.get(site)
        if s is None or not s.cast:
            out.append(f'spell mark {wp!r}: site {site!r} is not a cast point (give it Site.cast = platmap.CAST_CLEAR)')
            continue
        if m.waypoints.get(wp) != (s.x, s.y):
            out.append(f'spell mark {wp!r}: not on site {site!r} itself ({m.waypoints.get(wp)} vs {(s.x, s.y)})')
        out += [f'spell mark {wp!r}: {o.template} at ({o.x:g}, {o.y:g}) stands inside the cast circle of {site!r} ({s.cast:g})'
                for o in m.objects if platmap._gap_to(o, s.x, s.y) < s.cast]
    return out


_DESIGN = {}


def map_design(m):
    """K4e: the map's own design lint -- ramps, building sites, structures on flat dry ground, bridges, blocks, gaps,
    the scenery clear of every way and place (platmap.lint, platprops.lint), and every refinery by its ore (ore_lint) --
    on every build, not only in a preview. The map part is held per map module (it does not depend on the mission), the
    ore part reads the mission's objects as well."""
    import platmap
    import platprops
    mod = m.map
    if mod.__name__ not in _DESIGN:
        if hasattr(mod, 'LAYOUT'):
            _DESIGN[mod.__name__] = platmap.lint(mod.LAYOUT, mod.SITES, getattr(mod, 'OBJECTS', []),
                                                 getattr(mod, 'SCENERY', []))
        elif hasattr(mod, 'ground'):
            _DESIGN[mod.__name__] = platprops.lint(None, mod.SITES, getattr(mod, 'OBJECTS', []), mod.SCENERY,
                                                   ground=mod.ground())
        else:
            _DESIGN[mod.__name__] = []
    return [f'map {mod.__name__}: {p}' for p in _DESIGN[mod.__name__]] + \
           [f'map {mod.__name__}: {p}' for p in platmap.ore_lint(_placed(m))]


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
    known = {AREA_ARG: ('area', m.areas), TEAM_ARG: ('team', set(getattr(m.map, 'TEAMS', {}).values()) | set(m.teams.values())),
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
    out += said_outside_the_outlet(m, cat)
    out += said_lines_kept(m)
    out += said_once_and_on_time(m)
    out += team_orders_land(m) + kind_counts_in_area(m)
    out += camera_outside_the_view(m)
    out += music_resumes(m) + ending_line_fits(m)
    out += single_orders(m)
    out += ore_faces_refinery(m) + ore_in_groups(m) + oil_off_the_camps(m) + base_has_ore(m) + cast_points_clear(m) + map_design(m)
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


# What an acceptance check may add to the mission it checks (ADR 0016: the test build is the release build plus
# observation): the action -> the index of the name it writes. Everything here only reads the game into the check's
# own counters, flags, timers and references, or moves the camera as a player can. Not here, and so not allowed:
# anything that acts on units (kill, health, teleport, status, orders, abilities fired by script), money, AI, and the
# view rules -- MAP_REVEAL_ALL_PERM would hide a black start (K5), MAP_SWITCH_BORDER changes the playable area.
OBSERVE = {
    'SET_COUNTER': 1, 'INCREMENT_COUNTER': -1, 'SET_MILLISECOND_TIMER': 1, 'SET_FLAG': 1,
    'SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER': -1, 'SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER': -1,
    'SET_PLAYER_MONEY_TO_COUNTER': -1, POINTS_AT_UNNAMED: -1,
    'MOVE_CAMERA_TO': None,
}


def observes(mission, test):
    """Why `test` is not observation only (empty: it is, and may run as an acceptance check on the release build):
    it adds units or objects, uses an action outside OBSERVE, or writes a counter / flag / timer / reference the
    mission's own scripts use (overriding the level, like a switch held off every frame). Waypoints and trigger
    areas it adds are fine: they are geometry, read by its conditions only. A test that acts is a device unit test
    (机关单测): useful, but no evidence for the player's game."""
    out = [f'adds {len(getattr(test, f))} {f}' for f in ('units', 'objects') if getattr(test, f)]
    if test.counters and len(test.counters) + len(mission.countdowns) > 4:          # model.COUNTER_LINES
        out.append(f'{len(test.counters)} counters would push the mission\'s countdowns off the screen')
    used = {a for s in mission.scripts for part in (s.when, s.do) for x in part if isinstance(x, tuple)
            for a in x[1:] if isinstance(a, str)}
    for s in test.scripts:
        for x in s.do:
            if x[0] not in OBSERVE:
                out.append(f'{s.name}: {x[0]} acts on the game')
            elif OBSERVE[x[0]] is not None and x[OBSERVE[x[0]]] in used:
                out.append(f'{s.name}: {x[0]} writes {x[OBSERVE[x[0]]]!r}, which the mission itself uses')
    return out
