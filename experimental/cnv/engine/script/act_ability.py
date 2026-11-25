"""L6 script actions pressing buttons and casting powers (ADR 0029, docs/engine/sim-layers.md; L2): a named unit's or a
team's command button (capture, build, deploy and pack, garrison ejects, weapon-fire abilities, at a waypoint or on an
object) and a player's or a unit's special power at a waypoint (superweapon hits, the curtains).

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS.
The button family is one function (`named_buttons`): its guarded branches share names, kept in the old chain's order.

A button press is a command through the run's command port (`_order`: a Command by 'script', its unit the object's name;
R3 13d-2): a capture, a factory's build button, an unpack, a toggle, the weapon-fire / leap / movement / self powers
(`power` with `via`: the action picks the module entry by what the unit's template has). Not orders, so not through it:
- `script_cast`, the special power's cast (NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT and the buttons left over): the
  SpecialPower module's effect, not a giver's order -- the player's `power` command comes to it too (order_power ->
  this action), so the port cannot route to it until the module (M8) holds it. The ice engineer's walk and build
  there (R5, AssembleStructureSpecialAbilityUpdate) is that effect: a `power` the unit's module carries out (the
  structure is the module's, not the giver's), not `place` (a builder told a template and a spot by its player);
- the god's-hand / effect branches of named_buttons: a yard packing back (replace, due), the drop store's and the
  time belt's recorded casts, the ejects and the repair dispatch (their own modules, no command kind yet)."""
import math
import random

import engine.objects.garrison as simgarrison
import engine.data.units as simunits
import engine.objects.locomotion as simlocomotion
import engine.players.tech as simtech
from engine.kernel import interfaces, module
from engine.ports.command import Command
from engine.objects.power import (CRASH, CRASH_AT, CRASHES, CURTAIN, PACK_FRAMES, PACK_POWER, PROTOCOL_HITS, RELOAD_LAG,
                                  SQUADRON, SUPERWEAPON_HITS, UNPACK_POWER, start_reload)
from engine.script.common import hand_over, players_of, refined, stands, team_crew
from engine.world.handle import GAP_ACTION, free_name


def _order(sim, kind, unit, *args, **fields):
    """A map script's button press through the run's command port: (ok, why). `unit` the object's name as the action
    found it, or the object a team action picked (by serial: review 11-19 i #2); None: no unit (a factory's build);
    `args` more (name, value) pairs."""
    if unit is None or isinstance(unit, str):
        units, by = () if unit is None else (unit,), True
    else:
        units, by = (unit.serial,), 'serial'
    return sim.commands.do(Command(kind, 'script', units=units, args=(('objects', by),) + args, **fields))


def power_spelling(power):
    """A script's power name as the data spells it: retail writes 'specialpowernanoswarmhive' (s03, a07, j07) and the
    game finds it whatever its case (bench engine_super x)."""
    low = str(power).lower()
    return next((k for k in (*SUPERWEAPON_HITS, *CURTAIN, *simunits._retail_power_heads()) if k.lower() == low), power)


