"""Walk a game's campaign front end and keep what each screen looks like (the campaign shell probe, ADR 0014).

  python -I -X utf8 experimental/testbench/shell_shots.py CampShell <out dir> [--plain] [--slot 4]

nav.json's way into the first mission (main menu -> campaign -> faction card -> Continue -> intro video skipped -> mode ->
world map -> mission briefing -> in game), with one change: the faction screen is recognised by its title bar
(work/testbench/nav/step2_shell.png, cut from a frame of the screen), not by the card, because the mod repaints the card.
Every frame the walk looks at is kept as <out>/walk_<second>.png (the screens in between are in them). After the game is
up, a frame every 5 s for --hud-wait seconds (the HUD with the co-op panel's place at the top left comes back when the
opening scene ends). --plain: the game with no mod, retail as it is started directly.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness  # noqa: E402
import nav  # noqa: E402
from PIL import Image  # noqa: E402


class Walker(harness.Session):
    out = ''
    t_start = 0.0

    def _capture(self, name, bmp=False, timeout=3.0):
        got = super()._capture(name, bmp=bmp, timeout=timeout)
        if got is not None and bmp and self.out:
            try:
                Image.open(got).convert('RGB').save(os.path.join(self.out, f'walk_{time.monotonic() - self.t_start:05.1f}.png'))
            except OSError:
                pass
        return got

    def shot(self, name):
        path = self._capture('walk_' + name, bmp=True)
        if path is None:
            print('no frame for', name)
            return
        Image.open(path).convert('RGB').save(os.path.join(self.out, name + '.png'))
        print('shot', name)


def settle(b, h, wait=75):
    """On the main menu, let the game's backend "connection lost" box come and be answered (it comes once, about 40 s
    after the start, and throws the game back to the main menu wherever it is): the screens after it are undisturbed."""
    end = time.monotonic() + wait
    while time.monotonic() < end:
        time.sleep(1)
        frame = b._capture('nav', bmp=True)
        pop = nav.popup(frame) if frame else None
        if pop:
            harness.click(h, *pop[1])
            time.sleep(4)
            return


chapter_step = harness.chapter_step     # the chapter list's row `slot`, then Proceed (the bench walks it too)


def tour(mod, out, plain=False, visible=False, parts='cards,overview,chapters', slot=None, linger=6, look=8):
    """The campaign screens, lingered on (the walk passes them in seconds), one game per part: `cards` the faction menu
    and the Allies card clicked, `overview` the world map with the talking head (`look` frames 0.6 s apart) and then the
    mission briefing (a frame a second for `linger` s), `chapters` the chapter list (main menu -> campaign -> chapters).
    `slot`: the overview of that chapter (picked from the chapter list) instead of the first one."""
    with open(os.path.join(nav.OUT, 'nav.json'), encoding='utf-8') as f:
        steps = json.load(f)
    steps[2] = dict(steps[2], box=[190, 28, 360, 68], template='step2_shell.png', threshold=18)
    if slot:
        steps = harness.shell_steps(slot)
    use = None if plain else mod
    for part in parts.split(','):
        b = Walker()
        b.out, b.t_start = out, time.monotonic()
        try:
            if part == 'cards':
                b.start(use, visible=visible, timeout=240, hold=False, steps=steps[:2] + [dict(steps[2], actions=[])])
                h = harness.main_window(b.p.pid)
                time.sleep(2)
                b.shot('cards_00')
                harness.click(h, 637, 315)
                for k in range(1, 4):
                    time.sleep(1)
                    b.shot(f'cards_{k:02d}')
            elif part == 'overview':
                b.start(use, visible=visible, timeout=240, hold=False, steps=[dict(steps[0], actions=[])])
                h = harness.main_window(b.p.pid)
                settle(b, h)
                b._walk_menus(visible, 240, steps[:6] + [dict(steps[6], actions=[])])
                for k in range(look):
                    b.shot(f'overview_{k:02d}')
                    time.sleep(0.6)
                harness.click(h, 1040, 676)                       # Continue: on to the mission briefing
                for k in range(linger):
                    time.sleep(1)
                    b.shot(f'briefing_{k:02d}')
                harness.click(h, 870, 100)                        # the "commander overview" tab: our mission notes
                for k in range(3):
                    time.sleep(1)
                    b.shot(f'commander_{k:02d}')
            elif part == 'chapters':
                b.start(use, visible=visible, timeout=240, hold=False,
                        steps=[steps[0], dict(steps[1], actions=[['click', 375, 426]])])
                for k in range(4):
                    time.sleep(2)
                    b.shot(f'chapters_{k:02d}')
        finally:
            b.stop()
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mod')
    ap.add_argument('out')
    ap.add_argument('--plain', action='store_true', help='the game with no mod')
    ap.add_argument('--hud-wait', type=int, default=90)
    ap.add_argument('--every', type=float, default=5.0, help='seconds between the frames kept once the game is up')
    ap.add_argument('--walk-timeout', type=int, default=240, help='seconds for the walk into the game')
    ap.add_argument('--visible', action='store_true')
    ap.add_argument('--slot', type=int, help='start the chapter of this slot (1-9) from the chapter list instead of the first one')
    ap.add_argument('--tour', nargs='?', const='cards,overview,chapters', metavar='PARTS',
                    help='linger on screens instead of walking into the mission: cards, overview (+ briefing), chapters')
    ap.add_argument('--linger', type=int, default=6, help='--tour overview: seconds on the mission briefing (a frame a second)')
    ap.add_argument('--look', type=int, default=8, help='--tour overview: frames of the world map (0.6 s apart)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.tour:
        tour(a.mod, a.out, a.plain, a.visible, a.tour, a.slot, a.linger, a.look)
        return
    with open(os.path.join(nav.OUT, 'nav.json'), encoding='utf-8') as f:
        steps = json.load(f)
    steps[2] = dict(steps[2], box=[190, 28, 360, 68], template='step2_shell.png', threshold=18)
    if a.slot:
        steps = [steps[0], dict(steps[1], actions=[['click', 375, 426]]), chapter_step(a.slot)] + steps[3:]
    b = Walker()
    b.out, b.t_start = a.out, time.monotonic()
    try:
        b.start(None if a.plain else a.mod, visible=a.visible, timeout=a.walk_timeout, hold=False, steps=steps)
        print('in game:', *b.log[-4:], sep='\n  ')
        t_end = time.monotonic() + a.hud_wait
        k = 0
        while time.monotonic() < t_end:
            time.sleep(a.every)
            b.shot(f'game_{k:02d}')
            k += 1
    finally:
        b.stop()


if __name__ == '__main__':
    main()
