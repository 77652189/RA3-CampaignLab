"""Engine line D round 68: read the AI's teams (template name -> team -> member ids) off ra3ext's CNVTeams module, on
the C line's aicr3 game (CreateUnits MinUnits 3: engine_aicreate). The mission (missions/aiteams_bench.py) is
aicreate_bench's aicr3 plus one object of the AI's own carrying the CNVTeams module. Every 15 frames the module logs
the host owner's teams to the run folder's ra3ext.log; experimental/cnv/teamlog.py reads them by name:

  team_size(run, 'CNVStateTF', frame)

The counters and expectations are engine_aicreate's (s41..: three Guardians out, four Peacekeepers home); the team
reading is read off the log after the run, not asserted by the bench.
"""
from checks.engine_aicreate import a as aicreate

CHECKS = {'aicr3t': {'a': aicreate}}
