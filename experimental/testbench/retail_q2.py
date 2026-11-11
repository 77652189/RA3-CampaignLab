r"""Retail acceptance questions 2 and 3 (ADR 0026 item 2): Allied mission 2 (Cannes) and 3 (Heidelberg), played by NOBODY.
The plain game's campaign is linear (the world map only goes on to mission 2 after mission 1 is won), so the bench goes in
by the campaign shell built with ONE level only (CNV_SHELL_NAME=CampShRetail build.py a4 --shell: its other eight slots are
retail's own maps and scripts; CampShell itself carries our nine drafts, its slot 2 is not Cannes).

  python -X utf8 experimental/testbench/retail_q2.py <slot 2|3> [--until 90]   -> work/testbench/retail_q/a0<slot>_idle.json

Every STEP mission seconds the run is paused and a frame is archived (the mission menu is what the pause shows: objectives,
done marks); the frame ids and mission seconds go in the json, the pictures are read with bench_inspect or by eye.
"""
import argparse
import json
import os
import time

import calib  # this folder: first on the path when run as a script (guard G4: no sys.path edits)
import harness
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

OUT = os.path.join(labpaths.WORK, 'testbench', 'retail_q')


def run(slot, until=90.0, step=5.0, mod='CampShRetail'):
    s = harness.Session()
    rows = []
    try:
        s.start(mod, hold=True, steps=harness.shell_steps(slot))
        s.frame('start')
        while s.second() < until:
            s.run_for(step)
            s.pause()
            fid, _ = s.frame('idle')
            rows.append(dict(frame=fid, second=s.second()))
            s.resume()
        res = dict(slot=slot, mod=mod, until=until, samples=rows, run_dir=s.run_dir)
    finally:
        s.stop()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'a0{slot}_idle.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('slot', type=int)
    ap.add_argument('--until', type=float, default=90.0)
    ap.add_argument('--step', type=float, default=5.0)
    a = ap.parse_args()
    r = run(a.slot, a.until, a.step)
    print(r['run_dir'])
    for row in r['samples']:
        print(row)
