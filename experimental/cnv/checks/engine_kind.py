"""Retail-campaign conditions, batch 7 (round 243): PLAYER_HAS_COMPARISON_UNIT_KIND (3 uses: s04 (Player_1, ==, 0,
BEACON), ep01 (Allied02, <=, 3, FS_FACTORY), ep01 (Player_1, >, 0, ENGINEER)), PLAYER_LOST_OBJECT_TYPE (2: j06
(Player_1, the map's object list '_object list_japan all structs'), ep01 (Player_1, sovietchiefengineer -- an
Uprising unit the SDK lacks: AlliedEngineer stands in)) and NAMED_DESTROYED_BY_OBJECTTYPE (2, a04: (King Oni,
alliedcommandotech1) OR (King Oni, sovietcommandotech1) -> the bonus crate). Mission on maps/probe_border.py (level
ground), every place absolute; clear of probe_range's lanes (y 400, 1200-1900, 3300-3750) and the start (1250, 2500).
No trigger areas.

  all  kinds and losses: the player's AlliedEngineers eng p (1800, 2300) / eng p2 (1800, 2900), war factory F1
       (2500, 2400) and barracks F2 (3300, 2400); Soviet_4's war factory G1 (4200, 2400) and barracks G2 (4400,
       2950). Soviet_4's AlliedEngineer eng e (1000, 4600), Guardian truck w (2200, 4600) and King Oni (3600, 4600);
       the player's Tanya A (1000, 4000), Guardian gun (2200, 4000), Tanya B (3600, 4000): 600 north of their marks,
       beyond sight (200 / shroud 400). Every Soviet_4 unit and the player's engineers NO_ATTACK; truck w at 5 %.
       Object list 'CNV Kind Structs' = {AlliedWarFactory, AlliedBarracks} at 0 s.
       gun -> truck w at 2 s; NAMED_KILL eng p 4 s; Tanya A -> eng e 6 s (pistols); Tanya B -> King Oni 10 s (her
       charge: a vehicle); NAMED_KILL F1 12 s, eng p2 16 s, G1 20 s.
       种 (every frame) = 1 PLAYER_HAS_COMPARISON_UNIT_KIND(Player_1, >, 0, ENGINEER) 2 (Player_1, ==, 0, BEACON)
         4 (Soviet_4, <=, 3, FS_FACTORY) 8 (Soviet_4, >=, 1, ENGINEER) 16 (Player_1, ==, 2, FS_FACTORY)
       失 (adds its weight every frame a reader holds, never reset; in this order) = 1 PLAYER_LOST_OBJECT_TYPE(
         Player_1, AlliedEngineer) 2 (the same again) 4 (Soviet_4, AlliedEngineer) 8 (Player_1, AlliedWarFactory)
         16 (Player_1, 'CNV Kind Structs') 32 (Soviet_4, AlliedWarFactory)
       毁 (every frame) = 1 NAMED_DESTROYED_BY_OBJECTTYPE(eng e, alliedcommandotech1) 2 (King Oni,
         alliedcommandotech1) 4 (King Oni, sovietcommandotech1) 8 (truck w, alliedantivehiclevehicletech1)
         16 (eng p, alliedcommandotech1: a script's kill)
  [prediction from the data. PLAYER_HAS_COMPARISON_UNIT_KIND: Generals has only the _IN_TRIGGER_AREA one, which
   counts the one player's living non-INERT objects of the KindOf; RA3's _IN_TRIGGER_AREA was read (bench 10-25
   probe/count) to count EVERY player's objects. The two read apart here -- own (H-own): 31 to ~7 s (eng e dies:
   &8 off) 23, 12 s 7 (F1: &16 off), 16 s 6 (eng p2: &1 off), 6 after G1; every player's (H-all): 11 (4 FS_FACTORY:
   &4 / &16 off), 11 after eng e (eng p2 still an ENGINEER, any owner), 12 s 15 (3: &4 on), 16 s 6, 20 s 22 (2:
   &16 on). BEACON: only props (AIBeacon, MultiplayerBeacon ...) carry it, none here: &2 all run either way.
   PLAYER_LOST_OBJECT_TYPE (Generals evaluatePlayerLostObjectType): ONE stored count per (player, type string), the
   player's living objects of the type(s); a reader that finds fewer than stored stores the new count and is true
   -- one frame, and only for the first reader of that string (the second never sees it); a rise is stored
   silently. 失 1 at 4 s, 5 at ~7 s, 29 at 12 s (+8 +16: the list is its own string), 30 at 16 s, 62 at 20 s;
   per-reader memory would read 3 / 7 / 31 / 34 / 66. NAMED_DESTROYED_BY_OBJECTTYPE (RA3 only, no source): dead,
   and its killer's template that type; a script's kill has no killer. 毁 8 from ~3 s, 9 from ~7 s, 11 from ~13 s
   if her charge's kill is credited to Tanya (9 if to the charge object).]
  [bench 11-15 CampKindAll_mcp_1115_045506 (round 244): 种 11 / s11 15 / s15 6 / s18 22 -- every player's (H-all);
   失 s3 1 / s11 25 / s13 29 (eng e died late: Tanya walked) / s15 30 / s18 62 -- one shared count (the second
   reader never); 毁 0 all run. The steps ~1-2 s before the script timers.]

  by   all's units and timers, 毁 split into counters that add every evaluation (see by()). [bench 11-15
       CampKindBy_mcp_1115_045838: 死 s2 8 (eng p), s6 10 (truck w), s13 11 (eng e), s20 15 (King Oni); 毁 坦 王 0
       all run -- NAMED_DESTROYED_BY_OBJECTTYPE never true, not one evaluation, either case, any killer.]
"""
from maps import probe_border
from parts import Mission, Script, Test, kindof, status
import checks.engine_scripts8 as s8

