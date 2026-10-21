r"""Screen-driven menu navigation for run_bench.ps1 -Nav: from the main menu into the CNV test mission as soon as each
screen appears, instead of clicks at fixed seconds (the fixed timeline reached the mission at ~66 s, idling 16 s on
a main menu that was ready at 20 s; load times also vary run to run).

Each step waits for its screen, recognised by a small patch compared with a template cut from a reference run
(mean absolute grey difference), or by the mean brightness of a region (videos: dark, then bright), and then does
its actions. The templates are cut locally from a reference timeline (work/, not in git: no game art in the repo).

  python -I experimental/testbench/nav.py build <reference shots dir>     -> work/testbench/nav/ (templates + nav.json)
  python -I experimental/testbench/nav.py check <frame.bmp> <step index>  -> "match <metric>" | "no <metric>"

Reference frames (1280 x 720, see STEPS): run_bench.ps1 with the old fixed clicks and -Shots every few seconds.
"""
import json
import os
import sys

from PIL import Image, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'testbench', 'nav')

# (name, how, reference frame, box (x0, y0, x1, y1), threshold, actions); how: 'tpl' = patch matches the template
# (diff below threshold), 'dark' / 'bright' = mean brightness of the box below / above threshold.
# actions: ('click', x, y), ('key', vk), ('wait', seconds)
STEPS = [
    ('main menu', 'tpl', '028s', (290, 245, 430, 272), 18, [('click', 330, 258)]),
    ('campaign submenu', 'tpl', '037s', (330, 300, 430, 326), 18, [('click', 370, 313)]),
    ('faction select', 'tpl', '039s', (560, 220, 720, 420), 25, [('click', 637, 315), ('wait', 0.6),
                                                                  ('click', 875, 676)]),
    ('briefing video: black', 'dark', None, (440, 200, 840, 520), 12, []),
    ('briefing video: playing', 'bright', None, (440, 200, 840, 520), 30, [('key', 27)]),
    ('mode select', 'tpl', '048s', (640, 655, 800, 690), 18, [('click', 715, 672)]),
    ('world map', 'tpl', '053s', (960, 660, 1120, 690), 18, [('key', 27), ('wait', 1.5), ('click', 1040, 676)]),
    ('mission briefing', 'tpl', '062s', (800, 660, 960, 690), 18, [('click', 877, 675)]),
    ('in game', 'tpl', '066s', (1105, 580, 1275, 715), 25, []),
]


# Popups over the menus that eat the steps' clicks: (name, template, box, threshold, click). The Tacitus update
# dialog (C&C:Online's game patch, Data\dsound.dll) comes up on every start, even after updating (2026-10-20):
# answer No, which changes nothing (Never ask again would write the user's Tacitus.ini in the game folder).
POPUPS = [('tacitus update', 'popup_tacitus.png', (390, 132, 890, 152), 18, (553, 561))]


def cut_popups(frame):
    for name, tpl, box, _, _ in POPUPS:
        Image.open(frame).convert('L').crop(box).save(os.path.join(OUT, tpl))
        print(name, '->', os.path.join(OUT, tpl))


def popup(frame):
    """The click that dismisses a popup on this frame, or None."""
    for name, tpl, box, thr, click in POPUPS:
        path = os.path.join(OUT, tpl)
        if os.path.exists(path) and metric(frame, dict(how='tpl', box=box, template=tpl)) < thr:
            return name, click
    return None


def build(ref):
    os.makedirs(OUT, exist_ok=True)
    steps = []
    for k, (name, how, frame, box, thr, actions) in enumerate(STEPS):
        tpl = None
        if how == 'tpl':
            tpl = f'step{k}.png'
            Image.open(os.path.join(ref, frame + '.png')).convert('L').crop(box).save(os.path.join(OUT, tpl))
        steps.append(dict(name=name, how=how, box=box, threshold=thr, template=tpl, actions=actions))
    with open(os.path.join(OUT, 'nav.json'), 'w', encoding='utf-8') as f:
        json.dump(steps, f, ensure_ascii=False, indent=1)
    print(len(steps), 'steps ->', OUT)


def metric(frame, step):
    patch = Image.open(frame).convert('L').crop(tuple(step['box']))
    if step['how'] == 'tpl':
        tpl = Image.open(os.path.join(OUT, step['template']))
        a, b = patch.tobytes(), tpl.tobytes()
        return sum(abs(x - y) for x, y in zip(a, b)) / len(a)
    return ImageStat.Stat(patch).mean[0]


def matches(step, m):
    return m > step['threshold'] if step['how'] == 'bright' else m < step['threshold']


if __name__ == '__main__':
    if sys.argv[1] == 'build':
        build(sys.argv[2])
    elif sys.argv[1] == 'cutpopups':          # nav.py cutpopups <frame with the popups up>
        cut_popups(sys.argv[2])
    elif sys.argv[1] == 'popup':              # nav.py popup <frame> -> "popup <name> <x> <y>" | "none"
        p = popup(sys.argv[2])
        print(f'popup {p[0].replace(" ", "_")} {p[1][0]} {p[1][1]}' if p else 'none')
    else:
        with open(os.path.join(OUT, 'nav.json'), encoding='utf-8') as f:
            step = json.load(f)[int(sys.argv[3])]
        m = metric(sys.argv[2], step)
        print('match' if matches(step, m) else 'no', round(m, 1))
