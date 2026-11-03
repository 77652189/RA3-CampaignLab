"""Minimal complete new mission probe (CampNew2): own map folder, own strings, all LOD streams.

  python -I -X utf8 experimental/campaign/make_campnew2.py   -> Documents\\Red Alert 3\\Mods\\CampNew2

Allied campaign = [Allies_New, Allies_1 .. Allies_9]. Allies_New is retail Allies_3 (Heidelberg) with
  - MapName in a new folder, data\\maps\\official\\CAMP_CNV01_Probe\\ (a copy of the Heidelberg folder: map,
    pictures, its map streams and their 1.10 / 1.11 patch streams)
  - new string labels (title, short title, briefing summary, briefing objectives) from data\\mod.str
Checks: the new strings show (UTF-8 Chinese, with an ASCII "CNV01" tag in case it does not), the copied map
loads, and the mission exists at every LOD (static / static_l / static_m .12 tables).
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
import splice_assets                                     # noqa: E402
from ra3voice import big                                  # noqa: E402
import labpaths                                           # noqa: E402

# Mod SDK v3.0 (patch 1.12 layouts, AllTypesHash 1424942948 like the game). sdk\RA3ModSDK is a 1.10-era SDK: its
# GameObjects load but corrupt the heap once the unit is active (CampNew19 bisect, 2026-10-16) -- don't use it.
SDK = labpaths.SDK3
NAME = 'CampNew2'
SRC_DIR = os.path.join(SDK, 'Mods', NAME, 'data')
BUILT = os.path.join(SDK, 'BuiltMods', 'mods', NAME.lower(), 'data')
OUT = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods', NAME)
OLD_DIR = 'data\\maps\\official\\camp_a03_heidelberg_smith\\'
OLD_STEM = 'camp_a03_heidelberg_smith'
NEW_STEM = 'camp_cnv01_probe'
NEW_DIR = f'data\\maps\\official\\{NEW_STEM}\\'
# variant B (2026-10-16): the copied precompiled map streams crashed on load (they were built for the old folder);
# a user map is only a .map the game reads at run time, so ship the renamed .map and pictures, no map.* streams
SHIP_STREAMS = False
MAP_ARCHIVES = ['MapsCampaign.big', 'Maps10.big', 'Maps11.big', 'Maps12.big']   # later archives win
# more XML compiled into the static stream, type="all" (a music pack's PathMusicMap: experimental/music/pack.py;
# the game wants it from the start, before any map stream loads)
EXTRA_STATIC = []
# the campaign shell (experimental/cnv/shell.py, ADR 0014): all nine slots of the Allied campaign are ours; the built mission
# takes slot `slot` (retail's mission of that slot is the base: its briefing screens), the others keep retail's maps as
# placeholders. {'slot': 4, 'attrs': {template attribute: value} (the built mission's fields), 'others': {slot: attrs},
# 'no_portrait': drop the co-op commanders' pictures}
SHELL = None
STRINGS = [
    ('MissionName:CNV01', 'CNV01 新关卡测试：海德堡'),
    ('MissionName:CNV01_Short', 'CNV01 新关卡'),
    ('BriefingSummary:CNV01', 'CNV01：这是由配音 mod 测试生成的新关卡。地图来自新的文件夹，标题和简报来自 mod 自己的字符串。'),
    ('MISSIONOBJ:CNV01_1', 'CNV01 目标一：护送基地车'),
    ('MISSIONOBJ:CNV01_2', 'CNV01 目标二：攻下苏军总部'),
]


def template(xml, base, new_id, label, attrs=None, map_path=None, no_portrait=False):
    """retail template `base` copied as `new_id`, unlocked, with the labels of `label` (MissionName:<label> ...); map_path
    replaces its map; attrs: {'Element:Attr' or 'Attr': value} field edits (the element-less ones are the template's own)."""
    new = re.search(rf'<MissionTemplate\s+id="{base}".*?</MissionTemplate>', xml, re.S).group(0)
    new = new.replace(f'id="{base}"', f'id="{new_id}"')
    new = re.sub(r'<Prerequisite>\d+</Prerequisite>', '<Prerequisite>0</Prerequisite>', new)
    new = re.sub(r'ShortDisplayName="[^"]*"', f'ShortDisplayName="MissionName:{label}_Short"', new)
    new = re.sub(r'(?<!Short)DisplayName="[^"]*"', f'DisplayName="MissionName:{label}"', new)
    new = re.sub(r'BriefingSummary="[^"]*"', f'BriefingSummary="BriefingSummary:{label}"', new)
    for k, o in enumerate(re.findall(r'<Objective>[^<]*</Objective>', new)):
        new = new.replace(o, f'<Objective>MISSIONOBJ:{label}_{k + 1}</Objective>' if k < 2 else '', 1)
    if map_path:
        old_map = re.search(r'MapName="([^"]+)"', new).group(1)
        new = new.replace(old_map, map_path)
    for attr, value in (attrs or {}).items():           # 'Element:Attr' = inside that element only
        element, _, attr = attr.rpartition(':')
        pat = rf'(<{element}\b[^>]*?\s){attr}="[^"]*"' if element else rf'(?<![A-Za-z]){attr}="[^"]*"'
        new, n = re.subn(pat, (r'\g<1>' if element else '') + f'{attr}="{value}"', new, count=1)
        assert n == 1, f'shell: no {element or "template"} attribute {attr}'
    if no_portrait:                                     # the co-op commander's picture (an OnDemandImage; optional in the schema)
        new = re.sub(r'(<AICommander\b[^>]*?)\s+Portrait="[^"]*"', r'\1', new)
    return new


def sources():
    xml = open(os.path.join(SDK, 'SageXML', 'GlobalData', 'CampaignTemplates.xml'), encoding='ascii').read()
    camp = re.search(r'<CampaignTemplate\s+id="Allies".*?</CampaignTemplate>', xml, re.S).group(0)
    if not SHELL:
        new = template(xml, 'Allies_3', 'Allies_New', 'CNV01', map_path=NEW_DIR + NEW_STEM + '.map')
        news = [new]
        camp = camp.replace('<Mission>Allies_1</Mission>', '<Mission>Allies_New</Mission>\n\t<Mission>Allies_1</Mission>', 1)
        assert camp.count('<Mission>') == 10
    else:
        # the campaign shell: every slot of the Allied campaign is a copy of retail's mission in that slot with our labels
        # (CNV0<slot>); the built mission's slot gets our map too, the others keep retail's map (a placeholder)
        slot = SHELL.get('slot', 1)
        news = []
        for k in range(1, 10):
            mine = k == slot
            new_id = 'Allies_New' if mine else f'Allies_S{k}'
            attrs = SHELL.get('attrs', {}) if mine else SHELL.get('others', {}).get(k, {})
            news.append(template(xml, f'Allies_{k}', new_id, f'CNV{k:02d}', attrs, NEW_DIR + NEW_STEM + '.map' if mine else None,
                                 SHELL.get('no_portrait', False)))
            camp = camp.replace(f'<Mission>Allies_{k}</Mission>', f'<Mission>{new_id}</Mission>', 1)
        assert camp.count('<Mission>') == 9
        new = news[slot - 1]
    os.makedirs(SRC_DIR, exist_ok=True)
    with open(os.path.join(SRC_DIR, f'{NAME}.xml'), 'w', encoding='ascii', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="us-ascii"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n\n')
        f.write('\n\n'.join(news) + '\n\n' + camp + '\n\n</AssetDeclaration>\n')
    with open(os.path.join(SRC_DIR, 'mod.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                '\t<Tags></Tags>\n\t<Includes>\n'
                '\t\t<Include type="reference" source="DATA:static.xml" />\n'
                '\t\t<Include type="reference" source="DATA:global.xml" />\n'
                '\t\t<Include type="reference" source="DATA:audio.xml" />\n'
                f'\t\t<Include type="all" source="DATA:{NAME}/Data/{NAME}.xml" />\n'
                + ''.join(f'\t\t<Include type="all" source="{x}" />\n' for x in EXTRA_STATIC) +
                '\t</Includes>\n</AssetDeclaration>\n')
    print('mission:', re.search(r'MapName="([^"]+)"', new).group(1), '| templates', len(news))


def compile_mod():
    r = subprocess.run([os.path.join(SDK, 'tools', 'BinaryAssetBuilder.exe'), os.path.join(SRC_DIR, 'mod.xml'),
                        f'/od:{SDK}\\BuiltMods', f'/iod:{SDK}\\BuiltMods', '/ls:true', '/gui:false',
                        '/pc:true', '/vf:false', '/el:0'], cwd=SDK, capture_output=True, text=True, errors='replace')
    open(os.path.join(SDK, f'_build_{NAME}.log'), 'w', encoding='utf-8').write(r.stdout + r.stderr)
    if r.returncode or 'BinaryAssetBuilder complete' not in r.stdout:
        sys.exit('BinaryAssetBuilder failed, see ' + os.path.join(SDK, f'_build_{NAME}.log'))


def map_files():
    data = splice_assets.DATA
    found = {}
    for a in MAP_ARCHIVES:
        p = os.path.join(data, a)
        if not os.path.exists(p):
            continue
        names = [n for n, _, _ in big.read_index(p) if n.lower().startswith(OLD_DIR)]
        for n, v in big.read_files(p, names).items():
            leaf = n[len(OLD_DIR):]
            if not SHIP_STREAMS and leaf.lower().startswith('map.'):
                continue
            found[NEW_DIR + leaf.lower().replace(OLD_STEM, NEW_STEM)] = v     # the .map is named after its folder
    return sorted(found.items())


def mod_str():
    return ''.join(f'{k}\r\n"{v}"\r\nEND\r\n\r\n' for k, v in STRINGS).encode('utf-8')


def main():
    sources()
    compile_mod()
    files = splice_assets.spliced_files(BUILT)
    maps = map_files()
    print('map folder copy:', len(maps), 'files', [n.split('\\')[-1] for n, _ in maps])
    files += maps + [('data\\mod.str', mod_str())]
    os.makedirs(OUT, exist_ok=True)
    big.write(os.path.join(OUT, f'{NAME}.big'), files)
    with open(os.path.join(OUT, f'{NAME}_1.0.skudef'), 'w', encoding='ascii', newline='') as f:
        f.write(f'mod-game 1.12\r\nadd-big {NAME}.big\r\n')
    print('->', OUT)


if __name__ == '__main__':
    main()