TANK, ENG, TANYA, KING = ('AlliedAntiVehicleVehicleTech1', 'AlliedEngineer', 'AlliedCommandoTech1', 'JapanMechaKing')
NATASHA = 'SovietCommandoTech1'
FACTORY, BARRACKS = 'AlliedWarFactory', 'AlliedBarracks'
O = (1300.0, 4300.0)                            # probe_border's 'stop row'
UNITS = {'eng p': ('p1', ENG, (1800.0, 2300.0)), 'eng p2': ('p1', ENG, (1800.0, 2900.0)),
         'eng e': ('s4', ENG, (1000.0, 4600.0)), 'truck w': ('s4', TANK, (2200.0, 4600.0)),
         'oni': ('s4', KING, (3600.0, 4600.0)),
         'tanya a': ('p1', TANYA, (1000.0, 4000.0)), 'gun': ('p1', TANK, (2200.0, 4000.0)),
         'tanya b': ('p1', TANYA, (3600.0, 4000.0))}
BUILDINGS = {'f1': ('p1', FACTORY, (2500.0, 2400.0)), 'f2': ('p1', BARRACKS, (3300.0, 2400.0)),
             'g1': ('s4', FACTORY, (4200.0, 2400.0)), 'g2': ('s4', BARRACKS, (4400.0, 2950.0))}
LIST = 'CNV Kind Structs'
RUN = 30.0


def _n(part):
    return f'UNIT - CNV Kind {part.title()}'


def _put(m, template, x, y, **kw):
    m.put(template, 'stop row', x - O[0], y - O[1], **kw)


def mission():
    m = Mission(name='CampKind', map=probe_border, units=[], facts={})
    m.spawns |= {TANK, ENG, TANYA, KING, NATASHA}
    for role, (side, template, (x, y)) in {**UNITS, **BUILDINGS}.items():
        angle = 0.0 if role in BUILDINGS else (1.5708 if side == 'p1' else -1.5708)
        _put(m, template, x, y, side=side, angle=angle, name=_n(role), role=role)
    return m


def _seen(t, counter, label, parts):
    """counter += weight every frame a reader holds (never reset), one script per reader, in this order."""
    t.counters.append((counter, label))
    t.scripts += [Script(f'Test - {counter} {k}', [c], [('INCREMENT_COUNTER', w, counter)], once=False)
                  for k, (w, c) in enumerate(parts)]


