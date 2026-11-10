"""New bench PASS99/1/40/1; PREDICT before bench. Control1000HP Hammer takes10EXPLOSIVE.
High gun has ONLY WeaponOCLNugget OCL_AthenaCannon, no markerDamageNugget.
Retail OCL creates CannonEffect at target; Lifetime2s=30frames;
FireWeaponNugget FireDelay0.1s ->ceil1.5=2frames; AthenaCannonWeapon20.
GUESSED endpoint convention: loop fires frames2..30 inclusive=29 hits,
FireWeaponWhenDead adds1, total600EXPLOSIVE. BaseTankArmor100% ->40%HP.
Current simulator ignores FireDelay, predicts30 loop+1death=620 ->38%.
Probe isolates the lifetime TOTAL, not effect per-frame timing or area geometry.
Finite one clip loads1s, fire6s, NO_ATTACK6+4/15; four lines with alive.
"""
import re
from parts import Script
from checks.engine_laser import mission as laser_mission,check as laser_check

def mission():
    m=laser_mission();m.name='CampOclOne'
    for u in m.units:
        if u.id=='CNV_LaserBase':
            u.xml=u.xml.replace('Damage="100"','Damage="10"')
        if u.id=='CNV_LaserHigh':
            u.xml=re.sub(r'<DamageNugget\b[^>]*/>','',u.xml)
            u.xml=re.sub(r'<ActivateLaserNugget\b[^>]*/>','<WeaponOCLNugget WeaponOCL="OCL_AthenaCannon"/>',u.xml)
    return m

def check(m):
    t=laser_check(m)
    t.counters=[]
    for lane in ('base','high'):
        hp='CNV_Laser_'+lane+'HP';alive='CNV_OclOne_'+lane+'Alive';v='Laser '+lane+' target'
        t.counters.extend([(hp,lane+' HP'),(alive,lane+' alive')])
        t.scripts.extend([Script('Test - alive '+lane,[],[('SET_COUNTER',alive,1)],once=False),
                          Script('Test - dead '+lane,[('NAMED_DESTROYED',v)],[('SET_COUNTER',alive,0)],once=False)])
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(99,1,40,1))]
    return t
MISSION={'engine_oclone':mission}
CHECKS={'engine_oclone':{'a':check}}
