r"""Look things up in the retail campaign maps (RA3 + Uprising, 40 maps) the way a level designer asks: how do the
scripts use this action, where and how is this object placed, what are this map's objectives. The first call caches
every map's script text and object list in work/retailref/ (~2 min); later calls read the cache.

  python -I -X utf8 experimental/campaign/retailref.py scripts LINK_MISSION_OBJECTIVE [--maps s09,ep01] [--limit 8]
  python -I -X utf8 experimental/campaign/retailref.py objects "Bridge" [--maps j08] [--limit 20]
  python -I -X utf8 experimental/campaign/retailref.py goals [--maps a09]

scripts: every script with a condition / action matching the pattern (regex, case-insensitive), whole, with its map.
objects: placements of templates matching it: position, angle, flags, owner, name, terrain height under it (world).
goals: each map's objectives with their English titles, main / bonus.
"""
import argparse
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labpaths  # noqa: E402

sys.path.insert(0, labpaths.ROOT)
CACHE = os.path.join(labpaths.WORK, 'retailref')


def build_cache():
    from ra3voice import big
    import mapscript
    import mapstudy
    import mapterrain
    import mapxml
    os.makedirs(CACHE, exist_ok=True)
    index = []
    for game, arc, n, short in mapstudy.retail_maps():
        m = mapscript.MapFile(big.read_files(arc, [n])[n])
        hm = mapterrain.HeightMap(m)
        objs = []
        for o in mapxml.objects(m):
            i, j = hm.cell(o['x'], o['y'])
            inside = 0 <= i < hm.width and 0 <= j < hm.height
            ground = hm.elev[j * hm.width + i] * mapstudy.REAL if inside else None     # world units, water at 200
            p = o['props']
            objs.append(dict(t=o['template'], x=round(o['x']), y=round(o['y']), a=round(math.degrees(o['angle'])),
                             flags=o['flags'], owner=str(p.get('originalOwner', '')), name=str(p.get('objectName', '')),
                             ground=round(ground) if ground is not None else None))
        try:
            goals = [dict(name=g['name'], bonus=bool(g['bonus']), title=mapstudy.text(g['title']))
                     for g in m.objectives()]
        except StopIteration:
            goals = []
        with open(os.path.join(CACHE, short + '.txt'), 'w', encoding='utf-8') as f:
            f.write(m.script_text())
        with open(os.path.join(CACHE, short + '.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(objects=objs, goals=goals, water=mapstudy.water_height(m)), f, ensure_ascii=False)
        index.append(short)
        print('cached', short, flush=True)
    with open(os.path.join(CACHE, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f)
    return index


def maps(only=''):
    path = os.path.join(CACHE, 'index.json')
    names = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else build_cache()
    parts = [p.strip() for p in only.split(',') if p.strip()]
    return [n for n in names if not parts or any(p in n for p in parts)]


# the export's line suffixes as nearly every line has them: a condition as it reads / inverted; an action
COMMON = ('+0100000000000000', '+0100000001000000', '+01000000')


def condition(line):
    """A script line without its export suffix. A condition's suffix whose second half is 01000000 inverts it
    (yokohama and facility, checked against what the mission does: docs/design/teardowns/data/yokohama-facts.md):
    shown as `IF NOT ...`. The rare suffixes (first half 00000000: 4 conditions, 300 actions in all the campaign;
    what they mean is not checked) stay on, as they are."""
    text, sep, suffix = line.partition('  +')
    if not sep:
        return line
    suffix = '+' + suffix
    if suffix[9:17] == '01000000':
        text = re.sub(r'^(\s*IF )', r'\1NOT ', text)
    return text if suffix in COMMON else f'{text}  {suffix}'


def scripts(pattern, only='', limit=8):
    """Whole scripts (their indented block) holding a line that matches `pattern`."""
    rx, out = re.compile(pattern, re.I), []
    for name in maps(only):
        lines = open(os.path.join(CACHE, name + '.txt'), encoding='utf-8').read().splitlines()
        heads = [k for k, x in enumerate(lines) if x.strip().startswith('Script:')]
        for h, nxt in zip(heads, heads[1:] + [len(lines)]):
            block = lines[h:nxt]
            if any(rx.search(x) for x in block[1:]):
                out.append((name, '\n'.join(condition(x) for x in block)))
                if len(out) >= limit:
                    return out
    return out


def objects(pattern, only='', limit=20):
    rx, out = re.compile(pattern, re.I), []
    for name in maps(only):
        d = json.load(open(os.path.join(CACHE, name + '.json'), encoding='utf-8'))
        for k, o in enumerate(d['objects']):
            if rx.search(o['t']):
                out.append((name, k, o))
                if len(out) >= limit:
                    return out
    return out


def goals(only=''):
    return [(name, json.load(open(os.path.join(CACHE, name + '.json'), encoding='utf-8'))['goals'])
            for name in maps(only)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=('scripts', 'objects', 'goals', 'cache'))
    ap.add_argument('pattern', nargs='?', default='')
    ap.add_argument('--maps', default='')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    if a.what == 'cache':
        build_cache()
    elif a.what == 'scripts':
        hits = scripts(a.pattern, a.maps, a.limit or 8)
        print(f'{len(hits)} scripts' + (' (limit reached)' if len(hits) == (a.limit or 8) else ''))
        for name, block in hits:
            print(f'== {name}\n{block}')
    elif a.what == 'objects':
        hits = objects(a.pattern, a.maps, a.limit or 20)
        print(f'{len(hits)} placements (map, list index, template, x, y, angle, flags, owner, name, ground)')
        for name, k, o in hits:
            print(f"{name} #{k} {o['t']} ({o['x']}, {o['y']}) {o['a']}deg flags {o['flags']} {o['owner']} "
                  f"{o['name'] or '-'} ground {o['ground']}")
    else:
        for name, gs in goals(a.maps):
            print(f'== {name}')
            for g in gs:
                print(f"  {'bonus' if g['bonus'] else 'main '} {g['name']}: {g['title']}")


if __name__ == '__main__':
    main()
