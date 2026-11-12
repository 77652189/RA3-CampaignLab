"""SLUSH_FUND share isolation, using aiom13's two-plant opening.

Only the budget allocation changes: slush 100 / production 0 versus the reverse.
INFERRED prediction: the opening spends SLUSH_FUND, hence two plants versus none
at s40. No deposits, income, combat teams or defense production are introduced.
Original readings and ownership: work/re/c_slush_report.md.
"""
from missions.aiomove_bench import ALL, mission as opening_mission
from missions.aitower_bench import mission as tower_mission


def mission(slush):
    m = opening_mission('CampAISlush' + ('S' if slush else 'P'),
                        [('CNVOpenPPT30', '100%', ALL)], 2 if slush else 0, 0)
    name, xml, ref = m.assets[0]
    budget = f'''  <AIBudgetStateDefinition id="CNVSlushBudget">
    <Heuristic><ConstantHeuristic/></Heuristic>
    <Budget>
      <AccountShare Account="PRODUCTION" Percent="{0 if slush else 100}%"/>
      <AccountShare Account="DEFENSE" Percent="0%"/>
      <AccountShare Account="SLUSH_FUND" Percent="{100 if slush else 0}%"/>
    </Budget>
  </AIBudgetStateDefinition>
'''
    xml = xml.replace('  <AIPersonalityDefinition', budget + '  <AIPersonalityDefinition')
    removed = '\n'.join(f'    <BudgetState id="{key}" xai:joinAction="Remove"/>'
                        for key in ('CoopBudget', 'DefenseBudget', 'HeavyDefenseBudget', 'OpeningMoveBudget'))
    xml = xml.replace('  </AIPersonalityDefinition>', removed +
                      '\n    <BudgetState id="CNVSlushBudget" State="CNVSlushBudget"/>\n'
                      '  </AIPersonalityDefinition>')
    m.assets[0] = name, xml, ref
    return m


def defense(slush):
    """Round two: funded refinery, no opening, only the defense build state.

    Prediction: SLUSH_FUND 100% buys no turret; DEFENSE 100% buys at least one.
    The positive control distinguishes an idle host from account separation.
    """
    m = tower_mission('CampAISl' + ('SDef' if slush else 'DDef'), 0.5,
                      opener=False, refinery=True, defense=100, watch=65)
    name, xml, ref = m.assets[0]
    if slush:
        xml = xml.replace('Account="DEFENSE" Percent="100%"', 'Account="DEFENSE" Percent="0%"')
        xml = xml.replace('Account="SLUSH_FUND" Percent="0%"', 'Account="SLUSH_FUND" Percent="100%"')
    m.assets[0] = name, xml, ref
    m.facts['slush only'] = slush
    return m


MISSION = {'aislush100': lambda: mission(True), 'aislush0': lambda: mission(False),
           'aislsdef': lambda: defense(True), 'aislddef': lambda: defense(False)}
