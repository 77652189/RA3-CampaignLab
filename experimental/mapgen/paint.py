"""Choose materials for expanded terrain and let the map writer blend their edges."""
from dataclasses import replace
from pathlib import Path
from random import Random

import numpy as np
from scipy.ndimage import label as connected_components

from experimental.mapgen.campaign_writer import labpaths, noise_field, rules
from experimental.mapgen.library import SNOW_FIELDS, SNOW_RAMPS, WINTER_SURFACES, texture_kit
from experimental.mapgen.terrain import Blend


ART = Path(labpaths.SDK3) / 'Art' / 'Terrain'

USE_CLASS = {
    'oldtown': 'Road', 'residential': 'Road', 'industrial': 'Road', 'dock': 'Road', 'square': 'Road',
    'suburb': 'Grass', 'park': 'Grass', 'woodland': 'Grass', 'wildland': 'Grass',
    'farm': 'Dirt', 'canyon': 'Dirt', 'water': 'Sand',
    'snow': 'Snow', 'snow_woodland': 'Snow', 'ice': 'Snow',
}
# A style without the requested class borrows that class from a fixed donor.
# Heidelberg has one Dirt entry, Yucatan has no Cliff and only coastal Reef/Rock.
FALLBACK = {'Road': 'Heidelberg', 'Grass': 'Heidelberg', 'Dirt': 'Yucatan',
            'Cliff': 'Cape_Cod', 'Sand': 'Santa_Monica', 'Rock': 'Yucatan', 'Snow': 'Iceland'}
CLIFF_DONOR = {'Heidelberg': 'Gibraltar'}
HEIDELBERG_ASPHALT = {'Pavement_Heidel07', 'Pavement_Heidel08', 'Pavement_Heidel09'}


def _asset(label, asset):
    for field in ('Texture', 'BumpTexture'):
        name = asset.get(field)
        if not name or not (ART / name).is_file():
            raise ValueError(f'block {label}: missing texture {name or field} for {asset.get("id")}')
    return asset['id']


def _palette(kits, kit, kind, label, rng, count):
    fallback = CLIFF_DONOR.get(kit, FALLBACK[kind]) if kind == 'Cliff' else FALLBACK[kind]
    # Transition and Reef tiles are authored for specific edges, rather than a field.
    for source in dict.fromkeys((kit, fallback)):
        entries = kits.get(source, {}).get(kind, ())
        choices = sorted((entry for entry in entries if not entry['id'].startswith(('Transition', 'Reef'))
                          and entry['id'] not in HEIDELBERG_ASPHALT),
                         key=lambda entry: entry['id'])
        if choices:
            rng.shuffle(choices)
            return [_asset(label, asset) for asset in choices[:count]]
    raise ValueError(f'block {label}: missing texture for {kit}/{kind} (fallback {fallback})')


