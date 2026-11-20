from types import SimpleNamespace

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.testing.small import small_world  # noqa: E402

BODY = '<Body><ActiveBody MaxHealth="100"/></Body>'
LIFETIME = '<LifetimeUpdate MinLifetime="2s" MaxLifetime="2s"/>'
DEATH_WEAPON = '<FireWeaponWhenDead InitiallyActive="true" DeathWeapon="ScheduleBurst"/>'
BURST = (
    '<WeaponTemplate id="ScheduleBurst" RadiusDamageAffects="ALLIES ENEMIES NEUTRALS">'
    '<Nuggets><DamageNugget Damage="100" DamageType="UNRESISTABLE" Radius="10"/></Nuggets></WeaponTemplate>'
)


def _template(name, behaviors):
    return (f'<GameObject id="{name}" KindOf="INFANTRY">{BODY}'
            f'<Behaviors>{behaviors}</Behaviors></GameObject>')


def test_same_frame_death_weapons_keep_creation_order_after_named_rebuilds():
    s = small_world(model=False)
    s.own.update(ScheduleTimed=_template('ScheduleTimed', LIFETIME),
                 ScheduleBomb=_template('ScheduleBomb', LIFETIME + DEATH_WEAPON) + BURST,
                 SchedulePlain=_template('SchedulePlain', ''))
    s.waypoints['BlastSite'] = (1000., 1000.)
    script = SimpleNamespace(name='ScheduleOrder')

    def make(name, template, player):
        s.act('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', [name, template, f'{player}/Schedule', 'BlastSite'], script)

    for name in ('X', 'Y'):
        make(name, 'ScheduleTimed', 'Player_1')
    make('B', 'ScheduleBomb', 'Player_1')
    make('Victim', 'SchedulePlain', 'Player_3')
    for name in ('X', 'Y'):
        s.act('NAMED_DELETE', [name], script)
        make(name, 'SchedulePlain', 'Player_1')
    make('C', 'ScheduleBomb', 'Player_2')

    # INFERRED: the engine's order is unmeasured; the counter keeps creation order.
    assert s.bodies['B'].life_end == s.bodies['C'].life_end == 30
    s.clock.frame, s.t = 30, 2.0
    s.world.schedule.run('expire', 30)
    assert [(blast[0], blast[8].name) for blast in s.death_blasts] == [(30, 'B'), (30, 'C')]
    s.death_blast_due(30)
    assert [kill for kill in s.kills if kill[3] == 'Victim'] == [('Player_1', 'B', 'SchedulePlain', 'Victim')]
