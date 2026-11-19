"""The Body family's port and data (engine/modules/body.py, simunits.module_blocks BODY, step B2a): the 7 Body tags --
ActiveBody, ImmortalBody, PropBody, ManagerBody, ManagedActiveBody, ManagedImmortalBody, HighlanderBody -- read
from the nearest non-empty <Body> up the chain, taken whole, defines spelled out. The census against the readers it
replaces (immortal_body / manager_body / prop_body / max_health and Sim.add's health) is
work/re/sim_split/b2_draft/b2_census.py: 3448 retail + 520 own templates, no difference."""
from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import simunits  # noqa: E402
from engine.modules import body  # noqa: E402

BASE = ('<GameObject id="CNVBodyBase"><Body><ActiveBody id="B" MaxHealth="400"/></Body>'
        '<Behaviors><SlowDeath id="S"/></Behaviors></GameObject>')


def answer(template, own=None):
    """{tag: [MaxHealth, ...]} of the Body tags the port answers for the template."""
    got = {tag: [body.BodyData.parse(*b).max_health for b in simunits.module_blocks(template, tag, own)]
           for tag in body.TAGS}
    return {tag: v for tag, v in got.items() if v}


def test_the_port_and_the_data_name_the_same_seven_tags():
    assert set(body.TAGS) == simunits.BODY and len(body.TAGS) == 7


def test_the_data_reads_max_health_a_literal_with_an_equals_sign_too():
    assert body.BodyData.parse(' id="B" MaxHealth="1500"', '').max_health == 1500.0
    assert body.BodyData.parse(' id="B" MaxHealth="=50000"', '').max_health == 50000.0
    assert body.BodyData.parse(' id="DefaultBody"', '').max_health is None


def test_the_nearest_body_is_taken_whole():
    own = {'CNVBodyBase': BASE,
           'CNVBodyImm': ('<GameObject id="CNVBodyImm" inheritFrom="CNVBodyBase"><Body>'
                          '<ImmortalBody id="B" MaxHealth="900"/></Body></GameObject>'),
           'CNVBodyHeir': '<GameObject id="CNVBodyHeir" inheritFrom="CNVBodyBase"><Behaviors/></GameObject>'}
    assert answer('CNVBodyImm', own) == {'ImmortalBody': [900.0]}       # not the base's ActiveBody as well
    assert answer('CNVBodyHeir', own) == {'ActiveBody': [400.0]}        # no Body of its own: the base's


def test_an_empty_body_is_skipped_and_a_define_spelled_out():
    own = {'CNVBodyBase': BASE,
           'CNVBodyEmpty': ('<GameObject id="CNVBodyEmpty" inheritFrom="CNVBodyBase"><Body>\n'
                            '<!-- <ImmortalBody id="B"/> --></Body></GameObject>')}
    assert answer('CNVBodyEmpty', own) == {'ActiveBody': [400.0]}       # a commented-out block is no block
    # retail: AM_Apartments_01 writes <Body></Body>; BaseCivilianStructureMedium's =$CIV_HEALTH_MEDIUM is 3000
    assert answer('AM_Apartments_01') == {'ActiveBody': [3000.0]}
    assert answer('AM_FutureTech_02') == {'ActiveBody': [50000.0]}      # MaxHealth="=50000"


def test_a_removed_prop_body_keeps_the_body_a_prop():
    # retail: the torpedo removes BaseProjectile's PropBody for an ActiveBody of 100; read as prop_body read it
    assert answer('JapanAntiVehicleShipTorpedoSpreadProjectile') == {'PropBody': [100.0]}
    assert answer('BaseProjectile') == {'PropBody': [None]}
    own = {'CNVBodyBase': BASE,
           'CNVBodyGone': ('<GameObject id="CNVBodyGone" inheritFrom="CNVBodyBase"><Body>'
                           '<ActiveBody id="B" xai:joinAction="Remove"/><ImmortalBody id="I" MaxHealth="50"/>'
                           '</Body></GameObject>')}
    assert answer('CNVBodyGone', own) == {'ImmortalBody': [50.0]}       # another Remove block is just left out


def test_the_managed_and_the_other_bodies_are_their_own_tags():
    assert answer('BaseBridge') == {'ManagerBody': [1.0]}
    assert answer('BaseCivilianBridge') == {'ManagedActiveBody': [1000.0]}  # its own body, not BaseBridge's
    assert set(answer('BaseBridgeEnd')) == {'ManagedImmortalBody'}      # not an ImmortalBody
    assert set(answer('BaseMountRushmoreHead')) == {'HighlanderBody'}


def test_a_campaign_override_is_read_first_as_max_health_reads_it():
    # CampaignOverrides: the Yari's 2000 over its file's 1500; Sim.add's health still takes fight's 1500 (B2b keeps it)
    assert answer('JapanAntiStructureShip') == {'ActiveBody': [2000.0]}
    assert simunits.max_health('JapanAntiStructureShip') == 2000.0
    assert simunits.fight('JapanAntiStructureShip')['hp'] == 1500.0
