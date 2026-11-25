"""E174: retail multigunner listener, with a single-module deletion control."""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Unit


def mission(enabled=True):
    m = Mission(name='CampSecondOnE' if enabled else 'CampSecondOffE',
                map=probe_range, units=[], facts={'enabled': enabled})
    xml = (Path(labpaths.SDK3) / 'SageXML/Allied/Structures/AlliedBaseDefense.xml').read_text(encoding='utf-8-sig')
    if not enabled:
        xml, n = re.subn(r'<xi:include\s+href="DATA:Includes/InfantryFighting/IF_SecondaryObjectListener.xml"\s*/>', '', xml)
        assert n == 1
    ident = 'AlliedBaseDefense'
    m.units.append(Unit(ident, xml))
    m.assets.append((ident + '.xml', xml, 'GameObject:' + ident))
    m.replaces.append('GameObject:' + ident)
    m.put(ident, 'base gun', role='host', name='E174 Host')
    m.put('AlliedEngineer', 'base gun', 0, 100, role='crew', name='E174 Crew')
    m.put('AlliedPowerPlant', 'power 1', role='power')
    return m


def repair():
    """The repair the engineer's upgrade enables (ABD_RepairWeapon, AttackRange 25, 5 HEALING a shot): Guardians (480,
    radius 20) 40 north of the crewed turret (N), 150 north of it (F) and 40 north of an empty one (C)."""
    m = Mission(name='CampSecondRepE', map=probe_range, units=[], facts={})
    m.put('AlliedBaseDefense', 'base gun', role='host', name='E174 Host')
    m.put('AlliedBaseDefense', 'high gun', role='empty', name='E174 Empty')
    m.put('AlliedEngineer', 'base gun', -100, 0, role='crew', name='E174 Crew')
    m.put('AlliedPowerPlant', 'power 1', role='power')
    for row, site, dy in (('N', 'base gun', 40), ('F', 'base gun', 150), ('C', 'high gun', 40)):
        m.put('AlliedAntiVehicleVehicleTech1', site, 0, dy, role=row, name='E174 ' + row)
    return m


def turret():
    """E239: the turret's own GarrisonContain (ContainMax 1, own and allied infantry only, KillPassengersOnDeath; the
    turret GARRISONABLE_UNTIL_DESTROYED). GIs south of four turrets: cap (a 100 off, b 200 off, both walk in), foe (an
    idle enemy's turret, e walks in), worn (c put in, then the turret hurt and killed), blast (d put in, a hit kills it)."""
    m = Mission(name='CampTurretGarE', map=probe_range, units=[], facts={})
    for lane, site, crew in (('cap', 'base gun', 'ab'), ('foe', 'high gun', 'e'), ('worn', 'order gun', 'c'),
                             ('blast', 'removed gun', 'd')):
        m.put('AlliedBaseDefense', site, role=lane, side='s4' if lane == 'foe' else 'p1', name='E239 ' + lane)
        for k, r in enumerate(crew):
            m.put('AlliedAntiInfantryInfantry', site, 0, -100 * (k + 1), role=r, name='E239 ' + r)
    m.put('AlliedPowerPlant', 'power 1', role='power')
    return m


MISSION = {'engine_secondon_e': mission, 'engine_secondoff_e': lambda: mission(False), 'engine_secondrep_e': repair,
           'engine_turretgar_e': turret}
