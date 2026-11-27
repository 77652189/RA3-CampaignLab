"""Choose materials for expanded terrain and let the map writer blend their edges."""
from dataclasses import replace
from pathlib import Path
from random import Random

import numpy as np

from experimental.mapgen.campaign_writer import labpaths, noise_field, rules


ART = Path(labpaths.SDK3) / 'Art' / 'Terrain'

# Civilian SDK directories normally drop their two-letter suffix. These names
# differ, or have no usable terrain kit in the RA3 atlas sources (e.g. Romania).
KIT_ALIASES = {
    'Floating_Island_FI': 'Tokyo_Harbor', 'Miyako_MI': 'Hawaii',
    'Mount_Fuji_MJ': 'Hot_Springs', 'Northern_Russia_NR': 'Iceland',
    'Osaka_OK': 'Tokyo_Harbor', 'Romania_RM': 'Yucatan', 'Sakhalin_Island_SI': 'Iceland',
    'Shiro_Sanitarium_SS': 'Hot_Springs', 'Snowy_Hot_Springs_SN': 'Hot_Springs',
    'StPetersburg_ST': 'Saint_Petersburg', 'Yosemite_Park_YP': 'Mount_Rushmore',
}
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
WINTER_SURFACES = {
    # Murmansk and Iceland mix a continuous Solvang snow bed with exposed
    # Iceland ground and dirty snow. The scored Solvang tile reads as ice.
    'snow': ('Snow_Solvang01', 'Snow_Iceland04', 'Snow_Solvang08'),
    'snow_woodland': ('Snow_Solvang08', 'Snow_Solvang10', 'Snow_Solvang01'),
    'ice': ('Snow_Solvang02', 'Snow_Solvang09', 'Snow_Solvang03'),
}
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

    ramp_material = None
    for owner, surface in enumerate([*surfaces, None]):
        mask = ground.owners == (owner if surface else -1)
        label, kit, kind = backdrop, ground_kit, ground_class
        rng = Random(0)
        if surface:
            label = surface.id
            kit = KIT_ALIASES.get(surface.kit, surface.kit.rsplit('_', 1)[0])
            if surface.kit not in library.get('kits', {}) or kit not in kits:
                raise ValueError(f'block {label}: missing kit {surface.kit} (terrain kit {kit})')
            if surface.use not in USE_CLASS:
                raise ValueError(f'block {label}: unknown use {surface.use}')
            kind = USE_CLASS[surface.use]
            rng = Random(f'{label}:{surface.seed}')
            winter = WINTER_SURFACES.get(surface.use)
            try:
                base, *accents = ([_asset(label, catalogue[name][2]) for name in winter] if winter else
                                  _palette(kits, kit, kind, label, rng, 3))
            except ValueError:
                # A named ground (e.g. snow past the frame) covers the face below anyway.
                if surface.ground_texture is None:
                    raise
                base, accents = None, []
            textures[mask] = base
            j, i = np.nonzero(mask)
            if accents and i.size:
                # Broad wind-scoured patches on snow; smaller accents elsewhere.
                noise = noise_field(rng.getrandbits(32), 22 if winter else 12, i, j)
                lower, upper = (0.28, 0.72) if winter else (0.18, 0.82)
                for accent, patch in zip(accents, (noise > upper, noise < lower)):
                    textures[j[patch], i[patch]] = accent
            if surface.ground_texture is not None:
                entry = catalogue.get(surface.ground_texture)
                if entry is None:
                    raise ValueError(f'block {label}: missing texture {surface.ground_texture}')
                textures[mask] = _asset(label, entry[2])
        for role_mask, role in roles:
            cells = mask & role_mask
            if cells.any() or (surface is None and role == 'ramp' and ground.ramp.any()):
                ramp_class = 'Rock' if kind == 'Dirt' else 'Dirt'
                role_class = {'cliff': 'Cliff', 'shore': 'Snow' if ground_class == 'Snow' else 'Sand',
                              'ramp': ramp_class}[role]
                name, = _palette(kits, kit, role_class, label, rng, 1)
                textures[cells] = name
                if role == 'ramp' and surface is None:
                    ramp_material = name
        shoulder = mask & ground.ramp_edges & ~ground.hidden
        if shoulder.any():
            name, = _palette(kits, kit, 'Dirt' if kind == 'Dirt' else 'Grass', label,
                             Random(f'{kit}:ramp verge'), 1)
            textures[shoulder] = surface.ground_texture if surface and surface.ground_texture else name

    road_material = asphalt = None
    if roadbed is not None and roadbed.paved.any():
        kit = KIT_ALIASES.get(roadbed.kit, roadbed.kit.rsplit('_', 1)[0])
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

    def edge_texture(i, j, ni, nj, name):
        # Field 4 makes the model-covered foot transparent. Keep its substrate
        # out of neighbouring blends, and leave visible cliff faces exposed.
        if ground.hidden[j, i] or ground.hidden[nj, ni]:
            return None
        materials = (textures[j, i], textures[nj, ni])
        if road_material in materials or asphalt in materials:
            return name
        if ground.owners[j, i] == ground.owners[nj, ni]:
            return name
        if ground.blocked[j, i] or ground.blocked[nj, ni]:
            return name if ground.ramp_edges[j, i] or ground.ramp_edges[nj, ni] else None
        if ground.ramp[j, i] and ground.ramp[nj, ni]:
            return ramp_material
        return plan.ground

    # Global ordering is independent of block order and the palette picked by
    # any neighbour. At a three-material corner the writer takes one winner.
    fixed = {name for name in (plan.ground, ramp_material, road_material, asphalt) if name is not None}

    def priority(name):
        kind = catalogue[name][1]
        if kind == 'Cliff':
            return 0
        if kind == 'Sand':
            return 1
        return 2 if name in fixed else 3

    rank = tuple(sorted(set(textures.flat) | fixed, key=lambda n: (priority(n), n)))
    return replace(ground, textures=textures, rank=rank, edge_texture=edge_texture)
