"""Map fixtures bench scenes."""


def crane():
    """The paper crane's bench scene: the flier on the west field, an enemy Guardian on the east field (1800 away, in the
    shroud), a point 700 short of it to stop at -- inside the crane's 900, outside a retail flier's 500.

    retail=True: retail's Twinblade flies instead (the control). Published (the cast): scout, target; marks stop.
    """
    from maps import island
    from parts import Mission
    from units import crane as cr

    SHORT = 700.0


    AA = 'AlliedAntiAirVehicleTech1'                # the IFV, missiles up
    BEAR = 'SovietScoutInfantry'                    # the war bear: a stealth detector (300)


    def hide(name='CampCraneH', **unit):
        """Two cranes on the west field, each sent over two enemy IFVs 300 apart (A west, B east); B's IFVs have a war
        bear with them. Published (the cast): crane A, crane B; marks over A, over B."""
        u = cr.crane(**unit)
        m = Mission(name=name, map=island, units=[u])
        for k, dx in (('A', -100.0), ('B', 300.0)):
            m.put(u.id, 'west field', dx, -350, name=f'UNIT - CNV Crane {k}', role=f'crane {k}')
            for j, sx in enumerate((-30, 30)):
                m.put(AA, 'west field', dx + sx, 100, side='s1', name=f'UNIT - CNV AA {k}{j + 1}', role=f'aa {k} {j + 1}')
            m.waypoint(f'over {k}', f'CNV Crane Over {k}', 'west field', dx, 100)
        m.put(BEAR, 'west field', 300, 140, side='s1', name='UNIT - CNV Bear', role='bear')
        return m


    def mission(name='CampCrane', retail=False, **unit):
        u = cr.crane(**unit)
        m = Mission(name=name, map=island, units=[] if retail else [u])
        m.put('SovietAntiGroundAircraft' if retail else u.id, 'west field', 100, 0, name='UNIT - CNV Scout', role='scout')
        m.put('AlliedAntiVehicleVehicleTech1', 'east field', 0, 0, side='s1', name='UNIT - CNV Target', role='target')
        m.waypoint('stop', 'CNV Crane Stop', 'east field', -SHORT, 0)
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'crane': lambda: mission(),
        'crane_hide': lambda: hide(),
        'crane_retail': lambda: mission(name='CampCraneR', retail=True),
    }
    return dict(MISSION=MISSION)


