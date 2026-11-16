"""BuildEntry.Upgrade presence pair (C line): aicupgon:a / aicupgoff:a.

Prediction from retail AlliedTechBuildState and Upgrade_AlliedTech2: with a refinery,
money and a yard, the constant state's UPGRADE_TECH entry can buy the object upgrade
(1500, 15s). On should acquire Tech2 within 90s after wake; off omits that dedicated
state and should hold none.
Retail tech entries have MinTime >=180s, outside the observation. Timing, seller choice,
budget account, Tech3 and Japanese upgrades remain gaps. Evidence: work/re/c_upgrade_report.md.

RESULTS 2026-11-12: aicupgon archived rows s39..s120 show 2 Tech2 holders;
yard=1 throughout, refinery=1 then 2/3 as the opening continues. Saved frames rejudged
after correcting an unsupported expectation operator; no second engine run needed.
aicupgoff: Tech2 holders=0 throughout s1..105; yard=1, refinery>=1. All three
expectations PASS. This pair establishes upgrade-state effect, not the holder identities.
"""
from parts import Script, Test, counted


def a(m):
    t = Test()
    player = m.player('s1')
    t.scripts.append(Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]))
    counter = 'CNVCUpHolders'
    t.counters.append((counter, '二级持有'))
    t.scripts.append(Script('Test - holders zero', [], [('SET_COUNTER', counter, 0)], once=False))
    for n in range(1, 11):
        t.scripts.append(Script(f'Test - holders {n}',
                               [('PLAYER_HAS_NUM_UNITS_WITH_UPGRADE', player, n, 'Upgrade_AlliedTech2')],
                               [('SET_COUNTER', counter, n)], once=False))
    counted('CNVCUpRef', '矿厂数', t, template='AlliedRefinery', player=player)
    counted('CNVCUpYard', '建造厂数', t, template='AlliedConstructionYard', player=player)
    t.counters.append(('CNVCUpMoney', '资金'))
    t.scripts.append(Script('Test - money', [], [('SET_PLAYER_MONEY_TO_COUNTER', player, 'CNVCUpMoney')], once=False))
    wake = m.facts['wake at']
    t.expect = [('矿厂数', wake + 30, '>=', 1, wake + 90),
                ('建造厂数', wake + 30, '>=', 1, wake + 90),
                ('二级持有', wake, 'ever>=', 1, wake + 90) if m.facts['upgrade entry'] else
                ('二级持有', 0, '==', 0, wake + 90)]
    t.bench = [('bench_watch', dict(seconds=wake + 92, every=1, sheet=False, lines=4))]
    return t


BAN_UNTIL = 40.0


def ban(m):
    """ALLOW_DISALLOW_ONE_UPGRADE (engine A, round 257): aicupgon:a with s1's Upgrade_AlliedTech2 banned at the start
    (allow 0) and allowed again (1) at 40 s. Simulator prediction (Sim.upgrade_sellers skips a banned upgrade; the
    unbanned run buys at s20.5 and holds 2 from s36, bench s39): holders 0 to the allow, then the yard sells it again
    -- bought s40.5, 15 s to research, 2 holders from s56. Ignored ban: holders by ~s39 as aicupgon:a (the first
    expectation runs to s50 to catch that); a ban outliving the allow, or the AI giving the entry up after a refusal:
    0 to the end. (Not 60 s: by then the model's AI has spent its PRODUCTION account to 0 on units and buys nothing,
    which would not tell the allow.)"""
    t = a(m)
    player = m.player('s1')
    t.counters = [c for c in t.counters if c[0] != 'CNVCUpMoney']
    t.scripts = [s for s in t.scripts if s.name != 'Test - money']
    t.scripts.append(Script('Test - ban Tech2', [], [('ALLOW_DISALLOW_ONE_UPGRADE', player, 'Upgrade_AlliedTech2', 0),
                                                     ('SET_MILLISECOND_TIMER', 'CNVCUpBan', BAN_UNTIL)]))
    t.scripts.append(Script('Test - allow Tech2', [('TIMER_EXPIRED', 'CNVCUpBan')],
                            [('ALLOW_DISALLOW_ONE_UPGRADE', player, 'Upgrade_AlliedTech2', 1)]))
    end = m.facts['wake at'] + 92
    t.expect = [('二级持有', 0, '==', 0, BAN_UNTIL + 10),
                ('二级持有', BAN_UNTIL + 12, 'ever>=', 1, end - 2)]
    t.bench = [('bench_watch', dict(seconds=end, every=1, sheet=False, lines=4))]
    return t


CHECKS = {build: {'a': a} for build in ('aicupgon', 'aicupgoff')}
CHECKS['aicupgon']['ban'] = ban
