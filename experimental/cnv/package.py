"""Layer L3, packaging: the mission written into the container map, previewed without the game, and assembled into a
mod through the CampNew7 pipeline (experimental/campaign: mission slot, map cache, linked map stream, lint) -- the
old make_camp*.py chain stays as it was (user 2026-10-21: only new work is written this way).

Imports model.py and contract.py, never the other way round (tests/test_architecture.py, G-layers). Split out of
parts.py (ADR 0016).

  python -I -X utf8 experimental/cnv/build.py a8 [--test liberty_jump] [--name CampX]
"""
import os
import sys

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
    borders = getattr(mm.map, 'BORDERS', None)
    if borders:                             # MAP_SWITCH_BORDER(k) switches to the k-th; the first is the whole map
        import mapterrain
        hm = mapterrain.HeightMap(m)
        hm.set_borders([tuple(round(v / mapterrain.CELL) for v in r) for r in borders.values()])
        hm.store()
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    tmpl = lambda k: k.head[22:22 + int.from_bytes(k.head[20:22], 'little')].decode('latin-1')   # noqa: E731
    like = mm.map.like(m, objs, tmpl)
    objs.kids = [k for k in objs.kids if tmpl(k) == '*Waypoints/Waypoint']        # the map's starts stay
    wid = 1 + max(newmap.typed_props_of(m, k)[0].get('waypointID', (1, 0))[1] for k in objs.kids)
    for k, (wname, (x, y)) in enumerate(mm.waypoints.items()):
        objs.kids.append(newmap.object_node(m, *like['wp'], '*Waypoints/Waypoint', x, y, waypointName=wname,
                                            waypointID=wid + k, uniqueID=f'Waypoint {wid + k}'))
    # the map's own objects (a bridge's two ends stay next to each other), its scenery (civilian props), the mission's
    for o in list(getattr(mm.map, 'OBJECTS', [])) + list(getattr(mm.map, 'SCENERY', [])) + mm.objects:
        angle = o.angle if o.angle is not None else (1.5708 if o.side == 'p1' else -1.5708)
        extra = dict(o.props, **({'objectName': o.name} if o.name else {}))
        props, flags = like[o.side]
        objs.kids.append(newmap.object_node(m, props, flags if o.flags is None else o.flags, o.template, o.x, o.y,
                                            angle=angle, uniqueID=o.name or f'{o.template} {len(objs.kids)}', **extra))
    ours = [m.new_script(s.name, [m.new_content('Condition', *c) for c in s.when]
                         or [m.new_content('Condition', 'CONDITION_TRUE')],
                         [m.new_content('ScriptAction', *a) for a in s.do], one_shot=s.once,
                         difficulties=tuple(s.levels))
            for s in unnot(mm.scripts)]     # before clearing: chunk versions are read off existing nodes
    newmap.clear_scripts(m)[2].kids += ours
    m.set_trigger_areas(mm.areas)           # the base map's areas went with its scripts
    m.set_objectives([dict(name=g.name, title=g.title, desc=g.desc, bonus=int(g.bonus), flags=1)
                      for g in mm.objectives])


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


