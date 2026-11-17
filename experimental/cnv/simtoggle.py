"""L2 toggles (ADR 0029, docs/engine/sim-layers.md): ToggleStatusSpecialAbilityUpdate -- a button that steps a body's
toggle module to its next ToggleState.

`Toggles` keeps the presses waiting out their UnpackTime (`due`) and reaches the world only through
simworld.WORLD_API. The peers it reads are handed in by the caller (Sim.toggle_press / Sim.toggles_run): the
template's toggle modules (`toggles_of`, kept on the Sim: Sim.modify reads them too), whether a player is short of
power (L4) and the attribute modifiers' re-set (`modify`) -- this module never imports them.
Fields it owns: its own `due`; on a body `toggle_at`, `armor_up`.
"""
import simunits

TOGGLE_UNPACK_LAG = 0          # frames past UnpackTime x 15 a toggle's new state is first read (engine_toggle d: 16)


class Toggles:
    def __init__(self):
        self.due = {}                  # (body name, toggle module index) -> (frame, body, button): waiting presses

    def press(self, world, b, command, toggles_of, short_of_power, modify):
        """A toggle button (ToggleStatusSpecialAbilityUpdate whose SpecialPowerTemplate the button fires): the module
        goes to its next ToggleState, the old state's ObjectStatus and AttributeModifier off, the new one's on
        (Sim.modify). False when b has no toggle for that button.
        Bench 11-11 engine_toggle a-f: the new state's bits are read the press's frame (as here) with PackTime 0 or
        1 s alike (b); UnpackTime 1 s puts them off 16 frames (d: the engineer's tent); a state with a DisabledType
        (the engineer's tent, the Tesla trooper's short circuit: HELD) takes no further press (d, f: presses 45 and
        60 frames later change nothing; INFERRED that DisabledType is the cause, not read in the program)."""
        power = simunits.command_power(command, world.own)
        i = next((i for i, tm in enumerate(toggles_of(b)) if power and tm['power'] == power), None)
        if not b.alive or i is None:
            return False
        tm = toggles_of(b)[i]
        if 'POWERED' in b.kinds and short_of_power(b.owner):
            # engine_acts_tgl JB / engine_acts_twr (round 223): a Japanese tower of a player with no plant took
            # neither press (3 s, 15 s); with a SovietPowerPlant the same press at 3 s toggled it
            world.note('技能', f'{world.label(b)} 按 {command}：缺电，不切换')
            return True
        if tm['states'][b.toggle_at.get(i, 0) % len(tm['states'])]['disabled'] or (b.name, i) in self.due:
            world.note('技能', f'{world.label(b)} 按 {command}：当前状态不接受（DisabledType / 正在展开）')
            return True
        delay = int(round(tm['unpack'] * simunits.LIFE_FPS))
        if delay:
            self.due[(b.name, i)] = (world.frame_now() + delay + TOGGLE_UNPACK_LAG, b, command)
            return True
        self.enter(world, b, i, power, toggles_of, modify)
        return True

    def run(self, world, frame, toggles_of, modify):
        """The toggles whose UnpackTime ran out by this frame enter their next state."""
        for key, (due, b, command) in list(self.due.items()):
            if frame >= due:
                del self.due[key]
                if b.alive:
                    self.enter(world, b, key[1], simunits.command_power(command, world.own), toggles_of, modify)

    def enter(self, world, b, i, power, toggles_of, modify):
        tm = toggles_of(b)[i]
        b.toggle_at[i] = (b.toggle_at.get(i, 0) + 1) % len(tm['states'])
        if power == 'SpecialPower_ToggleArmorUp':
            b.armor_up = b.toggle_at[i] == 1
            world.used.add('miner armor')
        modify(b)
        loc = tm['states'][b.toggle_at[i]].get('locomotor')
        speed = simunits.locomotor_speed(b.template, world.own, loc) if loc else None
        if speed:           # the state's LocomotorSet (engine_acts_btn TT / VT: the Tengu's jet, the VX's flight)
            if b.base is not None:
                b.base['speed'] = speed
            b.speed = speed
        world.used.add('toggle')
        world.change()
