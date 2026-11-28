"""Measure retail street lots: python -m experimental.mapgen.lot_miner SPEC [SPEC ...]."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import pairwise
import json
import math
from pathlib import Path
import re

import cv2
import numpy as np
from scipy import ndimage as nd
from scipy.spatial import cKDTree
from skimage.measure import find_contours

from experimental.campaign import labpaths
from experimental.mapgen import retail
from experimental.mapgen.library import sdk_objects
from experimental.mapgen.retail import CELL, FOUR


OPENING = np.ones((3, 3), bool)
BUILT_EDGE = re.compile(r'castlewall|fortresswall|seawall|cliffwall|retainingwall')
EDGE = re.compile(r'fence|hedge|wall|railing|handrail|kerb|curb|palisade')
VEGETATION = r'flower|blossom|bush|plant|tree|grass|reed|vine|shrub|palm|cactus|weeds|kelp|lily|fern'
FEATURE = (r'fountain|statue|sculpture|sign|monument|windmill|water(?:mill|tower)|well[0-9_]|crane|dock|pier|'
           r'gantry|swing|gazebo|arch[0-9_]|pergola|silo|playground|sandbox|cask|waterwheel|lighthouse|pavilion|berth|subpen')
ROLES = [(name, re.compile(pattern)) for name, pattern in (
    ('furnishing', r'bench|chair|table|umbrella|parasol|kiosk|trash|garbage|dumpster|newsstand|picnic|mailbox|'
                   r'stool|planter|lounger|telephone|vending|signpost|billboard|booth|cabana'),
    ('cargo', r'crate|barrel|pallet|container|bollard|cable|buoy|mooring|cargohold|hay|bags|woodpile|supplybox|oildrum|stack'),
    ('vehicle', r'boat|yacht|barge|tug|ship|car[0-9_]|car$|auto[0-9_]|truck|trailer|tractor|forklift|tram|railcar|train'),
    ('enclosure', r'fence|railing|hedge|gate|wall|pylon|pillar'),
    ('lamp', r'lamp|lightpost|streetlight|floodlight|lightstand|lightpole|searchlight'),
    ('feature', FEATURE), ('vegetation', VEGETATION),
    ('natural', r'rock|boulder|coral|stump|glacier|iceberg|snowdrift|logs?'),
    ('building', r'house|building|bldg|hotel|cafe|shop|store|apartments?|warehouse|hangar|shack|shed|barn|residen|'
                 r'church|garage|greenhouse|bureau|farm|hut|tent|stable|brewery|shrine|temple'),
)]
NON_SCENE = re.compile(
    r'cliff|seawall|pieredge|stairs?edge|(?:foot|apron|cabana|drive)path|'
    r'street(?:segment|corner|cross|tjunction|end|curve|straight)|tunnel|sidewalk|road|crosswalk|marking|pavement|'
    r'decal|(?:white|yellow|parking|center|edge|double)line|runway|taxiway|railroad|railtrack|bridge|platformedge|'
    r'terrain|waypoint|^amb_|fx[0-9_]|concrete(?:trim|tile)|junction|median|manhole|ore(?:node|mine)|techstructure|'
    r'startposition|^cin_|^audio_|^light_|proxy|placeholder|^camera|^dummy|wallpiece|^cnc_|^neutral|radar|'
    r'supplydropzone|fortress|^generic|landingzone')
NON_BUILDING = re.compile(r'statue|fountain|bigtree|bigcask|sculpture|obelisk|tank|bus|shuttle|truck|car0|auto0')
DECAL = re.compile(r'sidewalk|line|trim|marking|road|track|crosswalk|parking|footpath|border|bricks|decal|segment|path|strip')
NEUTRAL = {'', 'PlyrCivilian', 'PlyrNeutral', 'PlyrCreeps'}
NEUTRAL_NAMES = {s.lower() for s in NEUTRAL} | {'worldbuilder'}
COMPANIONS = {'furnishing', 'vegetation', 'feature', 'prop', 'cargo', 'vehicle'}


@dataclass
class Lot:
    kind: str
    cells: int
    frontage: int
    depth: int
    texture: str
    edges: dict[str, Counter]
    buildings: Counter
    set_pieces: list
    scattered_props: Counter
    reserved_empty: bool


def _role(obj, catalogue, prefixes, parking_models):
    t = obj['template'].lower()
    owner = str(obj['props'].get('originalOwner', '')).split('/')[0]
    if obj['flags'] or not t or t.startswith(('*', 'amb_', 'cin_', 'audio_', 'fx_', 'dummy')):
        return ''
    if t in parking_models or re.search(r'parkinglot|parkingstall', t):
        return 'parking'
    if any(s in t for s in ('streetsegment', 'cliffwall', 'seawall', 'sidewalksegment', 'bridge')):
        return ''
    if EDGE.search(t):
        return 'edge'
    if re.search(r'shuttlebus|artillery_tanks', t):
        return 'vehicle'
    definitions = catalogue.get(t, ())
    source, node = definitions[0] if definitions else ('', {})
    sorting = node.get('EditorSorting', '')
    if 'orenode' in t or 'BaseOreNode' in node.get('inheritFrom', ''):
        return 'ore'
    if re.search(r'techstructure|oilderrick|observationpost', t) or 'TechStructure' in node.get('inheritFrom', ''):
        return 'tech'
    authored = '/buildings/' in source.lower() or '/structures/' in source.lower()
    if (authored or sorting == 'STRUCTURE') and owner in NEUTRAL and not NON_BUILDING.search(t):
        return 'building'
    neutral = owner.lower() in NEUTRAL_NAMES or re.fullmatch(r'(?:civilian|neutral)_?\d+', owner.lower())
    prefix, _, name = t.partition('_')
    regional = prefix in prefixes or t.startswith(('civilian', 'civ_', 'capecod'))
    if neutral and regional and not obj['props'].get('objectName') and not NON_SCENE.search(t):
        for role, pattern in ROLES:
            if pattern.search(name or t):
                return role
    if authored and source.startswith('sdk/SageXML/Civilian/') and obj['footprint'] and not re.search('statue|fountain', t):
        return 'building'
    if retail.MARKING.search(t) or t == 'scorch':
        return 'marking'
    if re.search(VEGETATION, t):
        return 'vegetation'
    if owner not in NEUTRAL:
        return 'player'
    if DECAL.search(t):
        return ''
    if sorting in ('DESTRUCTIBLE_PROPS', 'OPTIMIZED_PROPS', 'MISC_NATURAL', 'MISC_MAN_MADE') or re.search(r'rock|fence|coral|prop', t):
        return 'prop'
    if re.search(r'lamp|light0[0-9]|trafficlight', t):
        return 'lamp'
    if re.search(r'statue|fountain|bigcask|sculpture|obelisk', t):
        return 'feature'
    return ''


def _hedge_rows(objects):
    shrubs = defaultdict(list)
    for obj in objects:
        if obj['role'] == 'vegetation' and re.search('bush|shrub', obj['template'], re.I):
            shrubs[obj['template']].append((obj['x'], obj['y']))
    for name, points in shrubs.items():
        if len(points) < 4:
            continue
        xy = np.asarray(points)
        tree = cKDTree(xy)
        matches, used = [], set()
        for i, j in sorted(tree.query_pairs(34)):
            step = xy[j] - xy[i]
            spacing = np.linalg.norm(step)
            if spacing * 3 >= 58:
                d, ends = tree.query(xy[i] + np.array([[2], [3]]) * step, distance_upper_bound=4)
                if np.isfinite(d).all():
                    matches.append((spacing, {i, j, *ends}, i, ends[-1]))
        for _, match, start, end in sorted(matches, key=lambda m: -m[0]):
            if len(match & used) < 2:
                used.update(match)
                yield 'plant-row', name, xy[[start, end]]


def _signatures(m, objects):
    barrier = np.zeros(m.base.shape, np.uint8)
    park = m.parking.astype(np.uint8)
    edges = []
    for obj in objects:
        name = obj['template'].lower()
        if obj['role'] != 'edge' or BUILT_EDGE.search(name):
            continue
        points = retail.model_vertices(name)
        if not len(points):
            continue
        lo, hi = points.min(axis=0), points.max(axis=0)
        long, short = max(hi - lo), min(hi - lo)
        if not 15 <= long <= 240:
            continue
        if long >= 1.7 * short:
            axis = int(np.argmax(hi - lo))
            points = np.tile((lo + hi) / 2, (2, 1))
            points[:, axis] = lo[axis], hi[axis]
        else:
            points = cv2.convexHull(points.astype(np.float32)).reshape(-1, 2)
        points = retail.world_points(obj, points)
        category = next((k for k in ('hedge', 'wall') if k in name), 'fence')
        if re.search(r'kerb|curb', name):
            category = 'kerb'
        edges.append((category, obj['template'], points))
        cv2.polylines(barrier, [retail.grid_points(points)], len(points) > 2, 1, 1, shift=8)
    for name, a, b, width in m.segments:
        if 'parkinglines' in name.lower():
            cv2.fillConvexPoly(park, retail.grid_points(retail.strip(a, b, width)), 1, shift=8)
            edges.append(('parking-lines', name, [a, b]))
        elif re.search(r'sidewalk|kerb|curb|trim', name.lower()):
            cv2.polylines(barrier, [retail.grid_points([a, b])], False, 1, 1, shift=8)
            edges.append(('kerb', name, [a, b]))
    edges.extend(_hedge_rows(objects))
    # The survey used planted rows as evidence, while actual hedge pieces also cut faces.
    samples = []
    for kind, name, points in edges:
        chain = [*points, points[0]] if len(points) > 2 else points
        cells = np.vstack([np.linspace(a, b, max(1, math.ceil(math.dist(a, b) / 8)) + 1)
                           for a, b in pairwise(chain)])
        i, j = np.floor(cells.T / CELL).astype(int)
        valid = (j >= 0) & (j < barrier.shape[0]) & (i >= 0) & (i < barrier.shape[1])
        samples.append((kind, name, j[valid], i[valid]))
    return barrier.astype(bool), park.astype(bool), samples


def _nearest(labels):
    indices = nd.distance_transform_edt(labels == 0, return_distances=False, return_indices=True)
    return labels[tuple(indices)]


def _partition(block, family, barrier, park, min_cells):
    walls = barrier & block & ~park
    available = block & ~(walls | nd.binary_closing(walls, structure=FOUR))
    faces, _ = nd.label(available, structure=FOUR)
    sizes = np.bincount(faces.ravel())
    interior = np.bincount(faces[nd.binary_erosion(available, structure=OPENING)], minlength=len(sizes))
    parts = [faces == k for k in np.flatnonzero((sizes >= min_cells) & (interior >= np.maximum(4, .10 * sizes))) if k]
    labels = np.zeros(block.shape, np.int32)
    enclosure, parking = [0], [False]
    for part_id, part in enumerate(parts or [block], 1):
        local = np.zeros_like(labels)
        surfaces = [(family == v, False) for v in np.unique(family[part & ~park])] + [(park, True)]
        for surface, is_park in surfaces:
            seeds, _ = nd.label(nd.binary_opening(surface & part, structure=OPENING), structure=FOUR)
            for k in np.flatnonzero(np.bincount(seeds.ravel()) >= min_cells):
                if k:
                    local[seeds == k] = len(enclosure)
                    enclosure.append(part_id)
                    parking.append(is_park)
        if not local.any():
            local[part] = len(enclosure)
            enclosure.append(part_id)
            parking.append(False)
        labels[part] = _nearest(local)[part]
    labels[block] = _nearest(labels)[block]
    return labels, np.asarray(enclosure), parking


def _footprint(obj, shape):
    mask = np.zeros(shape, np.uint8)
    for entry in obj['footprint']:
        offset = entry.get('Offset', {})
        x, y = retail.world_points(obj, [offset.get(k, 0) for k in 'xy'])
        a = entry['MajorRadius']
        b = entry['MinorRadius'] if entry['Type'] == 'BOX' else a
        pad = math.hypot(a, b)
        i0, i1 = max(0, int((x - pad) // CELL)), min(shape[1], int((x + pad) // CELL) + 1)
        j0, j1 = max(0, int((y - pad) // CELL)), min(shape[0], int((y + pad) // CELL) + 1)
        if i0 < i1 and j0 < j1:
            j, i = np.ogrid[j0:j1, i0:i1]
            u, v = i * CELL + CELL / 2 - x, j * CELL + CELL / 2 - y
            if entry['Type'] == 'BOX':
                c, s = math.cos(obj['angle']), math.sin(obj['angle'])
                inside = (abs(c * u + s * v) <= a) & (abs(c * v - s * u) <= b)
            else:
                inside = np.hypot(u, v) <= a
            mask[j0:j1, i0:i1] |= inside
    if not obj['footprint']:
        points = retail.model_vertices(obj['template'])
        if len(points):
            hull = cv2.convexHull(points.astype(np.float32)).reshape(-1, 2)
            cv2.fillConvexPoly(mask, retail.grid_points(retail.world_points(obj, hull)), 1, shift=8)
        else:
            mask[obj['cell']] = 1
    return np.where(mask)


def _merge_buildings(labels, block, enclosure, parking, buildings):
    for cell, j, i in buildings:
        ids = labels[j, i]
        counts = Counter(ids[ids > 0])
        if not counts:
            continue
        target = labels[cell]
        if not target or counts[target] < .35 * counts.total():
            target = counts.most_common(1)[0][0]
        for other, n in counts.items():
            if other != target and enclosure[other] == enclosure[target] and not parking[other]:
                if n >= .45 * np.count_nonzero(labels == other):
                    labels[labels == other] = target
        inside = block[j, i] & (enclosure[labels[j, i]] == enclosure[target])
        labels[j[inside], i[inside]] = target
    for k in np.unique(labels[block]):
        islands, n = nd.label(labels == k, structure=FOUR)
        if n > 1:
            largest = 1 + np.argmax(np.bincount(islands.ravel())[1:])
            labels[(islands != 0) & (islands != largest)] = 0
    missing = block & (labels == 0)
    while missing.any():
        neighbours = nd.maximum_filter(labels, footprint=FOUR)
        labels[missing] = neighbours[missing]
        missing = block & (labels == 0)


def _lot_type(ground, roles, buildings, edges, parking, shore):
    if parking >= .32:
        return 'parking'
    if buildings:
        names = ' '.join(buildings).lower()
        if re.search(r'church|cathedral|hermitage|castle|hotel|cister(n|ne)|arch_0|missilebase|artillery', names):
            return 'civic'
        if re.search('restaurant|brewery|shop', names) and not re.search('house0|rowhouse|alpinebldg', names):
            return 'commercial'
        return 'house'
    if ground == 'grass':
        return 'garden' if roles['vegetation'] + roles['feature'] + edges >= 3 else 'lawn'
    if shore:
        return 'quay'
    if ground == 'paving':
        return 'plaza' if any(roles[k] for k in ('feature', 'furnishing', 'lamp')) else 'yard'
    return 'open'


def _frontage(lot, road):
    front = 0.
    for contour in find_contours(np.pad(lot, 1), .5):
        a, b = contour[:-1], contour[1:]
        steps, mid = b - a, (a + b) / 2
        lengths = np.linalg.norm(steps, axis=1)
        normal = steps[:, ::-1] * np.array([-1, 1]) / lengths[:, None]
        sides = [np.floor(mid + sign * normal * .49 + .5).astype(int) for sign in (-1, 1)]
        street = road[tuple(sides[0].T)] | road[tuple(sides[1].T)]
        front += lengths[street].sum() * CELL
    return round(front)


def _largest_open(labels, family, occupied, clearance, min_cells):
    clear = labels > 0
    if occupied.any():
        clear &= nd.distance_transform_edt(~occupied) > clearance / CELL
    largest = 0
    for k in np.unique(labels[clear]):
        free = clear & (labels == k)
        for surface in np.unique(family[free]):
            areas, _ = nd.label(free & (family == surface), structure=FOUR)
            largest = max(largest, np.bincount(areas.ravel())[1:].max(initial=0))
    return int(largest) if largest >= min_cells else 0


def _contents(members, building_cells, parking_cells, inner_edge):
    buildings = Counter(o['template'] for o in members if o['role'] == 'building')
    props = [o for o in members if o['role'] not in {'building', 'player', 'parking', 'ore', 'tech'}]
    grouped, set_pieces = set(), []
    for i, anchor in enumerate(props):
        if i in grouped or anchor['role'] not in ('feature', 'furnishing'):
            continue
        nearby = [j for j, obj in enumerate(props) if j != i and j not in grouped and obj['role'] in COMPANIONS and
                  math.hypot(obj['x'] - anchor['x'], obj['y'] - anchor['y']) <= 60]
        if len(nearby) >= 2:
            c, s = math.cos(anchor['angle']), math.sin(anchor['angle'])
            transforms = []
            for j in sorted(nearby, key=lambda j: props[j]['template']):
                obj = props[j]
                x, y = obj['x'] - anchor['x'], obj['y'] - anchor['y']
                transforms.append(dict(template=obj['template'], dx=round(c*x+s*y, 2), dy=round(c*y-s*x, 2),
                                       dz=round(obj['z'] - anchor['z'], 2),
                                       angle_deg=round(math.degrees(obj['angle'] - anchor['angle']) % 360, 2)))
            set_pieces.append((anchor['template'], transforms))
            grouped.update([i, *nearby])
    scatter = Counter(o['template'] for i, o in enumerate(props) if i not in grouped)
    reserved = not (members or building_cells or parking_cells or inner_edge)
    return buildings, set_pieces, scatter, reserved


def _lots(labels, family, base, names, road, distance, water, members, barrier, park, samples, roofs):
    padded_road = np.pad(road, 1)
    near_road = nd.binary_dilation(road, structure=FOUR, iterations=2)
    for k in np.unique(labels[labels > 0]):
        lot = labels == k
        count = np.count_nonzero(lot)
        adjacent = nd.binary_dilation(lot, structure=FOUR)
        rim = adjacent & ~nd.binary_erosion(lot, structure=FOUR)
        other = nd.binary_dilation((labels > 0) & ~lot, structure=FOUR)
        near_other = nd.binary_dilation(other & lot, structure=FOUR)
        sides = {'street': Counter(), 'lot_to_lot': Counter()}
        front = _frontage(lot, padded_road)
        hit_edges = 0
        for kind, name, j, i in samples:
            hits = rim[j, i]
            if hits.any():
                hit_edges += kind != 'parking-deck'
                if front and near_road[j[hits], i[hits]].any():
                    sides['street'][kind, name] += 1
                if near_other[j[hits], i[hits]].any():
                    sides['lot_to_lot'][kind, name] += 1
        for side, present in (('street', front), ('lot_to_lot', (other & lot).any())):
            if present and not sides[side]:
                sides[side]['open', ''] += 1
        inside = [o for cell, o in members if lot[cell] and o['role'] not in ('edge', 'marking')]
        roles = Counter(o['role'] for o in inside)
        parking_cells = np.count_nonzero(park & lot)
        buildings, pieces, scatter, empty = _contents(inside, (roofs & lot).any(), parking_cells,
                                                      (nd.binary_erosion(lot, structure=FOUR, iterations=2) & barrier).any())
        ground = Counter(family[lot]).most_common(1)[0][0]
        lot_type = _lot_type(ground, roles, buildings, hit_edges, parking_cells / count, (adjacent & water).any())
        texture = names[Counter(base[lot]).most_common(1)[0][0]]
        depth = round(float(np.ptp(distance[lot])) + CELL)
        yield Lot(lot_type, int(count), front, depth, texture, sides, buildings, pieces, scatter, empty)


def measure(m, map_spec, min_cells, clearance, catalogue, prefixes, parking_models):
    """Return per-block evidence and per-lot recipe observations for one map."""
    h, w = m.base.shape
    objects = [o | {'role': _role(o, catalogue, prefixes, parking_models)} for o in m.objects
               if 0 <= o['cell'][0] < h and 0 <= o['cell'][1] < w]
    objects = [o for o in objects if o['role']]
    walls, park, samples = _signatures(m, objects)
    for name, j, i in m.parking_models:
        deck = np.zeros(m.base.shape, bool)
        deck[j, i] = ~m.roads[j, i]
        samples.append(('parking-deck', name, *np.where(deck & ~nd.binary_erosion(deck, structure=FOUR))))
    roofs = np.zeros(m.base.shape, bool)
    footprints = {}
    for index, obj in enumerate(objects):
        if obj['role'] == 'building':
            roofs[points := _footprint(obj, m.base.shape)] = True
            footprints[index] = points
    distances = nd.distance_transform_edt(~m.roads) * CELL
    uses = {number: use for use, numbers in map_spec['uses'].items() for number in numbers}
    blocks = list(m.town_blocks())
    unknown = (uses.keys() | set(map_spec['exclude'])) - {number for number, _ in blocks}
    if unknown:
        raise ValueError(f"{map_spec['map']}: unknown street faces {sorted(unknown)}")
    for number, mask in blocks:
        if number in map_spec['exclude']:
            continue
        j, i = np.where(mask)
        y0, x0 = max(0, j.min()-5), max(0, i.min()-5)
        y1, x1 = j.max()+6, i.max()+6
        crop = np.s_[y0:y1, x0:x1]
        block, family, barrier, parking = mask[crop], m.family[crop], walls[crop], park[crop]
        members, buildings = [], []
        covered = (roofs & mask)[crop]
        content = roofs[crop] | parking
        for index, obj in enumerate(objects):
            y, x = obj['cell']
            if not mask[y, x]:
                continue
            cell = y - y0, x - x0
            members.append((cell, obj))
            if obj['role'] not in ('edge', 'marking'):
                content[cell] = True
            if index in footprints:
                j, i = footprints[index]
                hit = (j >= y0) & (j < y1) & (i >= x0) & (i < x1)
                buildings.append((cell, j[hit] - y0, i[hit] - x0))
        local_edges = []
        for kind, name, j, i in samples:
            hit = (j >= y0) & (j < y1) & (i >= x0) & (i < x1)
            if hit.any():
                local_edges.append((kind, name, j[hit] - y0, i[hit] - x0))
        labels, enclosure, park_seed = _partition(block, family, barrier, parking, min_cells)
        _merge_buildings(labels, block, enclosure, park_seed, buildings)
        largest = _largest_open(labels, family, content | (barrier & block), clearance, min_cells)
        lots = list(_lots(labels, family, m.base[crop], m.textures, m.roads[crop], distances[crop],
                          m.water[crop], members, barrier & block, parking, local_edges, covered))
        evidence = dict(block=number, use=uses.get(number, map_spec['default_use']), cells=int(block.sum()),
                        building_cells=int(covered.sum()), largest_open_cells=largest)
        yield evidence, lots


def _recipes(observations):
    by_type, mixes = defaultdict(list), defaultdict(Counter)
    for use, lots in observations:
        for lot in lots:
            mixes[use][lot.kind] += 1
            by_type[lot.kind].append(lot)
    types = {}
    for kind, rows in by_type.items():
        front = [lot.frontage for lot in rows]
        depth = [lot.depth for lot in rows]
        groups = {}
        for lot in rows:
            for anchor, transforms in lot.set_pieces:
                signature = anchor, tuple(t['template'] for t in transforms)
                entry = groups.setdefault(signature, dict(anchor=anchor, relative_transforms=transforms, count=0))
                entry['count'] += 1
        types[kind] = dict(
            samples=len(rows), frontage=[min(front), max(front)], depth=[min(depth), max(depth)],
            textures=Counter(lot.texture for lot in rows),
            edges={side: [dict(treatment=k, template=name or None, count=n) for (k, name), n in sorted(
                sum((lot.edges[side] for lot in rows), Counter()).items())] for side in ('street', 'lot_to_lot')},
            contents=dict(buildings=sum((lot.buildings for lot in rows), Counter()),
                          scattered_props=sum((lot.scattered_props for lot in rows), Counter()),
                          set_pieces=list(groups.values()),
                          reserved_empty=sum(lot.reserved_empty for lot in rows)))
    return types, mixes


def mine(spec, game, sage, catalogue):
    parking = {name.lower(): cut for name, cut in spec['parking_models'].items()}
    prefixes = {p.name.rsplit('_', 1)[-1].lower() for p in (sage / 'Civilian').glob('*_*') if p.is_dir()}
    prefixes |= {'hs', 'sv', 'ap', 'sp', 'jp', 'cb', 'sm'}
    observations, evidence = [], []
    for sample in spec['maps']:
        m = retail.read_map(game, sage, catalogue, sample, parking)
        blocks = []
        for block, lots in measure(m, sample, spec['min_lot_cells'], spec['open_clearance'], catalogue, prefixes, parking):
            observations.append((block['use'], lots))
            blocks.append(block | {'types': Counter(lot.kind for lot in lots)})
        evidence.append(m.source | {'map': sample['map'], 'blocks': blocks})
        print(sample['map'], len(blocks), sum(sum(b['types'].values()) for b in blocks), flush=True)
    types, mixes = _recipes(observations)
    return {'lots': {'types': types, 'mix_by_use': mixes, 'evidence': evidence}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('spec', type=Path, nargs='+')
    args = parser.parse_args()
    sage = Path(labpaths.SDK3) / 'SageXML'
    game = Path(labpaths.GAME)
    catalogue = sdk_objects(sage)
    styles = {}
    for path in args.spec:
        spec = json.loads(path.read_bytes())
        if spec['kit'] in styles:
            parser.error(f"Duplicate kit: {spec['kit']}")
        styles[spec['kit']] = mine(spec, game, sage, catalogue)
    output = Path(labpaths.WORK) / 'mapgen_probe/lots.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(styles, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
