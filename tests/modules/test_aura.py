"""The AttributeModifierAuraUpdate module (engine/modules/aura.py, step M12): its data read from the block (the shape
simunits.auras gave: RefreshDelay in frames, the ObjectFilter's Relationship / Include / Exclude, InitiallyActive,
RequiredObjectStatusFlags, AllowSelf), its refresh beat (the first at once, then every RefreshDelay counted from the
first, a late ask moved to the latest refresh due), and the port reading the template's own XML alone (an inherited
aura is not read: simunits.SELF_ONLY). The stasis zone on the map: tests/test_simmodifier.py."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simsmall  # noqa: E402
import simunits  # noqa: E402
from engine.kernel import interfaces  # noqa: E402
from engine.modules import aura  # noqa: E402

HEAD = (' id="ModuleTag_Aura" AttributeModifierName="Slow" Range="150" RefreshDelay="0.5s" InitiallyActive="false"'
        ' RequiredObjectStatusFlags="GENERIC_TOGGLE_STATE" AllowSelf="true"')
INNER = '<ObjectFilter Rule="ANY" Relationship="ENEMIES" Include="INFANTRY VEHICLE" Exclude="AIRCRAFT" />'
EMITTER = f'''<GameObject id="CNV_TestAura" KindOf="STRUCTURE">
  <Behaviors>
    <AttributeModifierAuraUpdate{HEAD}>{INNER}</AttributeModifierAuraUpdate>
  </Behaviors>
</GameObject>'''
CHILD = '<GameObject id="CNV_TestAuraChild" inheritFrom="CNV_TestAura" KindOf="STRUCTURE">\n</GameObject>'


def test_the_block_is_read_in_the_shape_the_old_reader_gave():
    assert aura.AuraData.parse(HEAD, INNER).rule == {
        'mod': 'Slow', 'range': 150.0, 'refresh': 8, 'relation': {'ENEMIES'}, 'include': {'INFANTRY', 'VEHICLE'},
        'exclude': {'AIRCRAFT'}, 'active': False, 'needs': {'GENERIC_TOGGLE_STATE'}, 'self': True}
    assert aura.AuraData.parse('', '').rule == {
        'mod': None, 'range': 0.0, 'refresh': 15, 'relation': {'ALLIES', 'ENEMIES', 'NEUTRAL'}, 'include': set(),
        'exclude': set(), 'active': True, 'needs': set(), 'self': False}


def test_the_beat_first_at_once_then_every_refresh_from_the_first():
    s = simsmall.small_world()
    s.own.update({'CNV_TestAura': EMITTER, 'CNV_TestAuraChild': CHILD})
    s.add('e', 'CNV_TestAura', 'Player_1', 100.0, 100.0)
    (m,) = s.bodies['e'].find(interfaces.Aura)
    assert m.last_beat() is None
    assert m.pulse(10) is True and m.last_beat() == 10
    assert m.pulse(17) is False and m.last_beat() == 10           # 7 < 8 frames
    assert m.pulse(18) is True and m.last_beat() == 18
    assert m.pulse(43) is True and m.last_beat() == 42            # late: the latest refresh due, 18 + 3 x 8


def test_an_inherited_aura_is_not_read():
    own = {'CNV_TestAura': EMITTER, 'CNV_TestAuraChild': CHILD}
    assert len(simunits.module_blocks('CNV_TestAura', 'AttributeModifierAuraUpdate', own)) == 1
    assert simunits.module_blocks('CNV_TestAuraChild', 'AttributeModifierAuraUpdate', own) == []
