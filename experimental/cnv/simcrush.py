"""C-line Crush eligibility for the AI host; preference/timing stay in tactics.

Levels follow engine_crush (strictly greater). Enemy-only is INFERRED for
allies/neutrals, matching Sim.crush_along. This is not a full Crush replay.
"""


def eligible(world, member, target):
    """Use the live bodies behind Fighters, within the existing ground collision model."""
    b, t = member.body, target.body
    return (b is not t and b.alive and t.alive
            and b.surface == 'ground' and t.surface == 'ground'
            and not t.scenery and not t.topple and t.name not in world.attachments
            and b.crusher is not None and t.crushable is not None
            and b.crusher > t.crushable and world.enemy(b.owner, t.owner))