def assemble(mission, test=None, name=None, shell=False):
    """Write the units, set the pipeline up for this mission (+ test) and build the mod; returns the mod folder.
    shell: the campaign shell (shell.py, ADR 0014): the mission in its slot of the Allied campaign, the other eight slots ours
    too, all with our own front end; the edition's name (langs.py: 'zh', 'intl') for the words of the shell, True = zh."""
    import make_campnew18 as c18                # the pipeline (c7 ... c2) and the generated island's start
    c18.install()
    c7, c6, c4, c2 = c18.c7, c18.c6, c18.c4, c18.c2
    import newmap
    mm = merged(mission, test)
    name = name or mm.name
    # bench 2026-10-21: the same build as CampLibRidersJump (17) and CampBisjcdXXXXXXX (17) crashed before the main
    # menu (exit 0xC000000D), as CampBisjcd (10) / CampBisjcdXXXX (14) / CampLibertyJump (15) it ran
    assert len(name) <= MAX_NAME, f'mod name {name!r} is {len(name)} characters: the game crashes above {MAX_NAME}'
    assert '_' not in name, f'mod name {name!r}: with an underscore the game crashes at start (CampA7East_What)'
    broken = contract(mm)
    assert not broken, 'uses what nobody published:\n  ' + '\n  '.join(broken)
    c4.NAME = c2.NAME = name
    c2.SRC_DIR = os.path.join(c2.SDK, 'Mods', name, 'data')
    c2.BUILT = os.path.join(c2.SDK, 'BuiltMods', 'mods', name.lower(), 'data')
    c2.OUT = c4.OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', name)
    c7.MAP_MOD = name + 'Map'
    out_dir = os.environ.get('CNV_OUT_DIR')     # testbench/fingerprint.py: build into this folder, never into Mods
    why = '' if out_dir else mod_busy(name)
    if out_dir:
        c2.OUT = c4.OUT = os.path.join(out_dir, name)
    elif why:
        c2.OUT = c4.OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'staging', name)
        print(f'{why} -> staging at', c4.OUT)

    import atexit
    release = sdk_build_lock(name)              # one build at a time: the SDK's CNVUnits folder is shared
    atexit.register(release)
    data = os.path.join(c2.SDK, 'Mods', 'CNVUnits', 'Data')
    os.makedirs(data, exist_ok=True)
    seen = set()
    for u in mm.units:
        if u.id in seen:
            continue
        seen.add(u.id)
        for fname, text in {u.id + '.xml': u.xml, **u.files}.items():
            with open(os.path.join(data, fname), 'w', encoding='utf-8', newline='\r\n') as f:
                f.write(text.replace('\r\n', '\n'))
        c7.EXTRA_TEMPLATES[u.id] = {'file': f'DATA:CNVUnits/Data/{u.id}.xml', 'EditorSorting': 'UNIT'}
        # every unit compiled and linked, placed or not: map.xml includes only the object files the map places, and an
        # object creation list or a builder names its template at run time, which the reference walk from the map
        # never reaches (bench 2026-10-22: an OCL made retail's Guardian but nothing of ours the map did not place;
        # the Soviet engineer building one of ours crashed the game)
        if u.id not in {o.template for o in mm.objects}:
            c7.EXTRA_ALL.append(f'DATA:CNVUnits/Data/{u.id}.xml')
        c7.EXTRA_OWN += [f'GameObject:{u.id}'.encode()]
        c7.EXTRA_OWN += [n if isinstance(n, bytes) else n.encode() for n in u.link]
        c7.EXTRA_ALL += [f'DATA:CNVUnits/Data/{f}' for f in u.also]
        c4.c3.STRINGS.update(u.strings)
    for fname, text, link in mm.assets:         # nothing in the map refers to them by file: included and linked
        with open(os.path.join(data, fname), 'w', encoding='utf-8', newline='\r\n') as f:
            f.write(text.replace('\r\n', '\n'))
        c7.EXTRA_ALL.append(f'DATA:CNVUnits/Data/{fname}')
        c7.EXTRA_OWN.append(link.encode())
    c4.c3.STRINGS.update(mm.strings)
    video = mm.video
    c2.SHELL, c4.c3.OVERRIDES, c4.c3.PREFIX_OVERRIDES = None, {}, {}
    if shell:
        import shell as shell_probe
        sp = shell_probe.make(str(getattr(mm, 'title', '') or mm.name), mm.name, shell if isinstance(shell, str) else 'zh')
        c2.SHELL = {'slot': sp.slot, 'attrs': sp.attrs, 'others': sp.others, **sp.template}
        c4.c3.STRINGS.update(sp.strings)
        c4.c3.OVERRIDES.update(sp.overrides)
        c4.c3.PREFIX_OVERRIDES.update(sp.prefix_overrides)
        from experimental.video import pack as video_pack
        video = video_pack.make({**(mm.video.clips if mm.video else {}), **sp.clips})
    # our music: its map into the static stream, its .mus files into the big, then checked in the spliced stream
    c2.EXTRA_STATIC = [mm.music.include] if mm.music else []
    c4.EXTRA_FILES = list(mm.music.files) if mm.music else []
    c4.CHECKS = [mm.music.check] if mm.music else []
    # our voice lines the same way, their subtitles (DIALOGEVENT:CNV_*) into the string table
    if mm.voice:
        c2.EXTRA_STATIC.append(mm.voice.include)
        c4.EXTRA_FILES += list(mm.voice.files)
        c4.CHECKS.append(mm.voice.check)
        c4.c3.STRINGS.update(mm.voice.strings)
    if video:                                   # our movies: the Video declarations into the static stream, the clips into the big
        c2.EXTRA_STATIC.append(video.include)
        c4.EXTRA_FILES += list(video.files)
        c4.CHECKS.append(video.check)
    if shell:                                   # the APT screens with our pictures (shell.py)
        c4.EXTRA_FILES += sp.files

    borders = []

    def edit(m):
        write_map(m, mm)
        import mapterrain
        names = list(getattr(mm.map, 'BORDERS', {}))
        borders[:] = [(names[k] if k < len(names) else str(k), [v * mapterrain.CELL for v in r])
                      for k, r in enumerate(mapterrain.HeightMap(m).borders())]
        print(f'{name}: {len(mm.objects)} objects, {len(mm.waypoints)} waypoints, {len(mm.areas)} areas, '
              f'{len(mm.scripts)} scripts, units {sorted(seen)}')

    c6.edit = edit
    c4.main()
    release()
    write_sidecar(c4.OUT, mm.map.__name__.split('.')[-1], borders)
    return c4.OUT


SIDECAR = 'cnv_map.json'


def write_sidecar(out, map_name, borders):
    """What the bench needs of the built map, next to the mod (testbench/harness.py reads it): the map's borders in
    world units, in MAP_SWITCH_BORDER order -- the minimap draws only the playable one (calib.world_to_minimap)."""
    import json
    with open(os.path.join(out, SIDECAR), 'w', encoding='utf-8') as f:
        json.dump(dict(map=map_name, borders=borders), f, ensure_ascii=False, indent=1)


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
