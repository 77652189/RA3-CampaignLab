"""A8's Liberty rewind on the bench (engine line D, user 11-11): an enemy (Soviet_1) Liberty that, at 1 % health,
goes back BACK seconds (units/rewind.py) and -- the mission's rules -- back to the owner it had then; a press of the
launcher hands it to the player for CONTROL seconds, then back to its owner unless it was rewound while ours.

The rules (scripts, every frame):
  rewind  health <= 1 % and the belt is ready: press it; not ready for COOLDOWN seconds; 回溯 + 1.
  die     health <= 1 %, not ready, GRACE seconds after the last press: NAMED_KILL (the cooldown's death).
  owner   every second the flags shift: Rw Own3 <- Own2 <- Own1 <- (ours now); a press hands it to the player if
          Own3 (ours 2-3 s ago), else to Soviet_1; ours at a press = ours for good (Rw Perm).
  control (control(m) by the check): ours now, back to Soviet_1 CONTROL s later unless Rw Perm.

Published (the cast): carrier (on the west field), gun 1 / gun 2 (our two Multigunners 450 west of it, out of
its sight and theirs: a check sends them in); marks start (the carrier), away (400 east of it).
"""
from maps import island
from parts import Mission, Script
from units import rewind as rw

COOLDOWN, GRACE, CONTROL = 20.0, 3.0, 15.0
CARRIER = 'UNIT - CNV Liberty Rw'
GUN = 'AlliedAntiAirVehicleTech1'


def control(m, at):
    """Scripts: at `at` the carrier is the player's for CONTROL s (the launcher), then Soviet_1's unless Rw Perm."""
    p1, s1 = m.player('p1'), m.player('s1')
    return [Script('Rw - control timer', [], [('SET_MILLISECOND_TIMER', 'Rw Control', at)]),
            Script('Rw - control', [('TIMER_EXPIRED', 'Rw Control')],
                   [('NAMED_TRANSFER_OWNERSHIP_PLAYER', CARRIER, p1),
                    ('SET_MILLISECOND_TIMER', 'Rw Control End', CONTROL)]),
            Script('Rw - control end', [('TIMER_EXPIRED', 'Rw Control End'), ('FLAG', 'Rw Perm', 0)],
                   [('NAMED_TRANSFER_OWNERSHIP_PLAYER', CARRIER, s1)])]


def rules(m, owner=True):
    p1, s1 = m.player('p1'), m.player('s1')
    low = ('UNIT_HEALTH', CARRIER, 1, 1)                    # <= 1 %
    out = [Script('Rw - start', [], [('SET_FLAG', 'Rw Ready', 1), ('SET_MILLISECOND_TIMER', 'Rw Tick', 1.0),
                                     ('SET_MILLISECOND_TIMER', 'Rw Grace', 0.1)]),
           Script('Rw - ready', [('TIMER_EXPIRED', 'Rw Cooldown'), ('FLAG', 'Rw Ready', 0)],
                  [('SET_FLAG', 'Rw Ready', 1)], once=False),
           Script('Rw - rewind', [low, ('FLAG', 'Rw Ready', 1)],
                  [('NAMED_USE_COMMANDBUTTON_ABILITY', CARRIER, m.ability('carrier', 'rewind')),
                   ('SET_FLAG', 'Rw Ready', 0), ('SET_FLAG', 'Rw Fired', 1), ('INCREMENT_COUNTER', 1, 'Rw Rewinds'),
                   ('SET_MILLISECOND_TIMER', 'Rw Cooldown', COOLDOWN), ('SET_MILLISECOND_TIMER', 'Rw Grace', GRACE)],
                  once=False),
           Script('Rw - die', [low, ('FLAG', 'Rw Ready', 0), ('TIMER_EXPIRED', 'Rw Grace')],
                  [('NAMED_KILL', CARRIER)], once=False)]
    if owner:
        tick = ('TIMER_EXPIRED', 'Rw Tick')
        for k in (3, 2):
            out += [Script(f'Rw - own{k} 0', [tick], [('SET_FLAG', f'Rw Own{k}', 0)], once=False),
                    Script(f'Rw - own{k} 1', [tick, ('FLAG', f'Rw Own{k - 1}', 1)], [('SET_FLAG', f'Rw Own{k}', 1)],
                           once=False)]
        out += [Script('Rw - own1 0', [tick], [('SET_FLAG', 'Rw Own1', 0)], once=False),
                Script('Rw - own1 1', [tick, ('NAMED_OWNED_BY_PLAYER', p1, CARRIER)], [('SET_FLAG', 'Rw Own1', 1)],
                       once=False),
                Script('Rw - tick', [tick], [('SET_MILLISECOND_TIMER', 'Rw Tick', 1.0)], once=False),
                Script('Rw - back ours', [('FLAG', 'Rw Fired', 1), ('FLAG', 'Rw Own3', 1)],
                       [('NAMED_TRANSFER_OWNERSHIP_PLAYER', CARRIER, p1), ('SET_FLAG', 'Rw Perm', 1)], once=False),
                Script('Rw - back theirs', [('FLAG', 'Rw Fired', 1), ('FLAG', 'Rw Own3', 0)],
                       [('NAMED_TRANSFER_OWNERSHIP_PLAYER', CARRIER, s1)], once=False)]
    out.append(Script('Rw - fired', [('FLAG', 'Rw Fired', 1)], [('SET_FLAG', 'Rw Fired', 0)], once=False))
    return out


