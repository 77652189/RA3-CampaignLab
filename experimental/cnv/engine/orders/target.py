"""AIUpdate's target rules (command family C1, ADR 0029): whom a shooter takes, no state of their own. The host lends
its queries as `q` (hostile, in_range, can_hit, side_sees, shot_blocked, reach_of; unshot, ai) and keeps what follows a
pick: the fire queues, engaged, the WeaponSet's PER_TARGET lock (Sim.aim, first_shot); chases ask takes_by_itself."""
import numpy as np


def takes_by_itself(a, t, q):
    """Whether `a` may take `t` with no order naming it (idle, on a plain move, attack-moving, going after: Generals
    AIUpdateInterface::getNextMoodTarget -> AI::findClosestEnemy): never an unshot template (`q.unshot`: the a4 ice
    nobody shoots, 2026-10-28), a NOT_AUTOACQUIRABLE one (INFERRED by its name; a script's NON_AUTOACQUIRABLE status
    each caller asks where it did: side_sees, asked before it in the chases, keeps its answer for the tick);
    a structure (PartitionFilterRejectBuildings) only when `a` is ATTACK_BUILDINGS, `t` a base defence (FS_BASE_DEFENSE;
    a garrisoned building that can fire is the other exception, not modelled) or `a`'s side is run by the skirmish AI
    (`q.ai`, woken: it keeps Generals' computer exception, INFERRED -- the bench's s1 had no AI; tests/test_simai).
    Bench 2026-11-08 engine_seal: the player's idle peacekeeper leaves the enemy's bunkers alone (erow), the enemy's
    (a computer player's) idle and attack-moving past leaves the player's bunker and plant alone (ebld / ebldam) --
    RA3 drops that exception. An order naming the target (`a.goal`) is not filtered here."""
    if t.template in q.unshot:
        return False
    if 'NOT_AUTOACQUIRABLE' in t.kinds and not ('AUTO_ACQUIRABLE_BY_AI' in t.kinds and a.ai_acquire):
        return False
    if 'STRUCTURE' in t.kinds and not a.ai_acquire:
        return ('ATTACK_BUILDINGS' in a.acquire or 'FS_BASE_DEFENSE' in t.kinds
                or a.owner in getattr(q, 'ai', ()))
    return True


def picks(a, targets, aimable, tx, ty, q):
    """`a`'s target for each of its weapons where it stands, out of `targets` (tx, ty: their centres; aimable: their
    serials). None: no foe at all (the aim gives up at once); else (the foes' centre distances, their indexes in
    targets, [a target or None for each weapon]). A weapon takes the order's target when it is in range, can hit it,
    `a`'s side sees it and the line is clear; else, when `a` takes targets by itself now -- an attack-mover always,
    idle or on a plain move only with AutoAcquireEnemiesWhenIdle YES (Generals' calledDuringIdle: the idle state and
    the turret's scan) -- the nearest foe in range it may take (takes_by_itself), can hit, sees, the line clear.
    Nearest by centre, ties (two foes made on one point) by list order: the default quicksort broke them by the
    array's length (a4 r121); the scan stops at the biggest foe's radius past the reach (R8)."""
    ks = [k for k, t in enumerate(targets) if t is not a and q.hostile(a, t)]
    if not ks:
        return None
    idx = np.array(ks)
    d = np.hypot(tx[idx] - a.x, ty[idx] - a.y)
    order, pad, g = np.argsort(d, kind='stable'), max(targets[k].radius for k in ks), a.goal
    out = []
    for w in a.weapons:
        if isinstance(g, type(a)) and g.alive and g.serial in aimable and q.in_range(a, g, w) and q.can_hit(w, g) \
                and q.side_sees(a.owner, g) and not q.shot_blocked(a, g, w):
            out.append(g)
            continue
        out.append(None)
        if a.mode != 'attack' and 'YES' not in a.acquire:
            continue
        for j in order:
            if d[j] - a.radius - pad > q.reach_of(w):       # sorted by centre: nobody nearer after this
                break
            t = targets[idx[j]]
            if q.in_range(a, t, w, d[j]) and takes_by_itself(a, t, q) and 'NON_AUTOACQUIRABLE' not in t.status and \
                    q.can_hit(w, t) and q.side_sees(a.owner, t) and not q.shot_blocked(a, t, w):
                out[-1] = t
                break
    return d, idx, out