def all_(m):
    t = Test()
    p1, s4 = m.player(), m.player('s4')
    n = {r: m.role(r).name for r in list(UNITS) + list(BUILDINGS)}
    quiet = ['eng p', 'eng p2', 'eng e', 'truck w', 'oni']
    t.scripts.append(Script('Test - Kind start', [], [
        ('UNIT_CHANGE_OBJECT_STATUS', n[r], status('NO_ATTACK'), 1) for r in quiet] + [
        ('UNIT_SET_HEALTH', n['truck w'], 5.0),
        ('OBJECTLIST_ADDOBJECTTYPE', FACTORY.lower(), LIST), ('OBJECTLIST_ADDOBJECTTYPE', BARRACKS.lower(), LIST)]))
    s8.at(t, 'gun', 2.0, [('NAMED_ATTACK_NAMED', n['gun'], n['truck w'])])
    s8.at(t, 'p', 4.0, [('NAMED_KILL', n['eng p'])])
    s8.at(t, 'ta', 6.0, [('NAMED_ATTACK_NAMED', n['tanya a'], n['eng e'])])
    s8.at(t, 'tb', 10.0, [('NAMED_ATTACK_NAMED', n['tanya b'], n['oni'])])
    s8.at(t, 'f1', 12.0, [('NAMED_KILL', n['f1'])])
    s8.at(t, 'p2', 16.0, [('NAMED_KILL', n['eng p2'])])
    s8.at(t, 'g1', 20.0, [('NAMED_KILL', n['g1'])])
    k = 'PLAYER_HAS_COMPARISON_UNIT_KIND'
    s8.total(t, 'CNV_Kind_Kind', '种', [
        (1, (k, p1, 4, 0, kindof('ENGINEER'))), (2, (k, p1, 2, 0, kindof('BEACON'))),
        (4, (k, s4, 1, 3, kindof('FS_FACTORY'))), (8, (k, s4, 3, 1, kindof('ENGINEER'))),
        (16, (k, p1, 2, 2, kindof('FS_FACTORY')))])
    lost = 'PLAYER_LOST_OBJECT_TYPE'
    _seen(t, 'CNV_Kind_Lost', '失', [
        (1, (lost, p1, ENG)), (2, (lost, p1, ENG)), (4, (lost, s4, ENG)), (8, (lost, p1, FACTORY)),
        (16, (lost, p1, LIST)), (32, (lost, s4, FACTORY))])
    d = 'NAMED_DESTROYED_BY_OBJECTTYPE'
    s8.total(t, 'CNV_Kind_By', '毁', [
        (1, (d, n['eng e'], TANYA.lower())), (2, (d, n['oni'], TANYA.lower())), (4, (d, n['oni'], NATASHA.lower())),
        (8, (d, n['truck w'], TANK.lower())), (16, (d, n['eng p'], TANYA.lower()))])
    t.expect = [('失', RUN - 1, '>=', 1), ('毁', RUN - 1, '>=', 1)]
    s8.watch(t, RUN)
    return t


def by(m):
    """all's 毁 read 0 all run (bench 11-15 CampKindAll_mcp_1115_045506) while eng e died (种 &8 off, 失 &4 at s13):
    tells a one-frame truth (a counter that never resets: its weight every evaluation a reader holds) from never
    true, the killer's template's case, and whether the victims died at all. 毁 = 1 (eng e, alliedcommandotech1) +
    1000 (eng e, AlliedCommandoTech1); 坦 = 1 (truck w, alliedantivehiclevehicletech1) + 1000 (eng p,
    alliedcommandotech1: a script's kill); 王 = 1 (King Oni, alliedcommandotech1) + 1000 (King Oni,
    sovietcommandotech1); 死 (every frame) = 1 NAMED_DESTROYED eng e, 2 truck w, 4 King Oni, 8 eng p."""
    t = all_(m)
    t.scripts = [s for s in t.scripts if s.name.startswith(('Test - Kind start', 'Test - S8'))]
    t.counters = []
    n = {r: m.role(r).name for r in list(UNITS) + list(BUILDINGS)}
    d = 'NAMED_DESTROYED_BY_OBJECTTYPE'
    _seen(t, 'CNV_Kind_By', '毁', [(1, (d, n['eng e'], TANYA.lower())), (1000, (d, n['eng e'], TANYA))])
    _seen(t, 'CNV_Kind_Tank', '坦', [(1, (d, n['truck w'], TANK.lower())), (1000, (d, n['eng p'], TANYA.lower()))])
    _seen(t, 'CNV_Kind_Oni', '王', [(1, (d, n['oni'], TANYA.lower())), (1000, (d, n['oni'], NATASHA.lower()))])
    s8.total(t, 'CNV_Kind_Dead', '死', [(w, ('NAMED_DESTROYED', n[r])) for w, r in
                                        ((1, 'eng e'), (2, 'truck w'), (4, 'oni'), (8, 'eng p'))])
    t.expect = [('死', RUN - 1, '>=', 1)]
    s8.watch(t, RUN)
    return t


MISSION = {'engine_kind': mission}
CHECKS = {'engine_kind': {'all': all_, 'by': by}}
