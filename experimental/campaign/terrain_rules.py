"""Terrain rules for editing a map's ground (the shell line's terrain editor, ADR 0017): what a height edit must change
along with it, and how passability and "flat enough to build" follow from the heights. Pure functions on height
arrays, no map file; docs/engine/terrain.md says which of these the engine line read in the game's code (码), measured
on the bench (测) or only inferred (推断).

Units. Our map code keeps heights as `elevation / 16` (mapterrain.SCALE, platmap.TIER, STEEP, FLAT ...). The game turns
a HeightMapData elevation into a world height by * 0.0390625 (= / 25.6, 码), so one of our units is 0.625 world units
(16 / 25.6). The cell is 10 world units across (码). Numbers in the game's data (AllowedHeightVariation..., ranges,
geometry) are world units: convert with world() / ours() before comparing.
"""
import numpy as np

CELL = 10.0                         # world units per height-map cell (the game: vertex x = (i - border) * 10)
RAW_PER_OURS = 16.0                 # mapterrain.SCALE: our height = raw elevation / 16
RAW_PER_WORLD = 25.6                # the game: world height = raw elevation * 0.0390625
WORLD_PER_OURS = RAW_PER_OURS / RAW_PER_WORLD     # 0.625

STEEP = 9.0                         # ours per cell: steeper dry ground gets the impassable bit (platmap.STEEP, newmap)
BUILD_VARIATION = 3.0               # world: BuildSystemSettings.AllowedHeightVariationForBuildingPlacement (schema
                                    # default; retail's BuildSystemSettings.xml sets nothing, so 3.0 holds)

# BlendTileData's eight per-cell bit fields, in file order (v27; mapterrain.Tiles.set_bit's field index). Names by the
# layout other SAGE readers give version 27 and by what is set on retail maps (field 0 on steep dry ground, 4 on ~94 %,
# 5 on ~2 %): 推断, not read in the game's code. Only field 0 is written by our generators (fill 0, field 4 all on).
# Field 0 is all the game goes by for ground units (测, checks/engine_terrain.py walk, 2026-11-04): a wall rising 40
# per cell with the bit off, a tank and an infantryman walked over; level ground with the bit on, neither crossed. The
# game does not work cliffs out of the heights, so a writer that moves heights must rewrite field 0 (apply_edit).
# Field 1 holds the player's units and not the enemy's (测, checks/engine_bits.py bits); fields 0 + 3 still hold
# (field 3 does not reopen field 0); field 6 held neither a helicopter nor a tank, so its name is unconfirmed.
# The water's logic edge is the map's water height (200 world = 320 ours), not newmap.WATERLINE (测, engine_bits water).
WATER_WORLD = 200.0                                # our maps' standing water (the template's; retail maps' own vary)
FIELDS = ('impassable', 'impassable_to_players', 'passage_width', 'extra_passable', 'visible', 'buildability',
          'impassable_to_air', 'tiberium_growable')
IMPASSABLE = FIELDS.index('impassable')

# What a height edit must bring along, in the order a writer does it (platmap.apply is the reference writer).
MUST_FOLLOW = (
    ('HeightMapData.elev', 'the raw elevations: round(ours * 16), clipped to 0..65535'),
    ('BlendTileData field 0', 'impassable: recompute with passable() over the edited cells and one ring round them '
                              '(a cell\'s slope reads its four neighbours)'),
    ('BlendTileData tiles', 'ground texture by height and slope (newmap.texture_for): cliff rock where it is steep; '
                            'only looks, the game does not read textures for passing'),
    ('WorldInfo / previews', 'the radar pictures (newmap.preview_tga): only looks'),
    ('objects and waypoints', 'keep their z: it reads as a height above the ground, not an absolute one (推断: ours '
                              'are all 0; on the 27 retail campaign maps 96 % of 160711 objects are 0 and the rest '
                              'small lifts such as a fence at 4, which an absolute height would bury)'),
    ('sites and lint', 'Site.build / Site.cast squares, ramps (RAMP_MAX), water edges: platmap.lint'),
)


def world(h):
    """Our height units -> world units (also for differences)."""
    return np.asarray(h, dtype=float) * WORLD_PER_OURS


def ours(h):
    """World units -> our height units."""
    return np.asarray(h, dtype=float) / WORLD_PER_OURS


def slope(e):
    """Per cell, the largest rise to one of its four neighbours (ours per cell), edges padded -- platmap.slope_of."""
    e = np.asarray(e, dtype=float)
    p = np.pad(e, 1, mode='edge')
    c = p[1:-1, 1:-1]
    return np.maximum.reduce([abs(p[1:-1, 2:] - c), abs(p[1:-1, :-2] - c), abs(p[2:, 1:-1] - c), abs(p[:-2, 1:-1] - c)])


def passable(e, waterline, steep=STEEP):
    """The impassable bit (field 0) as our writers set it: dry ground steeper than `steep` is impassable. Returns the
    cells a ground unit may stand on (True = passable): dry (above waterline + 10) and not steep. Water is left to the
    game's water areas, not to the bit. The game itself reads only the bit (测): this is where the bit should be, not
    what the game would work out from the heights."""
    e = np.asarray(e, dtype=float)
    return (e > waterline + 10) & (slope(e) <= steep)


def impassable_bits(e, waterline, steep=STEEP):
    """Field 0 as written: steep AND dry (newmap / platmap.apply)."""
    e = np.asarray(e, dtype=float)
    return (slope(e) > steep) & (e > waterline)


def relief(e, i, j, half):
    """How much the ground rises (ours) across the cells within `half` cells of (i, j)."""
    e = np.asarray(e, dtype=float)
    win = e[max(0, j - half):j + half + 1, max(0, i - half):i + half + 1]
    return float(win.max() - win.min())


def flat_enough(e, i, j, side, variation=BUILD_VARIATION):
    """Whether a building `side` world units across may stand centred on cell (i, j): the heights under it vary by at
    most `variation` world units (the game's building-placement setting). Which points the game samples under the
    footprint is 推断 (here: every vertex of the square)."""
    half = max(1, int(round(side / CELL / 2)))
    return world(relief(e, i, j, half)) <= variation


def edit_region(changed, ring=1):
    """The cells whose derived data (field 0, textures) must be recomputed after the heights in `changed` (bool array)
    moved: the changed cells and `ring` cells round them (a slope reads the neighbours)."""
    m = np.asarray(changed, dtype=bool)
    out = m.copy()
    for _ in range(ring):
        p = np.pad(out, 1)
        out = out | p[1:-1, 2:] | p[1:-1, :-2] | p[2:, 1:-1] | p[:-2, 1:-1]
    return out


def apply_edit(e, bits, changed, waterline, steep=STEEP):
    """After a height edit: field 0 recomputed inside edit_region(changed), kept elsewhere. e: the new heights (ours);
    bits: the old impassable field (bool, rows j); returns the new field."""
    region = edit_region(changed)
    new = np.asarray(bits, dtype=bool).copy()
    new[region] = impassable_bits(e, waterline, steep)[region]
    return new
