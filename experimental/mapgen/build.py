"""Expand and export a map from its design and original asset library."""

from copy import deepcopy
from dataclasses import dataclass, field, replace
import json
from pathlib import Path
from random import Random

import numpy as np

from experimental.mapgen import buildings, checks, design, dressing, library, paint, roads, terrain
from experimental.mapgen.campaign_writer import CONTAINER, MapFile, labpaths, mapterrain, newmap


@dataclass(frozen=True)
class MapBuild:
    plan: terrain.TerrainPlan
    ground: terrain.Ground
    roadbed: roads.Roadbed | None
    layout: buildings.Layout
    sketch: design.Design | None
    frame: terrain.DesignFrame | None
    scenery: tuple[terrain.Piece | roads.Placement, ...]
    atmosphere: dict | None = None
    footprints: tuple[buildings.Footprint, ...] = ()
    scenery_slots: dict[str, terrain.Piece] = field(default_factory=dict)
    level: str = 'full'
    has_road_kit: bool = False
    ore: dict = field(default_factory=dict)  # node ID -> (pad ID, field, native placement)
    generated: dict = field(default_factory=dict)

    @property
    def border_index(self):
        """Border to activate on mission start; zero leaves the full container active."""
        return len(self.frame.map_borders(CONTAINER[2])) - 1 if self.frame is not None else 0

    def check_relations(self):
        if self.sketch is None:
            return {}
        answers = checks.evaluate(self.sketch, self.ground, self.roadbed, self.layout, CONTAINER[2], self.frame,
                               self.footprints, sketch_only=self.level == 'sketch', has_road_kit=self.has_road_kit)
        return answers | checks.child_contents(self.plan, self.ground, self.layout, self.scenery,
                                                self.sketch.child_specs.keys() | self.generated.keys(),
                                                self.level, CONTAINER[2])

    def require_full(self):
        if self.level != 'full':
            raise ValueError(f'Native map export requires a full build (got {self.level})')

    def placements(self):
        if self.roadbed is not None:
            yield from self.roadbed.placements
        for piece in self.ground.pieces:
            yield roads.Placement(piece.template, piece.x, piece.y, piece.angle, z=piece.z)
        for _, group in self.layout.blocks:
            for piece in group:
                yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)
        for piece in self.scenery:
            yield piece if isinstance(piece, roads.Placement) else roads.Placement(
                piece.template, piece.x, piece.y, piece.angle)
        for _, _, placement in self.ore.values():
            yield placement

    def apply_terrain(self, m):
        """Fill the ground and atmosphere for the shared game/editor map."""
        self.require_full()
        if self.ground.errors:
            raise ValueError("\n".join(self.ground.errors))
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
        self.require_full()
        return m.map_file(), m.editor_file(), self.layout.to_bytes()

    def write(self, container, stem):
        """Fill a prepared map container and write both formats and the lock."""
        self.require_full()
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
            objects.append(newmap.object_node(m, {}, piece.flags or 0, piece.template, piece.x, piece.y,
                                             z=piece.z, angle=piece.angle, originalOwner=f'{owner}/team{owner}',
                                             uniqueID=f'{piece.template} {len(objects)}'))
        answers = self.check_relations()
        for suffix, data in zip(('game.map', 'editor.map', 'locked.json'), self.outputs(m), strict=True):
            Path(f'{stem}-{suffix}').write_bytes(data)
        if self.sketch is not None:
            checks.draw_failures(self.sketch, answers, f'{stem}-relations.svg')
            rows = ['# 地图关系', '']
            for name, answer in answers.items():
                result = {'pass': '🟢 通过', 'fail': '🔴 未通过', 'pending': '🟡 待展开'}[answer.status]
                rows.append(f'- {result} · `{name}` · {answer.sentence}')
                if answer.decision:
                    rows.append(f'  - {answer.decision}')
            if self.ground.issues:
                rows.extend(['', '## 地形提示', '', *(f'- {issue}' for issue in self.ground.issues)])
            Path(f'{stem}-checks.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')


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
    return deepcopy(matches[0]['atmosphere'])


def _ore(sketch):
    fields = sketch.mission.get('ore', {})
    if not fields:
        return {}
    from experimental.cnv import build as cnv  # noqa: F401 (initialize the campaign imports)
    import resources

    points = {name: p['at'] for name, p in sketch.points.items()} | sketch.mission.get('points', {})
    nodes = {}
    for name, spec in fields.items():
        pad, base = spec['pad'], spec.get('base', '')
        field = resources.Field(name, *points[pad], spec['facing'], twin=0, base=base,
                                owner='p1' if base else '', build=resources.PAD)
        obj, = resources.objects((field,))
        nodes[spec['node']] = (pad, field, roads.Placement(obj.template, obj.x, obj.y, obj.angle,
                                                          flags=obj.flags, side=obj.side))
    return nodes


