"""Layer L3, packaging: the mission written into the container map, previewed without the game, and assembled into a
mod through the CampNew7 pipeline (experimental/campaign: mission slot, map cache, linked map stream, lint) -- the
old make_camp*.py chain stays as it was (user 2026-10-21: only new work is written this way). One outlet: a ModSpec
(spec_of, plus layers such as the campaign shell) built by build_mod.

Imports model.py and contract.py, never the other way round (tests/test_architecture.py, G-layers). Split out of
parts.py (ADR 0016).

  python -I -X utf8 experimental/cnv/build.py a8 [--test liberty_jump] [--name CampX]
"""
import copy
import os
import sys
from dataclasses import dataclass, field, replace

from contract import contract
from model import MAX_NAME, merged, unnot

HERE = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = os.path.join(os.path.dirname(HERE), 'campaign')
sys.path.insert(0, CAMPAIGN)


def write_map(m, mm):
    """The mission (merged) written into the container map: the map's terrain and its own objects (ore, tech,
    bridges: map.OBJECTS), then the mission's waypoints, objects, scripts, trigger areas and objectives."""
    import mapxml
    import newmap
    mm.map.terrain(m)
    for side, props in mm.sides.items():
        mapxml.set_player(m, mm.player(side), **props)
    for team in mm.teams.values():          # the mission's own teams (Mission.crew), 'Owner/teamName'
        owner, name = team.split('/')
        mapxml.add_team(m, name, owner)
    borders = getattr(mm.map, 'BORDERS', None)
    if borders:                             # MAP_SWITCH_BORDER(k) switches to the k-th; the first is the whole map
        import mapterrain
        hm = mapterrain.HeightMap(m)
        hm.set_borders([tuple(round(v / mapterrain.CELL) for v in r) for r in borders.values()])
        hm.store()
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    tmpl = lambda k: k.head[22:22 + int.from_bytes(k.head[20:22], 'little')].decode('latin-1')   # noqa: E731
    like = mm.map.like(m, objs, tmpl)
    m.cnv_like = like                       # a later map edit (a check as a layer: write_more) places with these too
    objs.kids = [k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint']        # the map's starts stay
    _put_waypoints(m, objs, like, mm.waypoints)
    # the map's own objects (a bridge's two ends stay next to each other), its scenery (civilian props), the mission's
    _put_objects(m, objs, like, list(getattr(mm.map, 'OBJECTS', [])) + list(getattr(mm.map, 'SCENERY', [])) + mm.objects)
    ours = _script_nodes(m, unnot(mm.scripts))      # before clearing: chunk versions are read off existing nodes
    newmap.clear_scripts(m)[2].kids += ours
    m.set_trigger_areas(mm.areas)           # the base map's areas went with its scripts
    m.set_objectives([dict(name=g.name, title=g.title, desc=g.desc, bonus=int(g.bonus), flags=1)
                      for g in mm.objectives])


def write_more(m, waypoints, objects, scripts, areas):
    """More written into a map write_map wrote (a check riding on a build as a layer, check_layer): waypoints and
    objects after the mission's, placed like them; scripts (already unnot) after the mission's in the same list;
    `areas` the map's trigger areas from now on (the mission's, then the new ones)."""
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    _put_waypoints(m, objs, m.cnv_like, waypoints)
    _put_objects(m, objs, m.cnv_like, objects)
    psl = next(n for _, n in m.walk() if n.name == 'PlayerScriptsList')
    psl.kids[2].kids += _script_nodes(m, scripts)       # newmap.clear_scripts: index 2 runs our scripts
    m.set_trigger_areas(areas)


def _put_waypoints(m, objs, like, waypoints):
    import newmap
    wid = 1 + max(newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids)
    for k, (wname, (x, y)) in enumerate(waypoints.items()):
        objs.kids.append(newmap.object_node(m, *like['wp'], '*Waypoints/Waypoint', x, y, waypointName=wname,
                                            waypointID=wid + k, uniqueID=f'Waypoint {wid + k}'))


def _put_objects(m, objs, like, objects):
    import newmap
    for o in objects:
        angle = o.angle if o.angle is not None else (1.5708 if o.side == 'p1' else -1.5708)
        extra = dict(o.props, **({'objectName': o.name} if o.name else {}))
        props, flags = like[o.side]
        objs.kids.append(newmap.object_node(m, props, flags if o.flags is None else o.flags, o.template, o.x, o.y,
                                            angle=angle, uniqueID=o.name or f'{o.template} {len(objs.kids)}', **extra))


def _script_nodes(m, scripts):
    return [m.new_script(s.name, [m.new_content('Condition', *c) for c in s.when]
                         or [m.new_content('Condition', 'CONDITION_TRUE')],
                         [m.new_content('ScriptAction', *a) for a in s.do], one_shot=s.once,
                         difficulties=tuple(s.levels))
            for s in scripts]


def preview(mission, test=None, out=None):
    """The map a build would make, without compiling or the game (seconds, not the 70 s build): write_map on the
    container map, saved as a .map (default work/maps/<name>.map) for maprender / mapstudy. Returns the path."""
    import make_campnew18 as c18
    from mapscript import MapFile
    mm = merged(mission, test)
    broken = contract(mm)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    path, data = next((p, d) for p, d in c18.c6._map_files() if p.lower().endswith('.map'))
    m = MapFile(data)
    write_map(m, mm)
    out = out or os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'maps', mm.name + '.map')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(m.map_file())
    return out