def icewall():
    """The ice-wall engineer's bench scenes on the west field (east of its middle: the west edge is shallows).

    block: two lanes 300 apart (A west, B east), a Guardian of ours at the south end of each, a goal 500 north of it; an
      ice wall across lane A halfway (placed, not built). Cast: runner A, runner B, wall; marks goal A, goal B,
      behind A, behind B (the middle of the strip just past the wall's line in each lane).
    freeze: the engineer, a spot 150 north of him to raise a wall at. Cast: engineer, wall (built, not placed); mark spot.
      Variants: builder (retail's Soviet engineer walks there and builds it); spawn (his power makes another template --
      ice_spawn: our Tesla tank, placed nowhere: the check that every unit is compiled and linked).
    smash: a wall of ours, three enemy Hammers 120 south of it. Cast: wall, hammer 1 .. 3.
    """
    from maps import aso, island
    from parts import Mission, Role
    from units import icewall as iw
    from units import tesla as units_tesla

    MIDDLE = 150.0
    LANE = 150.0
    RUNNER = 'AlliedAntiVehicleVehicleTech1'        # the Guardian
    WALL_Y = 100.0                                  # block: the wall's line; the runners start at -150, goals at +350
    BEHIND = 65.0                                   # block: the middle of the strip just past the wall (north of it)


    def block(name='CampIceB'):
        w = iw.wall()
        m = Mission(name=name, map=island, units=[w])
        for tag, dx in (('A', MIDDLE - LANE), ('B', MIDDLE + LANE)):
            m.put(RUNNER, 'west field', dx, -150, name=f'UNIT - CNV Runner {tag}', role=f'runner {tag}', angle=1.5708)
            m.waypoint(f'goal {tag}', f'CNV Ice Goal {tag}', 'west field', dx, 350)
            m.waypoint(f'behind {tag}', f'CNV Ice Behind {tag}', 'west field', dx, WALL_Y + BEHIND)
        m.put(w.id, 'west field', MIDDLE - LANE, WALL_Y, name='UNIT - CNV Ice Wall', role='wall', angle=0.0)
        return m


    TURNS = {'A': dict(angle=0), 'B': dict(angle=90), 'C': dict(angle=0, shape='square')}


    def turns(name='CampIceT'):
        """Three lanes 200 apart, each with a runner at its south end, a goal 500 north, and an engineer by a spot on
        its line who builds a core there: A's leaves the bar at absolute 0, B's at 90, C's a square (blocks whichever
        way). Cast: runner A-C, engineer A-C; marks goal A-C, spot A-C, behind A-C."""
        m = Mission(name=name, map=island)
        for k, (tag, opts) in enumerate(TURNS.items()):
            dx = MIDDLE + (k - 1) * 200
            shape = opts.get('shape', 'bar')
            w = iw.wall(f'CNV_IceWallT{tag}', length=160, shape=shape)
            core = iw.seed(f'CNV_IceSeedT{tag}', w.id, angle=opts['angle'])
            e = iw.engineer(f'CNV_IceEngT{tag}', wall_id=core.id, stand=iw.clear_of(w))
            m.units += [w, core, e]
            m.put(RUNNER, 'west field', dx, -150, name=f'UNIT - CNV Runner {tag}', role=f'runner {tag}', angle=1.5708)
            m.put(e.id, 'west field', dx - 60, WALL_Y - 50, name=f'UNIT - CNV Ice Engineer {tag}', role=f'engineer {tag}')
            m.waypoint(f'goal {tag}', f'CNV Ice Goal {tag}', 'west field', dx, 350)
            m.waypoint(f'spot {tag}', f'CNV Ice Spot {tag}', 'west field', dx, WALL_Y)
            m.waypoint(f'behind {tag}', f'CNV Ice Behind {tag}', 'west field', dx, WALL_Y + BEHIND)
        return m


    def freeze(name='CampIceF', builder=False, spawn=None, extra=(), **wall):
        """builder: retail's Soviet engineer walks there and builds our wall instead. spawn: the engineer's power
        creates this template instead of the wall (extra: more units of ours the mission carries, placed nowhere)."""
        w = iw.wall(**wall)
        e = iw.retail_engineer(structure=w.id) if builder else iw.engineer(wall_id=spawn or w.id, build=not spawn)
        m = Mission(name=name, map=island, units=[e, w, *extra])
        m.cast['wall'] = Role(spawn or e.params['wall'])
        m.put(e.id, 'west field', MIDDLE, -100, name='UNIT - CNV Ice Engineer', role='engineer')
        m.waypoint('spot', 'CNV Ice Spot', 'west field', MIDDLE, 50)
        return m


    def smash(name='CampIceS'):
        w = iw.wall(lifetime=120)
        m = Mission(name=name, map=island, units=[w])
        m.put(w.id, 'west field', MIDDLE, 100, name='UNIT - CNV Ice Wall', role='wall', angle=0.0)
        for k, dx in enumerate((-60, 0, 60)):
            m.put('SovietAntiVehicleVehicleTech1', 'west field', MIDDLE + dx, -20, side='s1',
                  name=f'UNIT - CNV Hammer {k + 1}', role=f'hammer {k + 1}')
        return m


    GHOST = 'JapanAntiVehicleVehicleTech3'          # the Ghost King (glossary.py 鬼王)
    # ghost: four spots on the west field; a nearest-first walker visits them from the ghost's start in the order C, A, B, D
    GHOST_SPOTS = {'C': (150, -300), 'A': (150, -40), 'B': (150, 300), 'D': (-250, -300)}


    def ghost(name='CampIceG'):
        """Four built ice walls (the A4 device's: a core leaves a 160 square), each by its own engineer; later a Ghost King
        of the enemy appears by wall C. Asks: does it smash walls on its own, does it when ordered, can a script find the
        nearest unnamed wall and order it, is a wall in an area countable. Cast: engineer A-D, ghost, wall; marks spot A-D,
        ghost (where it appears)."""
        w = iw.wall('CNV_IceWallG', length=160, shape='square', lifetime=300)
        core = iw.seed('CNV_IceSeedG', w.id)
        e = iw.engineer('CNV_IceEngG', wall_id=core.id, stand=iw.clear_of(w))
        m = Mission(name=name, map=aso, units=[e, core, w])
        m.cast['wall'] = Role(w.id)
        m.put(GHOST, 'merc camp', 0, 0, side='s1', name='UNIT - CNV Ghost King', role='ghost')   # far off: the check brings it
        for k, (x, y) in GHOST_SPOTS.items():
            m.waypoint(f'spot {k}', f'CNV Ice Ghost Spot {k}', 'west field', x, y)
            m.put(e.id, 'west field', x + 120, y, name=f'UNIT - CNV Ice Engineer {k}',
                  role=f'engineer {k}')
        m.waypoint('ghost', 'CNV Ice Ghost Start', 'west field', 300, -300)   # where the check teleports it to
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'ice_block': lambda: block(),
        'ice_turns': lambda: turns(),
        'ice_freeze': lambda: freeze(),
        'ice_build': lambda: freeze(name='CampIceV', builder=True),
        'ice_spawn': lambda: freeze(name='CampIceO', spawn='CNV_TeslaTank', extra=[units_tesla.tesla()]),
        'ice_smash': lambda: smash(),
        'ice_ghost': lambda: ghost(),
    }
    return dict(MISSION=MISSION)


