r"""Run the skirmish AI on a mission: build a cnv build, make its Sim and let simai.SimAI play every player the
mission hands to the AI (R3 13f-2d: the entry point simai.py had). simai is a layered module (L8, tests/test_sim_layers.py)
that never names the Sim; this file makes one, as simproxy does for the proxy player.

  python -I -X utf8 experimental/cnv/simai_run.py [build] [--until <seconds>] [--check <check>]

A test that plays whole AI games loads this file and takes the AI from it (`simai = simai_run.simai`): one copy of
simai in the process, so a monkeypatch on simai (SimAI.efficiency, Brain.fire_unit) reaches the run."""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [p for p in (HERE, os.path.join(os.path.dirname(HERE), 'campaign')) if p not in sys.path]

import sim  # noqa: E402
import simai  # noqa: E402


def run(build, check='', until=200.0, level='normal', seed=1, lib=None, data=None, blocks=simai.BLOCKS, record=False,
        script=''):
    """Build `build` (a cnv build name), run it with the AI `until` seconds: the SimAI. record: HOOKS 9. script: the
    player's (sim.Sim's script)."""
    import build as bld
    m, t, _ = bld.resolve(build, check)
    w = simai.SimAI(sim.Sim(m, t, level, script), level, seed, lib, data, blocks, record)
    w.advance(int(until * simai.FPS))
    return w


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('build', nargs='?', default='aiopen')
    ap.add_argument('--check', default='')
    ap.add_argument('--until', type=float, default=200.0)
    a = ap.parse_args()
    try:
        w = run(a.build, a.check, a.until)
    except simai.NoModel as e:
        print(e)
        return 1
    for p, b in w.brains.items():
        print(f'{w.sim.who(p)}（第 {b.started} 帧开局；下面是开局后的帧）')
        for f, what, t in b.trace:
            print(f'  {f - b.started:5d} 帧 {(f - b.started) / simai.FPS:6.1f} s  {what:4s} {t}')
        for e in [e for e in b.ai.teams.log if e[1] in ('go', 'disband', 'ended')][-10:]:
            print('  team', e[0] - b.started, e[1:])
    return 0


if __name__ == '__main__':
    sys.exit(main())