def paint(plan, library, ground, roadbed=None):
    """Materialize each block's Surface on terrain.expand's ownership and geometry masks."""
    kits = library.get('texture_kits', {})
    catalogue = {entry['id']: (kit, kind, entry) for kit, classes in kits.items()
                 for kind, entries in classes.items() for entry in entries}
    backdrop = 'background'
    if plan.ground not in catalogue:
        raise ValueError(f'block {backdrop}: missing texture {plan.ground}')
    ground_kit, ground_class, asset = catalogue[plan.ground]
    _asset(backdrop, asset)
    textures = np.full(ground.raw.shape, plan.ground, object)
    cliff = ground.blocked & (rules.slope(ground.raw / rules.RAW_PER_OURS) > rules.STEEP)
    roles = ((ground.ramp & ~ground.blocked, 'ramp'), (ground.shore, 'shore'), (cliff, 'cliff'))
    surfaces = [block.surface for block in plan.blocks]
    for owner, surface in enumerate(surfaces):
        if surface is None:
            raise ValueError(f'block at {plan.blocks[owner].points[0]}: missing surface id, use and kit')

    fixed, soil_owners, dirt_paths = {plan.ground}, set(), {}
    for owner, surface in enumerate([*surfaces, None]):
        mask = ground.owners == (owner if surface else -1)
        label, kit, kind = backdrop, ground_kit, ground_class
        named_texture = None
        if surface:
            label = surface.id
            kit = texture_kit(surface.kit)
            if surface.kit not in library.get('kits', {}) or kit not in kits:
                raise ValueError(f'block {label}: missing kit {surface.kit} (terrain kit {kit})')
            if surface.use not in USE_CLASS:
                raise ValueError(f'block {label}: unknown use {surface.use}')
            kind = USE_CLASS[surface.use]
            if surface.ground_texture is not None:
                entry = catalogue.get(surface.ground_texture)
                if entry is None:
                    raise ValueError(f'block {label}: missing texture {surface.ground_texture}')
                named_texture = _asset(label, entry[2])
                textures[mask] = named_texture
            else:
                rng = Random(f'{label}:{surface.seed}')
                winter = SNOW_FIELDS.get(kit) if surface.use == 'snow' else WINTER_SURFACES.get(surface.use)
                entries = ([catalogue[name][2] for name in winter if name in catalogue] if winter else None)
                if winter and len(entries) != len(winter):
                    missing = next(name for name in winter if name not in catalogue)
                    raise ValueError(f'block {label}: missing texture {missing}')
                base, *accents = ([_asset(label, entry) for entry in entries] if winter else
                                  _palette(kits, kit, kind, label, rng, 3))
                textures[mask] = base
                if accents and mask.any():
                    j, i = np.nonzero(mask)
                    # Broad wind-scoured patches on snow; smaller accents elsewhere.
                    noise = noise_field(rng.getrandbits(32), 22 if winter else 12, i, j)
                    lower, upper = (0.28, 0.72) if winter else (0.18, 0.82)
                    for accent, patch in zip(accents, (noise > upper, noise < lower)):
                        textures[j[patch], i[patch]] = accent
        shoulder = mask & ground.ramp_edges & ~ground.hidden
        for role_mask, role in roles:
            cells = mask & role_mask
            if kind == 'Snow' and role == 'cliff':
                cells &= ~shoulder
            if cells.any():
                ramp_class = {'Snow': 'Snow', 'Dirt': 'Rock'}.get(kind, 'Dirt')
                role_class = {'cliff': 'Cliff', 'shore': 'Snow' if ground_class == 'Snow' else 'Sand',
                              'ramp': ramp_class}[role]
                packed = catalogue.get(SNOW_RAMPS.get(kit)) if role == 'ramp' and kind == 'Snow' else None
                if role == 'ramp' and named_texture is not None and catalogue[named_texture][1] == role_class:
                    name = named_texture
                elif packed:
                    name = _asset(label, packed[2])
                else:
                    rng = Random(f'{label}:{surface.seed if surface else 0}:{role}')
                    name, = _palette(kits, kit, role_class, label, rng, 1)
                textures[cells] = name
                if role == 'ramp':
                    fixed.add(name)
                    if role_class == 'Dirt':
                        soil_owners.add(owner if surface else -1)
                        if name == named_texture:
                            dirt_paths[owner] = name
        # Exposed snow shoulders keep the snow from the adjoining field.
        exposed = shoulder & cliff
        if kind != 'Snow' and exposed.any() and (
                kits.get(kit, {}).get('Rock') or kits.get(FALLBACK['Rock'], {}).get('Rock')):
            rock, = _palette(kits, kit, 'Rock', label, Random(f'{kit}:ramp cut'), 1)
            textures[exposed] = rock
        elif named_texture is not None and kind != 'Snow':
            textures[exposed] = named_texture
        verge = shoulder & ~ground.blocked
        if kind != 'Snow' and verge.any():
            if named_texture is None:
                named_texture, = _palette(kits, kit, 'Dirt' if kind == 'Dirt' else 'Grass', label,
                                          Random(f'{kit}:ramp verge'), 1)
            textures[verge] = named_texture

    if dirt_paths:
        # A single explicitly painted dirt path continues across the ramp and its exposed flank.
        paths, count = connected_components(ground.ramp)
        for index in range(1, count + 1):
            ramp = paths == index
            owners = set(ground.owners[ramp & ~ground.blocked])
            soils = {dirt_paths[i] for i in owners & dirt_paths.keys()}
            if len(soils) == 1 and owners <= soil_owners:
                flank = rules.edit_region(ramp) & ground.ramp_edges & cliff
                textures[(ramp | flank) & ~ground.hidden] = soils.pop()

    road_material = asphalt = None
    if roadbed is not None and roadbed.paved.any():
        kit = texture_kit(roadbed.kit)
        # The Heidelberg sample reads this exact substrate beneath the HV street meshes.
        paving = catalogue.get('Pavement_Heidelberg10') if kit == 'Heidelberg' else None
        road_material, = ([_asset('roadbed', paving[2])] if paving else
                          _palette(kits, kit, 'Road', 'roadbed', Random(0), 1))
        textures[roadbed.paved] = road_material
        if kit == 'Heidelberg' and roadbed.infill.any():
            # Heidelberg uses Havana street meshes. Use their smooth grey
            # road material at exposed joins, where the brick base shows.
            entry = catalogue.get('Pavement_Havana03')
            if entry is None:
                raise ValueError('road infill: missing texture Pavement_Havana03')
            asphalt = _asset('road infill', entry[2])
            textures[roadbed.infill] = asphalt
        ground = replace(ground, hidden=ground.hidden | roadbed.hidden)

    fixed.update(name for name in (road_material, asphalt) if name is not None)

    def priority(name):
        kind = catalogue[name][1]
        if kind == 'Cliff':
            return 0
        if kind == 'Sand':
            return 1
        return 2 if name in fixed else 3

    rank = tuple(sorted(set(textures.flat) | fixed, key=lambda n: (priority(n), n)))
    authored = frozenset(i for i, s in enumerate(surfaces) if s.ground_texture is not None)
    return replace(ground, textures=textures, rank=rank,
                   blend=Blend(plan.ground, road_material, asphalt, authored))
