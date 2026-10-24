r"""A skirmish map that plays itself, for desync hunting (SAGE-Unlocked, the voice line's request 2026-10-23): retail
map_mp_4_stewart_1 (4 players, ~1900 trees, ~220 street lamps, 8 bridges, some water) plus map scripts that hand
every slot, the human's too, to the skirmish AI. Skirmish games save a replay (campaign and mod missions do not:
the bench ran dozens of mod missions on 2026-10-23 and Replays\ did not change).

  python -I -X utf8 experimental/testbench/chaos_map.py      -> Documents\Red Alert 3\Mods\CNVChaos\

Shipped as a small mod, not as a user map: the bench game listed neither an edited nor a byte-identical copy of the
map from %APPDATA%\Red Alert 3\Maps (nor Documents\Red Alert 3\Maps), with UseLocalUserMaps = 0 in the registry.
The mod carries the map folder under a new name (the .map, its pictures and its compiled streams, which hold the
terrain textures and props -- make_campnew4) and the retail map cache with one entry appended: multiplayer, not
official (flags 1), so the game reads the .map, scripts and all, at run time.

Play (bench 2026-10-23): start RA3 with -modConfig <the skudef>, skirmish, map CNV_Chaos (4), you as observer
(the eye in the faction list) and 4 brutal AIs, no teams (that run: Soviet, Empire, Allies, Empire), start. The
profile's Skirmish.ini remembers the lobby, so later runs only need 对决 -> 遭遇战 -> 开始. That run went 15.3 min
with all four alive at the end, several superweapons; quitting saved Documents\Red Alert 3\Replays\最新重播.RA3Replay
(the bench's zh-TW name; the next game overwrites it, so copy it). Replaying needs the same mod and an unchanged map:
once replays exist, do not rebuild this map with different content.

The script below hands Player_1 .. Player_4 to the skirmish AI (the slots by start position, as the campaign co-op
maps name their humans). With the human observing it has nothing to do; it is kept so that the map, and with it
the recorded replays, stay as built. Scripts go into the first ScriptList: the nameless neutral side, where the
campaign maps keep theirs.
"""
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'experimental', 'campaign'))
sys.path.insert(0, ROOT)
import labpaths  # noqa: E402
import mapcache  # noqa: E402
import mapscript  # noqa: E402
from ra3voice import big  # noqa: E402

MOD = 'CNVChaos'
NAME = 'cnv_chaos'
SOURCE = 'map_mp_4_stewart_1'
ARCHIVES = ['MapsMultiplayer.big', 'Maps5.big', 'Maps8.big', 'Maps9.big', 'Maps10.big', 'Maps11.big',
            'Maps12.big']                                   # later archives win (patched streams)
OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', MOD)
OLD_DIR, NEW_DIR = f'data\\maps\\official\\{SOURCE}\\', f'data\\maps\\official\\{NAME}\\'
NEW_MAP = NEW_DIR + NAME + '.map'
PLAYERS = [f'Player_{k}' for k in range(1, 5)]
# a multiplayer map has no scripts, so no versions to copy: these are the retail campaign maps' (camp_a09)
VERSIONS = {'Script': 4, 'OrCondition': 1, 'Condition': 6, 'ScriptAction': 3, 'ScriptGroup': 3}


def scripts(m):
    true = m.new_content('Condition', 'CONDITION_TRUE')
    ai = m.new_script('Chaos - AI plays every slot', [true],
                      [m.new_content('ScriptAction', 'PLAYER_TOGGLE_SKIRMISH_AI', p, 1) for p in PLAYERS])
    return [ai]


def folder():
    """{new path: bytes} of the source map folder, renamed; the .map with the scripts added."""
    found = {}
    for a in ARCHIVES:
        p = os.path.join(labpaths.GAME, 'Data', a)
        names = [n for n, _, _ in big.read_index(p) if n.lower().startswith(OLD_DIR)]
        for n, v in big.read_files(p, names).items():
            leaf = n[len(OLD_DIR):].lower()
            if not leaf.endswith('_edit.map') and not leaf.endswith('_edit.tga'):
                found[NEW_DIR + leaf.replace(SOURCE, NAME)] = v
    m = mapscript.MapFile(found[NEW_MAP])
    m.version = VERSIONS.__getitem__
    lists = next(x for _, x in m.walk() if x.name == 'PlayerScriptsList').kids
    lists[0].kids.extend(scripts(m))
    data = m.map_file()
    assert mapscript.MapFile(data).chunk_file() == m.chunk_file()
    found[NEW_MAP] = data
    print(mapscript.MapFile(data).script_text())
    return found


def cache_entry():
    base = next(e for e in mapcache.decode(mapcache.retail()[1][1][4:]) if e['file'].lower() == OLD_DIR + SOURCE + '.map')
    return dict(base, file=NEW_MAP, id=zlib.crc32(NEW_MAP.lower().encode()), flags=1, display='CNV_Chaos')


def build():
    files = sorted(folder().items()) + mapcache.with_maps([cache_entry()])
    os.makedirs(OUT, exist_ok=True)
    big.write(os.path.join(OUT, f'{MOD}.big'), files)
    sku = os.path.join(OUT, f'{MOD}_1.0.skudef')
    with open(sku, 'w', encoding='ascii', newline='') as f:
        f.write(f'mod-game 1.12\r\nadd-big {MOD}.big\r\n')
    print('->', sku, [n.split('\\')[-1] for n, _ in files])


if __name__ == '__main__':
    build()
