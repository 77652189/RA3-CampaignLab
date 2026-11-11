"""Wide bench FAIL1099/1100/1100/1100: broad child did not fire.
Authorized stock-recipe followup ret: retain wide child and all positions/
NO_ATTACK, match ProductionKickbacks CIRCLE and broad ANY kind filter,
no relationship/status restriction. PREDICT0/0/1100/0 if dispatch occurs.
This does not invent a required marker or alter status without data.
Coordinator retry: wide changes only child to10000UNRESISTABLE/Radius10,
no object/status filters, all relations and anti masks, range/speed999999,
unlimited clip (same as original schema default). PREDICT0/0/1100/1100 if
dispatch works; unchanged1099/1100/1100/1100 falsifies that branch.
Parent Radius100/VEHICLE/ENEMIES, positions and NO_ATTACK remain identical.
Original failure follows: UNEXPLAINED new bench FAIL1099/1100/1100/1100, 2026-11-10.
Only marker damage landed; child damage was not observed. Archived0030.png
confirms all four alive. Radius anchor, filter relationship reference and
child firing conditions have not been separated. STOP; no prediction fitting.
Original PREDICT1089/1090/1100/1100 before bench (1000*alive + health%).
FireOnObjectsNugget Radius100, FireOnVictimObject true, FilterANY VEHICLE
ENEMIES dispatches CNV_FireObjectsChild to each live selected victim.
Child100UNRESISTABLE, Radius0, RadiusDamageAffectsSELF/ALLIES/ENEMIES/NEUTRALS.
1000HP primary also receives10UNRESISTABLE marker ->89%; vehicle60 east
receives100 ->90%; vehicle160 east spared; infantry80 north excluded ->100%.
No guesses about boundary extent: selected centres are far from edges.
Current sim ignores FireOnObjects, predicts1099/1100/1100/1100.
One initially EMPTY clip loads1s, order6s, stop6+4/15; four packed counters.
Each frame clears health counter before reading, so dead-object freeze cannot
preserve a passing health+alive packed reading. Child/OCL chains, upgrades,
status filters and FireOnVictimObject=false are outside this first check.
"""
import re
from maps import probe_range
from parts import Mission,Script,Test
from checks.engine_weaponfx import gun
from checks.engine_missile import target,TARGET_ID

def mission():
    effect='<FireOnObjectsNugget Radius="100" Weapon="CNV_FireObjectsChild" FireOnVictimObject="true"><Filter Rule="ANY" Include="VEHICLE" Relationship="ENEMIES"/></FireOnObjectsNugget>'
    u=gun('CNV_FireObjectsGun',10,effect)
    u.xml=u.xml.replace('DamageType="EXPLOSIVE"','DamageType="UNRESISTABLE"')
    child='<WeaponTemplate id="CNV_FireObjectsChild" AttackRange="500" RadiusDamageAffects="SELF ALLIES ENEMIES NEUTRALS"><Nuggets><DamageNugget Damage="100" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="0"/></Nuggets></WeaponTemplate>'
    u.xml=u.xml.replace('</AssetDeclaration>',child+'</AssetDeclaration>')
    u.link.append('WeaponTemplate:CNV_FireObjectsChild')
    m=Mission(name='CampFireObj',map=probe_range,units=[u,target(health=1000)],facts={})
    m.put(u.id,'base gun',side='p1',angle=1.5708,name='FireObj gun')
    for name,template,x,y in [('main',TARGET_ID,0,450),('inner',TARGET_ID,60,450),
                               ('outer',TARGET_ID,160,450),('man','AlliedAntiInfantryInfantry',0,530)]:
        m.put(template,'base gun',x,y,side='s1',angle=4.7124,name='FireObj '+name)
    return m

def check(m):
    t=Test(); names=['FireObj '+k for k in ('main','inner','outer','man')]
    start=[('MAP_REVEAL_ALL_PERM',m.player('p1')),('SET_MILLISECOND_TIMER','FireObj Fire',6.0),('SET_MILLISECOND_TIMER','FireObj Stop',6.0+4/15)]
    start += [('UNIT_CHANGE_OBJECT_STATUS',v,'NO_ATTACK',1) for v in names+['FireObj gun']]
    t.scripts=[Script('Test - start',[],start),
        Script('Test - fire',[('TIMER_EXPIRED','FireObj Fire')],[('UNIT_CHANGE_OBJECT_STATUS','FireObj gun','NO_ATTACK',0),('NAMED_ATTACK_NAMED','FireObj gun','FireObj main')]),
        Script('Test - stop',[('TIMER_EXPIRED','FireObj Stop')],[('UNIT_CHANGE_OBJECT_STATUS','FireObj gun','NO_ATTACK',1)])]
    for i,v in enumerate(names):
        c='CNV_FireObj_'+str(i);t.counters.append((c,v))
        t.scripts += [Script('Test - hp '+str(i),[],[('SET_COUNTER',c,0),('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER',v,c)],once=False),
                      Script('Test - alive '+str(i),[('NAMED_NOT_DESTROYED',v)],[('INCREMENT_COUNTER',1000,c)],once=False)]
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(1089,1090,1100,1100))]
    t.bench=[('bench_watch',dict(seconds=16.0,every=.5,sheet=False,lines=4))]
    return t
def wide_check(m):
    # Coordinator discriminator: change ONLY child weapon; keep parent filter/positions/statuses.
    u=next(u for u in m.units if u.id=='CNV_FireObjectsGun')
    child='<WeaponTemplate id="CNV_FireObjectsChild" AttackRange="999999" WeaponSpeed="999999" ClipSize="0" RequiredAntiMask="ANTI_GROUND ANTI_WATER ANTI_STRUCTURE ANTI_SUBMERGED ANTI_AIRBORNE_VEHICLE ANTI_AIRBORNE_INFANTRY" RadiusDamageAffects="SELF ALLIES ENEMIES NEUTRALS"><Nuggets><DamageNugget Damage="10000" DamageType="UNRESISTABLE" DeathType="NORMAL" Radius="10"/></Nuggets></WeaponTemplate>'
    u.xml,n=re.subn(r'<WeaponTemplate id="CNV_FireObjectsChild".*?</WeaponTemplate>',child,u.xml,flags=re.S)
    assert n==1
    t=check(m)
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(0,0,1100,1100))]
    return t

def retail_check(m):
    t=wide_check(m)
    u=next(u for u in m.units if u.id=='CNV_FireObjectsGun')
    # Match the stock ProductionKickbacks parent recipe; child remains the wide diagnostic.
    u.xml=u.xml.replace('<FireOnObjectsNugget Radius="100"',
        '<FireOnObjectsNugget Radius="100" PartitionFilterTestType="CIRCLE"')
    u.xml=u.xml.replace('<Filter Rule="ANY" Include="VEHICLE" Relationship="ENEMIES"/>',
        '<Filter Rule="ANY" Include="INFANTRY VEHICLE HUGE_VEHICLE STRUCTURE"/>')
    u.xml=u.xml.replace('RadiusDamageAffects="ENEMIES"','RadiusDamageAffects="ALLIES ENEMIES NEUTRALS"',1)
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(0,0,1100,0))]
    return t

MISSION={'engine_fireobjects':mission}
CHECKS={'engine_fireobjects':{'a':check,'wide':wide_check,'ret':retail_check}}
