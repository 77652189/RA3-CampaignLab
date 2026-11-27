"""Expand and export a map from its design and original asset library."""

from dataclasses import dataclass
import json
from pathlib import Path

from experimental.mapgen import buildings, checks, design, dressing, paint, roads, terrain
from experimental.mapgen.campaign_writer import CONTAINER, MapFile, labpaths, mapterrain, newmap


@dataclass(frozen=True)
class MapBuild:
    plan: terrain.TerrainPlan
    ground: terrain.Ground
    roadbed: roads.Roadbed | None
    layout: buildings.Layout
    sketch: design.Design | None
    frame: terrain.DesignFrame | None
    scenery: tuple[terrain.Piece, ...]
    atmosphere: dict | None = None

    @property
    def border_index(self):
        """Border to activate on mission start; zero leaves the full container active."""
        return len(self.frame.map_borders(CONTAINER[2])) - 1 if self.frame is not None else 0

    def check_relations(self):
        if self.sketch is None:
            return {}
        return checks.evaluate(self.sketch, self.ground, self.roadbed, self.layout, CONTAINER[2], self.frame)

    def placements(self):
        if self.roadbed is not None:
            yield from self.roadbed.placements
        for piece in self.ground.pieces:
            yield roads.Placement(piece.template, piece.x, piece.y, piece.angle, z=piece.z)
        for _, group in self.layout.blocks:
            for piece in group:
                yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)
        for piece in self.scenery:
            yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)

    def apply_terrain(self, m):
        """Fill the ground and atmosphere for the shared game/editor map."""
        previews = terrain.apply(m, self.plan, self.ground)
        if self.frame is not None:
            hm = mapterrain.HeightMap(m)
            borders = self.frame.map_borders(hm.border)
            if hm.borders() != borders:
                hm.set_borders(borders)
                hm.store()
        if self.atmosphere is not None:
            newmap.apply_atmosphere(m, self.atmosphere)
        return previews

    def outputs(self, m):
        """Encode a map filled by this build, including any campaign content."""
        return m.map_file(), m.editor_file(), self.layout.to_bytes()

    def write(self, container, stem):
        """Fill a prepared map container and write both formats and the lock."""
        m = MapFile(Path(container).read_bytes())
        self.apply_terrain(m)
        if self.border_index:
            scripts = next(node for _, node in m.walk() if node.name == 'PlayerScriptsList')
            scripts.kids[2].kids.insert(0, m.new_script(
                'Map design border', [m.new_content('Condition', 'CONDITION_TRUE')],
                [m.new_content('ScriptAction', 'MAP_SWITCH_BORDER', self.border_index)]))
        objects = next(node for _, node in m.walk() if node.name == 'ObjectsList').kids
        for piece in self.placements():
            owner = 'PlyrNeutral' if piece.side == 'neutral' else 'PlyrCivilian'
            objects.append(newmap.object_node(m, {}, piece.flags, piece.template, piece.x, piece.y,
                                             z=piece.z, angle=piece.angle, originalOwner=f'{owner}/team{owner}',
                                             uniqueID=f'{piece.template} {len(objects)}'))
        for suffix, data in zip(('game.map', 'editor.map', 'locked.json'), self.outputs(m), strict=True):
            Path(f'{stem}-{suffix}').write_bytes(data)
        if self.sketch is not None and self.sketch.relations:
            checks.draw_failures(self.sketch, self.check_relations(), f'{stem}-relations.svg')


def retail_atmosphere(mood, library):
    """Resolve the catalogue's designer name or retail map ID and recorded time of day."""
    if mood is None:
        return None
    selector = mood.strip().casefold()
    matches = []
    for key, entry in library.get('retail_moods', {}).items():
        key = key.casefold()
        aliases = (entry['name'].casefold(), key, f"{key}@{entry['time_of_day']}",
                   f"{key}@{entry['time_label'].casefold()}")
        if selector in aliases:
            matches.append(entry)
    if len(matches) != 1:
        raise design.DesignError('$.commitments', 'mood',
                                 f'{mood!r}: expected one retail mood in the library, found {len(matches)}')
    return matches[0]['atmosphere']


def build(design_file, library_file, plan=terrain.TerrainPlan(), *, kit=None, road_kit=None, fronts=None):
    """Expand a v2 design, with an optional terrain plan for the surrounding context.

    A terrain-only plan has no design file. With a design, the plan's blocks
    supply the backdrop and the design faces define the playable ground. A
    Design blocks can override the default kit for their surfaces, buildings
    and scenery. Road_kit supplies model roads; fronts gives measured civilian
    front angles in radians.
    """
    library = json.loads(Path(library_file).read_text(encoding='utf-8'))
    sketch = design.load(design_file) if design_file is not None else None
    atmosphere = retail_atmosphere(sketch.mood, library) if sketch is not None else None
    background_count = len(plan.blocks)
    border = CONTAINER[2]
    if sketch is not None:
        if kit is None:
            raise ValueError('building from a design requires a civilian kit')
        plan = terrain.from_design(sketch, plan, kit)
    ground = terrain.expand(plan, library, *CONTAINER)
    layout, roadbed = buildings.Layout(()), None
    frame, scenery = None, ()
    if sketch is not None:
        if road_kit is not None:
            roadbed = roads.expand(sketch, ground, border, road_kit)
        sage = Path(labpaths.SDK3) / 'SageXML'
        kits = {name: spec.get('kit', kit) for name, spec in sketch.blocks.items()}
        layout = buildings.BuildingPlanner(sketch, ground, library, kits,
                                           fronts or {}, sage, border).lock()
    ground = paint.paint(plan, library, ground, roadbed)
    if sketch is not None:
        # Roads and paint see the real backdrop before the frame closes it to movement.
        frame = terrain.design_frame(sketch, ground, background_count, border)
        dressed = dressing.expand(sketch, frame.close(ground), roadbed, layout, library, kits, sage, border)
        ground, scenery = dressed.ground, dressed.pieces
    return MapBuild(plan, ground, roadbed, layout, sketch, frame, scenery, atmosphere)
