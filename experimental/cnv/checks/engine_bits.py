"""Engine unit test: what BlendTileData's other bit fields do for passing, and at what height the game's logic puts the
water (docs/engine/terrain.md 3 and 1; engine line round 9).

On the probe map (maps/probe_bits.py) each pen holds two units, both ordered by script to the point 280 north, outside
the pen's ring. A pen's counter adds 1 for the first and 10 for the second standing there: 11 both got out, 1 only
the first, 10 only the second, 0 neither.

bits (row 1):
  players        field 1 on the ring; the player's tank (1), warrior (10)
  air            field 6 on the ring; the player's Cryocopter (1), tank (10)
  zero three     fields 0 and 3; the player's tank (1), warrior (10): does field 3 open what field 0 shut
  players enemy  field 1 again, far east (out of reach of the player's units); the enemy's tank (1), warrior (10):
                 which side field 1 holds back
enemy: players enemy as above, and zero (field 0 only; the enemy's tank, warrior): the control that the enemy's units
  obey field 0 too -- run it when players enemy reads 0.
water (row 2): moats with floors at 270 / 300 / 315 / 330 ours (169 / 187.5 / 197 / 206 world, the water at 200
  world); the player's tank (1), warrior (10) each.

Expected (测, 2026-11-04, run CampBitsBits / CampBitsWater): field 1 holds the player's units but not the enemy's;
field 3 does not open field 0; field 6 held neither the Cryocopter nor the tank (the first run guessed "aircraft only"
and read 11); the water's logic edge lies between 315 and 330 ours, as the game's scale puts 200 world at 320.
"""
from maps import probe_bits
from parts import Mission, Script, Test, square

TANK = 'AlliedAntiVehicleVehicleTech1'
ENEMY_TANK = 'SovietAntiVehicleVehicleTech1'
WARRIOR = 'JapanAntiInfantryInfantry'
COPTER = 'AlliedSupportAircraft'
_PAIR = (('tank', TANK, 'p1', 1), ('warrior', WARRIOR, 'p1', 10))
_ENEMY = (('enemy tank', ENEMY_TANK, 's1', 1), ('enemy warrior', WARRIOR, 's1', 10))
# pen: ((part, template, side, worth), ...)
WHO = {
    'players': _PAIR,
    'air': (('copter', COPTER, 'p1', 1), ('tank', TANK, 'p1', 10)),
    'zero three': _PAIR,
    'players enemy': _ENEMY,
    'zero': _ENEMY,
    'moat 270': _PAIR,
    'moat 300': _PAIR,
    'moat 315': _PAIR,
    'moat 330': _PAIR,
}
LABEL = {'players': '玩家位', 'air': '空军位', 'zero three': '零加三', 'players enemy': '玩家位敌', 'zero': '零位敌',
         'moat 270': '沟270', 'moat 300': '沟300', 'moat 315': '沟315', 'moat 330': '沟330'}
ROWS = {'bits': ('players', 'air', 'zero three', 'players enemy'), 'enemy': ('players enemy', 'zero'),
        'water': ('moat 270', 'moat 300', 'moat 315', 'moat 330')}
EXPECT = {'players': 0, 'air': 11, 'zero three': 0, 'players enemy': 11, 'zero': 0,
          'moat 270': 0, 'moat 300': 0, 'moat 315': 0, 'moat 330': 11}
RUN = 24.0


def _key(pen):
    return pen.title().replace(' ', '')


def mission():
    m = Mission(name='CampBits', map=probe_bits, facts={})
    for pen, who in WHO.items():
        for k, (part, template, side, _) in enumerate(who):
            m.put(template, pen, -30.0 + 60.0 * k, 0, side=side, name=f'UNIT - CNV Bits {_key(pen)} {_key(part)}',
                  role=f'{pen} {part}')
    return m


def _row(m, pens):
    t = Test()
    order = [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
    for pen in pens:
        out = f'Test Bits {_key(pen)} Out'
        t.waypoints[out] = m.site(f'{pen} out')
        t.areas[out] = square(*m.site(f'{pen} out'), 70)
        counter = f'CNV_Bits_{_key(pen)}'
        t.counters.append((counter, LABEL[pen]))
        t.scripts.append(Script(f'Test - {counter} zero', [], [('SET_COUNTER', counter, 0)], once=False))
        for part, _, _, worth in WHO[pen]:
            name = m.role(f'{pen} {part}').name
            order.append(('MOVE_NAMED_UNIT_TO', name, out))
            t.scripts.append(Script(f'Test - {counter} {_key(part)}', [('NAMED_INSIDE_AREA', name, out)],
                                    [('INCREMENT_COUNTER', worth, counter)], once=False))
        t.expect.append((LABEL[pen], RUN - 2, '==', EXPECT[pen]))
    t.scripts.insert(0, Script('Test - go', [], order))
    t.bench = [('bench_watch', dict(seconds=RUN, every=3, sheet=False, lines=4))]
    return t


def bits(m):
    return _row(m, ROWS['bits'])


def enemy(m):
    return _row(m, ROWS['enemy'])


def water(m):
    return _row(m, ROWS['water'])


# the builds this module makes and their checks (cnv/registry.py)
MISSION = {'engine_bits': mission}
CHECKS = {'engine_bits': {'bits': bits, 'enemy': enemy, 'water': water}}
