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


def _sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _on(p, a, b):
    return (_cross(_sub(p, a), _sub(b, a)) == 0
            and all(min(a[i], b[i]) <= p[i] <= max(a[i], b[i]) for i in (0, 1)))


def _along(p, a, b):
    axis = int(a[0] == b[0])
    return Fraction(p[axis] - a[axis], b[axis] - a[axis])


def _meet(a, b, c, d):
    """Return zero points, one contact, or both endpoints of an overlap."""
    if any(max(a[i], b[i]) < min(c[i], d[i]) or max(c[i], d[i]) < min(a[i], b[i])
           for i in (0, 1)):
        return ()
    ab, cd, ac = _sub(b, a), _sub(d, c), _sub(c, a)
    determinant = _cross(ab, cd)
    if not determinant:
        return tuple(sorted({p for p in (a, b, c, d) if _on(p, a, b) and _on(p, c, d)}))
    along_ab = _cross(ac, cd) / Fraction(determinant)
    along_cd = _cross(ac, ab) / Fraction(determinant)
    if 0 <= along_ab <= 1 and 0 <= along_cd <= 1:
        return ((a[0] + along_ab * ab[0], a[1] + along_ab * ab[1]),)
    return ()


def _area(ring):
    return sum(_cross(a, b) for a, b in pairwise(ring))


def _inside(p, ring):
    """Return 1 inside, 0 on the outline, and -1 outside."""
    inside = False
    for a, b in pairwise(ring):
        if _on(p, a, b):
            return 0
        if (a[1] > p[1]) != (b[1] > p[1]):
            left = _cross(_sub(b, a), _sub(p, a))
            inside ^= (left > 0) == (b[1] > a[1])
    return 1 if inside else -1


def _mid(a, b):
    return tuple((x + y) / Fraction(2) for x, y in zip(a, b))


def _line(raw, item):
    _list(raw, item, "line")
    line = tuple(_xy(p, item) for p in raw)
    _need(len(line) >= 2 and all(a != b for a, b in pairwise(line)),
          item, "line", "line needs at least one nonzero segment")
    return line


def _ring(refs, lines, item):
    _list(refs, item, "ring")
    ring, directed = [], []
    for ref in refs:
        _need(isinstance(ref, str), item, "reference", "ring expects line IDs")
        reverse = ref.startswith("-")
        name = ref.removeprefix("-")
        _ref(name, lines, item, "ring")
        line = lines[name][::-1] if reverse else lines[name]
        _need(not ring or ring[-1] == line[0], item, "enclosure", f"gap at {ref}")
        ring.extend(line if not ring else line[1:])
        directed.append((name, reverse))
    area = _area(ring)
    _need(len(ring) >= 4 and ring[0] == ring[-1] and area != 0, item,
          "enclosure", "ring must close and enclose an area")
    edges = list(pairwise(ring))
    for i, j in combinations(range(len(edges)), 2):
        contacts = _meet(*edges[i], *edges[j])
        adjacent = j == i + 1 or (i == 0 and j == len(edges) - 1)
        _need(len(contacts) == int(adjacent), item, "enclosure", "ring crosses or overlaps itself")
    # Index 0 is the left of the authored line, index 1 its right.
    return ring, [(name, reverse ^ (area < 0)) for name, reverse in directed]


def _check_nested(rings, parents, holes):
    for name, parent in parents.items():
        if parent is None:
            continue
        ring, outer = rings[name], rings[parent]
        _need(all(_inside(p, outer) == 1 for p in ring[:-1])
              and not any(_meet(*a, *b) for a in pairwise(ring) for b in pairwise(outer)),
              name, "nesting", f"child must lie strictly inside {parent}")
    for a, b in combinations(rings, 2):
        if parents[a] != parents[b]:
            continue
        for name, other in ((a, b), (b, a)):
            _need(not any(_inside(_mid(p, q), rings[other]) == 1 or
                          _inside(p, rings[other]) == 1 for p, q in pairwise(rings[name])),
                  name, "overlap", f"overlaps sibling {other}")
    for parent, boundary in holes.items():
        # Walk child/parent interfaces with the children on the left. An enclosed
        # island of parent ground would give a clockwise loop and a false graph shortcut.
        outgoing = {}
        for line in boundary:
            _need(line[0] not in outgoing, parent, "nesting", "child outlines pinch at a vertex")
            outgoing[line[0]] = line
        while outgoing:
            start = next(iter(outgoing))
            cursor, area = start, 0
            while cursor in outgoing:
                line = outgoing.pop(cursor)
                area += _area(line)
                cursor = line[-1]
                if cursor == start:
                    break
            _need(cursor == start and area > 0, parent, "nesting",
                  "children must leave a single connected parent interior")


