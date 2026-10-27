"""可造: the player's barracks and construction yard are copies that build our units too (units/production.py)."""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import plan  # noqa: E402
from units import production  # noqa: E402

PLAZAS = {'车队': {'类型': '车队', '出发': '开局 + 1:00'},
          '广场': {'类型': '冰雕广场', '车队': '车队', '每座兵': ['帝国武士'], '每座几个': 1}}


def small(**more):
    d = {'关卡': 'zz', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'}, '机关': PLAZAS,
         '开局': {'部队': [{'单位': '建造厂', '在': 'base yard'}, {'单位': '兵营', '在': 'base barracks'},
                           {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
         '段': [{'名字': '一'}]}
    d.update(more)
    return plan.Compiler(d).compile()


def cmds(x, set_id):
    body = re.search(rf'<LogicCommandSet id="{set_id}">(.*?)</LogicCommandSet>', x, re.S).group(1)
    return re.findall(r'<Cmd>([^<]+)</Cmd>', body)


def test_a_barracks_that_builds_ours_after_retails_own():
    u = production.building('AlliedBarracks', ['CNV_IceEngineer'], 'CNVZZAlliedBarracks')
    assert 'id="CNVZZAlliedBarracks"' in u.xml and 'CommandSet="CNVZZAlliedBarracksCommandSet"' in u.xml
    got = cmds(u.xml, 'CNVZZAlliedBarracksCommandSet')
    assert got == production.commands('AlliedBarracksCommandSet') + ['Command_ConstructCNV_IceEngineer']
    assert '<LogicCommand Type="UNIT_BUILD" id="Command_ConstructCNV_IceEngineer">' in u.xml
    assert 'source="DATA:CNVUnits/Data/CNV_IceEngineer.xml"' in u.xml


def test_a_yard_that_builds_the_copy_in_retails_place_at_both_tech_levels():
    y = production.yard('AlliedConstructionYard', {'AlliedBarracks': 'CNVZZAlliedBarracks'}, 'CNVZZYard')
    sets = re.findall(r'\bCommandSet="([^"]+)"', y.xml)
    assert sets == ['CNVZZYardAlliedConstructionYardCommandSet', 'CNVZZYardAlliedConstructionYardCommandSetLevel2']
    for s, tech in zip(sets, ('Command_PurchaseAlliedTech2', 'Command_PurchaseAlliedTech3')):
        got = cmds(y.xml, s)
        assert 'Command_ConstructCNVZZAlliedBarracks' in got and 'Command_ConstructAlliedBarracks' not in got
        assert 'Command_ConstructAlliedWarFactory' in got and tech in got
    assert 'Type="CONSTRUCTION_YARD_CONSTRUCT" id="Command_ConstructCNVZZAlliedBarracks"' in y.xml


def test_the_plan_places_the_copies_for_the_player_only():
    m = small(可造={'兵营': ['冰幕工兵']})
    placed = {(o.template, o.side) for o in m.objects}
    assert ('CNVZZAlliedBarracks', 'p1') in placed and ('CNVZZAlliedConstructionYard', 'p1') in placed
    assert ('JapanBarracks', 's1') in placed and ('AlliedBarracks', 'p1') not in placed
    ids = {u.id for u in m.units}
    assert {'CNVZZAlliedBarracks', 'CNVZZAlliedConstructionYard', 'CNV_IceEngineer'} <= ids


def test_without_it_the_player_has_retails():
    placed = {(o.template, o.side) for o in small().objects}
    assert ('AlliedBarracks', 'p1') in placed and not any(t.startswith('CNVZZ') for t, _ in placed)


def test_every_unit_of_ours_by_name():
    from units import roster
    for name in roster.NAMES:
        made = roster.make(name)
        assert made and all(u.id.startswith('CNV_') for u in made), name


def test_a_plan_places_and_builds_ours_by_name():
    m = small(可造={'兵营': ['超时空信标兵']},
              开局={'部队': [{'单位': '兵营', '在': 'base barracks'},
                             {'单位': '超时空信标兵', '在': 'west field', '角色': 'beacon'},
                             {'单位': '钻地运兵车', '在': 'north base', '阵营': '敌', '角色': 'digger'}]})
    assert m.cast['beacon'].template == 'CNV_Beacon' and m.cast['digger'].template == 'CNV_Burrower'
    assert {'CNV_Beacon', 'CNV_Burrower', 'CNVZZAlliedBarracks'} <= {u.id for u in m.units}
    barracks = next(u for u in m.units if u.id == 'CNVZZAlliedBarracks')
    assert 'Command_ConstructCNV_Beacon' in cmds(barracks.xml, 'CNVZZAlliedBarracksCommandSet')


@pytest.mark.parametrize('bad', [{'兵营': ['工程师']}, {'兵营': ['没这个兵']}])
def test_only_ours(bad):
    with pytest.raises((plan.PlanError, AssertionError)):
        small(可造=bad)
