"""Expand and export a map from its design and original asset library."""

from dataclasses import dataclass, replace
import json
from pathlib import Path

import numpy as np

from experimental.mapgen import buildings, design, paint, roads, terrain
from experimental.mapgen.campaign_writer import CONTAINER, MapFile, labpaths, newmap


@dataclass(frozen=True)
class MapBuild:
    plan: terrain.TerrainPlan
    ground: terrain.Ground
    roadbed: roads.Roadbed | None
    layout: buildings.Layout

    def placements(self):
        if self.roadbed is not None:
            yield from self.roadbed.placements
        for piece in self.ground.pieces:
            yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)
        for _, group in self.layout.blocks:
            for piece in group:
                yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)

    def apply_terrain(self, m):
        return terrain.apply(m, self.plan, self.ground)

    def outputs(self, m):
        """Encode a map filled by this build, including any campaign content."""
        return m.map_file(), m.editor_file(), self.layout.to_bytes()

    def write(self, container, stem):
        """Fill a prepared map container and write both formats and the lock."""
        m = MapFile(Path(container).read_bytes())
        self.apply_terrain(m)
        objects = next(node for _, node in m.walk() if node.name == 'ObjectsList').kids
        for piece in self.placements():
            owner = 'PlyrNeutral' if piece.side == 'neutral' else 'PlyrCivilian'
            objects.append(newmap.object_node(m, {}, piece.flags, piece.template, piece.x, piece.y,
                                             angle=piece.angle, originalOwner=f'{owner}/team{owner}',
                                             uniqueID=f'{piece.template} {len(objects)}'))
        for suffix, data in zip(('game.map', 'editor.map', 'locked.json'), self.outputs(m), strict=True):
            Path(f'{stem}-{suffix}').write_bytes(data)


def build(design_file, library_file, plan, *, kit=None, road_kit=None, fronts=None):
    """Expand using the seed in the design file and terrain features in the plan.

    A terrain-only plan has no design file. With a design, the plan's blocks
    supply the backdrop and the design faces define the playable ground. A
    design uses kit for its surfaces and buildings, and road_kit for model
    roads. Fronts gives measured civilian front angles in radians.
    """
    library = json.loads(Path(library_file).read_text(encoding='utf-8'))
    sketch = design.load(design_file) if design_file is not None else None
    background_count = len(plan.blocks)
    if sketch is not None:
        if kit is None:
            raise ValueError('building from a design requires a civilian kit')
        blocks = tuple(
            terrain.Block(tuple((float(x), float(y)) for x, y in sketch.rings[name][:-1]), spec['height'],
                          surface=terrain.Surface(name, spec['use'], kit, sketch.block_seed(name)))
            for name, spec in sketch.blocks.items() if spec.get('kind') != 'water'
        )
        plan = replace(plan, blocks=(*plan.blocks, *blocks))
    ground = terrain.expand(plan, library, *CONTAINER)
    layout, roadbed = buildings.Layout(()), None
    if sketch is not None:
        border = CONTAINER[2]
        if road_kit is not None:
            roadbed = roads.expand(sketch, ground, border, road_kit)
        sage = Path(labpaths.SDK3) / 'SageXML'
        layout = buildings.BuildingPlanner(sketch, ground, library, dict.fromkeys(sketch.blocks, kit),
                                           fronts or {}, sage, border).lock()
    ground = paint.paint(plan, library, ground, roadbed)
    if sketch is not None:
        # Backdrop can support a road at the frame, but is outside the design's
        # route graph. Close it after road fitting and painting so they still
        # see the actual grade and material at the end of the road.
        inside = ground.owners >= background_count
        water_faces = [name for name, spec in sketch.blocks.items() if spec.get('kind') == 'water']
        if water_faces:
            y, x = (np.indices(ground.raw.shape) - CONTAINER[2]) * terrain.CELL
            for name in water_faces:
                ring = tuple((float(a), float(b)) for a, b in sketch.rings[name][:-1])
                inside |= terrain.polygon_mask(ring, x, y)
        ground = replace(ground, blocked=ground.blocked | ~inside)
    return MapBuild(plan, ground, roadbed, layout)
