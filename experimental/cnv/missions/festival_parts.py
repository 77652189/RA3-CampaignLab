"""What A4 and J4 (镜像关①, maps/festival.py) both lay out: the plazas' gates and the convoy that runs the road.
Each mission keeps its own tag in the names (CNV A4 ..., CNV J4 ...) and decides whose the convoy is.

plazas(m, tag, at): every plaza's seal mark (seal k: where the ice that shuts the gate stands); returns the plaza
  numbers. The plazas are raised ground with cliffs round them and one ramp, the map's terrain.
Convoy(m, tag, side, leave, tick): three trucks (cast truck 1-3, units/convoy.py: unarmed, 500 health) at
  the convoy start, the exit mark and area; scripts: go (sets off at `leave`), roll (sends it on to the exit every
  `tick`; put after anything else that waits on the tick timer, which it sets again), tail (a truck at the exit is
  safe: counted in `arrived` and taken off the map; one destroyed before that is counted in `losses`).
"""
from parts import Script, square
from units import convoy

SEAL_IN = 0.0                                   # ice across a gate stands on the gate line, across the ramp's head


def north(m, k):
    """+1 when plaza k lies north of its gate, -1 when south."""
    return 1 if m.site(f'plaza {k}')[1] > m.site(f'gate {k}')[1] else -1


def plazas(m, tag, at='gate'):
    """at: the site each seal mark stands on -- 'gate' (across the gap: ice placed by the map) or 'inside' (the
    flat ground behind it: ice an engineer builds)."""
    ks = sorted(int(k.split()[1]) for k in m.map.SITES if k.startswith('gate '))
    for k in ks:
        s = north(m, k)
        m.waypoint(f'seal {k}', f'CNV {tag} Seal {k}', f'{at} {k}', 0, -s * SEAL_IN)
    return ks


class Convoy:
    def __init__(self, m, tag, side, leave, tick):
        self.m, self.tag, self.code = m, tag, f'CNV{tag}'
        self.trucks = [f'UNIT - CNV {tag} Truck {j}' for j in (1, 2, 3)]
        self.exit, self.exit_area = f'CNV {tag} Exit', f'CNV {tag} Exit Area'
        self.timer, self.go_timer, self.rolling = f'CNV {tag} Tick', f'CNV {tag} Go', f'CNV_{tag}_Rolling'
        self.arrived, self.losses = f'CNV_{tag}_Arrived', f'CNV_{tag}_Lost'  # ASCII: names go through Latin-1
        self.leave, self.tick = leave, tick
        m.waypoint('exit', self.exit, 'road exit')
        m.areas[self.exit_area] = square(*m.site('road exit'), m.where('road exit').r)
        truck = convoy.truck()
        m.units.append(truck)
        for j, t in enumerate(self.trucks):
            m.put(truck.id, 'convoy start', 60 - 60 * j, 0, side=side, name=t, role=f'truck {j + 1}', angle=0.0)

    def start(self):
        """The action that sets the convoy's departure (for the mission's intro script)."""
        return ('SET_MILLISECOND_TIMER', self.go_timer, self.leave)

    def go(self):
        return [Script(f'CNV {self.tag} - Go', [('TIMER_EXPIRED', self.go_timer)],
                       [('SHOW_MILITARY_CAPTION', f'SCRIPT:{self.code}_GO', 5.0), ('SET_FLAG', self.rolling, 1),
                        ('SET_MILLISECOND_TIMER', self.timer, 0.0)])]

    def roll(self):
        return [Script(f'CNV {self.tag} - Roll', [('FLAG', self.rolling, 1), ('TIMER_EXPIRED', self.timer)],
                       [('MOVE_NAMED_UNIT_TO', t, self.exit) for t in self.trucks] +
                       [('SET_MILLISECOND_TIMER', self.timer, self.tick)], once=False)]

    def tail(self):
        out = []
        for j, t in enumerate(self.trucks, 1):
            out += [Script(f'CNV {self.tag} - Safe {j}', [('NAMED_INSIDE_AREA', t, self.exit_area)],
                           [('SET_FLAG', f'CNV_{self.tag}_Safe_{j}', 1), ('INCREMENT_COUNTER', 1, self.arrived),
                            ('SHOW_MILITARY_CAPTION', f'SCRIPT:{self.code}_SAFE', 4.0), ('NAMED_DELETE', t)]),
                    Script(f'CNV {self.tag} - Hit {j}', [('NAMED_DESTROYED', t), ('FLAG', f'CNV_{self.tag}_Safe_{j}', 0)],
                           [('INCREMENT_COUNTER', 1, self.losses)])]
        return out

    def chase(self, j):
        """Conditions true while truck j is the leading one still on the road (those before it gone)."""
        return [('NAMED_NOT_DESTROYED', self.trucks[j])] + [('NAMED_DESTROYED', a) for a in self.trucks[:j]]
