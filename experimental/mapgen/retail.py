"""Shared read-only cell and object table for miners. Cell (j, i) starts at (10i, 10j)."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from itertools import pairwise
import math
import re

import cv2
import numpy as np
from scipy import ndimage as nd

from experimental.campaign import mapscript, mapsprite, mapstudy, mapterrain, mapxml
from experimental.mapgen.library import sdk_footprint, sdk_xml
from ra3voice import big


CELL = int(mapterrain.CELL)
FOUR = nd.generate_binary_structure(2, 1)
MARKING = re.compile(r'parkinglines|crosswalk|marking|whiteline|yellowline')
FAMILIES = {kind: family for family, kinds in {
    'grass': 'grass field', 'paving': 'pavement pave concrete brick asphalt road gravel',
    'earth': 'dirt sand mud rock',
}.items() for kind in kinds.split()}


@dataclass
class RetailMap:
    source: dict
    height: np.ndarray
    passable: np.ndarray
    textures: tuple[str, ...]
    base: np.ndarray                     # indices into textures
    family: np.ndarray
    water: np.ndarray
    playable: np.ndarray
    objects: list[dict]                  # includes the original flags, pose, and SDK footprint (local space)
    roads: np.ndarray
    parking: np.ndarray
    segments: list[tuple]                # Road Tool (template, start, end, width)
    parking_models: list[tuple]          # (template, row indices, column indices)

    def town_blocks(self, exclude=()):
        """201 street faces, numbered before filtering, with spec exclusions for special sites."""
        cliff = np.array([t.lower().startswith('cliff_') for t in self.textures])[self.base]
        dry = self.playable & self.passable & ~(self.water | cliff | self.roads)
        faces, _ = nd.label(dry, structure=FOUR)
        sizes = np.bincount(faces.ravel())
        street = nd.binary_dilation(self.roads, structure=FOUR) & ~self.roads
        fronts = np.bincount(faces[street], minlength=len(sizes))
        for number in np.flatnonzero((sizes >= 25) & (fronts >= 4)):
            if number and number not in exclude:
                yield int(number), faces == number


@lru_cache(maxsize=1)
def _model_index():
    from experimental.units import retail_mesh

    meshes = retail_mesh.library()
    return retail_mesh, meshes, {tuple(item.entry[:2]): name for name, item in meshes.items()}


@lru_cache(maxsize=256)
def _model(template):
    reader, meshes, keys = _model_index()
    result = []
    for name, _ in mapsprite.parts(meshes, keys, template):
        mesh = reader.load(meshes, name)
        result.append((np.asarray(mesh['vertices'], dtype=float)[:, :2], np.asarray(mesh['triangles'])))
    return result


def model_vertices(template):
    parts = _model(template.lower())
    return np.concatenate([vertices for vertices, _ in parts]) if parts else np.empty((0, 2))


def world_points(obj, points):
    c, s = math.cos(obj['angle']), math.sin(obj['angle'])
    return np.asarray(points) @ np.array([[c, s], [-s, c]]) + (obj['x'], obj['y'])


def grid_points(points, scale=1):
    return np.rint((np.asarray(points) * scale / CELL - .5) * 256).astype(np.int32)


def strip(a, b, width):
    a, b = np.asarray(a), np.asarray(b)
    x, y = b - a
    normal = np.array([-y, x]) * (width / (2 * math.hypot(x, y)))
    return [a + normal, b + normal, b - normal, a - normal]


def _clip(polygon, axis, offset, sign):
    """Keep the half of the model on the specified side of its local kerb."""
    kept = []
    for a, b in pairwise([*polygon, polygon[0]]):
        d, e = (a[axis] - offset) * sign, (b[axis] - offset) * sign
        if d >= 0:
            kept.append(a)
        if (d < 0) != (e < 0):
            kept.append(a + (b - a) * d / (d - e))
    return kept


def _project(mask, obj, cut=None):
    parts = _model(obj['template'].lower())
    if not parts:
        raise ValueError(f"Missing road mesh: {obj['template']}")
    for vertices, triangles in parts:
        for triangle in vertices[triangles]:
            (u, v), (x, y) = np.diff(triangle, axis=0)
            if abs(u * y - v * x) > 1e-7:
                polygon = _clip(triangle, *cut) if cut else triangle
                if len(polygon) >= 3:
                    cv2.fillConvexPoly(mask, grid_points(world_points(obj, polygon), 4), 1, shift=8)


def _road_layers(shape, objects, segments, parking_models):
    """Project carriageways at quarter-cell resolution, then close one-cell socket gaps."""
    road = np.zeros(tuple(4 * n for n in shape), np.uint8)
    deck = np.zeros_like(road)
    parking = []
    for obj in objects:
        template = obj['template'].lower()
        if obj['flags'] or 'streetsegment' not in template:
            continue
        if template not in parking_models:
            _project(road, obj)
            continue
        cut = parking_models[template]
        if cut:
            axis, offset, sign = cut
            _project(road, obj, cut)
            cut = axis, offset, -sign
        deck.fill(0)
        _project(deck, obj, cut)
        parking.append((obj['template'], *np.where(deck[2::4, 2::4])))
    for template, a, b, width in segments:
        name = template.lower()
        if 'road' in name and not MARKING.search(name):
            cv2.fillConvexPoly(road, grid_points(strip(a, b, width), 4), 1, shift=8)
    roads = road[2::4, 2::4].astype(bool)
    roads |= nd.binary_closing(roads, structure=FOUR)
    parks = np.zeros(shape, bool)
    for _, j, i in parking:
        parks[j, i] = True
    return roads, parks & ~roads, parking


def read_map(game, sage, catalogue, spec, parking_models):
    """Read one archive entry. Treat the first playable bounds as a mask on the cell table."""
    archive, inner = spec['archive'], spec['inner']
    raw = big.read_files(game / 'Data' / archive, [inner])[inner]
    native = mapscript.MapFile(raw)
    hm = mapterrain.HeightMap(native)
    tiles = mapterrain.Tiles(native, hm.width)
    b = hm.border
    cut = np.s_[b:hm.height-b, b:hm.width-b]
    height = np.asarray(hm.elev).reshape(hm.height, hm.width)[cut] * mapstudy.REAL
    bits = np.unpackbits(np.frombuffer(tiles.extra, np.uint8, tiles.row_bytes * tiles.height), bitorder='little')
    passable = ~bits.reshape(tiles.height, -1)[:, :hm.width][cut].astype(bool)
    textures = tuple(tiles.textures)
    starts = [entry[0] for entry in tiles.textures.values()]
    base = np.searchsorted(starts, np.asarray(tiles.arrays[0]).reshape(hm.height, hm.width)[cut] // 4,
                           side='right') - 1
    classes = {e.attrib['id'].lower(): e.attrib['Class'].lower()
               for e in sdk_xml(sage / 'Terrain/Terrain.xml').iter('TerrainAsset')}
    # Transition assets are painted ground joins. Keep them distinct from the SDK's grass class.
    names = ['transition' if t.startswith('transition_') else classes.get(t, t.split('_')[0])
             for t in map(str.lower, textures)]
    family = np.asarray([FAMILIES.get(n, n) for n in names])[base]
    waterline = mapstudy.water_height(native)
    water = height <= waterline + .5 if waterline is not None else np.zeros(height.shape, bool)
    playable = np.zeros(height.shape, bool)
    x0, y0, x1, y1 = hm.borders()[0]
    playable[y0:y1, x0:x1] = True

    objects = mapxml.objects(native)
    widths = {r.attrib['id'].lower(): (r.attrib['id'], float(r.attrib['RoadWidth']))
              for r in sdk_xml(sage / 'GlobalData/Roads.xml').iter('Road')}
    segments = []
    for a, b in pairwise(objects):
        if a['flags'] & 6 == 2 and b['flags'] & 6 == 4 and a['template'] == b['template']:
            first, last = (a['x'], a['y']), (b['x'], b['y'])
            definition = widths.get(a['template'].lower())
            if definition and first != last:
                segments.append((definition[0], first, last, definition[1]))
    footprints = {t: sdk_footprint(catalogue, t) for t in {o['template'] for o in objects if not o['flags']}}
    for obj in objects:
        obj['cell'] = int(obj['y'] // CELL), int(obj['x'] // CELL)
        obj['footprint'] = footprints.get(obj['template'], ())
    h, w = height.shape
    inside = [o for o in objects if 0 <= o['cell'][0] < h and 0 <= o['cell'][1] < w]
    roads, parking, decks = _road_layers(height.shape, inside, segments, parking_models)
    return RetailMap(dict(archive=archive, inner=inner, sha256=sha256(native.chunk_bytes).hexdigest()), height, passable,
                     textures, base, family, water, playable, objects, roads, parking, segments, decks)
