"""Engine line D 92: the player's formation switches on the bench (checks/engine_formation_player.py `s`).

CampFormS = the probe mission CampFormP (two lanes of two Guardian tanks + two Peacekeepers, CNVProbe copies) with both
switches on every unit (units/formation.py: 同速 / 密集 toggles next to their own buttons) and CNVSync's host for the
player. Published facts: 'sync command' / 'dense command' (NAMED_USE_COMMANDBUTTON_ABILITY presses them).
"""
from checks.engine_formation_player import LANES, X0, mission as probe_mission
from units import formation

HOST = 'CNVSyncHost'


def sync_mission():
    m = probe_mission()
    m.name = 'CampFormS'
    m.units = [formation.switches(u) for u in m.units] + [formation.host(HOST)]
    m.put(HOST, 'pace start', X0 - 500.0 - 250.0, LANES['plain'] - 1200.0 - 300.0, role='sync host',
          name='UNIT - CNV Form Sync Host')
    m.facts['sync command'] = formation.ids('sync')['command']
    m.facts['dense command'] = formation.ids('dense')['command']
    return m


MISSION = {'engine_formation_sync': sync_mission}
