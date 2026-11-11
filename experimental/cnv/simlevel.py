"""Creation upgrade -> rank -> veterancy upgrades (engine_levelup a).

Combat experience and rank modifiers except DAMAGE_MULT and full-health HEALTH_MULT remain unmodeled. This module
does not turn a direct Upgrade_Veterancy_HEROIC grant into a rank change.
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
                              int(simunits._attr(head, 'LevelCap', '0')))
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
    for mid, (triggers, gain, cap) in cache[b.template].items():
        if up not in triggers:
            continue
        if not on or mid in b.level_modules:
            if not on or newly_held:
                sim.gap('升级', 'LevelUpUpgrade/regrant', '移除后重给的等级行为未对拍')
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
                    elif abs(b.hp - b.max_hp) > 1e-9:
                        sim.gap('升级', 'LevelUpUpgrade/injured-health', '残血升级的血量变化未对拍')
                    else:
                        # engine_levelhealth a: elite max HP 500 -> 625, retained at heroic.
                        for multiplier in multipliers:
                            b.max_hp *= multiplier
                        b.hp = b.max_hp
            for upgrade in upgrades:
                b.upgrades.add(upgrade)
                b.up_since[upgrade] = sim.frame_now()
        sim.used.add('levelup')


def damage_modifiers(sim, b, xml):
    """Only the measured rank DAMAGE_MULT; never multiply ROF into one shot."""
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
            unsupported = sorted(set(m['types']) - supported)
            if m['status']:
                unsupported.append('ObjectStatusToSet')
            if unsupported:
                sim.gap('升级', 'LevelUpUpgrade/' + mid, '等级属性修正未模拟：' + ', '.join(unsupported))
            if 'DAMAGE_MULT' in m['types']:
                out.append(dict(m, types={'DAMAGE_MULT': m['types']['DAMAGE_MULT']}, status=set()))
    return out
