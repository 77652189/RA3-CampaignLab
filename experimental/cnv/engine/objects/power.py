"""L2 special powers (ADR 0029, docs/engine/sim-layers.md): a script's superweapon hits, the curtains, the reload
lag and the deploy / pack buttons' powers, moved out of sim.py so the action files read them without importing sim.
sim re-exports them all (`sim.SUPERWEAPON_HITS`, `sim.CURTAIN` still work). The reloads' host half (step M8):
the body's `ready_at` forward and starting a reload on the SpecialPower modules (engine/modules/specialpower.py)."""
from engine.kernel import interfaces


def ready_at(mods):
    """The body's ready_at forward: {power: the frame its reload ends} of the SpecialPower modules a cast started."""
    return {m.power(): m.ready_at() for m in mods if m.ready_at() is not None}


def start_reload(world, b, power, frame):
    """A cast of `power` by b starts its reload, over at `frame`: every SpecialPower module of b serving it; none --
    a power cast on a thing no block of whose template serves it -- one attached now (World.attach), as the body's
    dict took any key."""
    mods = [m for m in (b.find(interfaces.SpecialPower) if b.modules else ()) if m.power() == power]
    if not mods:
        mods = [world.world.attach(b, 'SpecialPower', head=f'SpecialPowerTemplate="{power}"')]
    for m in mods:
        m.set_ready_at(frame)

# A script's superweapon at a waypoint: [(frames after the cast, [(centre distance, damage)])], nothing past the last
# distance. Proton collider: bench 2026-11-07 engine_super p / q (base defenses of 1000 at 0 / 150 / 240 / 300): the
# first hit 56 frames after the cast (+-1), the others in rows ~7 frames apart (INFERRED +15 / +45); the one at 300
# untouched (XML Radius 250); the centre hit once only (the beams sweep: not a taper, not modelled further).
SUPERWEAPON_HITS = {
    'SpecialPowerParticleCannon': [
        (56, [(0.0, 560.0), (150.0, 500.0), (240.0, 390.0), (250.0, 390.0)]),
        (71, [(0.0, 0.0), (150.0, 440.0), (240.0, 340.0), (250.0, 340.0)]),
        (101, [(0.0, 0.0), (150.0, 0.0), (240.0, 150.0), (250.0, 150.0)]),
    ],
    # Vacuum Imploder: engine_super v / w (base defenses at 0 / 150 / 280 / 350): the first loss 62 frames after the cast
    # (the 4 s seed), then gradual in rows ~7 frames apart (~16 % / 11 % / 8 % a row) until 5 / 1 / 1 % are left (the
    # centre after 6 rows, 150 after 9, 280 after ~13); 350 untouched (XML Radius 300). Rows of 7 frames: INFERRED.
    'SpecialPowerVacuumBomb': [
        (62 + 7 * k, [(0.0, 158.0 if k < 6 else 0.0), (150.0, 110.0 if k < 9 else 0.0), (280.0, 76.0), (300.0, 76.0)])
        for k in range(13)
    ],
    # Psionic Decimator (the Empire's): engine_super d / e (base defenses of 1000 at 0 / 150 / 250 / 350): all within 250
    # dead 61 frames after the cast, 350 whole (XML: 4 s, damage 2000, radius 300 -- one hit, flat inside, INFERRED).
    'SpecialPowerTelekineticProjectorDevice': [(61, [(0.0, 2000.0), (300.0, 2000.0)])],
}
# Iron Curtain: engine_super j -- a scripted cast keeps tanks at 0 and 150 from the waypoint whole against enemy fire for
# ~355 frames (the 20 s modifier + the 3 s effect); NAMED_DAMAGE goes through (i). XML: vehicles and structures, aura
# 100, yet g / a (each tank shot by one enemy of its own, NAMED_ATTACK_NAMED, open ground): tanks at 100 / 300 / 500 /
# 800 whole till ~354, at 850 / 950 / 1050 / 1150 hit from frame ~20 -- the reach between 800 and 850 (800 taken; k / l /
# m / o / s were muddled by the enemies picking other targets).
# Nanoswarm Hive: engine_super n -- tanks at 0 and 150 untouched by enemy fire 497+ frames (the run's end), 250 hit from
# frame ~27 (XML radius 200, IN_STASIS 20 s; the end of the stasis not seen -- INFERRED 497); NAMED_DAMAGE goes through.
# Name -> (reach by centre, frames, kinds covered or None for all).
# Frames a superweapon's script cast takes over its ReloadTime before it is ready again: engine_super f -- the proton
# collider ready 5550 frames after the cast (ReloadTime 360 s = 5400; the 150 maybe the cast's own delay: INFERRED,
# the others not measured).
RELOAD_LAG = {'SpecialPowerParticleCannon': 150}
# The skirmish AI's own player powers (engine.ai.core Brain.player_powers): LogicCommand -> its bomb. Precision strike,
# bench aicrush1t / aicrush1g / airevkh: every Allied AI buys the protocol f11, casts f166 (cmd 1ff), the bomb lands 46
# frames on -- 575 EXPLOSIVE within 50 of the aim (centre to centre: guards 60 off untouched, 40 off dead), its
# ALLIES ENEMIES NEUTRALS, x 0.33 on a STRUCTURE (CampaignOverrides: 575 x 1.25 x 0.33 = 237.2 off the plant, read
# 762.8 / 1000). `ready`: frames after the AI's start it can first fire (INFERRED: the bench pins it to 107..121 by
# the f166 cast, 15-frame passes and READY_LAG 45); `needs`: the structure SpecialPowerTemplates names (its yard).
AI_POWERS = {'Command_PrecisionStrike': dict(power='SpecialPowerPrecisionStrike', needs='AlliedConstructionYard',
                                             ready=120, reload=3600, after=46, damage=575.0, type='EXPLOSIVE',
                                             radius=50.0, affects='ALLIES ENEMIES NEUTRALS', structure=0.33)}
CURTAIN = {'SpecialPowerIronCurtain': (800.0, 355, {'VEHICLE', 'STRUCTURE'}),
           'SpecialPowerNanoSwarmHive': (200.0, 497, None)}


def hit_at(table, d):
    """The damage of one hit's table at centre distance `d`: linear between its distances, 0 past the last."""
    if d > table[-1][0]:
        return 0.0
    for (d0, v0), (d1, v1) in zip(table, table[1:]):
        if d <= d1:
            return v0 + (v1 - v0) * (d - d0) / (d1 - d0) if d1 > d0 else v1
    return table[-1][1]


UNPACK_POWER = 'SpecialPower_UnpackReplaceSelf'     # the deploy buttons' power (LogicCommand.xml: MCVs, eggs, miner)
PACK_POWER = 'SpecialPower_PackReplaceSelf'         # a construction yard's pack button (Command_Pack...MCV)
PACK_FRAMES = 0                # the yard is its MCV from the press frame on (engine_pack a / s / j)
