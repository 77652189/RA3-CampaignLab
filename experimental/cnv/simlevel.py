"""Creation upgrade -> rank -> veterancy upgrades (engine_levelup a/b/c).

Combat experience and rank modifiers except DAMAGE_MULT, elite HEALTH_MULT,
heroic RANGE, Mirage SHROUD_CLEARING/ENEMY_SIGHTED and the measured Mirage heroic clip rate
remain unmodeled. This module does not turn a direct Upgrade_Veterancy_HEROIC
grant into a rank change.
"""
import functools
import os
import xml.etree.ElementTree as ET

import simunits


def rules(template, own):
    """Effective LevelUpUpgrade modules, by id, including BaseVehicle/Infantry."""
    found, seen = {}, set()
    while template and template.lower() not in seen:
        seen.add(template.lower())
        xml = simunits._xml(template, own) or ''
        for head, inner in simunits._blocks(xml, 'LevelUpUpgrade'):
            mid = simunits._attr(head, 'id')
            if mid not in found:
                found[mid] = (simunits._triggers(inner),
                              int(simunits._attr(head, 'LevelsToGain', '0')),
                              int(simunits._attr(head, 'LevelCap', '0')),
                              simunits._attr(head, 'Permanent', 'false').lower() == 'true')
        template = simunits.parent(xml, template)
    return found


@functools.lru_cache(maxsize=1)
def profiles():
    """Retail target -> rank -> (upgrades, modifiers), with template inheritance."""
    root = ET.parse(os.path.join(simunits.SAGEXML, 'GlobalData', 'ExperienceLevels.xml')).getroot()
    tag = lambda name: '{uri:ea.com:eala:asset}' + name
    nodes = {e.get('id'): e for e in root.findall(tag('ExperienceLevelTemplate'))}

    @functools.lru_cache(maxsize=None)
    def resolved(name):
        e = nodes[name]
        base = resolved(e.get('inheritFrom')) if e.get('inheritFrom') in nodes else (1, (), ())
        return (int(e.get('Rank', base[0])),
                tuple(x.text.strip() for x in e.findall(tag('Upgrade'))) or base[1],
                tuple(x.text.strip() for x in e.findall(tag('AttributeModifier'))) or base[2])

    out = {}
    for name, e in nodes.items():
        rank, upgrades, modifiers = resolved(name)
        for target in e.findall(tag('Target')):
            out.setdefault(target.text.strip().lower(), {})[rank] = (upgrades, modifiers)
    return out


def receive(sim, b, up, on, newly_held):
    cache = sim.__dict__.setdefault('_levelup_rules', {})
    if b.template not in cache:
        cache[b.template] = rules(b.template, sim.own)
    for mid, (triggers, gain, cap, permanent) in cache[b.template].items():
        if up not in triggers:
            continue
        if not on:
            # engine_levelup b/c: deactivation rearms each retail module without
            # undoing rank, veterancy upgrades or already applied HP scaling.
            if permanent:
                sim.gap('升级', 'LevelUpUpgrade/permanent', 'Permanent=true的移除重给未对拍')
            else:
                b.level_modules.discard(mid)
            continue
        if mid in b.level_modules:
            continue
        if not newly_held:
            continue
        profile = profiles().get(b.template.lower(), {})
        if len(triggers) != 1 or gain < 0 or cap <= 0 or not profile:
            sim.gap('升级', 'LevelUpUpgrade/trigger', f'{b.template} 的触发或等级表未模拟')
            continue
        old = b.level_rank
        new = max(old, min(cap, old + gain))
        if any(rank not in profile for rank in range(old + 1, new + 1)):
            sim.gap('升级', 'LevelUpUpgrade/profile', f'{b.template} 缺等级表')
            continue
        b.level_modules.add(mid)
        b.level_rank = new
        seen = {mid for rank, (_, mids) in profile.items() if rank <= old for mid in mids}
        for rank in range(old + 1, new + 1):
            upgrades, mids = profile[rank]
            for modifier_id in mids:
                if modifier_id in seen:
                    continue
                seen.add(modifier_id)
                modifier = simunits.modifier(sim.xml_of(b.template), modifier_id)
                multipliers = modifier['types'].get('HEALTH_MULT', []) if modifier else []
                if multipliers:
                    if modifier_id != 'Unit_Elite' or multipliers != [1.25]:
                        sim.gap('升级', 'LevelUpUpgrade/' + modifier_id, '该等级血量倍率未对拍')
                    else:
                        # engine_levelhealth a/b: 500 -> 625 max HP; keep health fraction.
                        for multiplier in multipliers:
                            b.max_hp *= multiplier
                            b.hp *= multiplier
            for upgrade in upgrades:
                b.upgrades.add(upgrade)
                b.up_since[upgrade] = sim.frame_now()
        sim.used.add('levelup')


def damage_modifiers(sim, b, xml):
    """Measured rank damage/range, Mirage shroud/sight query and discrete ROF."""
    if b.level_rank <= 1:
        return []
    out, seen = [], set()
    for rank, (_, mids) in profiles().get(b.template.lower(), {}).items():
        if rank > b.level_rank:
            continue
        for mid in mids:
            if mid in seen:
                continue
            seen.add(mid)
            m = simunits.modifier(xml, mid)
            if m is None:
                sim.gap('升级', 'LevelUpUpgrade/' + mid, '等级属性修正数据缺失')
                continue
            supported = {'DAMAGE_MULT'}
            if mid == 'Unit_Elite' and m['types'].get('HEALTH_MULT') == [1.25]:
                supported.add('HEALTH_MULT')
            if mid == 'Unit_Heroic' and m['types'].get('RANGE') == [1.25]:
                supported.add('RANGE')  # engine_levelrange a: heroic gun 150 -> 187.5
            if (mid == 'Unit_Heroic' and m['types'].get('SHROUD_CLEARING') == [1.25]
                    and b.template == 'AlliedAntiVehicleVehicleTech3'):
                supported.add('SHROUD_CLEARING')  # engine_levelshroud a: 500 -> 625
            if (mid == 'Unit_Heroic' and m['types'].get('VISION') == [1.25]
                    and b.template == 'AlliedAntiVehicleVehicleTech3'):
                supported.add('VISION')  # engine_levelvision a: supports 200 -> 250
            if (mid == 'Unit_Heroic' and m['types'].get('RATE_OF_FIRE') == [1.2]
                    and b.template == 'AlliedAntiVehicleVehicleTech3' and sim.shot_clock):
                supported.add('RATE_OF_FIRE')  # engine_levelrate a; other weapons remain gaps
            unsupported = sorted(set(m['types']) - supported)
            if 'VISION' in supported:
                unsupported.append('VISION/自动索敌及精确边界')  # only the script query was measured
            if m['status']:
                unsupported.append('ObjectStatusToSet')
            if unsupported:
                sim.gap('升级', 'LevelUpUpgrade/' + mid, '等级属性修正未模拟：' + ', '.join(unsupported))
            acting = {ty: values for ty, values in m['types'].items()
                      if ty in supported & {'DAMAGE_MULT', 'RANGE', 'RATE_OF_FIRE', 'SHROUD_CLEARING', 'VISION'}}
            if acting:
                out.append(dict(m, types=acting, status=set()))
    return out
