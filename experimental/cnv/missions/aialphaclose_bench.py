"""Independent health-threshold pair: introduce guards after target engagement.

The target is held at 70% until second 30. Twelve guards then appear around
it and the health hold ends. This removes the old recipe's early interception
as a prerequisite, without forcing an AI order or changing weapon reach.
Only AlphaStrikeTargetHealthPct differs between the builds. Target identity
and internal AlphaStrike eligibility still require independent observations.
"""
import math
from pathlib import Path

import labpaths

from missions import airetreat_bench as ar
from parts import Script, Unit


def mission(high, observe=False):
    m = ar.mission('CampAlCloseHi' if high else 'CampAlCloseLo',
                   RetreatPowerAdvantage='0.2', AlphaStrikeTargetHealthPct='0.9' if high else '0.01',
                   AlphaStrikeTargetTimeToKill='1000.0', Crush='false')
    plant = m.role('far plant').name
    m.facts.update({'alpha target': plant, 'guards at': 30.0, 'alpha high': float(high)})
    m.spawns.add(ar.at.INF)
    actions = []
    for k in range(ar.GUARDS):
        angle = 2 * math.pi * k / ar.GUARDS
        role = f'alpha guard {k + 1}'
        m.waypoint(role, f'CNV Alpha Guard {k + 1}', 'carrier home',
                   ar.GUARD_RING * math.cos(angle), ar.GUARD_RING * math.sin(angle))
        actions.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV Alpha Guard {k + 1}',
                        ar.at.INF, m.team('p1'), m.mark(role)))
    m.scripts += [
        Script('Alpha - hold health', [('FLAG', 'Alpha guards', 0)],
               [('UNIT_SET_HEALTH', plant, 70.0)], once=False),
        Script('Alpha - start timer', [], [('SET_MILLISECOND_TIMER', 'Alpha guard timer', 30.0)]),
        Script('Alpha - introduce guards', [('TIMER_EXPIRED', 'Alpha guard timer')],
               [('SET_FLAG', 'Alpha guards', 1), *actions])]
    if observe:
        # Use the existing yard: no extra object, economy or recruitment candidate.
        yard = m.role('ai yard')
        original = yard.template
        host = 'CNVAlphaTeamsYard'
        xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures' / (original + '.xml')).read_text(encoding='utf-8')
        assert xml.count('<Behaviors>') == xml.count(f'id="{original}"') == 1
        xml = xml.replace(f'id="{original}"', f'id="{host}"').replace(
            '<Behaviors>', '<Behaviors>\n  <DeletionUpdate id="ModuleTag_CNVTeams" MinFrames="15" MaxFrames="4000"/>')
        m.units.append(Unit(host, xml, names=dict(unit=host), what='原建造厂附带变化日志与每秒心跳', params=dict(every=15)))
        m.find(yard.name).template = yard.template = host
        m.name = 'CampAlObsHi' if high else 'CampAlObsLo'
        m.ext = True
    return m


MISSION = {'aialcloselo': lambda: mission(False), 'aialclosehi': lambda: mission(True),
           'aialobslo': lambda: mission(False, observe=True), 'aialobshi': lambda: mission(True, observe=True)}
