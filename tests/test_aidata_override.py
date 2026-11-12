"""A retail instance other than a GameObject recompiled under its retail id (AIData:AIData, from global.xml): the
mission names it in Mission.replaces, packaging hands it to make_campnew7.OVERRIDE instead of EXTRA_OWN (which links
only ids the static streams lack), and the override pass picks BAB's instance by its full name."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import make_campnew7 as c7  # noqa: E402
import package  # noqa: E402
from checks import engine_aiskirm as ck  # noqa: E402
from missions import aiskirm_bench as ab  # noqa: E402


def test_override_names_take_a_full_instance_name_or_a_gameobject_id(monkeypatch):
    monkeypatch.setattr(c7, 'OVERRIDE', ['JapanAntiInfantryInfantry', 'AIData:AIData'])
    assert c7.override_names() == {b'GameObject:JapanAntiInfantryInfantry', b'AIData:AIData'}


def test_the_aidata_canary_replaces_retail_aidata_instead_of_linking_a_new_id():
    m = ab.MISSION['aiskad']()
    spec = package.spec_of(m, ck.a(m))
    assert spec.replaces == ('AIData:AIData',)
    assert b'AIData:AIData' not in spec.extra_own
    assert 'DATA:CNVUnits/Data/CNVAIData.xml' in spec.extra_all
    xml = dict(spec.unit_files)['CNVAIData.xml']
    assert re.search(r'<AIData id="AIData"', xml)
    assert 'TeamSeconds="100000"' in xml and 'MaxRecruitDistance="1.0"' in xml


def test_the_formation_pair_differs_only_in_use_formations():
    on, off = (dict(package.spec_of(m, ck.fm(m)).unit_files)['CNVAIData.xml']
               for m in (ab.MISSION['aiskfon'](), ab.MISSION['aiskfof']()))
    assert on.replace('UseFormations="true"', 'UseFormations="false"') == off
