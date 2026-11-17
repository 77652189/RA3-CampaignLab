"""What a level's briefing tells the player, as data the auto players read (ADR 0026 item 4).

An auto player knows only what a human has in front of them: the objectives' markers on the map (Sim.markers), what
its units see, the countdowns on screen, and what the briefing points at. The last is this file: sites to scout when
nothing else is known, and the units the level asks to keep alive that the level drives itself (the player does not
steer a convoy). Nothing here says how to win; the card player's script (experimental/cnv/plays/<level>.txt) is the
only place the intended solution lives.
"""
import dataclasses
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CNV = os.path.join(os.path.dirname(HERE), 'cnv')


@dataclasses.dataclass(frozen=True)
class Brief:
    leads: tuple = ()           # map sites to scout when no objective marker or enemy is known, in the briefing's order
    escort: tuple = ()          # cast roles the level moves itself and asks to keep alive (the army stays round them)
    until: float = 1500.0       # seconds an auto player gets (the level's design is 8~15 min; double it for the lost)
    plan: str = ''              # the card player's script (the plan's own solution), or '' for none


def _a4_leads():
    """A4's leads are engine line B's proxy player's (simproxy.LEADS / ESCORT): one source for what the briefing names
    (autoplay.py has put the cnv folders on the path by the time a brief is asked for)."""
    import simproxy
    return simproxy.LEADS['a4'], simproxy.ESCORT['a4']


def _a4():
    leads, escort = _a4_leads()
    return Brief(leads=leads, escort=escort, plan=os.path.join(CNV, 'plays', 'a4.txt'))


def _a3():
    return Brief(leads=('park avenue', 'blackheath', 'riverside junction', 'church lane', 'west gap'),
                 plan=os.path.join(CNV, 'plays', 'a3.txt'))


BRIEFS = {'a3': _a3, 'a4': _a4}


def brief(level):
    """The level's Brief; a level with none gets the empty one (markers and what is seen still work)."""
    make = BRIEFS.get(level)
    return make() if make else Brief()
