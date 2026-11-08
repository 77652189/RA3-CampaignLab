"""Render line probe (missions/render_bench.py; docs/research/rendering.md "第 0 步结果"): a battle that keeps going for
the whole watch, under whatever renderer setup the game copy has (work/render/tools/switch.py).

Every 2 s each side gets one of each of its kinds at its rear while it has fewer than TOP of its main tank, and every
3 s both armies are told to attack-move to the other side's rear. Counters: 帧数 (+1 every script frame: logic frames
since the start; against the watch's real seconds it is the logic rate), 守护者 / 铁锤 (each side's main tank left).
"""
from missions.render_bench import ALLIED, SOVIET
from parts import Script, Test, counted

TOP, BIG, RUN = 24, 60, 120.0


def war(m, top=TOP):
    t = Test()
    p1, s1 = m.player('p1'), m.player('s1')
    west, east = m.mark('west rear'), m.mark('east rear')
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', p1), ('SET_MILLISECOND_TIMER', 'Test Order', 1.0),
                                                 ('SET_MILLISECOND_TIMER', 'Test Give', 2.0)]))
    t.counters.append(('CNV_Rw_Frames', '帧数'))
    t.scripts.append(Script('Test - frames', [], [('INCREMENT_COUNTER', 1, 'CNV_Rw_Frames')], once=False))
    counted('CNV_Rw_Allied', '守护者', t, template=ALLIED[0], player=p1)
    counted('CNV_Rw_Soviet', '铁锤', t, template=SOVIET[0], player=s1)
    t.scripts += [
        Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
               [('ATTACK_MOVE_TEAM_TO', m.team('p1'), east), ('ATTACK_MOVE_TEAM_TO', m.team('s1'), west),
                ('SET_MILLISECOND_TIMER', 'Test Order', 3.0)], once=False),
        Script('Test - give west', [('TIMER_EXPIRED', 'Test Give'), ('COUNTER', 'CNV_Rw_Allied', 0, top)],
               [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', k, m.team('p1'), west) for k in ALLIED], once=False),
        Script('Test - give east', [('TIMER_EXPIRED', 'Test Give'), ('COUNTER', 'CNV_Rw_Soviet', 0, top)],
               [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', k, m.team('s1'), east) for k in SOVIET], once=False),
        Script('Test - give again', [('TIMER_EXPIRED', 'Test Give')], [('SET_MILLISECOND_TIMER', 'Test Give', 2.0)],
               once=False)]
    t.bench = [('bench_watch', dict(seconds=RUN, every=2, sheet=False, lines=len(t.counters)))]
    return t


CHECKS = {'render_war': {'war': war, 'big': lambda m: war(m, BIG)}}     # big: BIG of each main tank
