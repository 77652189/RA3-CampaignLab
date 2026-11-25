"""Standalone mission factories for the economy and construction benches."""


def ban_bench():
    """禁造 on the bench (plan.py compile_bans, 准造): the player on the festival map with a construction yard, a power
    plant and a refinery, money; the airfield and the barracks banned from the start (retail Brighton Beach:
    ALLOW_DISALLOW_ONE_BUILDING on the player), let go at LET_GO. Looked at by hand (bench_start, select the yard, the
    build tab before and after): a human's build cannot be ordered by a script, so no counter tells it. Bench
    2026-10-28 (CampBan_mcp_1028_162857): at 2 s the barracks and the airfield showed a lock, at 36 s both were open.

    Published (the cast): yard; facts: let go.
    """
    import plan

    LET_GO = 30.0
    PLAN = {
        '关卡': 'bn', '名字': '禁造试验', '地图': 'festival',
        '阵营': {'我': '盟军', '敌': '帝国'},
        '开局': {'资金': 20000, '部队': [{'单位': '建造厂', '在': 'base yard', '角色': 'yard'},
                                     {'单位': '电厂', '在': 'base power'},
                                     {'单位': '矿厂', '在': 'base refinery'}]},
        '禁造': ['机场', '兵营'],
        '规则': [{'当': f'开局 + {LET_GO:g}', '做': [{'准造': ['机场', '兵营']}, '通报 机场和兵营放开了']}],
        '段': [{'名字': '一'}],
    }


    def mission(name='CampBan'):
        m = plan.Compiler(dict(PLAN), name).compile()
        m.facts['let go'] = LET_GO
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'ban': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def engine_countmodifier():
    """C CountModifier contrast; prediction/evidence: work/re/c_countmodifier_report.md."""
    from missions import aiskirm_bench as base


    def mission(modifier):
        m = base.mission('CampCMHalf' if modifier == 0.5 else 'CampCMFour', two='diff')
        pid = base.DIFF_PID
        xml = base._two_new_xml(pid, [('CNVCMBuild', 'EASY MEDIUM HARD BRUTAL', [
            f'Build="{base.NEW_PK}" Heuristic="FEWEST_UNIT" CountModifier="{modifier}"',
            f'Build="{base.NEW_JAV}" Heuristic="FEWEST_UNIT"'])])
        m.assets = [(name, xml if asset == f'AIPersonalityDefinition:{pid}' else text, asset)
                    for name, text, asset in m.assets]
        m.facts['count modifier'] = modifier
        m.facts.pop('difficulty gate')
        for template, count in [(base.NEW_PK, 4), (base.NEW_JAV, 2)]:
            for i in range(count):
                m.put(template, 'east base', -500 + i * 40, 200 if count == 4 else 300,
                      side='s1', role=f'count seed {template} {i}')
        return m


    MISSION = {'aicmhalf': lambda: mission(0.5), 'aicmfour': lambda: mission(4.0)}
    return dict(MISSION=MISSION)


def engine_powerdef():
    """Engine probe: does a POWERED defence building fire while its owner is short of power (engine_powerdef in checks.py)?

    The west field (island map), offsets from 'west field':
      coil   (0, 0)         s1's SovietBaseDefenseAdvanced (tesla coil: EnergyProduction -75, KindOf +POWERED,
                            weapon SovietBaseDefenseAdvancedTeslaGun AttackRange 350, Damage 450 TESLA)
      plant  (-130, 0)      s1's SovietPowerPlant (EnergyProduction +100): placed for on / cut; made at 10 s for back
      tanks  6 player tanks 'AlliedAntiVehicleVehicleTech1', NO_ATTACK, 175 north of the coil (half the range), 40 apart
    SageXML (sdk3/XMLFiles/Soviet/Structures): SovietBaseDefenseAdvanced.xml line 64-66, SovietPowerPlant.xml line 52.
    Published waypoint: plant (where back makes the plant).
    """
    from maps import island
    from parts import Mission

    COIL, PLANT, TANK = 'SovietBaseDefenseAdvanced', 'SovietPowerPlant', 'AlliedAntiVehicleVehicleTech1'
    N_TANKS, DIST, GAP = 6, 175.0, 40.0
    PLANT_AT = (-130.0, 0.0)
    VARIANTS = ('on', 'off', 'cut', 'back')


    def tank_name(k):
        return f'UNIT - CNV Pd Tank {k}'


    def mission(name, variant):
        m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant), 'tanks': N_TANKS})
        m.spawns |= {PLANT}
        m.put(COIL, 'west field', 0.0, 0.0, side='s1', role='coil', name='UNIT - CNV Pd Coil')
        if variant in ('on', 'cut'):
            m.put(PLANT, 'west field', *PLANT_AT, side='s1', role='plant', name='UNIT - CNV Pd Plant')
        for k in range(N_TANKS):
            m.put(TANK, 'west field', (k - (N_TANKS - 1) / 2) * GAP, DIST, role=f'tank {k}', name=tank_name(k))
        m.waypoint('plant', 'CNV Pd Plant', 'west field', *PLANT_AT)
        return m


    MISSION = {f'powerdef_{v}': (lambda v=v: mission('CampPd' + {'back': 'Bk'}.get(v, v.capitalize()), v)) for v in VARIANTS}
    return dict(MISSION=MISSION)


