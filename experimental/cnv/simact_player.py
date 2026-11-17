"""L6 script actions on the player systems (ADR 0029, docs/engine/sim-layers.md; L4): ownership, base power, special
powers granted, money, upgrades, protocols and the skirmish AI's switches.

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS.
A guarded one returns False where its guard fails (Sim.act's chain goes on, as before the move). They still reach the
Sim directly (sim.money, sim.books, ...): once the player systems are behind simmoney / simtech interfaces they call
those."""
import simtech
import simunits
from simworld import GAP_ACTION

# the skirmish AI's script switches, kept per player for simai (work/re l4_aiswitches.md; docs/engine/aiswitches.md)
AI_SWITCHES = ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', 'SKIRMISH_AI_USE_REPAIRS', 'SKIRMISH_AI_USE_REBUILD_SYSTEM')


def player_transfer_ownership_player(sim, name, a, script):
    # (from, to) the program (work/re/a217_transfer.md) calls the receiver's method with the giver. Bench 11-14
    # engine_acts_x own (round 217, twice): only the giver's units on no team a script names change hands --
    # Soviet_2's (off their teams since the container's start-up hand-over, skirmish_setup) and a Soviet_5
    # conscript UNIT_AI_TRANSFER took off its crew; ones on a team stay (teamSoviet_5's tank, Soviet_6's
    # conscript, a crew's, a Soviet_2 conscript put back on a crew). The giver's money goes whole to the
    # receiver (Player_1 1000 -> ~6000, Soviet_5 5000 -> < 100). Structures alike (INFERRED: only units placed)
    for b in sim.living():
        if b.owner == a[0] and not b.team:
            b.owner = a[1]
            sim.note('易主', f'{sim.label(b)} 归 {sim.who(a[1])}')
    sim.money[a[1]] = sim.money.get(a[1], 0) + sim.money.get(a[0], 0)
    sim.money[a[0]] = 0
    sim.change()


def named_transfer_ownership_player(sim, name, a, script):
    b = sim.body(a[0])
    if b and b.owner != a[1]:
        b.owner = a[1]
        sim.note('易主', f'{sim.label(b)} 归 {sim.who(a[1])}')
        sim.change()


def player_set_base_power(sim, name, a, script):
    # (player, n) INFERRED: n supply on top of its objects'
    sim.base_power[a[0]] = int(a[1])
    sim.change()


def player_grant_special_power(sim, name, a, script):
    # GRANT (power, player): the power's RequiredPlayerTech given, ready at once; COUNTDOWN (player, power, s):
    # ready s whole seconds on (d115 24: now + s x 15), only where held (not granted: nothing). Bench 11-13
    # engine_acts_u (spellbook_ready); a building's power (no RequiredPlayerTech) falls to the gap below
    if not ((simtech.power_needs(str(a[0] if name == 'PLAYER_GRANT_SPECIAL_POWER' else a[1])) or (None,))[0]):
        return False
    power, who = (a[0], a[1]) if name == 'PLAYER_GRANT_SPECIAL_POWER' else (a[1], a[0])
    tech = simtech.power_needs(str(power))[0]
    for p in sim.book_players(who):
        if name == 'PLAYER_GRANT_SPECIAL_POWER':
            sim.books[p].owned.add(tech)
            sim.power_at[(p, str(power).lower())] = sim.frame_now()
        elif sim.books[p].has(tech):
            sim.power_at[(p, str(power).lower())] = sim.frame_now() + int(a[2]) * simunits.LIFE_FPS
    sim.used.add('protocols')


def player_special_power_availability(sim, name, a, script):
    # (player, power, Available / Disabled / Hidden) INFERRED: the player's click refused unless Available
    # (power_refusal); a script's cast goes all the same. engine_scripts8 pdis asks the bench
    sim.powers_off[(a[0], str(a[1]).lower())] = str(a[2])


def player_toggle_resource_sharing(sim, name, a, script):
    # (player, on) d115 19: read when money comes in (earn)
    (sim.sharing.add if int(a[1]) else sim.sharing.discard)(a[0])


def team_upgrade(sim, name, a, script):
    # Living current members, with the ordinary object-upgrade consumers.
    # engine_teamup:a measures two Guardians and untouched other teams;
    # future members, absent/dead teams and map-local upgrades remain gaps.
    for b in sim.members(a[0]):
        sim.give_upgrade(b, a[1])


