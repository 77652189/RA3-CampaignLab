"""Choose materials for expanded terrain and let the map writer blend their edges."""
from dataclasses import replace
from pathlib import Path
from random import Random

import numpy as np
from scipy.ndimage import label as connected_components

from experimental.mapgen.campaign_writer import labpaths, noise_field, rules
from experimental.mapgen.library import child_recipe, place_recipe, style_section, texture_kit, weighted
from experimental.mapgen.terrain import Blend


ART = Path(labpaths.SDK3) / 'Art' / 'Terrain'

def _asset(label, asset):
    for field in ('Texture', 'BumpTexture'):
        name = asset.get(field)
        if not name or not (ART / name).is_file():
            raise ValueError(f'block {label}: missing texture {name or field} for {asset.get("id")}')
    return asset['id']


def _named(catalogue, label, name):
    if name not in catalogue:
        raise ValueError(f'block {label}: missing texture {name}')
    return _asset(label, catalogue[name][2])


def _palette(kits, kit, kind, label, rng, count, policy):
    fallback = policy.get(kind)
    # Transition and Reef tiles are authored for specific edges, rather than a field.
    for source in dict.fromkeys((kit, fallback)):
        entries = kits.get(source, {}).get(kind, ())
        choices = sorted((entry for entry in entries if not entry['id'].startswith(('Transition', 'Reef'))
                          and entry['id'] not in policy.get('exclude', ())),
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
    roles = ((ground.ramp & ~ground.blocked, 'ramp_surface'), (ground.shore, 'shore_surface'),
             (cliff, 'cliff_surface'))
    surfaces = [block.surface for block in plan.blocks]
    for owner, surface in enumerate(surfaces):
        if surface is None:
            raise ValueError(f'block at {plan.blocks[owner].points[0]}: missing surface id, use and kit')

    fixed, soil_owners, dirt_paths = {plan.ground}, set(), {}
    for owner, surface in enumerate([*surfaces, None]):
        mask = ground.owners == (owner if surface else -1)
        label, kit, kind = backdrop, ground_kit, ground_class
        key = surface.kit if surface else ground_kit
        edges = style_section(library, key, 'edges')
        places = style_section(library, key, 'places')
        policy = places['texture_palette'] | places.get('texture_donors', {})
        named_texture = None
        if surface:
            label = surface.id
            kit = texture_kit(surface.kit)
            if surface.kit not in library.get('kits', {}) or kit not in kits:
                raise ValueError(f'block {label}: missing kit {surface.kit} (terrain kit {kit})')
            recipe = place_recipe(library, key, surface.use)
            mined = child_recipe(library, key, surface.use)
            if mined:
                textures[mask] = _named(catalogue, label, weighted(Random(surface.seed), mined['textures']))
                fixed.update(set(textures[mask]))
                continue
            if surface.use == 'reserved':
                textures[mask] = _named(catalogue, label, surface.ground_texture or plan.ground)
                continue
            if 'material' not in recipe:
                raise ValueError(f'block {label}: unknown use {surface.use}')
            kind = recipe['material']
            if surface.ground_texture is not None:
                named_texture = _named(catalogue, label, surface.ground_texture)
                textures[mask] = named_texture
            else:
                rng = Random(f'{label}:{surface.seed}')
                fixed_palette = recipe.get('textures')
                base, *accents = ([_named(catalogue, label, n) for n in fixed_palette] if fixed_palette else
                                  _palette(kits, kit, kind, label, rng, policy['count'], policy))
                textures[mask] = base
                if accents and mask.any():
                    j, i = np.nonzero(mask)
                    scale, lower, upper = policy['fixed_noise' if fixed_palette else 'noise']
                    noise = noise_field(rng.getrandbits(32), scale, i, j)
                    for accent, patch in zip(accents, (noise > upper, noise < lower)):
                        textures[j[patch], i[patch]] = accent
        shoulder = mask & ground.ramp_edges & ~ground.hidden
        for role_mask, role in roles:
            cells = mask & role_mask
            treatment = edges[role]
            if role == 'cliff_surface' and kind in treatment.get('keep_shoulder', ()):
                cells &= ~shoulder
            if not cells.any():
                continue
            ramp = role == 'ramp_surface'
            adjacent = ground_class if role == 'shore_surface' else kind
            role_class = treatment.get('classes', {}).get(adjacent, treatment['material'])
            packed = catalogue.get(treatment.get('textures', {}).get(kind))
            if ramp and named_texture is not None and catalogue[named_texture][1] == role_class:
                name = named_texture
            elif packed:
                name = _asset(label, packed[2])
            else:
                rng = Random(f'{label}:{surface.seed if surface else 0}:{role.removesuffix("_surface")}')
                name, = _palette(kits, kit, role_class, label, rng, 1, policy)
            textures[cells] = name
            if ramp:
                fixed.add(name)
                if role_class == 'Dirt':
                    soil_owners.add(owner if surface else -1)
                    if name == named_texture:
                        dirt_paths[owner] = name
        ramp = edges['ramp_surface']
        exposed, verge = shoulder & cliff, shoulder & ~ground.blocked
        if kind in ramp.get('keep_shoulder', ()):
            continue
        rock = ramp['exposed']
        if exposed.any() and any(kits.get(source, {}).get(rock) for source in (kit, policy.get(rock))):
            rock, = _palette(kits, kit, rock, label, Random(f'{kit}:ramp cut'), 1, policy)
            textures[exposed] = rock
        elif named_texture is not None:
            textures[exposed] = named_texture
        if verge.any():
            if named_texture is None:
                verge_class = ramp.get('verge_classes', {}).get(kind, ramp['verge'])
                named_texture, = _palette(kits, kit, verge_class, label, Random(f'{kit}:ramp verge'), 1, policy)
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
        paving = style_section(library, roadbed.kit, 'edges').get('road_surface', {})
        places = style_section(library, roadbed.kit, 'places')
        policy = places['texture_palette'] | places.get('texture_donors', {})
        base = catalogue.get(paving.get('base'))
        road_material, = ([_asset('roadbed', base[2])] if base else
                          _palette(kits, kit, 'Road', 'roadbed', Random(0), 1, policy))
        textures[roadbed.paved] = road_material
        if (infill := paving.get('infill')) and roadbed.infill.any():
            asphalt = _named(catalogue, 'road infill', infill)
            textures[roadbed.infill] = asphalt
        if (cue := paving.get('ramp_infill')) and (ramp := ground.ramp & roadbed.infill & ~roadbed.hidden).any():
            cue = _named(catalogue, 'ramp infill', cue)
            textures[ramp] = cue
            fixed.add(cue)
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