@dataclass(frozen=True)
class ModSpec:
    """Everything one mod is built from, as data (ADR 0016: packaging has one outlet, build_mod). spec_of makes it for a
    mission (+ test); a layer -- the campaign shell (shell.contribute), later a check -- is a function spec -> spec that
    only adds to it (with_more), and never reaches into another module. build_mod pours it into the CampNew7 pipeline.
    Order is kept everywhere it reaches the mod: strings go into the csf in insertion order, packs into the static
    stream in tuple order.

    A layer (spec_of's layers, applied in order after the shell's) keeps to this:
    - it adds through with_more: map_edits / big_files / checks / extra_* get items after the spec's own (so a check's
      map edit runs after the mission's write_map and sees the mission whole), strings / overrides get new keys;
    - it rewrites no label, template or file another layer put in (a key it had, a big path twice) -- the shell's own
      exceptions are the video pack (the mission's clips merged into one pack, clips kept), slot and launcher;
    - it leaves name, mission, title, map_name, border_names, unit_files and templates as they were;
    - a check (ADR 0016 phase 2, build.py --shell --check) is one such layer on top of the shell's: its scripts as one
      more map edit, its counters' labels as strings, its expectations in checks; the mission it rides on is the one
      the player gets (test edition = release edition + observation)."""
    name: str                       # the mod folder (at most MAX_NAME characters, no underscore)
    mission: str = ''               # the mission it carries (mm.name) and its title (the plan's 名字)
    title: str = ''
    map_name: str = ''              # the map module's short name (the bench's sidecar)
    map_edits: tuple = ()           # f(MapFile), in order, on the container map: the mission's write_map, then any layer's
    border_names: tuple = ()        # the map's BORDERS names, in MAP_SWITCH_BORDER order (the sidecar)
    unit_files: tuple = ()          # (file name, text) written into the SDK's CNVUnits/Data before the compile
    templates: dict = field(default_factory=dict)       # GameObject id -> make_campnew7.EXTRA_TEMPLATES entry
    extra_all: tuple = ()           # XML files included type="all" (make_campnew7.EXTRA_ALL)
    extra_own: tuple = ()           # names linked though nothing references them (bytes, make_campnew7.EXTRA_OWN)
    strings: dict = field(default_factory=dict)         # new labels -> text
    overrides: dict = field(default_factory=dict)       # retail labels rewritten (make_campnew3.OVERRIDES)
    prefix_overrides: dict = field(default_factory=dict)    # retail label prefix -> text (make_campnew3.PREFIX_OVERRIDES)
    strings_base: str = ''          # the game's table the csf starts from (make_campnew3.STRINGS_BASE; '' = its default,
                                    # the installed CNVoice table); the edition's (langs.EDITIONS) for the shell
    packs: tuple = ()               # (kind, pack): music, voice, video ...; a pack's include into the static stream, its
                                    # files into the big, its check on the file list, its strings (if any) after `strings`
    big_files: tuple = ()           # more (big path, bytes), after the packs' (a name twice: the last one)
    map_files: tuple = ()           # f(MapFile) -> [(big path, bytes)] made from the built map (after map_edits), after
                                    # big_files: what is drawn from the map is drawn from this build's (the shell's map pictures)
    checks: tuple = ()              # more f(files) on the finished file list, after the packs'
    slot: dict = None               # the campaign shell's templates (make_campnew2.SHELL); None = the mission alone
    launcher: bool = True           # Play_<name>.bat next to the skudef (the shell has its own: launcher.py)
    bench: dict = field(default_factory=dict)           # more for the bench in the sidecar (a check on the shell: the
                                                        # slot to walk into); a release build has none
    goals: tuple = ()               # the mission's objectives where the player is sent, as published ((x, y) world
                                    # units, goal_points): the shell's briefing zooms there when shell_missions names none
    levels: tuple = ()              # a mod of several missions (the campaign shell with every level, shell.campaign):
                                    # ((slot, level ModSpec), ...), each level's map built into its own folder
                                    # (level_stem); the level's map_edits, unit_files, templates, extra_*, map_files and
                                    # border_names are its own map's, the rest of the mod is this spec's


