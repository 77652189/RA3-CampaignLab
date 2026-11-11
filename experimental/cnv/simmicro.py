"""C's bounded unit-power execution bridge for the MaximumDelay probe.

Only the retail warrior's zero-unpack, self-only Bonzai is supported here.
The existing modifier engine selects the sword and applies/ends its status
and speed. ArmorSetType, suppression immunity, garrison contest and bark
immunity remain explicit gaps; this does not establish full Bonzai combat.
Other commands retain their explicit unmodeled execution path.
"""
import simunits

COMMAND = 'Command_JapanAntiInfantryInfantryBonzai'


def recipe(world, body, command):
    if command != COMMAND:
        return None
    xml = world.xml_of(body.template)
    power = simunits.command_power(command, world.own)
    heads = [h for h, _ in simunits._blocks(xml, 'SpecialPower')
             if simunits._attr(h, 'SpecialPowerTemplate') == power]
    updates = [h for h, _ in simunits._blocks(xml, 'SpecialAbilityUpdate')
               if simunits._attr(h, 'SpecialPowerTemplate') == power]
    if len(heads) != 1 or len(updates) != 1:
        return None
    if simunits._attr(heads[0], 'AttributeModifierAffectsSelf') != 'true':
        return None
    if simunits._secs(simunits._attr(updates[0], 'UnpackTime')) != 0:
        return None
    mid = simunits._attr(heads[0], 'AttributeModifier')
    modifier = simunits.modifier(xml, mid)
    rules = simunits.power_rules(body.template, power, world.own)
    if not modifier or modifier['frames'] is None or not rules:
        return None
    return xml, mid, modifier['frames'], rules['reload']


def ready(world, body, command):
    """Honor the supported unit's reload before offering it to the micro manager."""
    return command != COMMAND or body.ready_at.get(command, 0) <= world.frame_now()


def fire(world, body, command):
    got = recipe(world, body, command)
    if got is None or not body.alive or not ready(world, body, command):
        return False
    xml, mid, duration, reload = got
    now = world.frame_now()
    body.auras_on[mid] = (now + duration, xml)
    body.ready_at[command] = now + reload
    world.modify(body)
    world.gap('升级', mid, '冲锋仅接状态、速度、武器选择；ArmorSetType护甲切换未模拟')
    world.change()
    world.note('AI', f'{body.name} 执行 {command}')
    return True
