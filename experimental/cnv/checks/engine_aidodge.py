"""DodgeThreats on/off, native precision-strike beacon, recruited Hunt warriors.

Prediction: both warriors fight inside the 150-half-side square before s30;
with DodgeThreats on at least one leaves during s30..34, off both stay.
Conscripts are kept healthy; powers and injured pullback are off. The beacon
dispatches no damage or push (the ordinary infantry fight still deals damage).
This square tests a movement difference, not the exact 200 safety radius.

MEASURED: named beacon on/off both present, two living warriors; on leaves
(frame 468: near 1, 479: 0), off stays (456..501: near 2). The bench capture
seconds drift against the frame counter: on's automatic seconds-window verdict
is FAIL, off PASS. Keep that diagnostic failure visible; replay by game frames
in tests/test_ai_dodge.py. A clock-stable engine acceptance check remains a gap,
the bounded single-beacon consumer is replayed there. Exact timing, safety-circle
boundaries, general filters and multi-threat choice remain gaps (work/re/e116_dodge.md).
"""
from model import Script, Test, counted, square, status


def probe(m):
    t = Test()
    s1 = m.player('s1')
    warrior = m.cnv_units[0]
    at = m.facts['threat at']
    end = at + m.facts['threat lifetime']
    area = 'CNV Dodge Sample'
    t.areas[area] = square(*m.point('dodge spot'), m.facts['sample half size'])
    t.scripts += [Script('Dodge - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]),
                  Script('Dodge - frame', [], [('INCREMENT_COUNTER', 1, 'CNV_Dodge_Frame')], once=False),
                  Script('Dodge - health', [],
                         [('UNIT_SET_HEALTH', r.name, 100.0) for r in m.roles('conscript')], once=False)]
    t.counters.append(('CNV_Dodge_Frame', '帧数'))
    counted('CNV_Dodge_Own', '造出', t, template=warrior, player=s1)
    counted('CNV_Dodge_Near', '范围', t, template=warrior, player=s1, area=area)
    # The native beacon's player ownership count stayed 0 on this probe.
    # Query the named object itself, so 0 cannot be mistaken for no threat.
    t.counters.append(('CNV_Dodge_Beacon', '威胁'))
    beacon = m.cnv_named['beacon']
    t.scripts += [Script('Dodge - beacon alive', [('NAMED_NOT_DESTROYED', beacon)],
                         [('SET_COUNTER', 'CNV_Dodge_Beacon', 1)], once=False),
                  Script('Dodge - beacon gone', [('NAMED_DESTROYED', beacon)],
                         [('SET_COUNTER', 'CNV_Dodge_Beacon', 0)], once=False)]
    t.expect += [('造出', at - 3, '==', 2, end), ('范围', at - 3, '==', 2, at - 1),
                 ('威胁', at, 'ever>=', 1, end),
                 ('范围', at + 1, 'ever<=' if m.facts['dodge enabled'] else '==',
                  1 if m.facts['dodge enabled'] else 2, end)]
    t.bench = [('bench_watch', dict(seconds=end + 3, every=1, sheet=False, lines=4))]
    return t


CHECKS = {name: {'r': probe} for name in ('aidodgeon', 'aidodgeoff')}


def timing(m):
    """Fixed 0/2 second contrast, latched in game frames (work/re/e117_dodge_clock.md).

    Prediction: both start with two living warriors in the same square; zero
    leaves sooner after the beacon. Leaving includes walking time, so neither
    latch measures the exact reaction frame. Random ranges remain a gap.

    MEASURED: both born f451; zero first leaves f454, two f486; bad stays 0.
    Replay asserts their order, not exact departure frames (model: 475/505).
    """
    t = probe(m)
    frame, born, left, bad = ('CNV_Dodge_Frame', 'CNV_Dodge_Born',
                              'CNV_Dodge_Left', 'CNV_Dodge_Bad')
    live = [('NAMED_NOT_DESTROYED', m.cnv_named['beacon'])]
    t.scripts += [
        Script('Dodge - born latch', live,
               [('SET_COUNTER_TO_COUNTER', born, frame)]),
        Script('Dodge - leave latch', live + [('COUNTER', born, 3, 1),
                                             ('COUNTER', 'CNV_Dodge_Near', 0, 2)],
               [('SET_COUNTER_TO_COUNTER', left, frame)])]
    # Keep the same count scripts, but display the latches within the four-line HUD.
    # Any missing member, or a pre-beacon departure, invalidates this contrast.
    for counter in ('CNV_Dodge_Own', 'CNV_Dodge_Near'):
        for op, value in ((0, 2), (4, 2)):
            t.scripts.append(Script(f'Dodge - prerequisite {counter} {op}',
                [('COUNTER', frame, 3, 405), ('COUNTER', frame, 0, 450),
                 ('COUNTER', counter, op, value)], [('SET_COUNTER', bad, 1)]))
    for op in (0, 4):
        t.scripts.append(Script(f'Dodge - survival {op}', live +
            [('COUNTER', 'CNV_Dodge_Own', op, 2)], [('SET_COUNTER', bad, 1)]))
    t.counters = [(frame, '帧数'), (born, '出现'), (left, '离开'), (bad, '失配')]
    t.expect = [('出现', 1, 'ever>=', 1, 45), ('离开', 1, 'ever>=', 1, 45),
                ('失配', 1, '==', 0, 45)]
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


def death(m):
    """timing, the fourth line the first frame a warrior is gone (A round 258).

    Prediction (model after A round 230, attack-movers aim from the frame they get in range): both conscripts
    shoot the nearer warrior from ~f392, 2 x ~10.6 dps on its 160 HP, dead ~f505 -- before the beacon ends
    (~f511), so 'two''s first-leave latch is that death, not a departure. The bench kept both alive while the
    beacon lived (timing: bad 0), so its death latch is > ~f511 or 0 (none by s45).
    """
    t = timing(m)
    frame, dead = 'CNV_Dodge_Frame', 'CNV_Dodge_Dead'
    t.scripts.append(Script('Dodge - death latch', [('COUNTER', frame, 3, 405),
                                                    ('COUNTER', 'CNV_Dodge_Own', 0, 2)],
                            [('SET_COUNTER_TO_COUNTER', dead, frame)]))
    t.counters = t.counters[:3] + [(dead, '阵亡')]
    # Bench 11-16 (A258): the game ran ~5 frames a second, the frame counter was at f301 by s73 -- no reading.
    # Watch long enough to pass the beacon even when the bench runs slow.
    # 11-16 (A259): 200 s, the CPU was still at 100 % (other lines' tests); the game ran ~12 frames a second.
    # RESULTS A259 (PASS, 257 s): born 451, left 454, first warrior gone at f706 -- the simulator's f511 is ~195
    # frames early. Simulator (a259_hp): both conscripts shoot warrior 289 from f398 (2 x 10.6 dps, 160 HP), the
    # beacon (3850, 2900) sends it radially north to (3842, 2700), into the conscripts (2709), dead f510. Unsplit:
    # later first shot, split fire, or another escape direction (the radial escape is INFERRED, micro.dodge_tick).
    t.expect = [('出现', 1, 'ever>=', 1, 200), ('离开', 1, 'ever>=', 1, 200)]
    t.bench = [('bench_watch', dict(seconds=200, every=1, sheet=False, lines=4))]
    return t


def split(m):
    """death's mission unchanged; tells apart the three readings of its f706 (A round 260).

    Named, handed-over warriors would not do: the recruiters refuse handed-over units (engine_aimicro, round 18),
    so the AI-built pair stays and the check latches both deaths instead of reading health. Lines: frame, the first
    and the second warrior gone (Own 2 -> 1, Own -> 0, from f405), and how many warriors stand in a band north of the
    sample square (150 deep, toward the conscripts), every second.
    Focus fire (both conscripts on one warrior, 2 x 10.6 dps, 160 HP) puts the second death >= ~110 frames after the
    first; split fire (one each) puts them close together. The band tells whether the dodge goes north (the
    simulator's radial escape, INFERRED) or elsewhere.
    Simulator (model RA3-EngineModel-a, work/logs/a260_s.py): zero 511 / 867, band 2 at s33, 1 at s34..35, then 0;
    two 511 / 918.
    RESULTS A260 zero (PASS, 235 s, ~15 frames a second): deaths 706 / 724 -- 18 frames apart: split fire (or both
    hit together), not the simulator's focus fire; the band 0 every second (s1..s218): no warrior dodged north.
    """
    t = death(m)
    frame, dead, dead2, band = 'CNV_Dodge_Frame', 'CNV_Dodge_Dead', 'CNV_Dodge_Dead2', 'CNV_Dodge_North'
    x, y = m.point('dodge spot')
    half = m.facts['sample half size']
    area = 'CNV Dodge North'
    t.areas = {area: [(x - half, y - half - 150), (x + half, y - half - 150), (x + half, y - half),
                      (x - half, y - half)], **t.areas}
    t.scripts.append(Script('Dodge - second death latch', [('COUNTER', frame, 3, 405),
                                                           ('COUNTER', 'CNV_Dodge_Own', 2, 0)],
                            [('SET_COUNTER_TO_COUNTER', dead2, frame)]))
    counted(band, '北带', t, template=m.cnv_units[0], player=m.player('s1'), area=area)
    t.counters = [(frame, '帧数'), (dead, '阵亡'), (dead2, '再亡'), (band, '北带')]
    t.expect = [('阵亡', 1, 'ever>=', 1, 200)]
    t.bench = [('bench_watch', dict(seconds=200, every=1, sheet=False, lines=4))]
    return t


def unpowered(m):
    """split's mission with s1's protocol points taken away; tells whether H6 makes the bench's f706 (A round 263).

    A round 262: on the bench s1 (Allied, starting point 1) put a freezing power on the east conscript (red f382,
    frozen white f397, ice and a sky beam f427..f503); the simulator's AI casts no player power. The program buys
    from frame 10 (simtech.Book.ai_buy), so a frame-0 script with points and their cap at 0 (as plan.py's
    '技能 否') leaves it nothing to buy or cast. Lines: the first and second warrior gone (as split), how many
    frames any p1 object is UNDER_FROZEN (AttributeModifer_CryoBeam_10's status; only adds), and how many
    conscripts stand deep, past the simulator's stop (y >= 2780, up to the sample square's far edge).
    H6 holds if the first death comes back near the simulator's ~511, frozen stays 0 and deep stays 0 before it.
    Simulator (powers never cast): deaths 511 / 867, frozen 0, deep 0 (conscripts stop at ~2710).
    RESULTS A263 zero (PASS, 221 s): deaths 527 / 777, frozen 0 all 204 s, deep 1 from s31 (s36-37 0), 2 from s52.
    H6 holds: without s1's power the first death is back to 527 (split's 706 was the freeze); focus fire (250
    frames apart). Left: one conscript stands past 2780 before the first death (the simulator's stop ~2710), and
    the second death is 90 frames before the simulator's -- the H5a gap (start / speed / stop depth), not H6.
    """
    t = split(m)
    s1, p1 = m.player('s1'), m.player('p1')
    frame, frozen, deep = 'CNV_Dodge_Frame', 'CNV_Dodge_Frozen', 'CNV_Dodge_Deep'
    x, y = m.point('dodge spot')
    half = m.facts['sample half size']
    area = 'CNV Dodge Deep'
    t.areas.pop('CNV Dodge North')
    t.areas = {area: [(x - half, 2780.0), (x + half, 2780.0), (x + half, y + half), (x - half, y + half)],
               **t.areas}
    t.scripts = [s for s in t.scripts if 'CNV_Dodge_North' not in str(s)]
    t.scripts.insert(0, Script('Dodge - no powers', [], [('PLAYER_SET_MAX_PLAYER_POWER_POINTS', s1, 0),
                                                         ('PLAYER_SET_PLAYER_POWER_POINTS', s1, 0)]))
    t.scripts.append(Script('Dodge - frozen frames',
                            [('PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS', p1, 3, 1, status('UNDER_FROZEN'))],
                            [('INCREMENT_COUNTER', 1, frozen)], once=False))
    counted(deep, '深入', t, template='SovietAntiInfantryInfantry', player=p1, area=area)
    t.counters = [('CNV_Dodge_Dead', '阵亡'), ('CNV_Dodge_Dead2', '再亡'), (frozen, '冻住'), (deep, '深入')]
    assert frame in str(t.scripts)
    return t


BANDS = (2550.0, 2750.0, 2850.0, 2950.0, 3050.0, 3150.0, 3350.0)


def where(m):
    """timing's latches with s1's powers off (as unpowered), plus where the two warriors stand (A round 265, H7).

    The simulator cannot cast the AI's player powers (A round 262), so timing's bench reading (powers on) is not
    the simulator's mission. Lines: frame, born, left (timing's latches) and the warriors' y bands as digits --
    digit k (units = k 0) = how many of s1's warriors stand in band k, north to south: y 2550-2750 (toward the
    conscripts), 2750-2850, 2850-2950 (the beacon at 2900), 2950-3050, 3050-3150, 3150-3350; x 3600-4100. So 1100
    = one in 2850-2950 and one in 2950-3050. The sample square is y 2750-3050 (bands 1..3).
    Simulator (model RA3-EngineModel-a 8f5d7c3, work/logs/a265_y.py): before the beacon one warrior at y 2841, one
    at 2863 (110); both in 2750-2850 by f465 (20); zero leaves f482, two's first warrior dies f511 at y 2818 (the
    latch is the death).
    RESULTS A265 (zero 183 s -- the run's judge crashed on a stale expectation, the frames re-read with
    work/logs/a265_reread.py; two PASS 165 s): both born f451; before it both warriors in 2850-2950 (200) from f339;
    zero: 20 by f466, left f490, 11 at f504, 2 at f526, one gone by f535, none by f777; two: 20 at f497, one gone
    and left f506, the other alone at 10, none by f785. So H7 is false: without the power the warriors stand where
    the simulator puts them (within one band) and both dodge north; e117's three-frame departure was the freeze.
    """
    t = timing(m)
    s1 = m.player('s1')
    x, _ = m.point('dodge spot')
    band = 'CNV_Dodge_Band'
    areas = {}
    parts = []
    for k, (y0, y1) in enumerate(zip(BANDS, BANDS[1:])):
        area = f'CNV Dodge Band {k}'
        areas[area] = [(x - 250, y0), (x + 250, y0), (x + 250, y1), (x - 250, y1)]
        parts += [Script(f'Dodge - band {k} {n}',
                         [('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA', s1, 2, n,
                           m.cnv_units[0], area)],
                         [('INCREMENT_COUNTER', n * 10 ** k, band)], once=False) for n in (1, 2)]
    # non-overlapping bands first: a type-in-area count keeps only the first ~7 declared areas (know-how, H5)
    t.areas = {**areas, **t.areas}
    t.scripts.insert(0, Script('Dodge - no powers', [], [('PLAYER_SET_MAX_PLAYER_POWER_POINTS', s1, 0),
                                                         ('PLAYER_SET_PLAYER_POWER_POINTS', s1, 0)]))
    t.scripts.append(Script('Dodge - band zero', [], [('SET_COUNTER', band, 0)], once=False))
    t.scripts += parts
    t.counters = t.counters[:3] + [(band, '武士带')]
    t.expect = [('出现', 1, 'ever>=', 1, 55), ('离开', 1, 'ever>=', 1, 55)]
    t.bench = [('bench_watch', dict(seconds=60, every=0.5, sheet=False, lines=4))]
    return t


CHECKS.update({name: {'r': timing, 'd': death, 's': split, 'n': unpowered, 'y': where}
               for name in ('aidodgezero', 'aidodgetwo')})
