"""Read map-generator sketches and check their design-layer topology."""

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import combinations, pairwise
import json
import math
from pathlib import Path
import re


STEP_WORLD = 70
STEP_RAW = 1792
# The engine routes on a 20-world-unit grid. A footpath has one routing cell;
# a street ramp leaves a carriageway on either side of its centre (two 90-unit lanes).
FOOT_RAMP_WIDTH = 20
STREET_RAMP_WIDTH = 180
LAND = frozenset(("foot", "vehicle", "amphibian"))
WATER = frozenset(("amphibian", "ship"))
KINDS = LAND | WATER
ID = r"[A-Za-z][A-Za-z0-9_-]*"


class DesignError(ValueError):
    def __init__(self, item, rule, detail):
        self.item, self.rule = item, rule
        super().__init__(f"{item} [{rule}] {detail}")


def _need(ok, item, rule, detail):
    if not ok:
        raise DesignError(item, rule, detail)


def _fields(value, item, required="", optional=""):
    _need(isinstance(value, dict), item, "shape", "expected an object")
    missing = set(required.split()) - value.keys()
    unknown = value.keys() - set((required + " " + optional).split())
    _need(not (missing or unknown), item, "fields",
          f"missing {sorted(missing)}, unknown {sorted(unknown)}")


def _id(value, item):
    _need(isinstance(value, str) and re.fullmatch(ID, value), item, "id",
          f"invalid ID {value!r}")


def _ref(value, choices, item, field):
    _need(isinstance(value, str) and value in choices, item, "reference",
          f"{field} refers to unknown ID {value!r}")


def _list(value, item, field, *, size=None):
    _need(isinstance(value, list) and (size is None or len(value) == size),
          item, "shape", f"invalid list for {field}")


def _text(value, item, field):
    _need(isinstance(value, str) and value.strip(), item, "text", f"{field} requires text")


def _int(value, item, field):
    _need(type(value) is int and value >= 0, item, "integer",
          f"{field} needs a nonnegative integer")


def _number(value, item, field):
    _need((type(value) is int or (type(value) is float and math.isfinite(value))) and value >= 0,
          item, "number", f"{field} needs a finite nonnegative number")


def _xy(value, item):
    _list(value, item, "coordinate", size=2)
    _need(all(type(n) is int and -(2**31) <= n < 2**31 for n in value),
          item, "coordinate", "expected two signed integer world coordinates")
    return tuple(value)


def _pass(value, item, allowed=KINDS):
    _list(value, item, "pass")
    for kind in value:
        _ref(kind, allowed, item, "pass")
    _need(len(set(value)) == len(value), item, "pass", "repeated unit kind")
    return frozenset(value)


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def on_segment(p, a, b):
    return (_cross(subtract(p, a), subtract(b, a)) == 0
            and all(min(a[i], b[i]) <= p[i] <= max(a[i], b[i]) for i in (0, 1)))


def _along(p, a, b):
    axis = int(a[0] == b[0])
    return Fraction(p[axis] - a[axis], b[axis] - a[axis])


def _meet(a, b, c, d):
    """Return zero points, one contact, or both endpoints of an overlap."""
    if any(max(a[i], b[i]) < min(c[i], d[i]) or max(c[i], d[i]) < min(a[i], b[i])
           for i in (0, 1)):
        return ()
    ab, cd, ac = subtract(b, a), subtract(d, c), subtract(c, a)
    determinant = _cross(ab, cd)
    if not determinant:
        return tuple(sorted({p for p in (a, b, c, d) if on_segment(p, a, b) and on_segment(p, c, d)}))
    along_ab = _cross(ac, cd) / Fraction(determinant)
    along_cd = _cross(ac, ab) / Fraction(determinant)
    if 0 <= along_ab <= 1 and 0 <= along_cd <= 1:
        return ((a[0] + along_ab * ab[0], a[1] + along_ab * ab[1]),)
    return ()


def signed_area_twice(ring):
    """Twice the oriented area of a closed ring."""
    return sum(_cross(a, b) for a, b in pairwise(ring))