def with_more(spec, **more):
    """spec with more of everything named: a tuple field gets the new items after its own, a dict field the new keys
    (a key it had keeps its place and takes the new value), anything else is replaced."""
    changes = {}
    for k, v in more.items():
        have = getattr(spec, k)
        changes[k] = (have + tuple(v) if isinstance(have, tuple) else {**have, **v} if isinstance(have, dict) else v)
    return replace(spec, **changes)


def spec_of(mission, test=None, shell=False, name=None, layers=()):
    """The ModSpec of `mission` (+ `test`): its units, assets, strings, music, voice and movies and the map edit that
    writes it; shell (an edition's name, langs.py: 'zh', 'intl'; True = zh) adds the campaign shell's layer, then each
    of `layers` (spec -> spec, ModSpec says what a layer may do) in order."""
    mm = merged(mission, test)
    name = name or mm.name
    broken = contract(mm)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    seen = set()
    unit_files, templates, extra_all, extra_own, strings = _unit_parts(mm.units, mm.objects, seen)
    for fname, text, link in mm.assets:         # nothing in the map refers to them by file: included and linked
        unit_files.append((fname, text))
        extra_all.append(f'DATA:CNVUnits/Data/{fname}')
        extra_own.append(link.encode())
    strings.update(mm.strings)
    # our music: its map into the static stream, its .mus files into the big, then checked in the spliced stream; our
    # voice lines the same way, their subtitles (DIALOGEVENT:CNV_*) into the string table; our movies: the Video
    # declarations into the static stream, the clips into the big
    packs = tuple((kind, p) for kind, p in (('music', mm.music), ('voice', mm.voice), ('video', mm.video)) if p)

    def edit(m):
        write_map(m, mm)
        print(f'{name}: {len(mm.objects)} objects, {len(mm.waypoints)} waypoints, {len(mm.areas)} areas, '
              f'{len(mm.scripts)} scripts, units {sorted(seen)}')

    spec = ModSpec(name=name, mission=mm.name, title=str(getattr(mm, 'title', '') or ''),
                   map_name=mm.map.__name__.split('.')[-1], map_edits=(edit,),
                   border_names=tuple(getattr(mm.map, 'BORDERS', {})), unit_files=tuple(unit_files),
                   templates=templates, extra_all=tuple(extra_all), extra_own=tuple(extra_own), strings=strings,
                   packs=packs, goals=goal_points(mm))
    if shell:
        import shell as shell_layer
        spec = shell_layer.contribute(spec, shell if isinstance(shell, str) else 'zh')
    for layer in layers:
        spec = layer(spec)
    return spec


def goal_points(mm):
    """Where the mission's objectives send the player, in their order ((x, y) world units): for each objective that is
    not a bonus, the first thing it marks that has a place -- a mark (waypoint), a cast part (its named object, else
    the site it stands on) or a map site. Objectives that mark nothing placed are left out."""
    sites = getattr(mm.map, 'SITES', {})
    by_name = {o.name: o for o in mm.objects if o.name}

    def where(part):
        if part in mm.marks:
            return tuple(mm.point(part))
        if part in mm.cast:
            r = mm.cast[part]
            if r.name in by_name:
                return by_name[r.name].x, by_name[r.name].y
            if r.sites and r.sites[0] in sites:
                return sites[r.sites[0]].at()
        if part in sites:
            return sites[part].at()
        return None

    out = []
    for g in mm.objectives:
        if g.bonus:
            continue
        got = next((p for p in map(where, g.show) if p), None)
        if got:
            out.append((float(got[0]), float(got[1])))
    return tuple(out)


