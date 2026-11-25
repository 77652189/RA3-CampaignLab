"""Standalone weapon firing scenes."""


def engine_acquire():
    """Engine probe mission (R8, docs/story/sim-vs-bench-a4.md last section): how far does a unit on its own look for
    enemies and go after them -- idle, guarding, attack-moving (benches/weapon/firing/checks.py#engine_acquire).

    The west field (island map), offsets from 'west field':
      S (0, -400)          the attacker's birth point (an enemy s1 'AlliedAntiVehicleVehicleTech1', weapon range 150,
                           vision 200, shroud 500; made at 1 s on the s1 crew 'Aq')
      T                    the player's tank, named, NO_ATTACK: idle / guard (0, -400 + d) straight north of S;
                           attack-move (300, -400 + d) beside the path, d to the side of the path's middle
      E (600, -400)        the attack-move end
    Published waypoints: s, e.
    """
    from maps import island
    from parts import Mission

    TANK = 'AlliedAntiVehicleVehicleTech1'
    S, E = (0.0, -400.0), (600.0, -400.0)
    VARIANTS = ('idle180', 'idle260', 'idle400', 'guard260', 'guard400', 'am260', 'am400', 'idle200', 'idle220', 'idle240',
                'hold180', 'hold220', 'agg220', 'agg240', 'agg260')


    def target(variant):
        d = float(variant[-3:])
        return (300.0, S[1] + d) if variant.startswith('am') else (0.0, S[1] + d)


    def mission(name, variant):
        m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
        m.crew('Aq', 's1')
        m.put(TANK, 'west field', *target(variant), role='tank', name='UNIT - CNV Aq Tank')
        for part, label, at in (('s', 'S', S), ('e', 'E', E), ('t', 'T', target(variant))):
            m.waypoint(part, f'CNV Aq {label}', 'west field', *at)
        return m


    MISSION = {f'acquire_{v}': (lambda v=v: mission('CampAq' + v[0].upper() + str(VARIANTS.index(v)), v)) for v in VARIANTS}
    return dict(MISSION=MISSION)


def engine_reorder():
    """Engine probe mission: does a unit that is re-ordered every frame still walk (benches/weapon/firing/checks.py#engine_reorder; A4's Ghost
    King, devices/horn.py ghost_scripts: `smashes` told it every frame and it stood still, `hunts` did and it walked).

    The west field (island map), offsets from 'west field':
      S (0, -400)   the attacker's birth point (an enemy s1 'AlliedAntiVehicleVehicleTech1', made at 1 s by the check
                    on the s1 crew 'Reo')
      W (0,  500)   the player's ice wall (no lifetime), named: 900 from S, far out of range, the attacker has to walk
      T (250, 500)  the player's tank, named, NO_ATTACK (the target of the tank / alt variants)
      M (0,  200)   the move point of the move variant
    Published waypoints: s, mid (0, 0), near (0, 330), m.
    """
    from maps import island
    from parts import Mission
    from units import icewall as iw

    WALL = 'CNV_ReoWall'
    TANK = 'AlliedAntiVehicleVehicleTech1'
    S, W, T, M = (0.0, -400.0), (0.0, 500.0), (250.0, 500.0), (0.0, 200.0)
    OLD = ('once', 'every', 'bare', 'tank', 'move', 'alt', 'late')
    DT = ('dt1', 'dtev', 'dtevg')      # detour: a barrier row at y = 50, open only at the east end
    TU = ('tu1', 'tuev', 'tuevg')      # turn: walk east to P (west was the sea), then attack W2 (due north of P, a 90 degree turn)
    VARIANTS = OLD + DT + TU
    BAR = 'CNV_ReoBar'
    WALL2 = 'UNIT - CNV Reo Wall2'
    P, W2, GAP = (200.0, -400.0), (200.0, -250.0), (380.0, 50.0)
    BAR_XS = list(range(-420, 251, 70)) + [250]   # 80-wide blocks at 70 steps, no seam; open for x > 290


    def modname(v):
        # the build names the mod name + 'Frames': 'CampRo' + 2 letters + 'Frames' = 14, the limit is 15
        short = {'dt1': 'D1', 'dtev': 'De', 'dtevg': 'Dg', 'tu1': 'U1', 'tuev': 'Ue', 'tuevg': 'Ug'}
        return 'CampRo' + (v[:2].capitalize() if v in OLD else short[v])


    def mission(name, variant):
        m = Mission(name=name, map=island, facts={'variant': VARIANTS.index(variant)})
        m.units += [iw.wall(WALL, length=60, shape='square', lifetime=None)]
        m.crew('Reo', 's1')
        m.put(WALL, 'west field', *W, role='wall', name='UNIT - CNV Reo Wall')
        m.put(TANK, 'west field', *T, role='tank', name='UNIT - CNV Reo Tank')
        for part, label, at in (('s', 'S', S), ('mid', 'Mid', (0.0, 0.0)), ('near', 'Near', (0.0, 330.0)), ('m', 'M', M)):
            m.waypoint(part, f'CNV Reo {label}', 'west field', *at)
        if variant in DT:
            m.units += [iw.wall(BAR, length=80, shape='square', lifetime=None)]
            m.waypoint('gap', 'CNV Reo Gap', 'west field', *GAP)
            for x in BAR_XS:
                m.put(BAR, 'west field', float(x), 50.0, role='bar')
        if variant in TU:
            m.put(WALL, 'west field', *W2, role='wall2', name=WALL2)
            m.waypoint('p', 'CNV Reo P', 'west field', *P)
        return m


    MISSION = {f'reorder_{v}': (lambda v=v: mission(modname(v), v)) for v in VARIANTS}
    return dict(MISSION=MISSION)


BENCHES = (
    engine_acquire, engine_reorder,
)
