r"""Does a radar clip go on playing while the mission is paused? (engine line A round 111)

The mod CampMovieRetail (build.py movie --check retail) plays the game's A02TH06 (18.9 s by its VP6 header) in the radar
window and counts the frames till HAS_FINISHED_VIDEO holds. Here the run is paused (Esc, the mission menu) every STEP
mission seconds, as retail_q2.py did on a02 -- if the clip runs on through the pauses it reads finished in fewer
mission frames than the 291 an unpaused x1 run counts (bench 2026-11-09).

  python -X utf8 experimental/testbench/movie_pause_probe.py [--step 1.4] [--hold 0]   (hold: extra real seconds per pause)
"""
import argparse
import time

import calib  # noqa: F401  this folder first on the path when run as a script
import counters
import harness


def run(step, hold, until=45.0):
    s = harness.Session()
    rows = []
    try:
        s.start('CampMovieRetail', hold=True)
        s.resume()
        while s.second() < until:
            s.run_for(step)
            s.pause()
            time.sleep(hold)
            s.resume()
            fid, img = s.frame('counters')
            c = counters.read(img, 4)
            rows.append((s.second(), c))
            print(s.second(), c, flush=True)
            if c[3] == 1:
                break
    finally:
        s.stop()
    return rows


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', type=float, default=1.4)
    ap.add_argument('--hold', type=float, default=0.0)
    a = ap.parse_args()
    run(a.step, a.hold)