def level_stem(slot):
    """The map folder and file stem of the level in campaign slot `slot` in a mod of several missions (ModSpec.levels);
    a mod of one mission keeps make_campnew2.NEW_STEM."""
    return f'camp_cnva{slot:02d}'


def _unit_parts(units, placed, seen):
    """What `units` bring to a ModSpec (those whose id is not in `seen` yet; `seen` takes theirs): (unit_files,
    templates, extra_all, extra_own, strings). `placed`: the objects the map places."""
    unit_files, templates, extra_all, extra_own, strings = [], {}, [], [], {}
    for u in units:
        if u.id in seen:
            continue
        seen.add(u.id)
        unit_files += list({u.id + '.xml': u.xml, **u.files}.items())
        templates[u.id] = {'file': f'DATA:CNVUnits/Data/{u.id}.xml', 'EditorSorting': 'UNIT'}
        # every unit compiled and linked, placed or not: map.xml includes only the object files the map places, and an
        # object creation list or a builder names its template at run time, which the reference walk from the map
        # never reaches (bench 2026-10-22: an OCL made retail's Guardian but nothing of ours the map did not place;
        # the Soviet engineer building one of ours crashed the game)
        if u.id not in {o.template for o in placed}:
            extra_all.append(f'DATA:CNVUnits/Data/{u.id}.xml')
        extra_own += [f'GameObject:{u.id}'.encode()]
        extra_own += [n if isinstance(n, bytes) else n.encode() for n in u.link]
        extra_all += [f'DATA:CNVUnits/Data/{f}' for f in u.also]
        strings.update(u.strings)
    return unit_files, templates, extra_all, extra_own, strings


def check_layer(mission, test):
    """A check as a layer (ADR 0016 phase 2, build.py --shell --check): what merged(mission, test) has more than the
    mission -- the check's units; its waypoints, objects, scripts and trigger areas as one more map edit after the
    mission's write_map (write_more), so only the mission's map gets them; its strings and its counters' labels -- with
    nothing of the mission rewritten. The scripts come out as spec_of(mission, test) writes them, except that the
    check's own NOT flags' scripts stand after the mission's scripts instead of first (still before the check's, the
    only ones that read them). On a shell build it also tells the bench the slot to walk into (ModSpec.bench)."""
    plain, whole = merged(mission), merged(mission, test)
    broken = contract(whole)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    for f in ('waypoints', 'areas', 'strings'):
        had, has = getattr(plain, f), getattr(whole, f)
        clash = sorted(key for key in had if has[key] != had[key])
        assert not clash, f'the check rewrites the mission\'s {f}: {clash}'
    assert whole.scripts[:len(plain.scripts)] == plain.scripts and whole.objects[:len(plain.objects)] == plain.objects
    objects = whole.objects[len(plain.objects):]
    waypoints = {k: v for k, v in whole.waypoints.items() if k not in plain.waypoints}
    # unnot(whole) = the mission's NOT scripts, the check's, the mission's scripts, the check's (unnot numbers the tests
    # in order, the mission's first); the mission's two parts are what write_map wrote
    full, mine = unnot(whole.scripts), unnot(plain.scripts)
    k, j = len(mine) - len(plain.scripts), len(full) - len(whole.scripts)
    assert full[:k] == mine[:k] and full[j:j + len(plain.scripts)] == mine[k:]
    scripts = full[k:j] + full[j + len(plain.scripts):]
    seen = {u.id for u in plain.units}
    unit_files, templates, extra_all, extra_own, strings = _unit_parts(whole.units, whole.objects, seen)
    strings.update({key: v for key, v in whole.strings.items() if key not in plain.strings})

    def edit(m):
        write_more(m, waypoints, objects, scripts, whole.areas)
        print(f'check: {len(objects)} objects, {len(waypoints)} waypoints, {len(whole.areas) - len(plain.areas)} '
              f'areas, {len(scripts)} scripts more')

    def layer(spec):
        return with_more(spec, map_edits=(edit,), unit_files=unit_files, templates=templates, extra_all=extra_all,
                         extra_own=extra_own, strings=strings, bench={'slot': spec.slot['slot']} if spec.slot else {})
    return layer


def assemble(mission, test=None, name=None, shell=False, layers=()):
    """Write the units, set the pipeline up for this mission (+ test) and build the mod; returns the mod folder.
    shell: the campaign shell (shell.py, ADR 0014): the mission in its slot of the Allied campaign, the other eight slots ours
    too, all with our own front end; the edition's name (langs.py: 'zh', 'intl') for the words of the shell, True = zh."""
    spec = spec_of(mission, test, shell, name, layers)
    return build_mod(spec, mod_folder(spec.name))


