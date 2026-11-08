"""The playtest's dev keys in the game (ADR 0025; capture_shim.cpp "the playtest's keys"), checked on the playtest copy:
the bench walks CampShell's chapter list into a slot and stops at the mission's start (the opening scene running),
then asks the shim through dev.req, as the keys would:

  1. skip   the scene runs at x8 until the bars go, then x1 again (the log: bars up, bars down, back to x1)
  2. faster x3 -> x8, normal -> x1
  3. skip   with no scene up: it ends by itself after 1.5 s, back to the speed from before

  python -X utf8 experimental/testbench/devkeys_check.py [slot]        (slot 4 = A4; the game must be closed)

Prints the shim's dev lines with their times and PASS / FAIL per step; the full log stays in <copy>\\playshots.
"""
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COPY = os.environ.get('RA3_PLAY_DIR') or os.path.join(ROOT, 'work', 'testbench', 'RA3play')
os.environ['RA3_BENCH_DIR'] = COPY              # before harness reads it (slots.BENCH): the playtest copy, not the bench's
os.environ['RA3_BENCH_SPEED'] = '2'             # so the harness starts the game with the clocks hooked (never sped up here)
os.environ['CNV_DEV_KEYS'] = '1'

import harness                                  # noqa: E402  (run from this folder: python puts it on the path)


def log_path():
    return os.path.join(harness.SHOTS, 'cnv_testbench.log')        # the slot's shot folder, known once started


def dev_lines():
    with open(log_path(), encoding='utf-8', errors='replace') as f:
        return [line.rstrip() for line in f if ' dev' in line or 'speed x' in line]


def bars(img):
    """The shim's own test (bars_up): two rows in each bar, the top bar across 10..90 %, the bottom one at its ends."""
    if img is None:
        return False
    img = img.convert('RGB')
    w, h = img.size
    xs_top = [w * (10 + c * 80 // 23) // 100 for c in range(24)]
    xs_bottom = [w * (2 + c * 16 // 11 if c < 12 else 82 + (c - 12) * 16 // 11) // 100 for c in range(24)]
    for pct, xs in ((3, xs_top), (9, xs_top), (91, xs_bottom), (97, xs_bottom)):
        if any(max(img.getpixel((x, h * pct // 100))) > 24 for x in xs):
            return False
    return True


def ask(cmd):
    with open(os.path.join(harness.SHOTS, 'dev.req'), 'w', encoding='ascii') as f:
        f.write(cmd)
    time.sleep(0.4)


def wait_for(pattern, seconds, since):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        hit = [line for line in dev_lines()[since:] if re.search(pattern, line)]
        if hit:
            return hit[0]
        time.sleep(0.2)
    return None


def main(slot=4):
    if harness.game_running():
        sys.exit('devkeys_check: RA3 is running: close it first')
    s = harness.Session()
    steps = harness.shell_steps(slot)[:-1]           # stop at the briefing's click: the scene is still to come
    s.start('CampShell', steps=steps, timeout=200)
    verdicts = []
    try:
        if not wait_for(r'dev keys on', 5, 0):
            sys.exit('devkeys_check: the shim has no dev keys (CNV_DEV_KEYS not seen): ' + log_path())
        end = time.monotonic() + 120                  # the loading screen, then the opening scene with its bars
        while not bars(s._capture('bars')):
            if time.monotonic() > end:
                sys.exit('devkeys_check: no letterbox seen in 120 s after the briefing')
            time.sleep(0.5)
        n = len(dev_lines())
        t0 = time.monotonic()
        ask('skip')
        up = wait_for(r'bars are up', 5, n)
        down = wait_for(r'skip over', 120, n)
        real = time.monotonic() - t0
        verdicts.append((bool(up and down and 'bars are down' in down and 'x1' in down),
                         f'skip in the opening scene: {up or "bars never seen"} / {down or "no end"} ({real:.1f} s real)'))
        n = len(dev_lines())
        for _ in range(3):
            ask('faster')
        top = wait_for(r'faster -> x8', 3, n)
        ask('normal')
        back = wait_for(r'normal -> x1', 3, n)
        verdicts.append((bool(top and back), f'faster x3, normal: {top} / {back}'))
        n = len(dev_lines())
        ask('skip')
        alone = wait_for(r'skip over', 5, n)
        verdicts.append((bool(alone and 'no scene' in alone), f'skip with no scene: {alone}'))
        s.frame('after the dev keys check')
    finally:
        s.stop()
    for ok, text in verdicts:
        print(('PASS ' if ok else 'FAIL ') + text)
    print('RESULT ' + ('PASS' if all(ok for ok, _ in verdicts) else 'FAIL') + f' (log {log_path()}; frames {s.run_dir})')


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 4)