def point_in_ring(p, ring):
    """Return 1 inside, 0 on the outline, and -1 outside."""
    inside = False
    for a, b in pairwise(ring):
        if on_segment(p, a, b):
            return 0
        if (a[1] > p[1]) != (b[1] > p[1]):
            left = _cross(subtract(b, a), subtract(p, a))
            inside ^= (left > 0) == (b[1] > a[1])
    return 1 if inside else -1


def midpoint(a, b):
    return tuple((x + y) / Fraction(2) for x, y in zip(a, b))


def _line(raw, item):
    _list(raw, item, "line")
    line = tuple(_xy(p, item) for p in raw)
    _need(len(line) >= 2 and all(a != b for a, b in pairwise(line)),
          item, "line", "line needs at least one nonzero segment")
    return line


def _split_lines(lines):
    segments = [(name, a, b) for name, line in lines.items() for a, b in pairwise(line)]
    splits = [{a, b} for _, a, b in segments]
    for i, j in combinations(range(len(segments)), 2):
        name, a, b = segments[i]
        other, c, d = segments[j]
        points = _meet(a, b, c, d)
        _need(len(points) < 2, name, "overlap", f"line overlaps {other}")
        splits[i].update(points)
        splits[j].update(points)
    edges = defaultdict(list)
    for (name, a, b), points in zip(segments, splits):
        ordered = sorted(points, key=lambda p: _along(p, a, b))
        edges[name].extend(pairwise(ordered))
    return edges


def _angle(a, b):
    x, y = subtract(b, a)
    # Exact counterclockwise order starting at the downward ray.
    return (x < 0 or (x == 0 and y > 0), Fraction(y, x) if x else -math.inf)


def face_rings(edges):
    """Trace both sides of each noded edge, returning positive and other walks."""
    neighbors = defaultdict(list)
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    pending = {}
    for vertex, adjacent in neighbors.items():
        adjacent.sort(key=lambda p: _angle(vertex, p))
        for i, incoming in enumerate(adjacent):
            pending[incoming, vertex] = vertex, adjacent[i - 1]
    rings, other = [], []
    while pending:
        start = edge = next(iter(pending))
        ring = [start[0]]
        while True:
            ring.append(edge[1])
            edge = pending.pop(edge)
            if edge == start:
                break
        (rings if signed_area_twice(ring) > 0 else other).append(ring)
    return sorted(rings, key=signed_area_twice), other


def _spans(border, item, length, named_ramp):
    spans = {}
    raw = border.get("segments", {})
    _need(isinstance(raw, dict), item, "shape", "segments needs an object keyed by ID")
    for name, segment in sorted(raw.items()):
        sid = f"{item}.{name}"
        _id(name, sid)
        if isinstance(segment, dict) and ("from" in segment or "to" in segment):
            _fields(segment, sid, "from to pass")
            start, end = named_ramp(segment, sid)
        else:
            _fields(segment, sid, "span pass", "width")
            _list(segment["span"], sid, "span", size=2)
            start, end = segment["span"]
            if end is None:
                end = length
        _number(start, sid, "span start")
        _number(end, sid, "span end")
        _need(start < end <= length, sid, "span", f"span must fit the border length {length:g}")
        if "width" in segment:
            _width(segment["width"], sid)
        spans[sid] = (start, end, _pass(segment["pass"], sid))
    spans = dict(sorted(spans.items(), key=lambda pair: pair[1][:2]))
    cursor = 0
    for sid, (start, end, _) in spans.items():
        _need(start >= cursor, sid, "span", "overlaps a previous span")
        cursor = end
    return spans


def _width(value, item):
    _number(value, item, "width")
    _need(value > 0, item, "width", "width must be positive")


def _visit(graph, start):
    seen, stack = {start}, [start]
    while stack:
        for neighbor in graph[stack.pop()] - seen:
            seen.add(neighbor)
            stack.append(neighbor)
    return seen