def engine_powerupgrade_e():
    """E175: isolated retail turbine hosts and module-only deletion controls."""
    import re
    from pathlib import Path
    import labpaths
    from maps import probe_range
    from model import Mission, Unit

    UP = 'Upgrade_PowerPlantTurbine'
    ROWS = [('normalon', 'p1', 'base gun', False, True),
            ('normaloff', 's1', 'high gun', False, False),
            ('advancedon', 's2', 'removed gun', True, True),
            ('advancedoff', 's3', 'switch gun', True, False)]


    def mission():
        m = Mission(name='CampPwrUpE', map=probe_range, units=[])
        for tag, side, site, advanced, enabled in ROWS:
            template = 'SovietPowerPlant' + ('Advanced' if advanced else '')
            if not enabled:
                xml = (Path(labpaths.SDK3) / f'SageXML/Soviet/Structures/{template}.xml').read_text(
                    encoding='utf-8-sig')
                xml, n = re.subn(r'<PowerUpgrade\b[^>]*>.*?</PowerUpgrade>', '', xml, flags=re.S)
                assert n == 1
                ident = template + 'E175Off'
                xml = xml.replace(f'id="{template}"', f'id="{ident}"', 1)
                m.units.append(Unit(ident, xml))
                template = ident
            m.put(template, site, side=side, role=tag, name='E175 ' + tag)
        return m


    MISSION = {'engine_powerupgrade_e': mission}
    return dict(MISSION=MISSION)


def engine_tech():
    """Tech probe mission (engine_tech check): the player's construction yard, a power plant and two war factories on
    the Niagara map -- one 300 east of the start (inside the yard's TechUpgrade radius 600, rectangular), one 750 east of
    the yard (outside). The check's variants delete what they do not need. Published (the cast): yard, power, near
    factory, far factory.
    """
    import resources
    from maps import niagara
    from parts import Mission

    WAR_FACTORY, GUARDIAN = 'AlliedWarFactory', 'AlliedAntiVehicleVehicleTech1'
    FAR_DX = 450.0                          # from 'base factory' (yard at 300 west of it): far factory 750 from the yard


    def _n(part):
        return f'UNIT - CNV Tech {part}'


    def mission(name='CampTech'):
        m = Mission(name=name, map=resources.measured(niagara), units=[], facts={})
        m.spawns |= {GUARDIAN}
        m.put('AlliedConstructionYard', 'base yard', angle=0.0, role='yard', name=_n('Yard'))
        m.put('AlliedPowerPlant', 'base power', angle=0.0, role='power', name=_n('Power'))
        m.put('AlliedRefinery', 'base refinery', role='refinery', name=_n('Refinery'))   # the Tech2 button needs one
        m.put(WAR_FACTORY, 'base factory', angle=3.1416, role='near factory', name=_n('Near'))
        m.put(WAR_FACTORY, 'base factory', FAR_DX, 0.0, angle=3.1416, role='far factory', name=_n('Far'))
        return m


    MISSION = {'engine_tech': mission}
    return dict(MISSION=MISSION)


def plan_words():
    """Engine probe for the plan words added to line up with the retail missions (docs/story/plans/retail/README.md), a
    small plan compiled like a level's (plan.py) but kept here, not among the levels' plans. Read back by
    plan_words in checks.py:

      - 规则 每隔: from the start, +100 money every 5 s (the first at once);
      - a random time, 开局 + 0:06~0:10: one guardian given in that window;
      - 无敌: an imperial warrior beside the player's guardians that nothing can aim at, a plain one beside it as the
        control; at 0:30 `取消无敌` and it falls like the control did.

    Facts: money (at the start), bonus (each rule run), gap, give from / until, undo at.
    """
    import plan

    MONEY, BONUS, GAP = 3000, 100, 5.0
    GIVE = (6.0, 10.0)
    UNDO_AT = 30.0

    PLAN = {
        '关卡': 'pw', '地图': 'festival', '阵营': {'我': '盟军', '敌': '帝国'},
        '开局': {'资金': MONEY, '部队': [
            {'单位': '守护者坦克', '数量': 2, '在': 'west field', '偏移': [250, 30], '角色': 'guardian'},
            {'单位': '帝国武士', '在': 'west field', '偏移': [200, 200], '阵营': '敌', '角色': 'shielded', '无敌': '是'},
            {'单位': '帝国武士', '在': 'west field', '偏移': [300, 200], '阵营': '敌', '角色': 'control'}]},
        '段': [{'名字': '一'}],
        '规则': [{'当': '开局', '每隔': GAP, '做': [{'资金': f'+{BONUS}'}]},
               {'当': f'开局 + {GIVE[0]:g}~{GIVE[1]:g}', '做': [{'给': {'守护者坦克': 1}, '在': 'west field'}]},
               {'当': f'开局 + {UNDO_AT:g}', '做': [{'取消无敌': 'shielded'}]}],
    }


    def mission(name='CampPW'):
        m = plan.Compiler(dict(PLAN), name).compile()
        m.facts.update({'money': MONEY, 'bonus': BONUS, 'gap': GAP, 'give from': GIVE[0], 'give until': GIVE[1],
                        'undo at': UNDO_AT})
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'plan_words': lambda: mission(),
    }
    return dict(MISSION=MISSION)


BENCHES = (ban_bench, engine_countmodifier, engine_powerdef, engine_powerupgrade_e, engine_tech, plan_words,)
