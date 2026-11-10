"""Engine line D, round 10 (ADR 0027/0028): the vertical sweep's carrier, with ra3ext injected and without. Retail's
LinearDamageUpdate (the dolphin's sonar wave) is a damage line that walks away from the shooter: ActivateLinearDamageNugget
starts it toward the weapon's target (flat, z dropped), from StartDistanceOffset out to StartDistanceOffset + Length at
Speed, one SweepWeapon hit every 2 x Radius. What retail lacks is a laser beam that follows the walking point; the
ra3ext module tagged ModuleTag_CNVSweep is to write the point into the LaserState's end each frame (handoff-d round 9).

The shooter is engine_shot's V4 (no scatter, no pre-attack) under its own id, its weapon: a DamageNugget of AIM_DAMAGE on the
aimed Hammer (counted: did it fire), ActivateLinearDamageNugget (Lifetime LIFE) and ActivateLaserNugget (LaserId 1,
Lifetime LIFE); the clip loads RELOAD after birth, the order comes after it, the next clip after the far row's hit. Behaviors: LinearDamageUpdate id=ModuleTag_CNVSweep (StartDistanceOffset START, Radius RADIUS,
Length LENGTH, Speed SPEED, SweepWeapon CNV_SweepHit = 500 damage in RADIUS, FollowTerrain), LaserState LaserId 1;
Draws: the prism tower's LaserDraw (LaserStateID 1).

Two lanes, a shooter at '<lane> gun' each, aimed (at ORDER) at a Hammer AIM north; three more Hammers (10 000 health,
engine_missile's) between, at ROW north -- counted, never aimed at:

  base   CNV_Sweep       FiringDuration 0 (engine_shot's)
  high   CNV_SweepHold   FiringDuration LIFE (the update sleeps once the weapon slot says it stopped: does it?)

Counter per row Hammer: frames from the order until its first hit (stops counting at the hit). Near < mid < far =
the line walks outward; the gaps say the speed (SPEED / 15 a frame, so 100 apart = 100 x 15 / SPEED frames).

  engine_sweep     Mission(ext=True)   the dll's sweep module (once written: handoff-d round 10 step 2) logs nodes
  engine_sweepoff  Mission(ext=False)  plain retail: the damage line alone, the beam stays on the aimed Hammer
"""
from maps import probe_range
from parts import Mission, Script, Test
from checks.engine_missile import TARGET_ID, _sub1, target
from checks.engine_shot import _nuggets, shot_v4

# the V4's clip is empty at birth and loads ClipReloadTime later (fire_state.md round 27): round 10's reload of 60 s
# never let it fire in a 20 s run (bench 11-10 03:39, no row Hammer hit). Loaded at RELOAD, ordered at ORDER after it;
# the next clip comes RELOAD after the first shot, past the far row's hit (ORDER + (350 - START) / SPEED)
ORDER, RUN, RELOAD = 8.0, 22.0, 6.0
START, RADIUS, LENGTH, SPEED = 50.0, 10.0, 450.0, 60.0     # covers 50 .. 500 north in 7.5 s, 4 a frame
LIFE = 8.0
ROW, AIM = (150.0, 250.0, 350.0), 450.0
TAG, HIT = 'ModuleTag_CNVSweep', 'CNV_SweepHit'
LANES = {'base': ('CNV_Sweep', 0.0), 'high': ('CNV_SweepHold', LIFE)}
LABELS = ('近', '中', '远')
AIM_LABEL, AIM_DAMAGE = '瞄', 200.0      # the shot's own hit on the aimed Hammer: did the V4 fire at all

LASER_DRAW = '''
			<LaserDraw id="ModuleTag_CNVSweepLaserDraw" Texture1_UTile="1" Texture1_VTile="1" Texture1_UScrollRate="0"
				Texture1_VScrollRate=".2" Texture1_NumFrames="1" Texture1_FrameRate="30" Texture2_UTile="1"
				Texture2_VTile=".3" Texture2_UScrollRate="0" Texture2_VScrollRate="1.4" Texture2_NumFrames="1"
				Texture2_FrameRate="30" LaserWidth="8" LaserStateID="1">
				<FXShader ShaderName="Laser.fx" TechniqueIndex="0">
					<Constants>
						<Texture Name="Texture1"><Value>FXObeliskLaser</Value></Texture>
						<Texture Name="Texture2"><Value>FXLaserOverlay</Value></Texture>
						<Float Name="ColorEmissive"><Value>5.000000</Value><Value>5.000000</Value><Value>2.000000</Value></Float>
					</Constants>
				</FXShader>
			</LaserDraw>
		'''


def hit_weapon():
    return (f'\t<WeaponTemplate id="{HIT}" RadiusDamageAffects="ENEMIES">\n\t\t'
            + _nuggets(f'<DamageNugget Damage="500.0" Radius="{RADIUS:g}" DamageType="EXPLOSIVE" DeathType="NORMAL" />')
            + '\n\t</WeaponTemplate>\n')