def _spans(border, item, length):
    spans = {}
    raw = border.get("segments", {})
    _need(isinstance(raw, dict), item, "shape", "segments needs an object keyed by ID")
    for name, segment in sorted(raw.items()):
        sid = f"{item}.{name}"
        _id(name, sid)
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
        _fields(data, "$", "version blocks", "seed roads borders points states relations patches")
        _need(type(data["version"]) is int and data["version"] == 1,
              "$", "version", "expected format version 1")
        _int(data.get("seed", 0), "$", "seed")
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
        _need(self.blocks, "$", "blocks", "at least one block is required")
        self.lines = self._read_lines()
        self.rings, self.sides, self.depth = self._read_blocks()
        self._read_borders()
        self._read_points()
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
            _fields(border, item, "line sides", "width pass segments closed_reason")
            lines[item] = _line(border["line"], item)
        return lines

    def _read_blocks(self):
        rings, parents, depth = {}, {}, {}
        occupied = {line: [None, None] for line in self.lines}
        for item, block in self.blocks.items():
            _fields(block, item, "ring height use", "parent kind seed protagonist")
            _text(block["use"], item, "use")
            _int(block["height"], item, "height")
            _ref(block.get("kind", "land"), ("land", "water"), item, "kind")
            if "seed" in block:
                _int(block["seed"], item, "seed")
            if "protagonist" in block:
                _text(block["protagonist"], item, "protagonist")
            parent = block.get("parent")
            if "parent" in block:
                _ref(parent, self.blocks, item, "parent")
            parents[item] = parent
            rings[item], directed = _ring(block["ring"], self.lines, item)
            for line, side in directed:
                other = occupied[line][side]
                _need(other is None, item, "sides", f"{line} already has {other} on this side")
                occupied[line][side] = item
        for item in self.blocks:
            ancestors = {item}
            parent = parents[item]
            while parent is not None:
                _need(parent not in ancestors, item, "nesting", f"parent cycle through {parent}")
                ancestors.add(parent)
                parent = parents[parent]
            depth[item] = len(ancestors)

        holes = defaultdict(list)
        for name, sides in occupied.items():
            left, right = sides
            if left and right:
                _need(parents[left] == parents[right], name, "nesting",
                      f"{left} and {right} must share a parent")
            elif left or right:
                child = left or right
                parent = parents[child]
                sides[int(left is not None)] = parent
                if parent:
                    holes[parent].append(self.lines[name] if left else self.lines[name][::-1])
        _check_nested(rings, parents, holes)
        return rings, occupied, depth

    def _read_borders(self):
        self.spans, self.lengths, self.base_pass = {}, {}, {}
        for item, border in self.borders.items():
            sides = border["sides"]
            _list(sides, item, "sides", size=2)
            for side in sides:
                if side is not None:
                    _ref(side, self.blocks, item, "sides")
            _need(any(sides) and sides == self.sides[item], item, "sides",
                  f"expected left/right blocks {self.sides[item]}, got {sides}")
            if "width" in border:
                _width(border["width"], item)
            if "closed_reason" in border:
                _text(border["closed_reason"], item, "closed_reason")
            length = self.lengths[item] = sum(math.dist(a, b) for a, b in pairwise(self.lines[item]))
            self.spans[item] = _spans(border, item, length)
            if "pass" in border:
                self.base_pass[item] = _pass(border["pass"], item)
            self.base_pass.update({sid: span[2] for sid, span in self.spans[item].items()})
        self.base_pass.update(dict.fromkeys(self.roads, LAND))

    def _read_points(self):
        for item, point in self.points.items():
            _fields(point, item, "block at", "use")
            if "use" in point:
                _text(point["use"], item, "use")
            _ref(point["block"], self.blocks, item, "block")
            at = _xy(point["at"], item)
            _need(_inside(at, self.rings[point["block"]]) == 1 and
                  self._face(at, boundary=True) == point["block"], item, "point",
                  f"point must be in the interior of {point['block']}")

    def _face(self, point, *, boundary=False):
        candidates = (name for name, ring in self.rings.items()
                      if _inside(point, ring) >= (0 if boundary else 1))
        return max(candidates, key=self.depth.get, default=None)

    def _medium(self, block):
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
                _need(self._medium(name) == WATER, item, "heights", f"{name} is not water")
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
            "通不通": ("from to who", "only_via reachable"),
            "谁先到": ("a b to who min_lead", ""),
            "罩住": ("point road by fraction", ""),
            "绕多远": ("from to via who max_extra", ""),
            "看得见": ("from to visible", ""),
            "放得下": ("point side", ""),
        }
        references = {"from": endpoints, "to": endpoints, "a": endpoints, "b": endpoints,
                      "only_via": self.via_ids, "via": self.via_ids, "point": self.points, "road": self.roads,
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
        segments, splits = [], {}
        for name, line in self.lines.items():
            offset = 0
            for a, b in pairwise(line):
                if name in self.roads:
                    splits[len(segments)] = {a, b}
                segments.append((name, a, b, offset))
                offset += math.dist(a, b)
        road_contacts, border_contacts = defaultdict(set), defaultdict(dict)
        for i, j in combinations(range(len(segments)), 2):
            name, a, b, offset = segments[i]
            other, c, d, other_offset = segments[j]
            contacts = _meet(a, b, c, d)
            if not contacts:
                continue
            _need(len(contacts) == 1, name, "overlap", f"line overlaps {other}")
            point, = contacts
            if name != other and all(any(self.sides[n]) for n in (name, other)):
                _need(all(point in (self.lines[n][0], self.lines[n][-1]) for n in (name, other)),
                      name, "enclosure", f"split outlines at their junction with {other}")
            if i in splits:
                splits[i].add(point)
            if j in splits:
                splits[j].add(point)
            if (i in splits) != (j in splits):
                road, border, start, distance = ((name, other, c, other_offset) if i in splits
                                                 else (other, name, a, offset))
                road_contacts[point].add(road)
                border_contacts[point][border] = distance + math.dist((0, 0), _sub(point, start))

        self.pieces, self.junctions = [], defaultdict(list)
        neighbors = defaultdict(set)
        for i, points in splits.items():
            name, a, b, _ = segments[i]
            owners = frozenset(filter(None, self.sides[name]))
            ordered = sorted(points, key=lambda p: _along(p, a, b))
            for start, end in pairwise(ordered):
                face = None if owners else self._face(_mid(start, end))
                _need(owners or face is not None, name, "road", "road leaves the mapped blocks")
                piece = len(self.pieces)
                self.pieces.append((name, owners or frozenset((face,))))
                self.junctions[start].append(piece)
                self.junctions[end].append(piece)
        for item, road in self.roads.items():
            first, last = self.lines[item][0], self.lines[item][-1]
            for end, point in (("start", first), ("end", last)):
                _need(len(self.junctions[point]) > 1 or end in road.get("ends", []),
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

        self.contacts = {
            point: [(name, self._span_at(name, arc)) for name, arc in sorted(borders.items())]
            for point, borders in border_contacts.items()
        }
        for state, passes in self.state_pass.items():
            self._check_road_state(state, passes, road_contacts)
        self._check_cliffs()

    def _span_at(self, border, arc):
        for item, (start, end, _) in self.spans[border].items():
            if start <= arc < end or arc == end == self.lengths[border]:
                return item
        return border

    def _check_road_state(self, state, passes, road_contacts):
        for point, borders in self.contacts.items():
            for road in sorted(road_contacts[point]):
                if not passes[road]:
                    continue
                for _, opening in borders:
                    _need(passes.get(opening, LAND), road, "road_no_pass",
                          f"meets closed {opening} in state {state}")
        heights = self.state_heights[state]
        for road in self.roads:
            left, right = self.sides[road]
            if left and right and passes[road]:
                _need(heights[left] == heights[right] and self._medium(left) == self._medium(right),
                      road, "sides", f"road sides must have equal height and kind in state {state}")

    def _crossings(self, border):
        """IDs of positive-length passages, including uncovered parts of the border."""
        cursor, has_gap = 0, False
        for item, (start, end, _) in self.spans[border].items():
            has_gap |= start > cursor
            cursor = end
            yield item
        if has_gap or cursor < self.lengths[border]:
            yield border

    def _road_links(self):
        for point, pieces in self.junctions.items():
            for a, b in combinations(pieces, 2):
                _, sides_a = self.pieces[a]
                _, sides_b = self.pieces[b]
                for face in sorted(sides_a & sides_b):
                    yield a, b, face, face, None, None
                for border, opening in self.contacts.get(point, ()):
                    left, right = self.sides[border]
                    if left in sides_a and right in sides_b:
                        yield a, b, left, right, border, opening
                    if right in sides_a and left in sides_b:
                        yield a, b, right, left, border, opening

    def _check_cliffs(self):
        road_passages = {
            border for a, b, _, _, border, opening in self._road_links()
            if border and self.base_pass.get(opening, LAND)
            & self.base_pass[self.pieces[a][0]] & self.base_pass[self.pieces[b][0]]
        }
        heights = self.state_heights["base"]
        for item, border in self.borders.items():
            left, right = self.sides[item]
            if left and right and heights[left] != heights[right]:
                kinds = self._medium(left) & self._medium(right)
                _need(border.get("closed_reason") or item in road_passages or
                      any(kinds & self.base_pass.get(name, frozenset()) for name in self._crossings(item)),
                      item, "closed_cliff", "height change needs an opening or closed_reason")

    def _graph(self, who, state, without):
        faces = self.playable[state] - {without}
        passes = self.state_pass[state]
        graph = defaultdict(set)

        def link(a, b):
            graph[a].add(b)
            graph[b].add(a)

        for face in faces:
            if who in self._medium(face):
                graph[face] = set()
        for border in self.borders:
            left, right = self.sides[border]
            if border != without and left in graph and right in graph:
                if any(item != without and who in passes.get(item, ()) for item in self._crossings(border)):
                    link(left, right)

        for i, (road, owners) in enumerate(self.pieces):
            if road != without and who in passes[road] and owners & faces:
                graph[i] = set()
                for face in owners:
                    if face in graph:
                        link(i, face)
        for a, b, left, right, border, opening in self._road_links():
            if a in graph and b in graph and left in faces and right in faces:
                if border is None or (without not in (border, opening) and who in passes.get(opening, LAND)):
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
            ok = self.reachable(*args, state=state) == rel.get("reachable", True)
            if ok and "only_via" in rel:
                ok = not self.reachable(*args, state=state, without=rel["only_via"])
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