def mission(name='CampRw', body='HighlanderBody'):
    u = rw.rewind(body=body, probe=3000)
    m = Mission(name=name, map=island, units=[u])
    m.ext = True                                        # ra3ext's CNVProbe on the carrier: its position per frame
    m.put(u.id, 'west field', 0, -60, side='s1', name=CARRIER, role='carrier')
    for k, dy in ((1, -100), (2, -20)):
        m.put(GUN, 'west field', -450, dy, name=f'UNIT - CNV Rw Gun {k}', role=f'gun {k}')
    m.waypoint('start', 'CNV Rw Start', 'west field', 0, -60)
    m.waypoint('away', 'CNV Rw Away', 'west field', 400, -60)
    m.scripts += rules(m)
    return m


NEW = 'UNIT - CNV Liberty Rw New'
SWAP_AT, NEW_HURT = 15, 3000            # health % that swaps it; damage to the new one (6000 hp: 50 %)


def swapped(name='CampRwS'):
    """The show the user chose instead of a real rewind (11-11): at SWAP_AT % the carrier is killed (its crash plays)
    and a new one spawned where it was (UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION), playing Tanya's
    time-warp FX as it is made (FXListBehavior onCreate), on the player's team if the old one was the player's then,
    else Soviet_1's, and hurt to 50 %. Our Multigunners stand 100 south of it (gun 1 / gun 2)."""
    u = lib_carrier()
    m = Mission(name=name, map=island, units=[u])
    m.put(u.id, 'west field', 0, -60, side='s1', name=CARRIER, role='carrier')
    for k, dx in ((1, -40), (2, 40)):
        m.put(GUN, 'west field', dx, 40, name=f'UNIT - CNV Rw Gun {k}', role=f'gun {k}')
    low = ('UNIT_HEALTH', CARRIER, 1, SWAP_AT)
    for side, cond in (('p1', [('NAMED_OWNED_BY_PLAYER', m.player('p1'), CARRIER)]), ('s1', [])):
        m.scripts.append(Script(f'Rw - swap {side}', [low, ('FLAG', 'Rw Swapped', 0)] + cond,
                                [('UNIT_SPAWN_NAMED_OBJECT_ON_TEAM_AT_NAMED_OBJECT_LOCATION', NEW, u.id,
                                  island.TEAMS[side], CARRIER),
                                 ('NAMED_DELETE', CARRIER), ('NAMED_DAMAGE', NEW, NEW_HURT), ('SET_FLAG', 'Rw Swapped', 1)]))
    return m


def lib_carrier(id='CNV_LibRwS'):
    from units import liberty as lib
    from units.liberty import sub1
    u = lib.liberty(id, tag='RwS', drone_range=1, drones_home=False, model=None)
    # bench CampRwSSwap_mcp_1111_163449: with retail's ActiveBody a 5200 blow at 56 % killed it before the swap ran;
    # ImmortalBody holds it at 1 hp, so the swap always runs (and deletes it: NAMED_KILL cannot kill this body)
    u.xml = sub1(u.xml, '<ActiveBody\n\t\t\t\tid="ModuleTag_Body"', '<ImmortalBody\n\t\t\t\tid="ModuleTag_Body"')
    u.xml = sub1(u.xml, '\t\t</Behaviors>', '''			<FXListBehavior id="ModuleTag_CNV_RewindFX">
				<DieMuxData DeathTypes="ALL"/>
				<Event Index="onCreate" FX="FX_TanyaTimeWarp"/>
			</FXListBehavior>
		</Behaviors>''')
    u.what = '自由号（演出版回溯）：出生时播谭雅时空腰带的特效'
    return u


MISSION = {'rewind_swap': lambda: swapped(),'rewind': lambda: mission(), 'rewind_imm': lambda: mission(name='CampRwI', body='ImmortalBody')}
