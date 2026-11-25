"""TrackDamage (SovietMiner: TimeToTrack 2s, InstantWeaponsOnly): the look-behind of Damage.expected_damage.
Bench: benches/weapon/target_effects/readings.toml#engine_inform_ai (inform_ai_track_damage_keeps_the_instant_hit...)."""

HIT = ('<WeaponTemplate id="SampleHit"><Nuggets><DamageNugget Damage="100" DamageType="UNRESISTABLE"/>'
       '</Nuggets></WeaponTemplate>')


def test_an_instant_hit_is_kept_for_time_to_track(weapon_world):
    s, fire = weapon_world
    gun = s.add('gun', 'SovietAntiVehicleVehicleTech1', 'Player_1', 1250, 2500)
    miner = s.add('miner', 'SovietMiner', 'Soviet_1', 1350, 2500)
    fire(HIT, miner, gun)
    f, lost = s.frame_now(), miner.max_hp - miner.hp            # the applied loss (flank scalar and all)
    assert lost > 0 and s.expected_damage(miner, 2, 0, now=f + 29) == lost     # 2 s = 30 frames: age 29 in, 30 out
    assert s.expected_damage(miner, 2, 0, now=f + 30) == 0
    assert s.expected_damage(miner, 3, 0, now=f + 30) == 0       # TimeToTrack caps a longer look
    assert s.expected_damage(miner, 1, 0, now=f + 15) == 0       # the micro's shorter window
    assert s.expected_damage(miner, 0, 0, now=f) == 0
    fire(HIT, gun, miner)                                        # no TrackDamage on the gun: nothing kept
    assert gun.hp < gun.max_hp and s.expected_damage(gun, 2, 0) == 0


def test_a_shell_is_not_an_instant_weapon(weapon_world):
    s, fire = weapon_world
    gun = s.add('gun', 'SovietAntiVehicleVehicleTech1', 'Player_1', 1250, 2500)
    miner = s.add('miner', 'SovietMiner', 'Soviet_1', 1350, 2500)
    weapon = fire(HIT, miner, gun, shots_due=lambda *_: 0)
    s.queue_projectile_hit(s.frame_now(), miner, 150, gun, weapon)
    s.volleys = []
    s.deal(1 / 15)
    assert miner.hp < miner.max_hp
    assert s.expected_damage(miner, 2, 0) == 0
