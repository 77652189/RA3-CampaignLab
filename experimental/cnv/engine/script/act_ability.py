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

import engine.objects.garrison as simgarrison
import engine.data.units as simunits
from engine.ports.command import Command
from engine.objects.power import CURTAIN, PACK_FRAMES, PACK_POWER, RELOAD_LAG, SUPERWEAPON_HITS, UNPACK_POWER, start_reload
from engine.script.common import refined
from engine.world.handle import GAP_ACTION


def _order(sim, kind, unit, *args, **fields):
    """A map script's button press through the run's command port: (ok, why). `unit` the object's name as the action
    found it, or the object a team action picked (by serial: review 11-19 i #2); None: no unit (a factory's build);
    `args` more (name, value) pairs."""
    if unit is None or isinstance(unit, str):
        units, by = () if unit is None else (unit,), True
    else:
        units, by = (unit.serial,), 'serial'
    return sim.commands.do(Command(kind, 'script', units=units, args=(('objects', by),) + args, **fields))


def named_buttons(sim, name, a, script, unit=None):
    """The button on `a[0]` -- or on `unit`, a member a team action picked (the object itself, not a reference that
    has its name: review 11-19 i #2)."""
    body = (lambda _n: unit) if unit is not None else sim.body
    who = unit if unit is not None else a[0]
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
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and \
            (simunits._commands(sim.own)[1].get(a[1]) or ('',))[0] == 'EVACUATE':
        # the Twinblade's evacuate (s09's Hinds): lands, all out together where it is (engine_acts_btn EV)
        if not sim.garrison.evacuate(body(a[0])):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有载着人的载具')
    elif (name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and a[1] == 'Command_UnPackJapanEgg'
          and simunits.command_power(a[1], sim.own) is None
          and body(a[0]) and body(a[0]).template in
          ('JapanBaseDefenseEgg', 'JapanPowerPlantEgg', 'JapanNavalYardEgg')):
        # engine_eggcmd:a / engine_eggnav:a: legacy id leaves these cores home; concrete buttons deploy.
        # Other hosts and map-local command definitions remain gaps, not aliases for UnpackReplaceSelf.
        pass
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and \
            simunits.command_power(a[1], sim.own) == UNPACK_POWER:
        # an MCV / a Japanese egg deploys at the point: drives there, then turns into its replacement (bench
        # engine_unpack mcv / egg: the yard stands on the point, the name passes on)
        b, p = body(a[0]), sim.point(a[2])
        if not (b and p is not None and _order(sim, 'unpack', who, ('button', a[1]), place=a[2])[0]):
            sim.note('技能', f'{a[0]} 按 {a[1]}：没有能展开的单位或路点')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            simunits.command_power(a[1], sim.own) == PACK_POWER and \
            simunits.replace_self(body(a[0]).template, a[1], sim.own):
        # a construction yard packs back into its MCV where it stands (engine_pack a / s / j)
        b = body(a[0])
        _, into = simunits.replace_self(b.template, a[1], sim.own)
        sim.used.add('unpack')
        b.replace = True
        sim.__dict__.setdefault('pack_hold', {})[b.serial] = simunits.replace_unpack_frames(b.template, a[1], sim.own)
        sim.due.append((sim.frame_now() + PACK_FRAMES, into, b.owner, b.team, b.x, b.y, b))   # by the thing (sweep)
        sim.note('技能', f'{sim.label(b)} 收起成 {into}')
        sim.build_due(sim.frame_now())        # the press frame's later scripts already see the MCV
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED' and \
            body(a[0]) and body(a[0]).alive and \
            sim.assignments.press(body(a[0]), a[1], sim.body(a[2])):
        sim.note('技能', f'{a[0]} 显式派发维修到 {a[2]}')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT' and body(a[0]) and body(a[0]).alive and \
            sim.point(a[2]) is not None and simunits.ocl_power(
                body(a[0]).template, simunits.command_power(a[1], sim.own) or '', sim.own):
        # engine_acts_wet DP / DS (round 226): the campaign bomber drop store's button is seen cast
        # (PLAYER_TRIGGERED_SPECIAL_POWER) the player's and the computer's alike -- and nobody comes, in six
        # runs (its OCL's CREATE_AT_EDGE_NEAR_SOURCE not explained: inventory NOTES)
        b = body(a[0])
        sim.casts.append((sim.frame_now(), b.owner, simunits.command_power(a[1], sim.own).lower(), b.serial,
                           sim.point(a[2])))
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
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and \
            _order(sim, 'toggle', who, ('button', a[1]))[0]:
        sim.note('技能', f'{a[0]} 按 {a[1]} 切换状态')
    elif name == 'NAMED_USE_COMMANDBUTTON_ABILITY' and body(a[0]) and body(a[0]).alive and \
            simunits.press_records(body(a[0]).template, a[1], sim.own):
        # engine_cast (round 242): Tanya's time belt seen cast twice (simunits.press_records); her jump back in
        # time is not simulated
        b = body(a[0])
        power, n = simunits.press_records(b.template, a[1], sim.own)
        sim.used.add('special power')
        sim.casts += [(sim.frame_now(), b.owner, power.lower(), b.serial, None)] * n
        sim.note('技能', f'{sim.label(b)} 按 {a[1]}：记 {n} 次施放')
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
        if not sim.at_site(b, 0.0):
            sim.send(b, p)
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
        if hits and q is not None and cooling:
            sim.used.add('superweapon')
            sim.note('技能', f'{sim.label(b)} 的 {a[1]} 还在重装：没打出来')
        elif hits and q is not None:       # a script's cast fires though the power is not ready
            sim.used.add('superweapon')
            now = sim.frame_now()
            for after, table in hits:
                sim.blasts.append((now + after, q[0], q[1], table, b.owner, b))
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
        if b and b.alive and not ((hits or a[1] in CURTAIN) and q is not None):
            sim.gap(GAP_ACTION, refined(name, a), f'{a[1]} 只记进时间线（special power），没有效果')


