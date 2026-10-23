"""纸鹤侦察机 (J3, campaign only; docs/story/units.md 4: Yuriko's infiltration scouts the way with paper cranes). An
unarmed flier that sees far: it clears the shroud `sight` around itself (retail: 500 for most units, 750 for scouts)
and sees `vision` for targeting; it is stealthy, so only detectors see it. Stand-in: the Twinblade, which hovers
without an airfield, its guns taken off (art last).

Published: what and params; no ability (it is sent: MOVE_NAMED_UNIT_TO).
"""
import os
import re

import make_campnew2 as c2
from parts import Unit

SAGE = os.path.join(c2.SDK, 'SageXML', 'Soviet', 'Units')


def sub1(x, old, new):
    assert x.count(old) == 1, (old[:60], x.count(old))
    return x.replace(old, new, 1)


def crane(id='CNV_Crane', sight=900, vision=300, stealth=True):
    """stealth (the user's decision, 2026-10-22): always hidden -- it never fires, and retail's default template
    only drops stealth while firing; enemy detectors (dogs, bears, burst drones: StealthDetectorUpdate, 300) see it."""
    x = open(os.path.join(SAGE, 'SovietAntiGroundAircraft.xml'), encoding='utf-8').read()
    x = sub1(x, 'id="SovietAntiGroundAircraft"', f'id="{id}"')
    x = sub1(x, 'EditorName="SovietAntiGroundAircraft"', f'EditorName="{id}"')
    x = sub1(x, 'VisionRange="200"\n\t\t\tShroudClearingRange="=$STANDARD_SHROUD_CLEAR"',
             f'VisionRange="{vision}"\n\t\t\tShroudClearingRange="{sight}"')
    x, n = re.subn(r'\s*<WeaponSetUpdate\b.*?</WeaponSetUpdate>', '', x, count=1, flags=re.S)
    assert n == 1, 'no WeaponSetUpdate'
    if stealth:
        x = sub1(x, '</Behaviors>', '''	<InvisibilityBehavior id="ModuleTag_CNV_Stealth" InvisibilityTemplate="DefaultInvisibilityTemplate"/>
		</Behaviors>''')
    return Unit(id, x, what=f'纸鹤侦察机：双刃底，没有武器；驱雾 {sight}、视野 {vision}' + ('；隐身，探测单位看得见' if stealth else ''),
                params=dict(sight=sight, vision=vision, stealth=stealth))
