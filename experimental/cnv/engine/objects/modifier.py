"""L2 attribute modifiers and auras (ADR 0029, docs/engine/sim-layers.md; bench docs/engine/upgrades.md).

`Modifiers` sets a body's acting values from the modifiers on it (`modify`) and lets the aura objects hang theirs
(`aura_tick`) over the world it is given (simworld.WORLD_API only); an aura's rule and last refresh are its kernel
module's (engine/modules/aura.py, step M12), the modifiers hung on a body stay the body's (auras_on: the engine's
Object holds them, no module) as does `base`, this host's copy of the values before modifiers. The peers it reads are
handed in by the caller (Sim.modify / Sim.aura_tick): the template's toggles and freeze tracker (L2), the upgrade names
a weapon line tests and the player's granted upgrades (L4), how two owners stand (`relation`) -- this module never
imports them. Fields it owns on a body: `level_rate`, `level_vision`, `shielded`, `taken`, `dealt`; the weapons the
status picks and the range scales it writes to the body's WeaponSet module (step W2, WeaponSet.hold).
"""
import math

import engine.objects.level as simlevel
import engine.data.units as simunits
from engine.kernel import interfaces
from engine.objects.status import ACTED_STATUS
from engine.world.handle import GAP_STATUS, GAP_UPGRADE

# R8: a weapon reaches (AttackRange - UNDERSIZE) x its range multiplier, not the full AttackRange (Generals UNDERSIZE,
# a quarter of a 20-unit path cell): read for both the AI hostile gate and the firing check (work/re D162, not benched)
UNDERSIZE = 5.0


