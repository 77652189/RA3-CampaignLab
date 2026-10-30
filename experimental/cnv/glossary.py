"""Unit names a level plan (docs/story/plans) may write, in Chinese, and the retail templates behind them. A name that
is the same thing in every faction (建造厂, 兵营, 基地车 ...) is resolved by the side's faction (the plan's 阵营);
a name of one faction's own unit (守护者坦克, 帝国武士 ...) stands for that unit whoever owns it. A plan may also
write a template id outright (AlliedAntiVehicleVehicleTech1). Our own units (冰幕工兵, 冰雕 ...) come from the plan's
devices (plan.py), which publish them by name.

The template spellings are retail's own, as the campaign maps place them (retail_objects).
"""

FACTIONS = ('盟军', '苏联', '帝国')
PREFIX = {'盟军': 'Allied', '苏联': 'Soviet', '帝国': 'Japan'}

# the same building / unit in each faction: {name: template suffix}
SHARED = {
    '建造厂': 'ConstructionYard', '基地车': 'MCV', '兵营': 'Barracks', '战车工厂': 'WarFactory',
    '电厂': 'PowerPlant', '矿厂': 'Refinery', '机场': 'Airfield', '船坞': 'NavalYard', '工程师': 'Engineer',
    '矿车': 'Miner', '围墙': 'WallPiece', '科技中心': 'TechStructure',
}

# one faction's own units and buildings: {name: template}
OWN = {
    # 盟军
    '维和步兵': 'AlliedAntiInfantryInfantry', '标枪兵': 'AlliedAntiVehicleInfantry', '警犬': 'AlliedScoutInfantry',
    '间谍': 'AlliedInfiltrationInfantry', '谭雅': 'AlliedCommandoTech1', '守护者坦克': 'AlliedAntiVehicleVehicleTech1',
    '幻影坦克': 'AlliedAntiVehicleVehicleTech3', '多功能步兵车': 'AlliedAntiAirVehicleTech1',
    '激流 ZX': 'AlliedAntiInfantryVehicle', '雅典娜炮': 'AlliedAntiStructureVehicle', '未来坦克': 'AlliedFutureTank',
    '阿波罗战机': 'AlliedFighterAircraft', '冷冻直升机': 'AlliedSupportAircraft', '世纪轰炸机': 'AlliedBomberAircraft',
    '海豚': 'AlliedAntiNavalScout', '水翼船': 'AlliedAntiAirShip', '突击驱逐舰': 'AlliedAntiNavyShipTech1',
    '航空母舰': 'AlliedAntiStructureShip', '多功能炮塔': 'AlliedBaseDefense', '光谱塔': 'AlliedBaseDefenseAdvanced',
    '指挥中心': 'AlliedOutpost',
    # 苏联
    '动员兵': 'SovietAntiInfantryInfantry', '防空步兵': 'SovietAntiVehicleInfantry',
    '磁暴步兵': 'SovietHeavyAntiVehicleInfantry', '战熊': 'SovietScoutInfantry', '娜塔莎': 'SovietCommandoTech1',
    '镰刀': 'SovietAntiInfantryVehicle', '铁锤坦克': 'SovietAntiVehicleVehicleTech1',
    '磁暴坦克': 'SovietAntiVehicleVehicleTech2', '天启坦克': 'SovietAntiVehicleVehicleTech3',
    'V4 火箭车': 'SovietAntiStructureVehicle', '恐怖机器人': 'SovietScoutVehicle', '牛蛙': 'SovietAntiAirShip',
    '米格战机': 'SovietFighterAircraft', '双刃直升机': 'SovietAntiGroundAircraft', '基洛夫空艇': 'SovietBomberAircraft',
    '哨戒炮': 'SovietBaseDefenseGround', '防空炮': 'SovietBaseDefenseAir', '磁暴线圈': 'SovietBaseDefenseAdvanced',
    # 帝国
    '帝国武士': 'JapanAntiInfantryInfantry', '坦克杀手': 'JapanAntiVehicleInfantry',
    '忍者': 'JapanInfiltrationInfantry', '百合子': 'JapanCommandoTech1', '火箭天使': 'JapanAntiVehicleInfantryTech3',
    '爆裂无人机': 'JapanScoutInfantry', '天狗': 'JapanAntiInfantryVehicle', '打击者': 'JapanAntiAirVehicleTech1',
    '海啸坦克': 'JapanAntiVehicleVehicleTech1', '鬼王': 'JapanAntiVehicleVehicleTech3',
    '波能炮': 'JapanAntiStructureVehicle', '突击运输车': 'JapanLightTransportVehicle', '波能塔': 'JapanBaseDefenseAdvanced',
    '守卫塔': 'JapanBaseDefense',
    # the voice line's names (RA3-ChineseVoice lines/GLOSSARY.md, the authority for unit names; the flow scripts
    # write these): the older ones above stay for the plans written with them
    '激流气垫船': 'AlliedAntiInfantryVehicle', '阿波罗战斗机': 'AlliedFighterAircraft', '未来坦克X-1': 'AlliedFutureTank',
    '镰刀机甲': 'SovietAntiInfantryVehicle', 'V4火箭车': 'SovietAntiStructureVehicle', '基洛夫飞艇': 'SovietBomberAircraft',
    '天狗机甲': 'JapanAntiInfantryVehicle', '鹰击者VX': 'JapanAntiAirVehicleTech1',
}


def template(name, faction):
    """The template a plan's unit name stands for, for a side of `faction`; a template id stays as it is."""
    if name in OWN:
        return OWN[name]
    if name in SHARED:
        assert faction in PREFIX, f'{name}: which faction? ({faction!r} is none of {FACTIONS})'
        return PREFIX[faction] + SHARED[name]
    assert name[:1].isascii(), f'no unit called {name!r}: known are {sorted(OWN) + sorted(SHARED)}'
    return name


def names():
    """Every name a plan may write (for plan_vocab)."""
    return dict(shared=sorted(SHARED), own=dict(OWN))
