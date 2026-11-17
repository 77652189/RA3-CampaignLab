"""L0 world handle (ADR 0029, docs/engine/sim-layers.md): what a subsystem moved out of sim.py may use of the world.

A subsystem gets the world as an argument (`world`) and touches only the names in WORLD_API on it -- object
registry, frame time, the template data handle, relations, the audit set and gap log. Rules of other subsystems are
reached through their own functions, never through the world. tests/test_sim_layers.py holds every layered module to
this list. (Today the world is the Sim itself; the list is the contract that lets L0 move out of it later without
touching the subsystems.) The minimal world for rule tests is simsmall.small_world.
"""

CIV = 'PlyrCivilian'   # the neutral side: owns the map's scenery and civilians; pays and is paid nothing

WORLD_API = frozenset({
    'bodies',          # name -> Body, every body made (dead too), in the order made
    'living',          # () -> the bodies alive now, in bodies' order
    'own',             # the template data handle (simunits)
    'fps',             # engine frames a second
    'frame_now',       # the engine frame now
    'relations',       # (player, player) -> 'Friend' / 'Enemy' / 'Neutral'
    'used',            # the audit set: rules the run leaned on (append only)
    'gap',             # an unmodelled rule met (Sim.gap)
})
