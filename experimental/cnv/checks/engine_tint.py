"""New bench PASS2/90/2/90; PREDICT before bench: TintObjectsNugget changes color only.
Use Laser probe's two1000HP Hammer lanes and100EXPLOSIVE one-shot guns;
replace only high's ActivateLaserNugget with retail-style tint fields:
PreColorTime0.5s, SustainedColorTime2s, PostColorTime0s, Frequency1,
Amplitude0, ColorR2/G0/B0. Schema fields are color/animation parameters,
no damage/movement/armor field. HP and hit timing should match control
through tint expiry. Pixel rendering is not judged by this numeric probe.
Initially empty clips load1s; fire6s; NO_ATTACK6+4/15; four counters.
"""
from checks.engine_laser import mission as laser_mission,check

def mission():
    m=laser_mission();m.name='CampTint'
    for u in m.units:
        u.xml=u.xml.replace('<ActivateLaserNugget LaserId="201" Lifetime="2s"/>',
            '<TintObjectsNugget PreColorTime="0.5s" SustainedColorTime="2s" PostColorTime="0s" Frequency="1" Amplitude="0"><Color R="2" G="0" B="0"/></TintObjectsNugget>')
    return m
MISSION={'engine_tint':mission}
CHECKS={'engine_tint':{'pair':check}}
