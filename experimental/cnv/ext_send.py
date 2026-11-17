"""Send orders to a running bench game from outside it (engine line D round 60; checks/engine_cmd.py).

The game side is ra3ext's CNVCmd module: every frame it looks for ra3ext_cmd.txt next to the run's ra3ext.log, runs
its lines (`set NAME V`, `add NAME V`, `get NAME` on the map's script counters) and deletes the file. This program waits
for a run folder made after it started whose ra3ext.log says 'cmd: listening', waits --after seconds more, writes the
lines (under a temporary name, then renamed, so the game never reads half a file), waits for the file to go (the
game's acknowledgement) and prints the log's 'cmd:' lines.

  python -I -X utf8 experimental/cnv/ext_send.py --after 8 "set Cmd_Call 1" "get Cmd_Time"
"""
import argparse
import os
import sys
import time

import importlib.util

_spec = importlib.util.spec_from_file_location(
    'labpaths', os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'campaign', 'labpaths.py'))
labpaths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(labpaths)

RUNS = os.path.join(labpaths.WORK, 'testbench', 'runs')


def listening(since, prefix):
    """The newest run folder (made after `since`, name starting with `prefix`) whose ra3ext.log is listening."""
    best = None
    for n in os.listdir(RUNS) if os.path.isdir(RUNS) else []:
        d = os.path.join(RUNS, n)
        log = os.path.join(d, 'ra3ext.log')
        if n.startswith(prefix) and os.path.isfile(log) and os.path.getmtime(d) >= since - 5:
            with open(log, encoding='utf-8', errors='replace') as f:
                if 'cmd: listening' in f.read() and (best is None or os.path.getmtime(d) > os.path.getmtime(best)):
                    best = d
    return best


def cmd_lines(run):
    with open(os.path.join(run, 'ra3ext.log'), encoding='utf-8', errors='replace') as f:
        return [x.rstrip() for x in f if x.startswith('cmd:')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('lines', nargs='+')
    ap.add_argument('--after', type=float, default=5.0, help='seconds after the module starts listening')
    ap.add_argument('--prefix', default='CampCmd')
    ap.add_argument('--wait', type=float, default=300.0, help='give up after this many seconds')
    a = ap.parse_args()
    t0 = time.time()
    run = None
    while run is None:
        if time.time() - t0 > a.wait:
            sys.exit('no listening game')
        time.sleep(0.5)
        run = listening(t0, a.prefix)
    print('run', run, flush=True)
    time.sleep(a.after)
    cmd = os.path.join(run, 'ra3ext_cmd.txt')
    with open(cmd + '.tmp', 'w', encoding='ascii') as f:
        f.write('\n'.join(a.lines) + '\n')
    os.replace(cmd + '.tmp', cmd)
    sent = time.time()
    print(f'sent {a.lines} at {sent - t0:.1f} s', flush=True)
    while os.path.exists(cmd):
        if time.time() - sent > 60:
            sys.exit('the game did not take the file in 60 s')
        time.sleep(0.1)
    print(f'taken after {time.time() - sent:.2f} s', flush=True)
    time.sleep(0.5)
    print('\n'.join(cmd_lines(run)))


if __name__ == '__main__':
    main()
