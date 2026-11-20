"""L6 script conditions on a player's systems (ADR 0029, docs/engine/sim-layers.md; L4): protocols and their points,
special powers ready and cast, power, credits, upgrades, and who plays the side (human or which AI).

Each condition is `fn(sim, name, a)`, moved verbatim out of Sim.cond's chain; simcond.cond looks them up in
CONDITIONS. None back: not taken (a gap; SKIRMISH_SPECIAL_POWER_READY of a power no protocol gives)."""
import simtech
from simscript import CMP
from simworld import inside


def player_has_comparison_power_points(sim, name, a):
    # (player, comparison, n): the points to spend
    sim.used.add('protocols')
    sim.tech_read = True
    return int(a[1]) in CMP and any(CMP[int(a[1])](b.points, int(a[2])) for b in sim.books_of(a[0]))


def player_has_player_tech(sim, name, a):
    # (player, protocol): held (a rank's, bought, the default)
    sim.used.add('protocols')
    sim.tech_read = True
    return any(b.has(str(a[1])) for b in sim.books_of(a[0]))


def skirmish_special_power_ready(sim, name, a):
    if not ((simtech.power_needs(str(a[1])) or (None,))[0]):
        return None
    sim.used.add('protocols')
    return sim.spellbook_ready(a[0], str(a[1]))


def player_triggered_special_power(sim, name, a):
    # (player, power[, named / area]): the player's casts wait in a list until a reader TAKES one -- the
    # first condition that matches erases the entry (Generals' ScriptEngine::isSpecialPowerTriggered,
    # removeFromList TRUE); one no one reads stays. engine_cast all (round 242, bench 11-15
    # CampCastAll_mcp_1115_040813): 名 1 / 3 -- each shockwave read by its own FROM_NAMED reader only, the
    # same-named reader after it and PLAYER_TRIGGERED never; the belt read by a reader enabled 3 s after it
    # (+16: two entries, simunits.press_records); 区 1 / 5 -- IN_AREA looks at the cast's point (the hive's
    # own zone never), the cast outside both zones taken by PLAYER_TRIGGERED, FROM_NAMED(hive) never.
    # Seen from the next frame's scripts (bench 11-09 engine_scripts8b pfire 施放数 1, pdis 2). INFERRED:
    # FROM_NAMED with the named unit dead is false (Generals looks the object up). The cast keeps its caster's
    # serial (Generals: the ObjectID; same-name sweep 11-19b O38 -- by name, a unit made under the dead caster's name
    # took its cast, and a reference pointing at the caster missed it)
    now = sim.frame_now()
    for k, (f, owner, power, who, q) in enumerate(sim.casts):
        if f >= now or owner != a[0] or power != str(a[1]).lower():
            continue
        if name.endswith('_FROM_NAMED'):
            src = sim.body(a[2])
            if src is None or not src.alive or src.serial != who:
                continue
        if name.endswith('_IN_AREA') and not (q and inside(sim.areas[a[2]], *q)):
            continue
        del sim.casts[k]
        return True
    return False


def player_excess_power_compare_value(sim, name, a):
    # (player, cmp, n): supply - demand (the engine model's
    sup, dem = sim.power(a[0])                     # world.py reads it so; not measured)
    sim.used.add('power')
    return CMP[a[1]](sup - dem, a[2])


def player_has_power(sim, name, a):
    has_power = not sim.infiltrators.disabled(a[0]) and not sim.short_of_power(a[0])
    return has_power if name == 'PLAYER_HAS_POWER' else not has_power


def player_is_human_or_ai_personality(sim, name, a):
    # (player, personality) l2_scripts1 2.1: "Human" = the player has no AI; else its AI's personality is the
    # name. Bench 11-08 engine_scripts1 cond: Player_1 Human holds, Soviet_1 (a campaign computer player, its
    # AI never woken) is not Human from the start -- every computer player has its AI object
    # The map keeps the personality as an asset reference ('AIPersonalityDefinition:AIP_A03_Coop_...'), the
    # script names it bare: compared by the name after the type, case aside (asset names)
    if a[1] == 'Human':
        return a[0] == sim.human
    want = str(a[1]).split(':')[-1].lower()
    if a[0] in sim.personality_of:     # its AI took another one than the map named (bench aisksd2)
        return sim.personality_of[a[0]].lower() == want
    return a[0] != sim.human and any(sim.players.get(s) == a[0] and
                                      str(p.get('aiPersonality', '')).split(':')[-1].lower() == want
                                      for s, p in getattr(sim.m, 'sides', {}).items())


def player_has_num_units_with_upgrade(sim, name, a):
    # (player, n, upgrade): the player's living objects holding it -- its own (a bought OBJECT upgrade) or by
    # a TechUpgradeReceiver near a holder (holds_upgrade's tiers). INFERRED >= n and the receiver counting:
    # bench 2026-11-12 engine_aiupgrade a aicupgon (C line) reads 2 holders with one yard, its barracks beside
    low = a[2].lower()
    n = sum(1 for b in sim.living() if b.owner == a[0] and not b.scenery
            and (low in {u.lower() for u in b.upgrades} or sim._tier_held(a[0], b, low)))
    return n >= a[1]


def player_has_credits(sim, name, a):
    # retail batch 1 (round 207, checks/engine_conds.py; d115_script_semantics.md where it says 码)
    # (player, comparison, n)
    return CMP[int(a[1])](int(sim.money.get(a[0], 0)), int(a[2]))


CONDITIONS = {
    'PLAYER_HAS_COMPARISON_POWER_POINTS': player_has_comparison_power_points,
    'PLAYER_HAS_PLAYER_TECH': player_has_player_tech,
    'SKIRMISH_SPECIAL_POWER_READY': skirmish_special_power_ready,
    'PLAYER_TRIGGERED_SPECIAL_POWER': player_triggered_special_power,
    'PLAYER_TRIGGERED_SPECIAL_POWER_FROM_NAMED': player_triggered_special_power,
    'PLAYER_TRIGGERED_SPECIAL_POWER_IN_AREA': player_triggered_special_power,
    'PLAYER_EXCESS_POWER_COMPARE_VALUE': player_excess_power_compare_value,
    'PLAYER_HAS_POWER': player_has_power,
    'PLAYER_HAS_NO_POWER': player_has_power,
    'PLAYER_IS_HUMAN_OR_AI_PERSONALITY': player_is_human_or_ai_personality,
    'PLAYER_HAS_NUM_UNITS_WITH_UPGRADE': player_has_num_units_with_upgrade,
    'PLAYER_HAS_CREDITS': player_has_credits,
}