def build(design_file, library_file, plan=terrain.TerrainPlan(), *, kit=None, road_kit=None, fronts=None,
          level='full', dump_children=None):
    """Expand a v2 design or terrain-only plan against the asset library.

    Design faces define the playable ground and supply the grade at a dry
    rectangular frame. Blocks can override the default kit for their surfaces, buildings
    and scenery. Road_kit supplies model roads; fronts gives measured civilian
    front angles in radians. Sketch stops at terrain, layout adds roads and buildings,
    and full adds surface paint, dressing and mood. Dump_children exports generated block entries.
    """
    if level not in ('sketch', 'layout', 'full'):
        raise ValueError(f'Unknown map build level: {level!r}')
    catalogue = library.load_library(library_file)
    sketch = design.load(design_file) if design_file is not None else None
    atmosphere = retail_atmosphere(sketch.mood, catalogue) if sketch is not None and level == 'full' else None
    background_count = len(plan.blocks)
    border = CONTAINER[2]
    if sketch is not None:
        kit = kit or sketch.commitments.get('kit')
        road_kit = road_kit or sketch.commitments.get('road_kit')
        if 'ground_texture' in sketch.commitments:
            plan = replace(plan, ground=sketch.commitments['ground_texture'])
        if kit is None:
            raise ValueError('building from a design requires a civilian kit')
        if level != 'sketch' and road_kit is None:
            road = next(roads.unpainted_roads(sketch), None)
            if road is not None:
                raise design.DesignError(road, 'road_kit', 'supply a model kit or paint the entire dry road')
        plan = terrain.from_design(sketch, plan, kit)
        if not background_count:
            expanded = terrain.frame_apron(sketch, plan, CONTAINER)
            background_count = len(expanded.blocks) - len(plan.blocks)
            plan = expanded
    ground = terrain.expand(plan, catalogue, *CONTAINER)
    layout, roadbed = buildings.Layout(()), None
    frame, scenery, footprints, slots = None, (), (), {}
    ore = {}
    generated, children, parking = {}, {}, {}
    if sketch is not None:
        sage = Path(labpaths.SDK3) / 'SageXML'
        assets = dressing.Assets(catalogue, sage)
        ore = _ore(sketch)
        native = (*ground.pieces, *(placement for _, _, placement in ore.values()))
        if level != 'sketch':
            if road_kit is not None:
                roadbed = roads.expand(sketch, ground, border, road_kit)
                # The road markers and bridge generators are already represented by Roadbed.
                native += tuple(p for p in roadbed.placements if p.side != 'road' and p.template != roads.BRIDGE_TEMPLATE)
        kits = {name: spec.get('kit', kit) for name, spec in sketch.blocks.items()}
        footprints = assets.occupied(native)
        frame = terrain.design_frame(sketch, ground, background_count, border)
        occupied = clear = None
        if level != 'sketch':
            obstacles = tuple(s for obj in footprints for s in obj.placement + obj.collision)
            planner = buildings.BuildingPlanner(sketch, ground, catalogue, kits, fronts or {}, sage, border,
                                                obstacles)
            groups = {name: (planner.protagonist(name),) for name, spec in sorted(sketch.blocks.items())
                      if 'protagonist' in spec}
            y, x = (np.indices(ground.raw.shape) - border) * terrain.CELL
            clear = np.zeros_like(ground.blocked)
            for rel in sketch.relations.values():
                if rel.get('purpose'):
                    px, py = sketch.points[rel['point']]['at']
                    half = rel['side'] / 2 + terrain.CELL / 2
                    clear |= (abs(x - px) <= half) & (abs(y - py) <= half)
            occupied = clear.copy()
            anchor_shapes = tuple(s for b, in groups.values() for s in b.placement + b.collision)
            for shape in anchor_shapes:
                occupied |= shape.contains(x, y, pad=terrain.CELL / 2)
        if level != 'sketch' or sketch.child_specs:
            plan, ground, children, generated = roads.cut_blocks(
                sketch, ground, roadbed, plan, catalogue, kits, border, occupied, clear)
        if level != 'sketch':
            planner.obstacles += anchor_shapes
            updated = list(plan.blocks)
            for name, (owner, frontage) in children.items():
                spec = sketch.blocks[name]
                mask = (ground.owners == owner) & ~clear
                groups[name] = planner.contents(name, mask, frontage)
                if spec['use'] == 'parking':
                    recipe = library.child_recipe(catalogue, kits[name], 'parking')
                    parking[name] = dressing.parking_bays(recipe, sage, mask, border, frontage)
                if name in generated and ((spec['use'] in library.BUILDING_USES and not groups[name])
                                          or (spec['use'] == 'parking' and not parking[name])):
                    parent = spec['parent']
                    style = library.child_style(catalogue, kits[parent])
                    mix = style['mix_by_use'][library.TOWN_USES[sketch.blocks[parent]['use']]]
                    choices = {use: count for use, count in mix.items()
                               if use not in library.BUILDING_USES | {'parking'}}
                    if not choices:
                        raise design.DesignError(name, 'contents', 'no fitting use in the measured mix')
                    fallback = library.weighted(Random(sketch.block_seed(name)), choices)
                    spec['use'] = generated[name]['use'] = fallback
                    updated[owner] = replace(updated[owner], surface=replace(updated[owner].surface, use=fallback))
            plan = replace(plan, blocks=tuple(updated))
            layout = buildings.Layout(tuple((name, groups.get(name, ())) for name in sorted(sketch.blocks)))
    if level == 'full':
        ground = paint.paint(plan, catalogue, ground, roadbed)
    if sketch is not None:
        # Roads and paint see the real backdrop before the frame closes it to movement.
        ground = frame.close(ground)
        if level == 'full':
            dressed = dressing.expand(sketch, ground, roadbed, layout, catalogue, kits, sage, border, frame,
                                       assets=assets, native=footprints, children=children)
            checks.check_dressing_routes(sketch, ground, roadbed, layout, border, frame,
                                         footprints, dressed.footprints)
            ground, footprints, slots = dressed.ground, dressed.footprints, dressed.slots
            scenery = (*dressed.pieces, *(mark for marks in parking.values() for mark in marks))
    built = MapBuild(plan, ground, roadbed, layout, sketch, frame, scenery, atmosphere, footprints, slots,
                    level, road_kit is not None, ore, generated)
    if dump_children is not None:
        Path(dump_children).write_text(json.dumps(generated, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return built