def player_fire_special_power_at_waypoint(sim, name, a, script):
    # (player, power, waypoint) INFERRED: the player's first living object that has the power casts it, as
    # NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT (a script's cast: no reload asked); none, nothing. Retail fires
    # protocols this way mostly (orbital refuse, final squadron): those have no source object, not simulated
    power = next((k for k in (*SUPERWEAPON_HITS, *CURTAIN) if k.lower() == str(a[1]).lower()), a[1])
    src = next((b for b in sim.living() if b.owner == a[0]
                and simunits.power_rules(b.template, power, sim.own)), None)
    if src:
        _member(sim, 'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', [src.name, power, a[2]], script, src)   # itself
    else:
        sim.gap(GAP_ACTION, refined(name, a), f'{a[0]} 没有带 {a[1]} 的物体（协议类不模拟）')


def team_use_commandbutton_ability(sim, name, a, script):
    # (team, button) l2_scripts1 8: the button on every living member, no target. Bench 11-08 button: both
    # Peacekeepers of the crew raised their shields
    for b in sim.members(a[0]):
        _member(sim, 'NAMED_USE_COMMANDBUTTON_ABILITY', [b.name, a[1]], script, b)


def team_use_commandbutton_ability_at_waypoint(sim, name, a, script):
    # (team, button, waypoint): the button at the spot on every living member (engine_acts_btn TB: the crew's
    # Bullfrog threw its passengers at the waypoint, as NAMED_..._AT_WAYPOINT did in round 152)
    for b in sim.members(a[0]):
        _member(sim, 'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT', [b.name, a[1], a[2]], script, b)


def _member(sim, name, a, script, b):
    """A team button on one member as the named action is on it (Sim.act's run of it: a branch declined is a gap),
    the member itself pressed -- a reference of its name cannot take its place (review 11-19 i #2)."""
    if named_buttons(sim, name, a, script, unit=b) is False:
        sim.unknown[name] = sim.unknown.get(name, 0) + 1
        sim.gap(GAP_ACTION, refined(name, a), 'Sim.act 不认识：没效果')


ACTIONS = {
    'NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT': named_buttons,
    'NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED': named_buttons,
    'PLAYER_FIRE_SPECIAL_POWER_AT_WAYPOINT': player_fire_special_power_at_waypoint,
    'TEAM_USE_COMMANDBUTTON_ABILITY': team_use_commandbutton_ability,
    'TEAM_USE_COMMANDBUTTON_ABILITY_AT_WAYPOINT': team_use_commandbutton_ability_at_waypoint,
}
