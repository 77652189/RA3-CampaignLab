"""L2 toggles (ADR 0029, docs/engine/sim-layers.md): the host's side of ToggleStatusSpecialAbilityUpdate, whose
modules (engine/modules/toggle.py, step M5) keep each toggle's state and its waiting press.

press: which of a body's toggle modules a button presses (the command's special power), a POWERED body short of
power, the notes. entered: what a module's new state switches, told through World.toggled -- the modifiers' re-set
(`modify`), the state's LocomotorSet speed -- until those families read the Toggle interface themselves.
Both reach the world only through simworld.WORLD_API; whether a player is short of power (L4) and `modify` are handed
in by the caller (Sim.toggle_press / Sim's World) -- this module never imports them.
Fields it owns: none (the body's toggle_at / armor_up are read-only forwards of the modules since M5).
"""
import engine.data.units as simunits
from engine.kernel import interfaces
from engine.modules import locomotor


def press(world, b, command, short_of_power):
    """A toggle button (ToggleStatusSpecialAbilityUpdate whose SpecialPowerTemplate the button fires): its module goes
    to its next ToggleState, the old state's ObjectStatus and AttributeModifier off, the new one's on (entered).
    False when b has no toggle for that button.
    Bench 11-11 engine_toggle a-f: the new state's bits are read the press's frame (as here) with PackTime 0 or
    1 s alike (b); UnpackTime 1 s puts them off 16 frames (d: the engineer's tent); a state with a DisabledType
    (the engineer's tent, the Tesla trooper's short circuit: HELD) takes no further press (d, f: presses 45 and
    60 frames later change nothing; INFERRED that DisabledType is the cause, not read in the program)."""
    power = simunits.command_power(command, world.own)
    mods = b.find(interfaces.Toggle) if b.modules else ()
    m = next((m for m in mods if power and m.rules()['power'] == power), None)
    if not b.alive or m is None:
        return False
    if 'POWERED' in b.kinds and short_of_power(b.owner):
        # engine_acts_tgl JB / engine_acts_twr (round 223): a Japanese tower of a player with no plant took
        # neither press (3 s, 15 s); with a SovietPowerPlant the same press at 3 s toggled it
        world.note('技能', f'{world.label(b)} 按 {command}：缺电，不切换')
        return True
    if not m.press(world.frame_now()):
        world.note('技能', f'{world.label(b)} 按 {command}：当前状态不接受（DisabledType / 正在展开）')
    return True


def entered(world, b, m, modify):
    """A toggle module of b entered its next state (World.toggled): the miner's armour noted, the modifiers re-set,
    the state's LocomotorSet speed and surface taken, a way under way re-routed on the new surface (engine_acts_btn
    TT / VT: the Tengu's jet, the VX's flight)."""
    tm = m.rules()
    if tm['power'] == 'SpecialPower_ToggleArmorUp':
        world.used.add('miner armor')
    modify(b)
    loc = tm['states'][m.state()].get('locomotor')
    speed, surf = simunits.locomotor_of(b.template, world.own, loc) if loc else (None, [])
    if speed:
        # engine_acts_wing (round 278): the Sea-Wing's SUPERSONIC set (Surfaces AIR) took it up the press's second
        # (AIRBORNE_TARGET) and over the bank; NORMAL (DEEP_WATER) back on the water
        if b.base is not None:
            b.base['speed'] = speed
        surface = locomotor.surface_of(surf, b.kinds) if surf else b.surface
        if b.path and surface != b.surface:
            # review 1121nn P2: a way on the old surface is not taken on the new one -- re-routed to where it was
            # sent (back on the water short of a land point: no way, it stops; INFERRED mid-flight -- pressed standing
            # over land it stays there, engine_acts_wing lnd)
            locomotor.write(world.world, b, path=world.ground.route(surface, (b.x, b.y), b.dest, closest=True) or [])
        locomotor.write(world.world, b, speed=speed, surface=surface)
    world.used.add('toggle')
    world.change()


def toggle_at(mods):
    """The body's toggle_at forward: {module index: its state} of the toggle modules a press ever moved."""
    return {i: m.state() for i, m in enumerate(mods) if m.entered()}


def armor_up(mods):
    """The body's armor_up forward: the miner's armour toggle in its second state."""
    return any(m.rules()['power'] == 'SpecialPower_ToggleArmorUp' and m.state() == 1 for m in mods)
