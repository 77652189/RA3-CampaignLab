"""Static checks on our unit XML before the 70 s compile and the bench: the pitfalls that each cost bench runs
(HANDOFF「这两天测试台上反复踩的坑」), caught from the files alone.

  python -I -X utf8 experimental/campaign/lint.py [file.xml ...]   (no files: every XML in CNVUnits/Data)

Builders call run() from make_campnew7.compile_map with the files of this build and the templates placed on the map;
an ERROR stops the build (CNV_LINT=warn: print only). Rules:
  vision     (WARN) a WeaponSetUpdate weapon reaches past the unit's own VisionRange: ours turned and never fired (时滞炮车, 自由号)
  immobile   an INFANTRY unit's file sets IMMOBILE: infantry must turn to aim, use IMMOBILE_ALLOW_ROTATE (烟花兵)
  filter     a SpecialPowerTemplate driving StoreObjects / TeleportStoredObjects has no ObjectFilter: nothing moves
  toggle     a ToggleState without SkirmishAiInfo: the build's XML check fails (阻塞气球车)
  retail-id  a GameObject of ours under a retail id (an inheriting variant left in a copied retail file, e.g. the
             Tank Buster's _Ambush): the build fails
  spawn      a SpawnBehavior spawns our own template that is not placed on the map: it never loads (自由号炮塔);
             one linked by name (experimental/cnv links every unit) counts as placed
  chooser    (WARN) armed, but its target chooser picks no targets (CanPickDynamicTargets false, or an AIUpdate
             written on BaseObject without one): ours never fired on their own (装甲列车, 自由号炮塔)
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import labpaths  # noqa: E402

SAGE = os.path.join(labpaths.SDK3, 'SageXML')
UNITS = os.path.join(labpaths.SDK3, 'Mods', 'CNVUnits', 'Data')
INDEX = os.path.join(labpaths.WORK, 'lint_retail_index.json')
TRIGGER_RANGE = 5000            # weapons fired by FireWeaponUpdate / SourceWeapon carry AttackRange 10000: not aimed
# bench record: range/vision 1.25 (烟花兵 250/200) and 1.5 (磁钩坦克 300/200, the Guardian's painter) fired;
# 2 (时滞炮车 400/200) and 4 (自由号 600/150) never did
VISION_RATIO = 1.5


def blocks(text, tag):
    """(attributes of the opening tag, whole block) for every <tag ...> ... </tag> or <tag .../>."""
    out = []
    for m in re.finditer(rf'<{tag}\b([^>]*?)(/?)>', text, re.S):
        if m.group(2):
            out.append((m.group(1), m.group(0)))
            continue
        end = text.find(f'</{tag}>', m.end())
        out.append((m.group(1), text[m.start():end + len(tag) + 3] if end >= 0 else m.group(0)))
    return out


def attr(attrs, name):
    m = re.search(rf'(?<![A-Za-z]){name}="([^"]*)"', attrs)
    return m.group(1) if m else None


def num(s):
    """A number attribute, or None for a define (AttackRange="=$SPECTRUM_TOWER_LINK_RANGE")."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def retail_index():
    """{'objects': [retail GameObject ids], 'ranges': {WeaponTemplate id: AttackRange}} from the SDK's SageXML,
    cached in work/ (it reads ~4000 files)."""
    if os.path.exists(INDEX):
        with open(INDEX, encoding='utf-8') as f:
            return json.load(f)
    objects, ranges = set(), {}
    for p in glob.glob(os.path.join(SAGE, '**', '*.xml'), recursive=True):
        text = open(p, encoding='utf-8', errors='replace').read()
        for a in re.findall(r'<GameObject\b([^>]*)>', text, re.S):
            if attr(a, 'id'):
                objects.add(attr(a, 'id'))
        for a in re.findall(r'<WeaponTemplate\b([^>]*)>', text, re.S):
            if attr(a, "id") and num(attr(a, "AttackRange")) is not None:
                ranges[attr(a, "id")] = num(attr(a, "AttackRange"))
    data = dict(objects=sorted(objects), ranges=ranges)
    os.makedirs(os.path.dirname(INDEX), exist_ok=True)
    with open(INDEX, 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return data


def check(files, placed=None, overrides=()):
    """[(level, file name, message)] for our XML files; placed = templates on the map (None: skip the spawn rule)."""
    idx = retail_index()
    retail = set(idx['objects']) - set(overrides)
    texts = {p: open(p, encoding='utf-8', errors='replace').read() for p in files if os.path.exists(p)}
    ranges = dict(idx['ranges'])
    own_objects = set()
    for text in texts.values():
        for a, _ in blocks(text, 'WeaponTemplate'):
            if attr(a, "id") and num(attr(a, "AttackRange")) is not None:
                ranges[attr(a, "id")] = num(attr(a, "AttackRange"))
        own_objects |= {attr(a, 'id') for a, _ in blocks(text, 'GameObject')}
    out = []
    for p, text in texts.items():
        name = os.path.basename(p)
        objs = blocks(text, 'GameObject')
        # a retail unit recompiled whole (make_campnew33's OVERRIDE, its variants included) is retail on purpose
        recompiled = bool(objs) and attr(objs[0][0], 'id') in set(idx['objects'])
        for a, body in objs:
            oid, kinds = attr(a, 'id'), (attr(a, 'KindOf') or '').split()
            if recompiled:
                continue
            if oid in retail:
                out.append(('ERROR', name, f'retail-id: GameObject {oid} has a retail id (an inheriting variant left '
                                           'in a copied file? delete it)'))
            # WARN, not ERROR: retail has units like this (the Tengu's land missile 300, vision 200); ours did not fire
            # on the bench (时滞炮车, 自由号), so look at it first when a new unit does not fire
            vis = re.search(r'(?<![A-Za-z])VisionRange="([\d.]+)"', body)
            for w in sorted(set(re.findall(r'<Weapon\b[^>]*?Template="([^"]+)"', body, re.S))):
                r = ranges.get(w)
                if vis and r and r < TRIGGER_RANGE and r > VISION_RATIO * float(vis.group(1)):
                    out.append(('WARN', name, f'vision: {oid} weapon {w} reaches {r:g} past its VisionRange '
                                              f'{vis.group(1)}: ours have turned and never fired like this'))
            # WARN: weapons on fixed mounts only, and a target chooser that picks none -- it says not to (retail's
            # prop train: 装甲列车), or an AIUpdate written from scratch on BaseObject without one (自由号炮塔).
            # Left alone: a turret slot (the Tesla tank fires with CanPickDynamicTargets false) and copies of retail
            # units with no chooser written (the Imperial Warrior)
            armed = '<WeaponSlotHardpoint' in body and '<WeaponSlotTurret' not in body
            scratch = (attr(a, 'inheritFrom') == 'BaseObject' and re.search(r'<AIUpdate\b', body)
                       and 'CanPickDynamicTargets="true"' not in body)
            if armed and ('CanPickDynamicTargets="false"' in body or scratch):
                out.append(('WARN', name, f'chooser: {oid} is armed but picks no targets (UnitAITargetChooserData '
                                          'CanPickDynamicTargets): ours like this never fired on their own'))
            if 'INFANTRY' in kinds and re.search(r'ObjectStatusToSet="[^"]*\bIMMOBILE\b(?!_)', text):
                out.append(('ERROR', name, f'immobile: {oid} is infantry and the file sets IMMOBILE: use '
                                           'IMMOBILE_ALLOW_ROTATE (infantry turn to aim)'))
            for t in re.findall(r'<SpawnTemplate>\s*([^<\s]+)\s*</SpawnTemplate>', body):
                if placed is not None and t in own_objects and t not in placed:
                    out.append(('ERROR', name, f'spawn: {oid} spawns {t}, ours and not placed on the map: it never '
                                               'loads (place one somewhere out of the way)'))
        moved = set(re.findall(r'<(?:StoreObjectsSpecialPower|TeleportStoredObjectsSpecialPower)\b[^>]*?'
                               r'SpecialPowerTemplate="([^"]+)"', text, re.S))
        for a, body in blocks(text, 'SpecialPowerTemplate'):
            if attr(a, 'id') in moved and '<ObjectFilter' not in body:
                out.append(('ERROR', name, f'filter: {attr(a, "id")} drives a chrono store/send without an '
                                           'ObjectFilter: nothing will be moved'))
        for a, body in blocks(text, 'ToggleState'):
            if 'SkirmishAiInfo' not in body:
                out.append(('ERROR', name, 'toggle: a ToggleState without SkirmishAiInfo (the build fails)'))
    return out


def data_path(src):
    """'DATA:CNVUnits/Data/X.xml' -> the file under the SDK's Mods folder."""
    return os.path.join(labpaths.SDK3, 'Mods', *src.split(':', 1)[1].split('/'))


def run(templates, also=(), placed=None, overrides=()):
    """The builders' hook: lint this build's files, print the findings, stop on an ERROR unless CNV_LINT=warn."""
    files = sorted({data_path(v['file']) for v in templates.values()} | {data_path(s) for s in also})
    found = check(files, placed, overrides)
    for level, name, msg in found:
        print(f'LINT {level} {name}: {msg}')
    if any(f[0] == 'ERROR' for f in found) and os.environ.get('CNV_LINT') != 'warn':
        sys.exit('lint found errors (CNV_LINT=warn to build anyway)')
    print(f'lint: {len(files)} files, {len(found)} findings')


if __name__ == '__main__':
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(UNITS, '*.xml')))
    found = check(files)
    for level, name, msg in found:
        print(level, name, msg, sep=' | ')
    print(len(files), 'files,', len(found), 'findings')
