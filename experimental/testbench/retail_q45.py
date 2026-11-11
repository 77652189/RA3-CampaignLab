r"""Retail acceptance questions 4 and 5 (ADR 0026 item 2): the Empire's first mission (j01) and the Soviets' first (s01),
played by NOBODY. The plain game's campaign is linear, so the way in is the first mission of each faction: the faction select
screen's card (harness.faction_steps: s Soviet left, j Empire right), then nav.json's briefing video / world map / briefing.

  python -X utf8 experimental/testbench/retail_q45.py <j|s> [--until 90] [--step 5]   -> work/testbench/retail_q/<j|s>01_idle.json

Every STEP mission seconds the run is paused and a frame is archived (the mission menu is what the pause shows: objectives,
done marks); the frame ids and mission seconds go in the json, the pictures are read with bench_inspect or by eye.
"""
import argparse
import json
import os

import calib  # this folder: first on the path when run as a script (guard G4: no sys.path edits)
import harness
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

OUT = os.path.join(labpaths.WORK, 'testbench', 'retail_q')
MAPS = {'j': 'camp_j01_russianvillage_white', 's': 'camp_s01_leningradcanals_rao'}


def run(letter, until=90.0, step=5.0):
    s = harness.Session()
    rows = []
    try:
        s.start(None, hold=True, retail_map=MAPS[letter])
        s.frame('start')
        while s.second() < until:
            s.run_for(step)
            try:
                s.pause()
                held = True
            except harness.BenchError:      # the opening cutscene (letterbox, portrait in the radar): Esc opens no menu
                held = False
            sec = s.second()
            fid, _ = s.frame('idle' if held else 'idle (running: cutscene)')
            rows.append(dict(frame=fid, second=sec, held=held))
            s.resume()
        res = dict(faction=letter, map=MAPS[letter], until=until, samples=rows, run_dir=s.run_dir, log=s.log[-12:])
    finally:
        s.stop()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f'{letter}01_idle.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('faction', choices=sorted(MAPS))
    ap.add_argument('--until', type=float, default=90.0)
    ap.add_argument('--step', type=float, default=5.0)
    a = ap.parse_args()
    r = run(a.faction, a.until, a.step)
    print(r['run_dir'])
    for row in r['samples']:
        print(row)