def named_buttons(sim, name, a, script, unit=None):
    """The button on `a[0]` -- or on `unit`, a member a team action picked (the object itself, not a reference that
    has its name: review 11-19 i #2)."""
    if name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT':
        a = [a[0], power_spelling(a[1]), *a[2:]]
    body = (lambda _n: unit) if unit is not None else sim.body
    who = unit if unit is not None else a[0]
    cpower = simunits.command_power(a[1], sim.own)      # the button's power (None for a power name or no such button)
    things = sim.bodies.values()                        # the recall's and the bribe's
    evacuate = lambda: (simunits._commands(sim.own)[1].get(a[1]) or ('',))[0] == 'EVACUATE'    # noqa: E731
    if name == 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED' and a[1] == 'Command_CaptureBuilding':
        _order(sim, 'capture', who, target=a[2])
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            simunits.built(body(a[0]).template, a[1], sim.own, body(a[0]).upgrades):
        # a factory's build button: queued there as the player's click (bench engine_production e); a banned unit
        # queued all the same and waits (g); refused where the player's click would be for the rest (can_build:
        # tier, a factory still unpacking -- INFERRED, not measured)
        f = body(a[0])
        tmpl = simunits.built(f.template, a[1], sim.own, f.upgrades)
        # the factory as the action found it, by serial (same-name sweep 11-19b O07: by name the port read `a[0]`
        # again, a reference of a member's name took its press)
        if not _order(sim, 'build', None, ('press', True), ('target_serial', f.serial), player=f.owner,
                      template=tmpl, target=f.name)[0]:
            sim.note('生产', f'{sim.label(f)} 按 {a[1]}：现在造不了 {tmpl}')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and simgarrison.ejects(a[1], sim.own):
        # a transport's eject at the spot (simgarrison; bench 11-10 engine_transport load 跳)
        b, p = body(a[0]), sim.point(a[2])
        if not (b and p is not None and sim.garrison.eject(b, a[1], p)):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有能弹出乘员的载具或路点')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and simgarrison.ejects(a[1], sim.own):
        # the untargeted eject (a01's intro bombers, SovietSupportBomber_S07): out where it is (engine_acts_btn EJ)
        b = body(a[0])
        if not (b and sim.garrison.eject(b, a[1], (b.x, b.y))):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有能弹出乘员的载具')
    elif name in ('NAMED_USE_COMMANDBUTTON_ABILITY', 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT') and body(a[0]) \
            and (a[1] == 'Command_UnPackJapanEgg' or evacuate() or
                 cpower in (UNPACK_POWER, PACK_POWER)) and a[1] not in \
            simunits._commands(sim.own)[0].get(simunits.command_set(body(a[0]).template, body(a[0]).upgrades, sim.own), ()):
        # an unpack / pack button the unit's own CommandSet lacks does nothing, though its ReplaceSelf module takes
        # the same power: retail's legacy egg id (engine_eggcmd / engine_eggnav), the power plant egg's button on
        # the defense egg (engine_unpack crs), an egg's on a Guardian (review 1121oo #1); the pack side INFERRED;
        # so does an EVACUATE button not the host's (the Sudden transport's on a Twinblade, review 1122yy #1;
        # INFERRED as the pack side: every benched evacuate was its host's own)
        sim.note('技能', f'{a[0]} 按 {a[1]}：它的 CommandSet 里没有这个按钮，不动')
    elif name in ('NAMED_USE_COMMANDBUTTON_ABILITY', 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT') and evacuate():
        # the Twinblade's evacuate (s09's Hinds): lands, all out together where it is (engine_acts_btn EV); a
        # waypoint given is ignored (a05's: engine_acts_eva w, nobody at the point 600 off)
        if not sim.garrison.evacuate(body(a[0])):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有载着人的载具')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and \
            cpower == UNPACK_POWER:
        # an MCV / a Japanese egg deploys at the point: drives there, then turns into its replacement (bench
        # engine_unpack mcv / egg: the yard stands on the point, the name passes on)
        b, p = body(a[0]), sim.point(a[2])
        if not (b and p is not None and _order(sim, 'unpack', who, ('button', a[1]), place=a[2])[0]):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有能展开的单位或路点')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and cpower == UNPACK_POWER:
        # untargeted (a07 / s07's eggs when hit): nothing unfolds, and one on its way to unpack stops short (bench
        # engine_unpack pin / mid; a stop: INFERRED)
        _order(sim, 'stop', who)
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            cpower == PACK_POWER and \
            simunits.replace_self(body(a[0]).template, a[1], sim.own):
        # a construction yard packs back into its MCV where it stands (engine_pack a / s / j)
        b = body(a[0])
        _, into = simunits.replace_self(b.template, a[1], sim.own)
        sim.used.add('unpack')
        b.replace = True
        sim.production.pack(b, into, PACK_FRAMES, simunits.replace_unpack_frames(b.template, a[1], sim.own))
        sim.note('技能', f'{sim.label(b)} 收起成 {into}')
        sim.production.put_down(sim.frame_now())     # the press frame's later scripts already see the MCV
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED' and \
            body(a[0]) and body(a[0]).alive and \
            sim.assignments.press(body(a[0]), a[1], sim.body(a[2])):
        sim.note('技能', f'{a[0]} 显式派发维修到 {a[2]}')
        _seen(sim, body(a[0]).owner, cpower, body(a[0]).serial)    # E66: seen cast once (a refused press too: INFERRED)
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and body(a[0]) and body(a[0]).alive and \
            sim.point(a[2]) is not None and simunits.ocl_power(
                body(a[0]).template, cpower or '', sim.own):
        # engine_acts_wet DP / DS (round 226): the campaign bomber drop store's button is seen cast
        # (PLAYER_TRIGGERED_SPECIAL_POWER) the player's and the computer's alike; its load: _drop
        b = body(a[0])
        q = sim.point(a[2])
        sim.casts.append((sim.frame_now(), b.owner, cpower.lower(), b.serial, q))
        if not _drop(sim, b, cpower, q):
            sim.note('技能', f'{sim.label(b)} 按 {a[1]}：算放了，没出东西（推断）')
    elif name in ('NAMED_USE_COMMANDBUTTON_ABILITY', 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED') and \
            body(a[0]) and body(a[0]).alive and \
            simunits.weapon_fire_ability(body(a[0]).template, a[1], sim.own):
        _order(sim, 'power', who, ('via', 'wfire'), ('button', a[1]), target=a[2] if len(a) > 2 else '')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and body(a[0]) and body(a[0]).alive and \
            sim.point(a[2]) is not None and simunits.weapon_fire_ability(body(a[0]).template, a[1], sim.own) \
            and simunits.self_projectile_speed(
                simunits.weapon_fire_ability(body(a[0]).template, a[1], sim.own)['weapon'], sim.own):
        _order(sim, 'power', who, ('via', 'leap'), ('button', a[1]), place=a[2])
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and body(a[0]) and body(a[0]).alive and \
            sim.point(a[2]) is not None and simunits.movement_power(body(a[0]).template, a[1], sim.own):
        _order(sim, 'power', who, ('via', 'movement'), ('button', a[1]), place=a[2])
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            simunits.self_module_power(body(a[0]).template, a[1], sim.own):
        _order(sim, 'power', who, ('via', 'self'), ('button', a[1]))
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            _order(sim, 'power', who, ('via', 'micro'), power=a[1])[0]:
        # the warrior's Bonzai (y01 / y03): the AI micro's charge (engine_aimicro c: the press is seen charging;
        # its reload heeded, INFERRED: retail presses once)
        pass
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and \
            _order(sim, 'toggle', who, ('button', a[1]))[0]:
        sim.note('技能', f'{a[0]} 按 {a[1]} 切换状态')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            simunits.press_records(body(a[0]).template, a[1], sim.own):
        # engine_cast (round 242): Tanya's time belt seen cast twice (simunits.press_records); engine_storestate_e
        # (E223): it takes her back to the oldest state her StoreCurrentStateUpdate keeps, place and health
        b = body(a[0])
        power, n = simunits.press_records(b.template, a[1], sim.own)
        sim.used.add('special power')
        _seen(sim, b.owner, power, b.serial, n=n)
        sim.note('技能', f'{sim.label(b)} 按 {a[1]}：记 {n} 次施放')
        back = next((m.oldest() for m in b.find(interfaces.Rewind) if m.oldest()), None) if n > 1 else None
        if back:
            b.x, b.y = back[:2]
            if b.hp > back[2]:
                b.damage(b.hp - back[2])
            else:
                b.mend(back[2] - b.hp)
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and any(
            m.power() == cpower for m in body(a[0]).find(interfaces.Dominate)):
        # engine_dominate_e (E216): the spy's bribe takes the enemies around it the press's frame
        b = body(a[0])
        _seen(sim, b.owner, cpower, b.serial)
        hand_over(sim, [t for m in b.find(interfaces.Dominate) if m.power() == cpower
                        for t in m.taken(list(things), lambda x, y, w: stands(sim, x, y, w))], b.owner, '被收买')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and any(
            m.power() == cpower for m in body(a[0]).find(interfaces.Recall)):
        # engine_recall_e (E184): the airport's recall seen cast once, the plane it made flies back to it;
        # engine_returnproducer_e (E173): the Apollo's own return, cast once, USER_1 on, it flies to its airport
        b, power = body(a[0]), cpower
        _seen(sim, b.owner, power, b.serial)
        for m in (m for m in b.find(interfaces.Recall) if m.power() == power):
            if m.mark():
                sim.set_model_condition(b, *m.mark())
            for p, home in m.flights(things):
                _order(sim, 'move', p, pos=(home.x, home.y))
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and \
            cpower in SUPERWEAPON_HITS:
        # a superweapon's button at a waypoint (s08's imploder): nothing, ready or not, no cast seen (bench
        # engine_super b / u, the player's imploder; the computer's and the other superweapons' INFERRED the same)
        pass
    elif name in ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', 'NAMED_USE_COMMANDBUTTON_ABILITY'):
        script_cast(sim, name, a, unit)
    else:
        return False


def script_cast(sim, name, a, unit=None):
    """A special power's cast by a script (and a button none of named_buttons' branches took): the SpecialPower
    module's effect, where the player's `power` command comes too (order_power); no order (module docstring). `unit`:
    the member a team action picked (named_buttons)."""
    b = unit if unit is not None else sim.body(a[0])
    # engine_oclnone / engine_oclwrong: no matching host module means
    # neither protection nor PLAYER_TRIGGERED_SPECIAL_POWER event.
    if b and b.alive and a[1] == 'SpecialPowerIronCurtain' and \
            not simunits.ocl_power(b.template, a[1], sim.own):
        sim.note('技能', f'{sim.label(b)} 没有匹配的铁幕 OCLSpecialPower')
        return
    if b and b.alive and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT':
        # bench 11-09 engine_scripts8b pfire / pdis: every script cast (the player-level one too, a second
        # one in the reload that hurts nobody) is seen by PLAYER_TRIGGERED_SPECIAL_POWER for one frame
        sim.casts.append((sim.frame_now(), b.owner, str(a[1]).lower(), b.serial,
                           sim.point(a[2]) if len(a) > 2 else None))
    got = b and b.alive and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' and \
        simunits.assemble(b.template, a[1], sim.own)
    p = sim.point(a[2]) if got and got[1] else None
    if p is not None:                       # R5: he walks there and builds (the ice engineer's core)
        sim.used.add('assemble')           # a script's cast heeds neither reload nor placing rules
        rules = simunits.power_rules(b.template, a[1], sim.own)    # (bench engine_skill a-c, w); it
        if rules and rules['reload']:                               # starts the reload all the same
            start_reload(sim, b, a[1], sim.frame_now() + rules['reload'])   # (RA3 1.13, read, l2_ability.md)
        b.building, b.goal, b.mode = (got[1], p, got[0]), None, 'move'
        sim.note('技能', f'{sim.label(b)} 去 {a[2]} 造 {got[1]}')
        if not sim.production.at_site(b, 0.0):
            simlocomotion.go_to(sim, b, p)
    else:
        sim.used.add('special power')
        sim.note('技能', f'{a[0]} 用 {a[1]}' + (f' 打 {a[2]}' if len(a) > 2 else ''))
        q = sim.point(a[2]) if len(a) > 2 and name == 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT' else None
        rules = simunits.power_rules(b.template, a[1], sim.own) if b and b.alive else None
        # bench 11-09 engine_scripts8b pdis: a second script cast ~20 s after the first (the collider's
        # reload, set by that cast, not over) is seen as triggered but hurts nobody; the first cast of a
        # collider never cast went though its power was not charged (engine_super p / q). INFERRED: a cast
        # in the reload a cast started brings no blast
        cooling = bool(b and b.alive and b.ready_at.get(a[1], 0) > sim.frame_now())
        if rules and rules['reload']:       # every cast starts the reload anew (RA3 1.13, read, work/re/l2_ability.md;
            start_reload(sim, b, a[1],                                                  # SDK GlobalData)
                         sim.frame_now() + rules['reload'] + RELOAD_LAG.get(a[1], 0))
        hits = SUPERWEAPON_HITS.get(a[1]) if b and b.alive else None
        if hits and q is not None:
            sim.used.add('superweapon')
        if hits and q is not None and cooling:
            sim.note('技能', f'{sim.label(b)} 的 {a[1]} 还在重装：没打出来')
        elif hits and q is not None:       # a script's cast fires though the power is not ready
            _land(sim, sim.frame_now(), q, hits, b.owner, b)
        curtain_host = True
        if a[1] == 'SpecialPowerIronCurtain' and b and b.alive:
            module = simunits.ocl_power(b.template, a[1], sim.own)
            curtain_host = bool(module and simunits.iron_curtain_ocl(module['OCL'], sim.own) and
                                module['CreateLocation'] == 'CREATE_AT_LOCATION' and
                                module['CanAffectObjectFilter'] ==
                                'SovietIronCurtainSpecialPowerObjectFilter')
            empty_dispatch = bool(module and
                                  (simunits.empty_ocl(module['OCL'], sim.own) or
                                   simunits.iron_curtain_ocl(module['OCL'], sim.own, zero_count=True)) and
                                  module['CreateLocation'] == 'CREATE_AT_LOCATION' and
                                  module['CanAffectObjectFilter'] ==
                                  'SovietIronCurtainSpecialPowerObjectFilter')
            if module and not curtain_host and not empty_dispatch:
                sim.gap(GAP_ACTION, refined(name, a), 'OCLSpecialPower 配置未对拍，见 work/re/e_ocl_e62.md')
        if a[1] in CURTAIN and q is not None and b and b.alive and curtain_host:
            sim.used.add('superweapon')
            reach, lasts, kinds = CURTAIN[a[1]]
            for t in sim.living():
                # the reach to the object's bounding circle (bench engine_super o: a tank 807 off covered,
                # 832 not; 800 + its 23.3 radius -- INFERRED, R8's measure)
                if (kinds is None or t.kinds & kinds) and \
                        math.hypot(t.x - q[0], t.y - q[1]) - t.radius <= reach:
                    t.immune_until = sim.frame_now() + lasts
        if b and b.alive and not ((hits or a[1] in CURTAIN) and q is not None) and \
                not (q is not None and (_drop(sim, b, a[1], q) or _teleport(sim, b, a[1], q))):
            sim.gap(GAP_ACTION, refined(name, a), f'{a[1]} 只记进时间线（special power），没有效果')


def _drop(sim, b, power, p):
    """b's OCLSpecialPower `power` at p when its OCL makes transports firing their eject (the campaign bomber drop:
    two bombers, 3 GIs + 2 Javelins in each). Bench engine_acts_drop air / at (round 276): the load is counted (in
    its bombers) round the store the press's frame, past its line 7 frames on, within 150 of the spot 38 on, all
    ten round the spot after; the bombers themselves never (Sim.counted). CREATE_AT_EDGE_NEAR_SOURCE made them at
    the store, not at the map's edge 700 off (INFERRED: the source's place); each flies to the spot + its offset
    and empties there (garrison.eject). False when the OCL makes no such thing."""
    own = sim.own
    module = simunits.ocl_power(b.template, power, own)
    drops = simgarrison.ocl_transports(module['OCL'], own) if module else []
    for template, dx, dy, eject in drops:
        g = sim.add(free_name(sim, '#created', template), template, b.owner, b.x + dx, b.y + dy, at=sim.t)
        for name, n in simgarrison.initial_payload(template, own):
            for _ in range(n):
                sim.garrison.put(sim.add(free_name(sim, '#created', name), name, b.owner, g.x, g.y,
                                         at=sim.t), g, script=True)
        sim.garrison.eject(g, None, (p[0] + dx, p[1] + dy), power=eject)
    if drops:
        sim.note('技能', f'{sim.label(b)} 放 {power}：{len(drops)} 架运输机从它那儿飞去')
    return bool(drops)


def _teleport(sim, b, power, p):
    """The Chronosphere's two steps at p (E227, engine/modules/teleport.py): b's StoreObjectsSpecialPower of `power`
    takes the things round p, its TeleportStoredObjectsUpdate of `power` begins the carry to p. False: neither."""
    stores = [m for m in b.find(interfaces.Store) if m.power() == power]
    carries = [m for m in b.find(interfaces.Teleport) if m.power() == power]
    for m in stores:
        m.store(p)
    for m in carries:
        m.begin(p)
    return bool(stores or carries)


def player_fire_special_power_at_waypoint(sim, name, a, script):
    # (player, power, waypoint) the program (work/re l2_specialpower 4.2): the player's own PlayerSpellBook object
    # first when it has a module of the power, else its first living object that has it, as
    # NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT (a script's cast: no reload asked); none, nothing
    power, own, living = power_spelling(a[1]), sim.own, list(sim.living())
    book = power.lower() in simtech.spellbook_powers() and a[0] in sim.books
    src = None if book else next((b for b in living if b.owner == a[0]
                                  and simunits.power_rules(b.template, power, own)), None)
    if src:
        _member(sim, 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', [src.name, power, a[2]], script, src)   # itself
    elif not (book and _book_cast(sim, a, power, own, living)):
        sim.gap(GAP_ACTION, refined(name, a), f'{a[0]} 用 {a[1]}：' + ('协议只进冷却和时间线，效果不模拟' if book else
                                                                       '没有带它的物体'))


DRONE_KINDS, DRONE_NOT = {'VEHICLE', 'HUGE_VEHICLE', 'SHIP'}, {'INFANTRY', 'AIRCRAFT', 'SUBMARINE'}   # GlobalDefines
DRONE_NOT_STATUS = {'SUBMERGED', 'AIRBORNE_TARGET', 'IN_NANOHIVE', 'NOT_IN_WORLD'}    # and the drone's own bit


def _seen(sim, owner, power, serial, q=None, n=1):
    """n casts of `power` for PLAYER_TRIGGERED_SPECIAL_POWER (Sim.casts); the frame."""
    now = sim.frame_now()
    sim.casts += [(now, owner, power.lower(), serial, q)] * n
    return now


def _land(sim, now, q, hits, owner, by):
    """A superweapon table's hits (power.SUPERWEAPON_HITS / PROTOCOL_HITS) queued at q from frame `now`; a hit
    (after, table, (dx, dy), keep) lands dx, dy off q and takes nothing below `keep` of its health."""
    for after, table, *more in hits:
        (dx, dy), keep = (more[0], more[1:]) if more else ((0, 0), ())
        sim.blasts.append((now + after, q[0] + dx, q[1] + dy, table, owner, by, *keep))


def _book_cast(sim, a, power, own, living):
    """Player a[0]'s protocol `power` from its book at a[2]: held or not, ready or not, a yard or not (bench
    engine_acts_ui n / g, a328: both tanks got their drones, g's READY 3 -> 0); seen cast (no caster object); its
    ReloadTime starts (SKIRMISH_SPECIAL_POWER_READY reads it). The point defense drones: each of the player's own
    vehicles / ships within 100 (its bounding circle) is given POINT_DEFENSE_DRONE_ATTACHED (INFERRED: an allied
    player's left out; the drone itself, its leech and death, not simulated) -- True; every other protocol's effect is
    not simulated -- False. Orbital refuse rank 1 and the desolator bombs land as superweapon hits (PROTOCOL_HITS, bench
    engine_protofx: the player's, no caster object); the final squadron's crashes too (power.SQUADRON): CRASHES on
    each enemy non-infantry in the radius, drawn in a random order, the aircraft left over at random points in it."""
    p, q, key = a[0], sim.point(a[2]), power.lower()
    now, rules = _seen(sim, p, power, None, q), simunits.power_rules('PlayerSpellBook', power, own)
    sim.power_at[(p, key)] = now + (rules['reload'] if rules else 0)
    sim.used.add('special power')
    if key in PROTOCOL_HITS and q is not None:
        _land(sim, now, q, PROTOCOL_HITS[key], p, None)
        return True
    if key in SQUADRON and q is not None:
        planes, reach = SQUADRON[key]
        rng = random.Random(f'{p} {key} {now}')        # the simulator's own draw: the same every run
        foes = [t for t in living if stands(sim, p, t.owner, 'ENEMIES') and 'INFANTRY' not in t.kinds
                and math.hypot(t.x - q[0], t.y - q[1]) <= reach]
        rng.shuffle(foes)
        spots = [(t.x, t.y) for t in foes for _ in range(CRASHES)][:planes]
        while len(spots) < planes:
            turn, r = rng.uniform(0.0, 2 * math.pi), reach * math.sqrt(rng.random())
            spots.append((q[0] + r * math.cos(turn), q[1] + r * math.sin(turn)))
        _land(sim, now, q, [(CRASH_AT, CRASH, (x - q[0], y - q[1])) for x, y in spots], p, None)
        return True
    if key != 'specialpower_pointdefensedrones' or q is None:
        return False
    for t in living:
        if t.owner == p and t.kinds & DRONE_KINDS and \
                not t.kinds & DRONE_NOT and not module.status_now(t) & DRONE_NOT_STATUS and \
                'POINT_DEFENSE_DRONE_ATTACHED' not in t.status and \
                t.template != 'JapanPointDefenseDrone' and math.hypot(t.x - q[0], t.y - q[1]) - t.radius <= 100:
            t.status.add('POINT_DEFENSE_DRONE_ATTACHED')
    return True


def fire_special_power_on_team(sim, name, a, script):
    # (player, power, team): as PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT at the middle of the team's members; none,
    # nothing (work/re a283)
    crew = sim.members(a[2])
    if crew:
        x, y = _middle(crew)
        player_fire_special_power_at_waypoint(sim, name, [a[0], a[1], f'@{x},{y}'], script)


def fire_special_power_on_nearest_objecttype_by_player(sim, name, a, script):
    # (player, power, type, team, target players): as PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT at the target players'
    # living object of that type nearest the middle of the team's members (an empty team: the map's corner,
    # INFERRED), the first player in slot order that has one (a mask, <This Player's Enemies>); none, or no such
    # team: nothing (work/re a283)
    crew = team_crew(sim, a[3])
    if crew is None:
        return
    x, y, want = *_middle(crew), sim.of_types(a[2])
    goal = next((g for g in (min((o for o in _owned(sim, p) if o.template.lower() in want),
                                 key=lambda o: math.hypot(o.x - x, o.y - y), default=None)
                             for p in players_of(sim, a[4])) if g), None)
    if goal is not None:
        player_fire_special_power_at_waypoint(sim, name, [a[0], a[1], f'@{goal.x},{goal.y}'], script)


def skirmish_fire_special_power_at_most_cost(sim, name, a, script):
    # (player, power): the player's power where the human's things are worth most (work/re a297). R = the power's
    # RadiusCursorRadius (50 at least); a <= 10 x 10 grid over the box of the human's structures, its x sides (only)
    # pulled in by R (flipped: the middle), worth within 2R; then 11 x 11 steps of R/10 round the best, worth within
    # R, ties averaged. The foe: the script player's AI's current enemy, none for a campaign AI -> the first human
    # (bench engine_scripts8bm most: the y sides kept -- both pulled in missed the 300 one). INFERRED: a human caster
    # (no AI) aims at nothing
    head = next((v for k, v in simunits._retail_power_heads().items() if k.lower() == a[1].lower()), '')
    r = max(50.0, simunits._num(simunits._attr(head, 'RadiusCursorRadius'), 0.0))
    human = sim.human
    if a[0] == human:
        return
    foe, own = _owned(sim, human), sim.own
    xs, ys = [b.x for b in foe if 'STRUCTURE' in b.kinds] or [0.0], [b.y for b in foe if 'STRUCTURE' in b.kinds] or [0.0]
    lo, hi = min(xs) + r, max(xs) - r
    axes = [(lo, hi) if lo <= hi else ((lo + hi) / 2,) * 2, (min(ys), max(ys))]
    n = [min(10, math.ceil((hi - lo) / r) + 1) for lo, hi in axes]
    grid = [(axes[0][0] + i * (axes[0][1] - axes[0][0]) / n[0], axes[1][0] + j * (axes[1][1] - axes[1][0]) / n[1])
            for i in range(n[0]) for j in range(n[1])]
    bx, by = max(grid, key=lambda p: _worth(own, foe, p, 2 * r))
    fine = [(bx + (i - 5) * r / 10, by + (j - 5) * r / 10) for i in range(11) for j in range(11)]
    top = max(_worth(own, foe, p, r) for p in fine)
    best = [p for p in fine if _worth(own, foe, p, r) == top]
    x, y = sum(p[0] for p in best) / len(best), sum(p[1] for p in best) / len(best)
    player_fire_special_power_at_waypoint(sim, name, [a[0], a[1], f'@{x},{y}'], script)


def _worth(own, foe, p, r):
    # what the foe's things within r of p cost, each by 1 - d / 2r (a command centre's a tenth, then over 3000 a tenth;
    # flying aircraft not counted), whole (a297's 82f8e0)
    r, total = max(r, 80.0), 0.0
    for b in foe:
        d = math.hypot(b.x - p[0], b.y - p[1])
        if d < r and not ('AIRCRAFT' in b.kinds and b.surface == 'air'):
            cost = simunits.production(b.template, own)[0] * (0.1 if 'COMMANDCENTER' in b.kinds else 1.0)
            total += cost * (0.1 if cost > 3000 else 1.0) * (1 - d / (2 * r))
    return int(total)


def _owned(sim, player):
    return [o for o in sim.bodies.values() if o.alive and o.owner == player]


def _middle(crew):
    return (sum(b.x for b in crew) / len(crew), sum(b.y for b in crew) / len(crew)) if crew else (0.0, 0.0)


def team_use_commandbutton_ability(sim, name, a, script):
    # (team, button) l2_scripts1 8: the button on every living member, no target. Bench 11-08 button: both
    # Peacekeepers of the crew raised their shields
    team_partial_use_commandbutton(sim, name, [100.0, a[0], a[1]], script)


def team_partial_use_commandbutton(sim, name, a, script):
    # (percent, team, button): the button, no target, on the first ceil(percent x members) living members in their
    # order (j05's Rocket Angels at 100). Bench 11-23 engine_acts_rkt:p: 50 % of 4 the first two, 50 % of 3 the first
    # two, 1 % of 3 the first one (ceil, not round; max(1, round) not told apart: INFERRED)
    crew = sim.members(a[1])
    for b in crew[:math.ceil(float(a[0]) * len(crew) / 100.0)]:
        _member(sim, 'NAMED_USE_COMMANDBUTTON_ABILITY', [b.name, a[2]], script, b)


def team_use_commandbutton_ability_at_waypoint(sim, name, a, script):
    # (team, button, waypoint): the button at the spot on every living member (engine_acts_btn TB: the crew's
    # Bullfrog threw its passengers at the waypoint, as NAMED_..._AT_WAYPOINT did in round 152)
    for b in sim.members(a[0]):
        _member(sim, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', [b.name, a[1], a[2]], script, b)


def named_set_special_power_countdown(sim, name, a, script):
    # (unit, power, s): its power's reload ends s whole seconds on (0: ready now). E145 engine_modulebatch: the
    # monitor showed the collider ready after 0, not after 10000; checks/engine_aispecial (first try): 5.2 / 5.4 acted
    # as 0, the integer 5 as 75 frames (review yy #7). The player-level READY: C's gap
    b = sim.body(a[0])
    if b and b.alive:
        s = float(a[2])
        start_reload(sim, b, str(a[1]), sim.frame_now() + (int(s) if s == int(s) else 0) * simunits.LIFE_FPS)


def _member(sim, name, a, script, b):
    """A team button on one member as the named action is on it (Sim.act's run of it: a branch declined is a gap),
    the member itself pressed -- a reference of its name cannot take its place (review 11-19 i #2)."""
    if named_buttons(sim, name, a, script, unit=b) is False:
        sim.unknown[name] = sim.unknown.get(name, 0) + 1
        sim.gap(GAP_ACTION, refined(name, a), 'Sim.act 不认识：没效果')


ACTIONS = {
    'NAMED_SET_SPECIAL_POWER_COUNTDOWN': named_set_special_power_countdown,
    'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED': named_buttons,
    'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT': player_fire_special_power_at_waypoint,
    'FIRE_SPECIAL_POWER_ON_TEAM': fire_special_power_on_team,
    'FIRE_SPECIAL_POWER_ON_NEAREST_OBJECTTYPE_BY_PLAYER': fire_special_power_on_nearest_objecttype_by_player,
    'SKIRMISH_FIRE_SPECIAL_POWER_AT_MOST_COST': skirmish_fire_special_power_at_most_cost,
    'TEAM_USE_COMMANDBUTTON_ABILITY': team_use_commandbutton_ability,
    'TEAM_PARTIAL_USE_COMMANDBUTTON': team_partial_use_commandbutton,
    'TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT': team_use_commandbutton_ability_at_waypoint,
}
