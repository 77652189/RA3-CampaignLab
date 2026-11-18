"""The simulator's kernel and the parts built on it (docs/engine/sim-modules.md, ADR 0031-0034): engine.kernel holds
the four things (thing, module, module data, world), the factory, the interfaces and the schedule. The rest of the
simulator still lives in sim*.py beside it and moves in one module family a step."""
