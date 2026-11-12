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
from parts import Mission, Role, Script
from units import rewind as rw

COOLDOWN, GRACE, CONTROL = 20.0, 3.0, 15.0
CARRIER = 'UNIT - CNV Liberty Rw'
GUN = 'AlliedAntiAirVehicleTech1'


def control(m):
    """Scripts: when timer Rw Control (a check sets it) runs out the carrier is the player's for CONTROL s (the
    launcher), then Soviet_1's unless Rw Perm."""
    p1, s1 = m.player('p1'), m.player('s1')
    return [Script('Rw - control', [('FLAG', 'Rw Control On', 1), ('TIMER_EXPIRED', 'Rw Control')],
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
    m.scripts += rules(m) + control(m)
    return m


SWAP_AT, MAX_HP, NEW_HURT = 15, 6000, 3000     # health % that swaps it; its max hp; then 3000 off: 50 %
ASIDE, BACK_AFTER = -330.0, 6.0  # round 54 (user 11-11): at the swap it jumps ASIDE (west: away from the base's pads; hull 280 across: off
                                # the wreck), BACK_AFTER s later -- the wreck's crash seen -- back to its spot


def swapped(name='CampRwS', scale=rw.WARP_SCALE):
    """The show the user chose instead of a real rewind (11-11). Round 49: the carrier itself stays on as "the new
    one" (its spot, facing and name the old one's by construction; round 47's spawned new one faced east whatever
    the old one did). At SWAP_AT % the mission presses its wreck button (units/rewind.py swap_carrier: an OCL drops
    a wreck on its spot and facing, the wreck plays the time-warp FX `scale` times larger and crashes after
    rw.WRECK_LIFE s; Rw Wrecks + 1) and puts it back at 50 % (NAMED_SET_MAX_HEALTH MAX_HP full -- bench
    engine_maxhealth: 100 % --, then NAMED_DAMAGE NEW_HURT; UNIT_SET_HEALTH did nothing to it, round 45). Ours at
    the swap = ours for good (Rw Perm: the control's end leaves it ours). Our Multigunners stand 100 south of it.
    Round 54: at the swap it also jumps (its deck jump) to mark aside, ASIDE west, so the wreck falls in sight, and
    BACK_AFTER s later back to mark home, where it stood (the bench's carrier does not move; a moving one would need
    its spot kept, which no script action does)."""
    w = rw.wreck(scale=scale)
    u = rw.swap_carrier(wreck_id=w.id)
    m = Mission(name=name, map=island, units=[u, w])
    m.put(u.id, 'west field', 0, -60, side='s1', name=CARRIER, role='carrier')
    m.waypoint('home', 'CNV Rw Home', 'west field', 0, -60)
    m.waypoint('aside', 'CNV Rw Aside', 'west field', ASIDE, -60)
    for k, dx in ((1, -40), (2, 40)):
        m.put(GUN, 'west field', dx, 40, name=f'UNIT - CNV Rw Gun {k}', role=f'gun {k}')
    low = ('UNIT_HEALTH', CARRIER, 1, SWAP_AT)
    jump = m.ability('carrier', 'jump')
    swap = [('NAMED_USE_COMMANDBUTTON_ABILITY', CARRIER, m.ability('carrier', 'wreck')),
            ('NAMED_SET_MAX_HEALTH', CARRIER, MAX_HP, 1), ('NAMED_DAMAGE', CARRIER, NEW_HURT),
            ('INCREMENT_COUNTER', 1, 'Rw Wrecks'), ('SET_FLAG', 'Rw Swapped', 1),
            ('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, jump, m.mark('aside')),
            ('SET_MILLISECOND_TIMER', 'Rw Back', BACK_AFTER)]
    m.scripts += [Script('Rw - swap p1', [low, ('FLAG', 'Rw Swapped', 0), ('NAMED_OWNED_BY_PLAYER', m.player('p1'), CARRIER)],
                         [('SET_FLAG', 'Rw Perm', 1)] + swap),
                  Script('Rw - swap s1', [low, ('FLAG', 'Rw Swapped', 0)], swap),
                  Script('Rw - back', [('FLAG', 'Rw Swapped', 1), ('TIMER_EXPIRED', 'Rw Back')],
                         [('NAMED_FIRE_SPECIAL_POWER_AT_WAYPOINT', CARRIER, jump, m.mark('home'))])]
    m.cast['wreck'] = Role(w.id, side='p1')     # dropped by the carrier at the swap (its owner's), no name
    m.scripts += control(m)
    return m


MISSION = {'rewind_swap': lambda: swapped(),'rewind': lambda: mission(), 'rewind_imm': lambda: mission(name='CampRwI', body='ImmortalBody')}