def assemble_campaign(missions, name=None, lang='zh', fallback=()):
    """The campaign shell carrying every mission of `missions` ({slot: mission}) in its slot (shell.campaign, I16), built
    into one mod (the edition `lang`'s shell name by default); `fallback`: slots with another edition standing in.
    Returns the mod folder."""
    import shell as shell_layer
    spec = shell_layer.campaign({k: spec_of(m) for k, m in missions.items()}, name, lang, fallback)
    return build_mod(spec, mod_folder(spec.name))


def mod_folder(name):
    """Where the mod is written: Documents\\Red Alert 3\\Mods\\<name>; CNV_OUT_DIR/<name> for testbench/fingerprint.py
    (never into Mods); work/staging/<name> while the game is up or a bench game has this mod open."""
    out_dir = os.environ.get('CNV_OUT_DIR')
    if out_dir:
        return os.path.join(out_dir, name)
    why = mod_busy(name)
    if why:
        out = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', name)
        print(f'{why} -> staging at', out)
        return out
    return os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', name)


CHAIN = ('make_campnew2', 'make_campnew3', 'make_campnew4', 'make_campnew6', 'make_campnew7', 'make_campnew18')


def _held(modules):
    """Every module-level value of `modules`, and a copy of each list / dict / set (restored in place by _restore)."""
    return {m: {k: (v, copy.copy(v) if isinstance(v, (list, dict, set)) else None) for k, v in vars(m).items()
                if not k.startswith('__')} for m in modules}


def _restore(held):
    for m, values in held.items():
        for k in [k for k in vars(m) if not k.startswith('__') and k not in values]:
            delattr(m, k)
        for k, (v, contents) in values.items():
            setattr(m, k, v)
            if isinstance(v, list):
                v[:] = contents
            elif isinstance(v, (dict, set)):
                v.clear()
                v.update(contents)


def build_mod(spec, out):
    """The one outlet of packaging (ADR 0016): the mod `spec` describes, built into the folder `out` (mod_folder); returns
    `out`. Holds the SDK for the build, pours the spec into the CampNew7 pipeline's globals (make_campnew2 ... 18, which
    stay as they were written) and puts every one of those globals back afterwards, so lists they only ever append to
    (make_campnew7.EXTRA_OWN ...) do not carry one build into the next in the same process."""
    import importlib
    name = spec.name
    # bench 2026-10-21: the same build as CampLibRidersJump (17) and CampBisjcdXXXXXXX (17) crashed before the main
    # menu (exit 0xC000000D), as CampBisjcd (10) / CampBisjcdXXXX (14) / CampLibertyJump (15) it ran
    assert len(name) <= MAX_NAME, f'mod name {name!r} is {len(name)} characters: the game crashes above {MAX_NAME}'
    assert '_' not in name, f'mod name {name!r}: with an underscore the game crashes at start (CampA7East_What)'
    c2, c3, c4, c6, c7, c18 = [importlib.import_module(n) for n in CHAIN]
    held = _held([c2, c3, c4, c6, c7, c18])
    release = sdk_build_lock(name)              # one build at a time: the SDK's CNVUnits folder is shared
    try:
        levels, maps = {}, []                   # several missions: each level's map on its own, first
        for slot, lv in spec.levels:
            _restore(held)
            c18.install()
            stem = level_stem(slot)
            c2.NEW_STEM, c2.NEW_DIR = stem, f'data\\maps\\official\\{stem}\\'
            c4.NEW_MAP = c2.NEW_DIR + stem + '.map'
            c7.MAP_MOD = f'{name}Map{slot}'
            borders, drawn = _map_part(lv, c4, c6, c7, c2.SDK)
            files = c2.map_files()
            maps.append((files, drawn, c4.cache_entry()))
            levels[slot] = dict(map=lv.map_name, borders=borders, mission=lv.mission)
            print(f'{name}: slot {slot} {lv.mission} -> {c4.NEW_MAP}')
        if spec.levels:
            _restore(held)
        c18.install()                           # the pipeline (c7 ... c2) and the generated island's start
        c4.NAME = c2.NAME = name
        c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', name, 'data')
        c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', name.lower(), 'data')
        c2.OUT = c4.OUT = out
        c7.MAP_MOD = name + 'Map'
        c3.STRINGS.update(spec.strings)
        for _, p in spec.packs:
            c3.STRINGS.update(getattr(p, 'strings', {}))
        c2.SHELL, c3.OVERRIDES, c3.PREFIX_OVERRIDES = spec.slot, dict(spec.overrides), dict(spec.prefix_overrides)
        if spec.strings_base:
            c3.STRINGS_BASE = spec.strings_base
        c2.EXTRA_STATIC = [p.include for _, p in spec.packs]
        c4.EXTRA_FILES = [f for _, p in spec.packs for f in p.files] + list(spec.big_files)
        c4.CHECKS = [p.check for _, p in spec.packs] + list(spec.checks)
        if spec.levels:                         # the maps are built: the mod gets their folders and cache entries
            c2.map_files = lambda: [f for files, _, _ in maps for f in files]
            c4.CACHE_ENTRIES = [e for _, _, e in maps]
            c4.EXTRA_FILES += [f for _, drawn, _ in maps for f in drawn]     # after big_files (a name twice: the last)
            borders = []
        else:
            borders, drawn = _map_part(spec, c4, c6, c7, c2.SDK)
            write = c6.edit

            def edit(m):
                write(m)
                # c4.main reads EXTRA_FILES after c2.map_files() (which calls this) has returned
                c4.EXTRA_FILES = c4.EXTRA_FILES + drawn
            c6.edit = edit
        c4.main()
    finally:
        release()
        _restore(held)
    if not spec.launcher and os.path.isfile(os.path.join(out, f'Play_{name}.bat')):
        os.remove(os.path.join(out, f'Play_{name}.bat'))
    more = dict(spec.bench)
    if spec.slot:                               # a shell build: the bench walks its chapter list (I18), not the faction menu
        more.setdefault('slot', spec.slot['slot'])
    if levels:
        more['levels'] = {str(k): v for k, v in levels.items()}
        more.setdefault('slot', min(levels))
        first = levels[more['slot']]
        write_sidecar(out, first['map'], first['borders'], more)
    else:
        write_sidecar(out, spec.map_name, borders, more)
    return out


