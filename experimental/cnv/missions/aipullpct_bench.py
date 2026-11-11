"""Pullback health threshold only: keep aipullsov's Soviet AI and Crane.

Prediction before measurement: at scripted 30% health, 0.2 does not trigger
pullback yet; 0.5 does. Later combat may take the low lane below 20%, so this
does not predict that it can never return. All other mission settings match.
"""
from missions.aipullback_bench import mission


MISSION = {
    'aipullpctlo': lambda: mission('CampPullPctLo', factory=True, faction='Soviet',
                                 PullbackInjuredHealthPct='0.2'),
    'aipullpcthi': lambda: mission('CampPullPctHi', factory=True, faction='Soviet',
                                 PullbackInjuredHealthPct='0.5'),
}