def named_receive_upgrade(sim, name, a, script):
    # (upgrade, object): recorded; of what an upgrade
    b = sim.body(a[1])                                              # does to a unit only the SPEED modifier is
    if b:                                                            # simulated (units/pace.py's 齐步); a range,
        sim._upgrade(b, a[0], name == 'NAMED_RECEIVE_UPGRADE')     # a shield are not; a tier (can_build) is


def allow_disallow_one_upgrade(sim, name, a, script):
    # (player, upgrade, allow): retail campaigns ban Tech2/3 with 0
    (sim.banned_ups.discard if a[2] else sim.banned_ups.add)((a[0], str(a[1]).lower()))


def player_set_money(sim, name, a, script):
    sim.money[a[0]] = a[1]


def player_give_money(sim, name, a, script):
    sim.money[a[0]] = sim.money.get(a[0], 0) + a[1]


def player_set_money_cap(sim, name, a, script):
    # (player, cap): bench 11-13 engine_acts_tel -- no script's money is held to it (give 5000 over a 3000 cap,
    # a 500 cap under 6000, set 10000 over it: all kept); harvest income is held to it (Sim._pay, bench 11-15 mineturn0 cap / capz)
    sim.money_cap[a[0]] = int(a[1])


def allow_disallow_one_building(sim, name, a, script):
    # the AI's production is not simulated; the player's 造 is
    (sim.banned.discard if a[2] else sim.banned.add)((a[0], str(a[1]).lower()))


def give_player_upgrade(sim, name, a, script):
    # (player, upgrade): a PLAYER upgrade; an OBJECT one (the tiers)
    # it gives unlocks nothing (bench 11-07 engine_tech b)
    sim.player_ups.setdefault(a[0], set()).add(a[1])
    for b in sim.living():
        if b.owner == a[0]:
            sim.modify(b)


def player_set_max_player_power_points(sim, name, a, script):
    sim.used.add('protocols')                  # (player, n) / (player, protocol, on): simtech.Book
    for book in sim.books_of(a[0]):
        if name == 'PLAYER_SET_MAX_PLAYER_POWER_POINTS':
            book.set_cap(a[1])
        elif name == 'PLAYER_SET_PLAYER_POWER_POINTS':
            book.set_points(a[1])
        elif not book.lock(str(a[1]), bool(int(a[2]))):
            sim.gap(GAP_ACTION, name, f'{a[1]} 不是协议：游戏也不管')


def skirmish_ai_set_all_enemy_players_priorities(sim, name, a, script):
    # (player, value): the skirmish AI's script switches; what
    sim.ai_switches.setdefault(a[0], {})[name] = int(a[1])     # they do is simai's (engine line B)


def skirmish_ai_set_enemy_player_priority(sim, name, a, script):
    # (player, enemy, n): one entry of the AI's enemy
    sim.ai_priorities.setdefault(a[0], []).append((a[1], int(a[2])))     # table, in order (simai)


def skirmish_ai_set_favored_enemy(sim, name, a, script):
    # (player, enemy): the enemy table emptied, then that enemy alone at score 10 (program, work/re
    # a219_skirmish_transfer.md 2; bench checks/engine_aifav.py). (None, 0) = the clear: simai tells the
    # model 'enemy priorities' 0 (asked of engine line B, work/re a220_favored_enemy.md)
    sim.ai_priorities.setdefault(a[0], []).extend([(None, 0), (a[1], 10)])


def skirmish_ai_transfer_all(sim, name, a, script):
    # (player, on): UNIT_AI_TRANSFER_ALL's team step without its AI wake (program, work/re
    # a219_skirmish_transfer.md; the wake left out is INFERRED, not benched). Bench 11-14 engine_acts_z all:
    # on -- off every team; off -- every unit on no team back onto the map's default team (teamSoviet_N,
    # not the crew it came from); a player never handed keeps its own -- and each default team counts one
    # member more than its units (Soviet_6's too, never handed: 1 -> 2): a hidden object every player has
    # on defaultSkirmishTeam from the start (its PlayerSpellBook: INFERRED, which object is not read)
    if int(a[1]):
        sim.off_teams((a[0],))
        sim.hidden_home.discard(a[0])
    else:
        sim.hidden_home.add(a[0])
        side = next((s for s, p in sim.players.items() if p == a[0]), None)
        home = sim.mm.team(side) if side else ''
        for b in sim.living():
            if b.owner == a[0] and not b.team and home:
                b.team = home
                sim.active.add(home)