class Design:
    """A validated design. Geometry is indexed once and shared by all states."""

    def __init__(self, data):
        _fields(data, "$", "version blocks", "seed roads borders points states relations patches commitments")
        _need(type(data["version"]) is int and data["version"] == 2,
              "$", "version", "expected format version 2")
        _int(data.get("seed", 0), "$", "seed")
        commitments = data.get("commitments", {})
        _fields(commitments, "$.commitments", optional="mood")
        self.mood = commitments.get("mood")
        if "mood" in commitments:
            _text(self.mood, "$.commitments", "mood")
        self.data = data
        all_ids = {"base"}
        for section in ("blocks", "roads", "borders", "points", "states", "relations", "patches"):
            entries = data.get(section, {})
            _need(isinstance(entries, dict), "$", "shape", f"{section} needs an object keyed by ID")
            for item in entries:
                _id(item, item)
                _need(item not in all_ids, item, "id", "ID already used or reserved")
                all_ids.add(item)
            setattr(self, section, dict(sorted(entries.items())))
        self.lines = self._read_lines()
        self.edges = _split_lines(self.lines)
        self.rings, self.sides = self._read_blocks()
        self._read_points()
        self._read_borders()
        self._read_states()
        self.via_ids = self.blocks.keys() | self.borders.keys() | self.base_pass.keys()
        self._read_relations()
        self._read_patches()
        self._index_roads()

    def _read_lines(self):
        lines = {}
        for item, road in self.roads.items():
            _fields(road, item, "line width", "ends")
            _ref(road["width"], ("alley", "street", "avenue"), item, "width")
            ends = road.get("ends", [])
            _list(ends, item, "ends")
            for end in ends:
                _ref(end, ("start", "end"), item, "ends")
            _need(len(set(ends)) == len(ends), item, "ends", "repeated end")
            lines[item] = _line(road["line"], item)
        for item, border in self.borders.items():
            _fields(border, item, "line", "width pass segments closed_reason shore")
            lines[item] = _line(border["line"], item)
        return lines

    def _read_blocks(self):
        edges = [edge for line in self.edges.values() for edge in line]
        rings, outer_walks = face_rings(edges)

        def containing(point):
            return next((i for i, ring in enumerate(rings) if point_in_ring(point, ring) == 1), None)

        names = {}
        for item, block in self.blocks.items():
            _fields(block, item, "at height use", "parent kind seed protagonist kit ground_texture")
            at = _xy(block["at"], item)
            _need(not any(on_segment(at, a, b) for a, b in edges), item, "enclosure", "at lies on a line")
            face = containing(at)
            _need(face is not None, item, "enclosure", "at is outside all enclosed faces")
            _need(face not in names, item, "enclosure", f"same face as {names.get(face)}")
            names[face] = item
            _text(block["use"], item, "use")
            _int(block["height"], item, "height")
            _ref(block.get("kind", "land"), ("land", "water"), item, "kind")
            if "seed" in block:
                _int(block["seed"], item, "seed")
            if "protagonist" in block:
                _text(block["protagonist"], item, "protagonist")
            if "kit" in block:
                _text(block["kit"], item, "kit")
            if "ground_texture" in block:
                _text(block["ground_texture"], item, "ground_texture")
                _need(block.get("kind") != "water", item, "ground_texture", "requires a land face")
            if "parent" in block:
                _ref(block["parent"], self.blocks, item, "parent")
        _need(rings, "$", "enclosure", "no enclosed faces")
        face_names = [names.get(i, f"@{i + 1}") for i in range(len(rings))]
        faces = dict(zip(face_names, rings))

        def enclosing(ring):
            # The midpoint is on this walk's rim, but inside a containing face.
            index = containing(midpoint(ring[0], ring[1]))
            return None if index is None else face_names[index]

        left = {edge: name for name, ring in faces.items() for edge in pairwise(ring)}
        for ring in outer_walks:
            left.update(dict.fromkeys(pairwise(ring), enclosing(ring)))
        sides = {edge: (left[edge], left[edge[::-1]]) for edge in edges}

        # Unnamed root faces take the terrain of a named face on the same
        # road network of face adjacencies, since roads cannot change height or kind.
        adjacent = defaultdict(set)
        for road in self.roads:
            for edge in self.edges[road]:
                a, b = sides[edge]
                if a and b and a != b:
                    adjacent[a].add(b)
                    adjacent[b].add(a)
        named_faces = set(self.blocks)
        for item, ring in reversed(faces.items()):
            parent = enclosing(ring)
            if item in self.blocks:
                _need(self.blocks[item].get("parent", parent) == parent, item, "nesting",
                      f"expected containing block {parent}")
            elif parent is not None:
                spec = self.blocks[parent]
                self.blocks[item] = dict(use=spec["use"], height=spec["height"],
                                         kind=spec.get("kind", "land"))
                if "kit" in spec:
                    self.blocks[item]["kit"] = spec["kit"]
            else:
                named = min(_visit(adjacent, item) & named_faces, default=None)
                spec = self.blocks.get(named, {})
                self.blocks[item] = dict(use="未指定", height=spec.get("height", 0),
                                         kind=spec.get("kind", "land"))
            if parent is not None:
                self.blocks[item] = self.blocks[item] | {"parent": parent}
        return faces, sides

    def _read_borders(self):
        self.spans, self.lengths, self.base_pass, self.border_edges = {}, {}, {}, {}
        for item, border in self.borders.items():
            if "width" in border:
                _width(border["width"], item)
            if "closed_reason" in border:
                _text(border["closed_reason"], item, "closed_reason")
            edges = iter(self.edges[item])
            offset, arcs = 0, []
            for a, b in pairwise(self.lines[item]):
                # Measure from the original vertices so splitting cannot move a span.
                while True:
                    edge = next(edges)
                    left, right = self.sides[edge]
                    _need(left != right, item, "enclosure", "border does not separate faces")
                    start, end = (offset + math.dist(a, p) for p in edge)
                    arcs.append((edge, start, end))
                    if edge[1] == b:
                        break
                offset = end
            self.lengths[item], self.border_edges[item] = offset, arcs
            self.spans[item] = _spans(border, item, offset, self._named_ramp)
            if "shore" in border:
                _ref(border["shore"], ("quay",), item, "shore")
                _need("pass" not in border and not self.spans[item], item, "shore",
                      "a quay closes the land/water crossing")
                _need(all(l and r and {self.medium(l), self.medium(r)} == {LAND, WATER}
                          for edge, _, _ in arcs for l, r in (self.sides[edge],)),
                      item, "shore", "a quay must separate land from water")
                self.base_pass[item] = frozenset()
            if "pass" in border:
                self.base_pass[item] = _pass(border["pass"], item)
            self.base_pass.update({sid: span[2] for sid, span in self.spans[item].items()})
        self.base_pass.update(dict.fromkeys(self.roads, LAND))

    def _named_ramp(self, spec, name):
        border = name.split(".", 1)[0]
        for end in ("from", "to"):
            _ref(spec[end], self.points, name, end)
        toe, crest = (self.points[spec[end]] for end in ("from", "to"))
        a, b = tuple(toe["at"]), tuple(crest["at"])
        low, high = toe["block"], crest["block"]
        _need(self.medium(low) == self.medium(high) == LAND
              and self.blocks[low]["height"] < self.blocks[high]["height"], name, "ramp",
              "from must be on lower land and to on higher land")
        allowed = _pass(spec["pass"], name)
        _need(allowed in ({"foot"}, LAND), name, "ramp",
              "choose foot alone or foot, vehicle and amphibian together")
        hits = {}
        for edge, start, _ in self.border_edges[border]:
            for p in _meet(a, b, *edge):
                hits.setdefault(p, set()).update(self.sides[edge])
        _need(len(hits) == 1 and next(iter(hits.values())) >= {low, high}, name, "ramp",
              f"{spec['from']} to {spec['to']} must cross this cliff once between those blocks")
        point = next(iter(hits))
        for edge, start, _ in self.border_edges[border]:
            if on_segment(point, *edge):
                center = start + math.dist(edge[0], point)
                break
        width = FOOT_RAMP_WIDTH if allowed == {"foot"} else STREET_RAMP_WIDTH
        return center - width / 2, center + width / 2

    def _read_points(self):
        for item, point in self.points.items():
            _fields(point, item, "block at", "use")
            if "use" in point:
                _text(point["use"], item, "use")
            _ref(point["block"], self.blocks, item, "block")
            at = _xy(point["at"], item)
            _need(self._face(at) == point["block"], item, "point",
                  f"point must be in the interior of {point['block']}")

    def _face(self, point):
        for name, ring in self.rings.items():
            location = point_in_ring(point, ring)
            if location >= 0:
                return name if location else None
        return None

    def medium(self, block):
        return WATER if self.blocks[block].get("kind") == "water" else LAND

    def _read_states(self):
        self.state_pass, self.state_heights, self.playable = {}, {}, {}
        targets = set(self.borders) | self.base_pass.keys()
        for item, state in (("base", {}), *self.states.items()):
            _fields(state, item, optional="pass heights playable")
            passes, heights = state.get("pass", {}), state.get("heights", {})
            for field, mapping in (("pass", passes), ("heights", heights)):
                _need(isinstance(mapping, dict), item, "shape", f"{field} needs an object")
            self.state_pass[item] = self.base_pass | {
                name: self._override_pass(item, name, value, targets)
                for name, value in passes.items()
            }
            self.state_heights[item] = {name: block["height"] for name, block in self.blocks.items()}
            for name, height in heights.items():
                _ref(name, self.blocks, item, "heights")
                _need(self.medium(name) == WATER, item, "heights", f"{name} is not water")
                _int(height, item, "height")
                self.state_heights[item][name] = height
            selected = state.get("playable", list(self.blocks))
            _list(selected, item, "playable")
            for name in selected:
                _ref(name, self.blocks, item, "playable")
            self.playable[item] = frozenset(selected)

    def _override_pass(self, item, name, value, targets):
        _ref(name, targets, item, "pass")
        return _pass(value, f"{item}.{name}", LAND if name in self.roads else KINDS)

    def _read_relations(self):
        endpoints = self.blocks.keys() | self.points.keys()
        schemas = {
            "通不通": ("from to who", "only_via reachable without"),
            "谁先到": ("a b to who min_lead", ""),
            "罩住": ("point road by fraction", ""),
            "绕多远": ("from to via who max_extra", ""),
            "看得见": ("from to visible", ""),
            "放得下": ("point side", ""),
        }
        references = {"from": endpoints, "to": endpoints, "a": endpoints, "b": endpoints,
                      "only_via": self.via_ids, "via": self.via_ids, "without": self.via_ids,
                      "point": self.points, "road": self.roads,
                      "who": KINDS, "state": self.state_pass, "by": ("range", "vision")}
        for item, rel in self.relations.items():
            _need(isinstance(rel, dict), item, "shape", "expected a relation object")
            _ref(rel.get("type"), schemas, item, "type")
            required, optional = schemas[rel["type"]]
            _fields(rel, item, "type " + required, "state " + optional)
            for field, choices in references.items():
                if field in rel:
                    _ref(rel[field], choices, item, field)
            for field in ("reachable", "visible"):
                if field in rel:
                    _need(type(rel[field]) is bool, item, "relation", f"{field} must be boolean")
            for field in ("min_lead", "max_extra", "fraction", "side"):
                if field in rel:
                    _number(rel[field], item, field)
            if "fraction" in rel:
                _need(rel["fraction"] <= 1, item, "relation", "fraction must be between 0 and 1")
            if "side" in rel:
                _need(rel["side"] > 0, item, "relation", "side must be positive")
            if "only_via" in rel:
                _need(rel.get("reachable", True), item, "relation", "only_via requires a path")

    def _read_patches(self):
        slots = set()
        for item, patch in self.patches.items():
            _need(isinstance(patch, dict), item, "shape", "expected a patch object")
            op = patch.get("op")
            params = {"move": "at", "delete": "", "replace": "with"}
            _ref(op, params, item, "op")
            _fields(patch, item, "op slot " + params[op])
            slot = patch["slot"]
            _need(isinstance(slot, str) and re.fullmatch(rf"{ID}\.{ID}\.{ID}", slot),
                  item, "slot", "expected block.kind.slot")
            _ref(slot.split(".")[0], self.blocks, item, "slot block")
            _need(slot not in slots, item, "slot", f"repeated patch for {slot}")
            slots.add(slot)
            if op == "move":
                _xy(patch["at"], item)
            if op == "replace":
                _text(patch["with"], item, "with")

    def block_seed(self, block):
        _ref(block, self.blocks, str(block), "block")
        spec = self.blocks[block]
        if "seed" in spec:
            return spec["seed"]
        key = f"{self.data.get('seed', 0)}:{block}".encode("utf-8")
        return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")

    def _index_roads(self):
        self.pieces, self.junctions = [], defaultdict(list)
        neighbors = defaultdict(set)
        for name in self.roads:
            for edge in self.edges[name]:
                owners = frozenset(filter(None, self.sides[edge]))
                _need(owners, name, "road", "road leaves the mapped blocks")
                piece = len(self.pieces)
                self.pieces.append((name, owners))
                for point in edge:
                    self.junctions[point].append(piece)
        self.contacts = defaultdict(list)
        for border, edges in self.border_edges.items():
            for edge, start, end in edges:
                left, right = self.sides[edge]
                for point, arc in zip(edge, (start, end)):
                    if point in self.junctions:
                        self.contacts[point].append((border, self._span_at(border, arc), left, right))
        for item, road in self.roads.items():
            first, last = self.lines[item][0], self.lines[item][-1]
            for end, point in (("start", first), ("end", last)):
                _need(len(self.junctions[point]) > 1 or point in self.contacts
                      or end in road.get("ends", []),
                      item, "dangling", f"{end} of road at {point} is unconnected")
        for pieces in self.junctions.values():
            names = {self.pieces[piece][0] for piece in pieces}
            for name in names:
                neighbors[name].update(names - {name})
        if self.roads:
            first = next(iter(self.roads))
            disconnected = self.roads.keys() - _visit(neighbors, first)
            _need(not disconnected, min(disconnected, default=first), "road_network",
                  f"road network is disconnected from {first}")

        for state, passes in self.state_pass.items():
            self._check_road_state(state, passes)
        self._check_cliffs()

    def _span_at(self, border, arc):
        for item, (start, end, _) in self.spans[border].items():
            if start <= arc < end or arc == end == self.lengths[border]:
                return item
        return border

    def _check_road_state(self, state, passes):
        for point, borders in self.contacts.items():
            for road in sorted({self.pieces[i][0] for i in self.junctions[point]}):
                if not passes[road]:
                    continue
                for _, opening, _, _ in borders:
                    _need(passes.get(opening, LAND), road, "road_no_pass",
                          f"meets closed {opening} in state {state}")
        heights = self.state_heights[state]
        for road, owners in self.pieces:
            if len(owners) == 2 and passes[road]:
                left, right = sorted(owners)
                _need(heights[left] == heights[right] and self.medium(left) == self.medium(right),
                      road, "sides", f"road sides must have equal height and kind in state {state}")

    def _crossings(self, border):
        """Face pairs and passage IDs for each positive-length border interval."""
        for _, _, left, right, item in self.border_sections(border):
            yield left, right, item

    def border_sections(self, border):
        """Oriented endpoints, face pair, and passage ID of each border section."""
        def at(a, b, start, end, offset):
            t = (offset - start) / (end - start)
            return tuple(float(p + (q - p) * t) for p, q in zip(a, b))

        for edge, start, end in self.border_edges[border]:
            left, right = self.sides[edge]
            a, b = map(lambda p: tuple(map(float, p)), edge)
            cursor = start
            for item, (lo, hi, _) in self.spans[border].items():
                lo, hi = max(start, lo), min(end, hi)
                if lo < hi:
                    if cursor < lo:
                        yield at(a, b, start, end, cursor), at(a, b, start, end, lo), left, right, border
                    yield at(a, b, start, end, lo), at(a, b, start, end, hi), left, right, item
                    cursor = hi
            if cursor < end:
                yield at(a, b, start, end, cursor), b, left, right, border

    def _road_links(self):
        for point, pieces in self.junctions.items():
            for a, b in combinations(pieces, 2):
                _, sides_a = self.pieces[a]
                _, sides_b = self.pieces[b]
                for face in sorted(sides_a & sides_b):
                    yield a, b, face, face, None, None
                for border, opening, left, right in self.contacts.get(point, ()):
                    if left in sides_a and right in sides_b:
                        yield a, b, left, right, border, opening
                    if right in sides_a and left in sides_b:
                        yield a, b, right, left, border, opening

    def _check_cliffs(self):
        road_passages = {
            (border, frozenset((left, right)))
            for a, b, left, right, border, opening in self._road_links()
            if border and self.base_pass.get(opening, LAND)
            & self.base_pass[self.pieces[a][0]] & self.base_pass[self.pieces[b][0]]
        }
        heights = self.state_heights["base"]
        for item, border in self.borders.items():
            passages = defaultdict(set)
            for left, right, opening in self._crossings(item):
                if left and right and heights[left] != heights[right]:
                    passages[frozenset((left, right))].add(opening)
            for pair, openings in passages.items():
                left, right = sorted(pair)
                kinds = self.medium(left) & self.medium(right)
                _need(border.get("closed_reason") or (item, pair) in road_passages or
                      any(kinds & self.base_pass.get(name, frozenset()) for name in openings),
                      item, "closed_cliff", f"{left}/{right} needs an opening or closed_reason")

    def _graph(self, who, state, without):
        faces = self.playable[state] - without
        passes = self.state_pass[state]
        graph = defaultdict(set)

        def link(a, b):
            graph[a].add(b)
            graph[b].add(a)

        for face in faces:
            if who in self.medium(face):
                graph[face] = set()
        for border in self.borders:
            if border not in without:
                for left, right, item in self._crossings(border):
                    if left in graph and right in graph and item not in without and who in passes.get(item, ()):
                        link(left, right)

        for i, (road, owners) in enumerate(self.pieces):
            if road not in without and who in passes[road] and owners & faces:
                graph[i] = set()
                for face in owners:
                    if face in graph:
                        link(i, face)
        for a, b, left, right, border, opening in self._road_links():
            if a in graph and b in graph and left in faces and right in faces:
                if border is None or (border not in without and opening not in without and who in passes.get(opening, LAND)):
                    link(a, b)
        return graph

    def reachable(self, start, end, who, *, state="base", without=None):
        """Check graph connectivity between block or point IDs, optionally cutting one ID."""
        endpoints = self.blocks.keys() | self.points.keys()
        _ref(start, endpoints, str(start), "start")
        _ref(end, endpoints, str(end), "end")
        _ref(who, KINDS, str(start), "who")
        _ref(state, self.state_pass, str(start), "state")
        if without is not None:
            _ref(without, self.via_ids, str(start), "without")
        return self._connected(start, end, who, state, {without} - {None})

    def _connected(self, start, end, who, state, without):
        graph = self._graph(who, state, without)
        a = self.points[start]["block"] if start in self.points else start
        b = self.points[end]["block"] if end in self.points else end
        return a in graph and b in _visit(graph, a)

    def check_relations(self):
        """Return the result of each declared relation, keyed by its design ID."""
        results = {}
        for item, rel in self.relations.items():
            if rel["type"] != "通不通":
                results[item] = "needs the grid"
                continue
            args = rel["from"], rel["to"], rel["who"]
            state = rel.get("state", "base")
            ok = self.reachable(*args, state=state, without=rel.get("without")) == rel.get("reachable", True)
            if ok and "only_via" in rel:
                ok = not self._connected(*args, state, {rel.get("without"), rel["only_via"]} - {None})
            results[item] = "pass" if ok else "fail"
        return results


class _Pairs(list):
    """Keep source keys until their full JSON path is known."""


def _unique_keys(value, path="$"):
    if isinstance(value, _Pairs):
        result = {}
        for key, child in value:
            field = f"{path}.{key}"
            _need(key not in result, field, "duplicate", "repeated JSON key")
            result[key] = _unique_keys(child, field)
        return result
    if isinstance(value, list):
        return [_unique_keys(child, f"{path}[{idx}]") for idx, child in enumerate(value)]
    return value


def load(path):
    """Read a UTF-8 JSON design and raise DesignError on the first structural error."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_Pairs)
    except (OSError, UnicodeError, ValueError) as exc:
        raise DesignError("$", "json", str(exc)) from exc
    return Design(_unique_keys(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("design")
    try:
        design = load(parser.parse_args().design)
    except DesignError as exc:
        parser.exit(1, f"{exc}\n")
    results = design.check_relations()
    print(json.dumps({"structure": "pass", "relations": results}, ensure_ascii=False))
    return int("fail" in results.values())


if __name__ == "__main__":
    raise SystemExit(main())