def _map_part(spec, c4, c6, c7, sdk):
    """Set the pipeline up for the map of `spec` (a mod's or a level's): its units into the SDK's CNVUnits/Data, its
    templates and linked names, the edit that writes it (c6.edit). Returns (borders, drawn): both fill when the map
    is made (c2.map_files runs the edit) -- the map's borders in world units, and the files drawn from it."""
    data = os.path.join(sdk, 'Mods', 'CNVUnits', 'Data')
    os.makedirs(data, exist_ok=True)
    for fname, text in spec.unit_files:
        with open(os.path.join(data, fname), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(text.replace('\r\n', '\n'))
    c7.EXTRA_TEMPLATES.update(spec.templates)
    c7.EXTRA_ALL += list(spec.extra_all)
    c7.EXTRA_OWN += list(spec.extra_own)
    borders, drawn = [], []

    def edit(m):
        for e in spec.map_edits:
            e(m)
        import mapterrain
        names = spec.border_names
        borders[:] = [(names[k] if k < len(names) else str(k), [v * mapterrain.CELL for v in r])
                      for k, r in enumerate(mapterrain.HeightMap(m).borders())]
        drawn[:] = [f for make in spec.map_files for f in make(m)]

    c6.edit = edit
    return borders, drawn


SIDECAR = 'cnv_map.json'


def write_sidecar(out, map_name, borders, more=None):
    """What the bench needs of the built map, next to the mod (testbench/harness.py reads it): the map's borders in
    world units, in MAP_SWITCH_BORDER order -- the minimap draws only the playable one (calib.world_to_minimap); and
    `more` (ModSpec.bench: a check on the shell's 'slot', harness.start walks the chapter list into it)."""
    import json
    with open(os.path.join(out, SIDECAR), 'w', encoding='utf-8') as f:
        json.dump(dict(map=map_name, borders=borders, **(more or {})), f, ensure_ascii=False, indent=1)


def mod_busy(name):
    """Why the mod must not be written into Mods now ('' if it may): the user's game is up, or a bench game has this
    mod open. Bench games with other mods do not stop it (several run at once: testbench/slots.py)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'testbench'))
    import slots
    return slots.busy(name)


def sdk_build_lock(name):
    """Wait for the SDK, hold it for this build; returns the release (testbench/slots.build_lock)."""
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'testbench'))
    import slots
    return slots.build_lock(name)


def game_running():
    import subprocess
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out