def sapporo_bench():
    """The A4 rework's map (maps/sapporo.py) with a stand-in plan, to preview and measure it (cnv_preview sapporo) before
    the A4 plan moves to it: the player at the corridor's west end, the convoy coming in off the border, the enemy on
    the north plateau, the main objective the harbour and the two bonuses the rework gives (the lane's repair depot,
    the TV tower) -- what terrain_measure takes the map's use from.

    Published (the cast): engineer 1-2, escort, depot, tower, camp; facts none.
    """
    import plan

    PLAN = {
        '关卡': 'sp', '名字': '札幌返工图', '地图': 'sapporo',
        '阵营': {'我': '盟军', '敌': '帝国', '其他': {'护送队': {'阵营': '盟军', '对我': '盟友', '对敌': '敌人'}}},
        '开局': {'资金': 0, '部队': [
            {'单位': '守护者坦克', '数量': 3, '在': 'start', '角色': 'escort'},
            {'单位': 'GarageTechStructure', '在': 'lane depot', '阵营': '敌', '角色': 'depot'},
            {'单位': 'ObservationPostTechStructure', '在': 'tv tower', '阵营': '敌', '角色': 'tower'},
            {'单位': '兵营', '在': 'north base', '阵营': '敌', '角色': 'camp'}]},
        '边界': 'corridor',
        '机关': {'车队': {'类型': '车队', '出发': '开局 + 0:30', '车': '护送队', '分批': [0, 50, 110]}},
        '段': [{'名字': '会场', '目标': ['护送到 2 号广场', '占修理厂'], '结束': '开局 + 3:00'},
              {'名字': '北营', '边界': 'west of the canal', '目标': ['拆北营', '占电视塔'], '结束': '段 北营 + 6:00'},
              {'名字': '最后一程', '边界': 'whole', '目标': ['送到港口']}],
        '目标': {'护送到 2 号广场': {'说明': '护送车队到 2 号广场', '标记': ['halt'], '完成': '车队.到达 halt'},
                 '拆北营': {'说明': '拆掉北营', '标记': ['camp'], '完成': '摧毁 camp'},
                 '送到港口': {'说明': '护送车队到港口', '标记': ['harbour'], '完成': '车队.到终点 2'},
                 '占修理厂': {'奖励': True, '说明': '占领后巷的修理厂', '标记': ['depot'], '完成': '占领 depot'},
                 '占电视塔': {'奖励': True, '说明': '占领西岭的电视塔', '标记': ['tower'], '完成': '占领 tower'}},
    }


    def mission(name='CampSap'):
        return plan.Compiler(dict(PLAN), name).compile()


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'sapporo': lambda: mission(),
    }
    return dict(MISSION=MISSION)


def sight():
    """Does low ground see high ground? (docs/design/principles.md P26: the design line guesses RA3 has no rule that
    ground below cannot see up a cliff.) On the festival map's north plateau (its top ~80 world units above the low
    ground, the cliff between ~60-70 wide): pairs of a viewer (the player's MCV: no weapon, vision 200, does not move)
    and a target (an enemy imperial engineer: no weapon), PAIRS apart along y --
      up 120, up 180:   the viewer at the cliff's foot, the target on the plateau's top
      flat 180, flat 400: both on the plateau's top -- the control: seen within its reach, not beyond it
    each pair 400 and more from the others. Read back by checks/sight.py.

    Published (the cast): viewer <pair>, target <pair>; facts vision.
    """
    from maps import festival
    from parts import Mission

    VIEWER, TARGET = 'AlliedMCV', 'JapanEngineer'
    VISION = 200.0                                  # AlliedMCV's VisionRange (SageXML)
    # pair: (x, the viewer's y, apart): measured off the layout's heights 2026-10-27 (the low ground walkable up to
    # y ~3500 at x 2450-2950, the plateau's top from ~3570), each one clear of the scenery
    PAIRS = {'up 120': (2480.0, 3460.0, 120.0), 'up 180': (2950.0, 3490.0, 180.0),
             'flat 180': (2160.0, 3640.0, 180.0), 'flat 400': (3250.0, 3680.0, 400.0)}
    # bench 2026-10-27: a control 260 apart was discovered too -- the MCV clears the shroud to 250 (ShroudClearingRange),
    # past its vision, and both have a body: the far control well beyond


    def mission(name='CampSight'):
        m = Mission(name=name, map=festival)
        cx, cy = m.site('island')
        for k, (x, y, apart) in PAIRS.items():
            tag = k.title().replace(' ', '')
            m.put(VIEWER, 'island', x - cx, y - cy, name=f'UNIT - CNV Sight Viewer {tag}', role=f'viewer {k}',
                  angle=1.5708)
            m.put(TARGET, 'island', x - cx, y + apart - cy, side='s1', name=f'UNIT - CNV Sight Target {tag}',
                  role=f'target {k}', angle=-1.5708)
        m.facts.update({'vision': VISION})
        return m


    # the builds this module makes (cnv/registry.py): build name -> mission factory
    MISSION = {
        'sight': lambda: mission(),
    }
    return dict(MISSION=MISSION)


BENCHES = (
    crane, icewall, sapporo_bench, sight,
)
