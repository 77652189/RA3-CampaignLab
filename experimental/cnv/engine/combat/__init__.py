"""Weapon effects (ADR 0029, docs/engine/sim-modules.md "武器效果"; step N1): one handler a nugget kind, registered
with @registry.nugget(kind, phase). The host (simdamage.Damage.deal) makes a registry.Context for each volley and runs
its phases in turn; what runs, and in which order, is registry.ORDER -- never the order these files are imported in,
nor the order of a weapon's fields.

Importing this package registers every handler (named here, so the simulator's file tools see them)."""
from engine.combat import (contained, damage, dot, leech, line_damage, paralyze, projectile,  # noqa: F401
                           registry, secondary, strip, suppression)  # (registers them)
