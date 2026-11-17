"""InformTargetNugget (69 uses), next by usage: bounded damage isolation.
PREDICT99/99 after100 marker,89/89 after1000,79/79 after second1000;
both alive. Clone the already-benched attribute two-lane check, replacing
ONLY the high lane modifier with retail's empty InformTargetNugget.
The nugget schema has no damage amount. Simulator currently ignores it.
This check ONLY isolates additional HP effects. Incoming-projectile AI
response is NOT tested; do not promote whole-item coverage from this check.
Empty initial clips load1s, order6s, each burst stopped byNO_ATTACK.
"""
from checks.engine_weaponfx import mission,check

def damage_check(m):
    t=check(m,'attribute')
    for u in m.units:
        u.xml=u.xml.replace('<AttributeModifierNugget AttributeModifierName="AttributeMod_TargetPainted"/>','<InformTargetNugget/>')
    t.expect=[(label,14,'==',v,16) for (_,label),v in zip(t.counters,(79,1,79,1))]
    return t

def make():
    m=mission();m.name='CampInfo';return m
MISSION={'engine_inform':make}
CHECKS={'engine_inform':{'damage':damage_check}}
