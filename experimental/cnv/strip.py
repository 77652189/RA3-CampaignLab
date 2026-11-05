"""The strip, read off a simulated run (I1, CampShell acceptance 2026-11-05).

In the shipped game one box takes everything the player reads -- a military caption, the subtitle of a dubbed line, the text
of an announcer event -- and it accumulates: a new line goes under the old ones, nothing leaves alone, and the whole stack
clears ctx.PANEL_CLEAR after the last line came up. The offline rules used to model two channels (a one-line caption box and
a panel for the subtitles, E6) and so counted each apart; the screen showed 3 and 4 lines at once. This reads the run's
timetable the way the screen does: every line that came up, grouped into stacks, and `too_deep` the stacks that grew past
ctx.STRIP_MAX. Read-only: it needs nothing of the simulator but its `log` and the mission's subtitles.
"""
from ctx import PANEL_CLEAR, STRIP_MAX

SHOWN = ('通报', '原版播报')              # the sim's log kinds of a caption and of an announcer event; a 配音 only with a subtitle


def lines(s):
    """What came up in the strip during the run `s`: [(time, kind, text)]."""
    subtitled = set(s.mm.subtitles)
    return [(t, k, x) for t, k, x in s.log if k in SHOWN or (k == '配音' and x in subtitled)]


def stacks(s):
    """The strip's stacks in order: each a list of the lines that were on screen together (a line joins the stack while
    the last line came up less than PANEL_CLEAR ago)."""
    out = []
    for line in lines(s):
        if not out or line[0] >= out[-1][-1][0] + PANEL_CLEAR:
            out.append([])
        out[-1].append(line)
    return out


def too_deep(s, limit=None):
    """[(time of its first line, lines)] of the stacks deeper than `limit` (default ctx.STRIP_MAX)."""
    limit = STRIP_MAX if limit is None else limit
    return [(round(g[0][0], 1), len(g)) for g in stacks(s) if len(g) > limit]