def player_toggle_skirmish_ai(sim, name, a, script):
    # (player, on): the AI's paused byte = not on (program, work/re a270_skirmish_start.md); its per-frame
    # update does nothing while paused -- simai Brain.tick (bench aipause:a)
    if a[0] in sim.players.values():
        (sim.ai_paused.discard if int(a[1]) else sim.ai_paused.add)(a[0])
    else:
        sim.gap('ScriptAction', name, '开关遭遇战 AI 仅具名玩家已量；玩家范围未量')


def unit_ai_transfer_all(sim, name, a, script):
    # SKIRMISH_AI_START = UNIT_AI_TRANSFER_ALL's wake alone, no team step (program, work/re
    # a270_skirmish_start.md). MAKE_BASE wakes nobody (program; bench ainowake:a / aixfer:a, no library:
    # MAKE_BASE + money, with or without the team step, never spends): it stands in for the wake only for
    # the library's players (Lib_Skirmish_Setup's frame-0 UNIT_AI_TRANSFER_ALL; engine line B's simai is
    # fitted to the mission's own wake). Building also needs a yard handed to the AI: simai Brain.yards.
    sim.used.add('ai')
    if name == 'UNIT_AI_TRANSFER_ALL' and int(a[1]):
        sim.off_teams((a[0],))
    woke = (name in ('SKIRMISH_AI_START', 'UNIT_AI_TRANSFER_ALL')    # TRANSFER_ALL wakes either way (a219)
            or name == 'SKIRMISH_AI_MAKE_BASE' and a[0] in sim.library_ai)
    if woke and a[0] not in sim.ai:
        sim.ai[a[0]] = sim.t
        sim.note('AI', f'{sim.who(a[0])} 交给遭遇战 AI（造兵、进攻不模拟）')


ACTIONS = {
    'PLAYER_TRANSFER_OWNERSHIP_PLAYER': player_transfer_ownership_player,
    'NAMED_TRANSFER_OWNERSHIP_PLAYER': named_transfer_ownership_player,
    'PLAYER_SET_BASE_POWER': player_set_base_power,
    'PLAYER_GRANT_SPECIAL_POWER': player_grant_special_power,
    'PLAYER_SET_SPECIAL_POWER_COUNTDOWN': player_grant_special_power,
    'PLAYER_SPECIAL_POWER_AVAILABILITY': player_special_power_availability,
    'PLAYER_TOGGLE_RESOURCE_SHARING': player_toggle_resource_sharing,
    'TEAM_UPGRADE': team_upgrade,
    'NAMED_RECEIVE_UPGRADE': named_receive_upgrade,
    'NAMED_REMOVE_UPGRADE': named_receive_upgrade,
    'ALLOW_DISALLOW_ONE_UPGRADE': allow_disallow_one_upgrade,
    'PLAYER_SET_MONEY': player_set_money,
    'PLAYER_GIVE_MONEY': player_give_money,
    'PLAYER_SET_MONEY_CAP': player_set_money_cap,
    'ALLOW_DISALLOW_ONE_BUILDING': allow_disallow_one_building,
    'GIVE_PLAYER_UPGRADE': give_player_upgrade,
    'PLAYER_SET_MAX_PLAYER_POWER_POINTS': player_set_max_player_power_points,
    'PLAYER_SET_PLAYER_POWER_POINTS': player_set_max_player_power_points,
    'PLAYER_LOCK_PLAYER_TECH': player_set_max_player_power_points,
    **dict.fromkeys(AI_SWITCHES, skirmish_ai_set_all_enemy_players_priorities),
    'SKIRMISH_AI_SET_ENEMY_PLAYER_PRIORITY': skirmish_ai_set_enemy_player_priority,
    'SKIRMISH_AI_SET_FAVORED_ENEMY': skirmish_ai_set_favored_enemy,
    'SKIRMISH_AI_TRANSFER_ALL': skirmish_ai_transfer_all,
    'PLAYER_TOGGLE_SKIRMISH_AI': player_toggle_skirmish_ai,
    'UNIT_AI_TRANSFER_ALL': unit_ai_transfer_all,
    'SKIRMISH_AI_MAKE_BASE': unit_ai_transfer_all,
    'SKIRMISH_AI_START': unit_ai_transfer_all,
}
