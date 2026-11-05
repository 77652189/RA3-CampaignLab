"""What the player reads at once, read off a simulated run (I1, CampShell acceptance 2026-11-05, second round).

The screen has two places for text: the military caption box at the top (one line; a new caption replaces it, each leaves
after its own seconds) and the dialogue panel at the bottom (the subtitle of a dubbed line, the text of an announcer event;
they stack and the whole stack clears ctx.PANEL_CLEAR after the last came up). The player's rule is that no more than
ctx.STRIP_MAX sentences are on screen at any moment, wherever they are: the 2026-11-05 round saw a caption on top and a
different line in the panel together, and the same words in both (a recording whose label reached the string table came up
as a subtitle after its caption). This reads the run's timetable the way the screen does: at the moment each line comes
up, the lines then visible. Read-only: it needs nothing of the simulator but its `log`, `box_log` and the mission's subtitles.
"""
from ctx import PANEL_CLEAR, STRIP_MAX

CAPTION, ANNOUNCER = '通报', '原版播报'      # the sim's log kinds of a caption and of an announcer event; a 配音 only with a subtitle


def lines(s):
    """What came up on screen during the run `s`: [(time, kind, text)]."""
    subtitled = set(s.mm.subtitles)
    return [(t, k, x) for t, k, x in s.log if k in (CAPTION, ANNOUNCER) or (k == '配音' and x in subtitled)]


def panel(s):
    """The panel's lines in order, as [(time, kind, text)]: subtitles and announcer events (a caption is not one of them)."""
    return [x for x in lines(s) if x[1] != CAPTION]


def visible(s, t):
    """The sentences on screen at t: the caption box's line, and the panel's lines of the stack that is up (a stack is up
    from its first line until PANEL_CLEAR after its last)."""
    out, cap = [], next((x for a, b, x in s.box_log if a <= t + 1e-6 < b), None)
    if cap is not None:
        out.append(('通报', cap))
    group = []
    for line in panel(s):
        if group and line[0] >= group[-1][0] + PANEL_CLEAR:
            if group[-1][0] + PANEL_CLEAR > t:
                break
            group = []
        group.append(line)
        if line[0] > t + 1e-6:
            group.pop()
            break
    if group and group[0][0] <= t + 1e-6 < group[-1][0] + PANEL_CLEAR:
        out += [(k, x) for _, k, x in group]
    return out


def stacks(s):
    """[(time, what is on screen)] at the moment each line came up."""
    return [(round(t, 1), visible(s, t)) for t, _, _ in lines(s)]


def too_deep(s, limit=None):
    """[(time, number)] of the moments a line came up and more than `limit` sentences (default ctx.STRIP_MAX) were on screen."""
    limit = STRIP_MAX if limit is None else limit
    return [(t, len(v)) for t, v in stacks(s) if len(v) > limit]
