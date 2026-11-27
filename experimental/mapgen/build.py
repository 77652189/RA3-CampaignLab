"""Expand and export a map from its design and original asset library."""

from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path

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
    scenery: tuple[terrain.Piece, ...]
    atmosphere: dict | None = None
    footprints: tuple[buildings.Footprint, ...] = ()
    scenery_slots: dict[str, terrain.Piece] = field(default_factory=dict)
    level: str = 'full'
    has_road_kit: bool = False
    ore: dict = field(default_factory=dict)  # node ID -> (pad ID, field, native placement)

    @property
    def border_index(self):
        """Border to activate on mission start; zero leaves the full container active."""
        return len(self.frame.map_borders(CONTAINER[2])) - 1 if self.frame is not None else 0

    def check_relations(self):
        if self.sketch is None:
            return {}
        return checks.evaluate(self.sketch, self.ground, self.roadbed, self.layout, CONTAINER[2], self.frame,
                               self.footprints, sketch_only=self.level == 'sketch', has_road_kit=self.has_road_kit)

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
            yield roads.Placement(piece.template, piece.x, piece.y, piece.angle)
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
          level='full'):
    """Expand a v2 design or terrain-only plan against the asset library.

    Design faces define the playable ground and supply the grade at a dry
    rectangular frame. Blocks can override the default kit for their surfaces, buildings
    and scenery. Road_kit supplies model roads; fronts gives measured civilian
    front angles in radians. Sketch stops at terrain, layout adds roads, buildings
    and flanks, and full adds surface paint, dressing and mood.
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
            flanks = tuple(dressing.footpath_flanks(sketch, assets))
            scenery = tuple(prop for _, prop in flanks)
        footprints = assets.occupied((*native, *scenery))
        if level != 'sketch':
            obstacles = tuple(s for obj in footprints for s in obj.placement + obj.collision)
            layout = buildings.BuildingPlanner(sketch, ground, catalogue, kits, fronts or {}, sage, border,
                                               obstacles).lock()
            dressing.check_flanks(sketch, roadbed, layout, flanks, assets)
    if level == 'full':
        ground = paint.paint(plan, catalogue, ground, roadbed)
    if sketch is not None:
        # Roads and paint see the real backdrop before the frame closes it to movement.
        frame = terrain.design_frame(sketch, ground, background_count, border)
        ground = frame.close(ground)
        if level == 'full':
            dressed = dressing.expand(sketch, ground, roadbed, layout, catalogue, kits, sage, border, frame,
                                       assets=assets, native=footprints, flanks=flanks)
            checks.check_dressing_routes(sketch, ground, roadbed, layout, border, frame,
                                         footprints, dressed.footprints)
            ground, scenery, footprints, slots = dressed.ground, dressed.pieces, dressed.footprints, dressed.slots
    return MapBuild(plan, ground, roadbed, layout, sketch, frame, scenery, atmosphere, footprints, slots,
                    level, road_kit is not None, ore)