class Modifiers:
    def modify(self, world, b, toggles_of, cold_of, upgrades_of, player_ups):
        """Sets b's acting values from the attribute modifiers on it (simunits.effect): the upgrades it holds (an
        AttributeModifierUpgrade's modifier, until its Duration runs out from the giving: bench upgrades.md 4; a
        StatusBitsUpgrade's bits) and what auras hung on it (aura_tick, each until its frame). SPEED x the speed,
        RANGE x the weapons' range only, VISION x vision and sight (upgrades.md 1, 2); the status = the script's bits
        + the modifiers', IN_STASIS meaning IMMOBILE NO_ATTACK UNATTACKABLE (INFERRED: the measured stasis modifier
        sets them all); shielded, ARMOR (taken), DAMAGE_MULT x RATE_OF_FIRE (dealt). First the upgrades held (its own
        and its player's, as a weapon's) are told to its Upgrade modules (step K3: the kernel's upgrade broadcast)."""
        b.upgrades_moved(upgrades_of(b))
        now = world.frame_now()
        xml = world.xml_of(b.template)
        mods = []
        level_mods = simlevel.damage_modifiers(world, b, xml)
        b.level_rate = simunits.stack([v for m in level_mods for v in m['types'].get('RATE_OF_FIRE', [])])
        level_shroud = simunits.stack([v for m in level_mods for v in m['types'].get('SHROUD_CLEARING', [])])
        b.level_vision = simunits.stack([v for m in level_mods for v in m['types'].get('VISION', [])])
        # Measured rank ROF belongs to the clip clock. Other modifiers retain
        # their existing continuous-DPS approximation until separately benched.
        mods.extend(dict(m, types={ty: values for ty, values in m['types'].items()
                                  if ty not in {'RATE_OF_FIRE', 'SHROUD_CLEARING', 'VISION'}})
                    for m in level_mods)
        if b.suppression_rule and b.suppressed:
            mods.append(simunits.modifier(xml, b.suppression_rule['modifier']))
        for up, mid in simunits.upgrade_mods(xml, b.upgrades):
            m = simunits.modifier(xml, mid)
            if m and (m['frames'] is None or now < b.up_since.get(up, now) + m['frames']):
                mods.append(m)
        for mid, (until, src) in list(b.auras_on.items()):
            if now >= until:
                # Expiry clears the template's bits even if a script set the
                # same bit later; it is not source-counted. This isolated
                # timed-modifier path makes no attack-order retention claim.
                expired = simunits.modifier(src, mid)
                if expired:
                    b.script_status.difference_update(expired['status'])
                del b.auras_on[mid]
            else:
                mods.append(simunits.modifier(src, mid))
        toggle_bits = set()
        for i, tm in enumerate(toggles_of(b)):              # each toggle module's current ToggleState
            st = tm['states'][b.toggle_at.get(i, 0) % len(tm['states'])]
            toggle_bits |= st['status']
            if st['modifier'] and simunits.modifier(xml, st['modifier']):
                mods.append(simunits.modifier(xml, st['modifier']))
        step = cold_of(b)[0]['steps'][b.cold_step] if b.cold_step >= 0 else None
        if step and step[1]:
            mods.append(simunits.modifier(xml, step[1]))
        # engine_spngp a: a PLAYER grant triggers the owner's StatusBitsUpgrade.
        player_bits = {up for up in player_ups.get(b.owner, ())
                       if simunits.upgrade_type(up, world.own) == 'PLAYER'}
        on, off = simunits.status_bits(xml, b.upgrades | player_bits)
        e = simunits.effect(mods, on | b.script_status | b.attachment_status | b.lift_status | toggle_bits, off)
        if not mods and not on and not off and b.base is None:
            b.status = set(b.script_status | b.attachment_status | b.lift_status | toggle_bits)
            if b.slots:
                b.find(interfaces.WeaponSet).hold(simunits.pick_weapons(b.slots, b.status, upgrades_of(b)))
            return
        if b.base is None:
            b.base = {'speed': b.speed, 'vision': b.vision, 'sight': b.sight, 'weapons': b.weapons, 'armor': b.armor}
        st = e['status']
        if 'IN_STASIS' in st:
            st = st | {'IMMOBILE', 'NO_ATTACK', 'UNATTACKABLE'}
        if 'UNDER_FROZEN' in st or (step and step[2]):          # frozen (OnEnterDisable): stopped and silent
            st = st | {'IMMOBILE', 'NO_ATTACK'}
        b.armor = cold_of(b)[1] if step and step[3] and cold_of(b)[1] else b.base['armor']
        b.status = st
        # Suppression SPEED75%:50->37.5 (bench44->59); retain fractional speed.
        b.speed = b.base['speed'] * e['SPEED']
        b.vision, b.sight = b.base['vision'] * e['VISION'], b.base['sight'] * e['VISION']
        if level_shroud != 1.0:
            # engine_levelshroud a measures discovery, not VISION/auto-acquire.
            # Recompute from retail shroud, never from last frame's scaled value.
            shroud = simunits.stats(b.template, world.own)['shroud'] or 0.0
            b.vision = max(b.vision, shroud * level_shroud)
        held = simunits.pick_weapons(b.slots, st, upgrades_of(b)) if b.slots else b.base['weapons']       # the status picks the guns
        guns = b.find(interfaces.WeaponSet) if b.modules else None     # step W2: its WeaponSet holds them (none:
        if guns is not None:                                            # it has none, held and base are [])
            guns.hold(held if e['RANGE'] == 1.0 else [dict(w, range=w['range'] * e['RANGE'],
                                                           undersize=UNDERSIZE * e['RANGE']) for w in held])
        b.shielded = e['shielded']
        # Suppression ARMOR75%: EXPLOSIVE40 on150HP reads80%; UNRESISTABLE bypasses it.
        b.taken, b.dealt = e['ARMOR'], e['DAMAGE_MULT'] * e['RATE_OF_FIRE']
        if mods or on:
            world.used.add('modifier')
        for m in mods:
            for ty in sorted(set(m['types']) - simunits.ACTING_TYPES) if m else ():
                world.gap(GAP_UPGRADE, m['id'], f'修正类型 {ty} 没模拟')
        for bit in sorted(e['status'] - b.script_status - b.attachment_status - b.lift_status - ACTED_STATUS - ({'UNDER_IRON_CURTAIN'} if b.shielded else set())):
            world.gap(GAP_STATUS, bit, f'{b.template} 身上的修正 / 升级给的，只记下来')

    def aura_tick(self, world, relation, modify):
        """Once a tick before the fight: every living aura object's aura modules (interfaces.Aura, active, holding the bits it needs)
        hangs its modifier on what its filter takes within Range, centre to centre, once every RefreshDelay (the first
        at once), until then + the modifier's Duration (none: the refresh); then every body with a modifier is re-set
        (modify). Bench upgrades.md 5 / 5.1 (engine_stasis_edge / _leave): the edge is the unit's centre (a Guardian
        at 190 from a 200 zone held, at 205 not, though its box is 20 x 12); a unit out of the zone keeps it Duration
        after the last refresh (hold 2 s: 26 frames after the teleport); a hold shorter than the refresh flickers
        (refresh 1 s, hold 0.2 s: on 22 of 150 frames) -- a 0.5 s tick shows that only as on at a refresh tick."""
        now = world.frame_now()
        live = world.living()
        for e in live:
            for aura in (e.find(interfaces.Aura) if e.modules else ()):     # step M12: its aura modules, block order
                a = aura.rules()
                if not a['mod'] or not a['active'] or not a['needs'] <= e.status:
                    continue
                m = simunits.modifier(world.xml_of(e.template), a['mod'])
                if m is None or not aura.pulse(now):
                    continue
                until = now + (m['frames'] or a['refresh'])
                for t in live:
                    if t is e and not a['self']:
                        continue
                    if t.scenery or (a['include'] and not a['include'] & t.kinds) or a['exclude'] & t.kinds:
                        continue
                    if relation(e.owner, t.owner) not in a['relation']:
                        continue
                    if math.hypot(t.x - e.x, t.y - e.y) <= a['range']:
                        t.auras_on[a['mod']] = (until, world.xml_of(e.template))
        for b in live:
            if b.auras_on or b.base is not None:
                modify(b)
