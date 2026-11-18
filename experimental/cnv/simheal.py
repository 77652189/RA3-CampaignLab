"""L2 self-healing (ADR 0029, docs/engine/sim-layers.md): PassiveAreaEffectBehavior. (AutoHealBehavior is the kernel
module engine/modules/autoheal.py since step K1.)

`Heal` keeps the template rules read so far and runs one frame of them over the world it is given; it reaches the
world only through simworld.WORLD_API. The frame loop calls it (simloop's passive_area_heal cell).
"""
import math

import simunits

ALIGN = {'passive area heal': 'PassiveAreaEffectBehavior (simheal.py): the SDK rate in 20-frame batches on a shared '
                              'mission-frame phase (frame % 20 == 11, INFERRED), own / allied infantry, the source '
                              'itself left out, two identical sources count once (bench E70 / E145 / E163 / E165 / '
                              'E166); other overlaps and relations are gaps'}     # sim.ALIGN takes it


class Heal:
    def __init__(self):
        self.passive_area_of = {}      # template -> simunits.passive_area rule (False: an untested configuration)

    def passive_area_heal(self, world):
        """E70/E163 single engineer, own/allied infantry, scripted status on/off.

        E72/E73 crossing gaps are 20/20/20 script frames. Apply the SDK's
        10%/second in 20-frame batches. INFERRED: a shared mission-frame phase
        (frame % 20 == 11 after scripts) replays both activation times; this
        does not establish the clock source or dynamic creation/reset timing.
        Batch magnitude is inferred from the SDK rate, not an exact HP probe.
        See work/re/e_passive_e74.md.
        E145 measures one versus unlimited wounded beneficiaries. Candidate
        order below is INFERRED: the plate counts recipients, not identities.
        E163 adds explicit bilateral cross-player Friend eligibility. Enemy
        exclusion is retained; the changed-relation snapshot was not reached.
        E165: the source stays exactly half-health while a nearby inactive
        engineer and infantry heal fully; exclude the source itself, not the
        engineer template. See work/re/e165_areaself.md.
        E166 tests two identical unlimited full-health sources against a single
        source. Use one contribution for that shape; source identity is INFERRED
        (identical rates, no cap). See work/re/e166_areaoverlap.md.
        Implicit alliances, neutral/asymmetric relations, other overlap shapes
        and self/beneficiary-cap interaction remain gaps.
        """
        cache = self.passive_area_of
        sources = []
        for b in world.bodies.values():
            if not b.alive:
                continue
            if b.template not in cache:
                cache[b.template] = simunits.passive_area(b.template, world.own)
            rule = cache[b.template]
            if rule is False:
                world.gap('物体模块', 'PassiveAreaEffectBehavior configuration', '未测的范围效果配置')
            elif rule and 'GENERIC_TOGGLE_STATE' in b.status:
                sources.append((b, rule))
        if not sources:
            return
        world.gap('物体模块', 'PassiveAreaEffectBehavior timing',
                 'INFERRED: E72/E73支持20帧分批；共用任务帧相位及SDK换算跳幅仅限已有回放，'
                 '时钟来源、动态创建/重开状态/调查周期仍未测，见work/re/e_passive_e74.md')
        period, phase = 20, 11
        if (world.frame_now() - phase) % period:
            return
        healed_by = {}
        if any(rule[2] for _, rule in sources):
            world.gap('物体模块', 'PassiveAreaEffectBehavior beneficiary order',
                     'INFERRED: E145只量受益人数；按物体遍历次序选满一人，具体身份顺序未测，见work/re/e145_modulebatch.md')
        for target in world.bodies.values():
            if not target.alive or target.hp >= target.max_hp or 'INFANTRY' not in target.kinds:
                continue
            if target.template == 'SovietScoutVehicle':
                continue
            eligible = [(source, rule) for source, rule in sources
                        if math.hypot(target.x - source.x, target.y - source.y) <= rule[0]]
            if any(source.owner != target.owner and
                   (world.relations.get((source.owner, target.owner)),
                    world.relations.get((target.owner, source.owner))) not in
                   (('Friend', 'Friend'), ('Enemy', 'Enemy')) for source, _ in eligible):
                world.gap('物体模块', 'PassiveAreaEffectBehavior relationship',
                         'E163仅测显式双向友军/敌对；隐式联盟、中立和单向关系仍未测')
            eligible = [(source, rule) for source, rule in eligible
                        if source.owner == target.owner or
                        (world.relations.get((source.owner, target.owner)),
                         world.relations.get((target.owner, source.owner))) == ('Friend', 'Friend')]
            if len(eligible) > 1:
                if (len(eligible) == 2 and eligible[0][1] == eligible[1][1]
                        and not eligible[0][1][2]
                        and all(source is not target and source.hp >= source.max_hp
                                for source, _ in eligible)):
                    # E166: same-rule full-health pair, unlimited beneficiaries.
                    # One rate only; which identical source owns it is INFERRED.
                    eligible = eligible[:1]
                else:
                    world.gap('物体模块', 'PassiveAreaEffectBehavior overlap',
                             '仅测双满血同规则无限人数源；其他重叠/受伤源/人数上限交互未测')
                    continue
            # E165 excludes the source itself; E166 does not test wounded sources.
            if eligible and eligible[0][0] is target:
                continue
            if eligible:
                source, rule = eligible[0]
                used = healed_by.get(source.name, 0)
                if rule[2] and used >= rule[2]:
                    continue
                target.mend(target.max_hp * rule[1] * period / world.fps)
                healed_by[source.name] = used + 1
                world.used.add('passive area heal')
