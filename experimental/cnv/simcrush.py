"""C-line Crush eligibility for the AI host; preference/timing stay in tactics.

Levels follow engine_crush (strictly greater). Enemy-only is INFERRED for
allies/neutrals, matching Sim.crush_along. This is not a full Crush replay.
L2 locomotion (ADR 0029): reaches the world only through simworld.WORLD_API; the attached bodies (`attached`, the
simulator's attachments) are handed in by the caller.
"""


def eligible(world, member, target, attached):
    """Use the live bodies behind Fighters, within the existing ground collision model."""
    b, t = member.body, target.body
    return (b is not t and b.alive and t.alive
            and b.surface == 'ground' and t.surface == 'ground'
            and not t.scenery and not t.topple and t.name not in attached
            and b.crusher is not None and t.crushable is not None
            and b.crusher > t.crushable and world.enemy(b.owner, t.owner))