def sweeper(id, firing):
    nug = _nuggets(f'<DamageNugget Damage="{AIM_DAMAGE:g}" Radius="1.0" DamageType="MAGIC" DeathType="NORMAL" />',
                   f'<ActivateLinearDamageNugget id="CNVSweepActivate" Lifetime="{LIFE:g}s" />',
                   f'<ActivateLaserNugget id="CNVSweepLaser" Lifetime="{LIFE:g}s" LaserId="1" />')
    hold = f'，开火持续 {firing:g} s' if firing else ''
    u = shot_v4(id, nug, extra=hit_weapon(), reload=RELOAD,
                what=f'竖扫载体 V4（探针）：武器开伤害线 + 激光，LinearDamageUpdate（{TAG}）由近 {START:g} 到远 '
                     f'{START + LENGTH:g}、速度 {SPEED:g}{hold}')
    if firing:
        u.xml = _sub1(u.xml, '<FiringDuration\n\t\t\tMinSeconds="0s"\n\t\t\tMaxSeconds="0s"',
                      f'<FiringDuration\n\t\t\tMinSeconds="{firing:g}s"\n\t\t\tMaxSeconds="{firing:g}s"')
    u.xml = _sub1(u.xml, '<Behaviors>', f'''<Behaviors>
			<LinearDamageUpdate id="{TAG}" StartDistanceOffset="{START:g}" Radius="{RADIUS:g}" Length="{LENGTH:g}"
				SweepWeapon="{HIT}" Speed="{SPEED:g}" FollowTerrain="true" />
			<LaserState id="ModuleTag_CNVSweepLaser" LaserId="1" />''')
    u.xml = _sub1(u.xml, '</Draws>', LASER_DRAW + '</Draws>')
    u.link.append(f'WeaponTemplate:{HIT}')
    u.names.update(hit=HIT, tag=TAG)
    u.params.update(start=START, radius=RADIUS, length=LENGTH, sweep_speed=SPEED, life=LIFE, firing=firing)
    return u


def _n(lane, part):
    return f'UNIT - CNV Sweep {lane.title()} {part}'


def mission(ext=True):
    m = Mission(name='CampSweep' if ext else 'CampSweepOff', map=probe_range,
                units=[sweeper(tpl, firing) for tpl, firing in LANES.values()] + [target()], facts={}, ext=ext)
    for lane, (tpl, _) in LANES.items():
        site = f'{lane} gun'
        m.put(tpl, site, side='p1', role=f'{lane} sweeper', name=_n(lane, 'Shooter'))
        m.put(TARGET_ID, site, 0.0, AIM, side='s1', role=f'{lane} aim', name=_n(lane, 'Aim'))
        for k, d in enumerate(ROW):
            m.put(TARGET_ID, site, 0.0, d, side='s1', role=f'{lane} row {d:g}', name=_n(lane, f'Row{k}'))
    return m


def sweep_test(m, lane='base'):
    """Check a: the base lane; b: the high lane (four counter lines at most). The other lane stays NO_ATTACK."""
    t = Test()
    held = [_n(x, p) for x in LANES for p in ['Shooter', 'Aim'] + [f'Row{k}' for k in range(len(ROW))]]
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))]
                            + [('UNIT_CHANGE_OBJECT_STATUS', x, 'NO_ATTACK', 1) for x in held]
                            + [('SET_MILLISECOND_TIMER', 'Test Order', ORDER)]))
    shooter = _n(lane, 'Shooter')
    t.scripts.append(Script('Test - order', [('TIMER_EXPIRED', 'Test Order')],
                            [('UNIT_CHANGE_OBJECT_STATUS', shooter, 'NO_ATTACK', 0),
                             ('NAMED_ATTACK_NAMED', shooter, _n(lane, 'Aim')), ('SET_FLAG', 'Test Ordered', 1)]))
    for k, label in list(enumerate(LABELS)) + [(len(LABELS), AIM_LABEL)]:
        c, tg = f'CNV_Sweep_{k}', _n(lane, f'Row{k}' if k < len(LABELS) else 'Aim')
        t.counters.append((c, label))
        t.scripts.append(Script(f'Test - {c} frames', [('FLAG', 'Test Ordered', 1), ('UNIT_HEALTH', tg, 2, 100)],
                                [('INCREMENT_COUNTER', 1, c)], once=False))
    # check a: every row Hammer is hit before the end (a counter that never stops reads ~15 a second); b only reads
    never = (RUN - ORDER - 2.0) * 15
    t.expect = ([(label, RUN - 1, '<', never) for label in LABELS + (AIM_LABEL,)] if lane == 'base'
                else [(LABELS[0], 0, '>=', 0)])
    t.bench = [('bench_watch', dict(seconds=RUN, every=1, sheet=False, lines=len(t.counters)))]
    return t


_CHECKS = {'a': sweep_test, 'b': lambda m: sweep_test(m, 'high')}
MISSION = {'engine_sweep': mission, 'engine_sweepoff': lambda: mission(False)}
CHECKS = {'engine_sweep': _CHECKS, 'engine_sweepoff': _CHECKS}
