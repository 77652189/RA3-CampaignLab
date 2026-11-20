"""The nugget handlers' register (engine/combat/registry.py, step N1): order is registry.ORDER only."""
import types

import pytest
from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import engine.combat  # noqa: E402,F401  (registers the handlers)
from engine.combat import registry  # noqa: E402


def _weapon(**extra):
    return dict(dmg=10.0, type='CANNON', **extra)


def test_effects_follow_order_not_the_weapons_field_order():
    line = dict(dynamic=True, width=1, lead=0, out=0)
    a = dict(_weapon(), projectile='Shell', line=line)
    b = dict(reversed(list(a.items())))
    assert [k for k, _ in registry.effects(a)] == [k for k, _ in registry.effects(b)] == \
        ['Projectile', 'LineDamage', 'Damage']
    assert [k for k, _ in registry.effects(_weapon())] == ['Damage']     # a zero-field weapon still deals its dmg


def test_a_direct_hit_books_the_dot_then_the_passengers_the_cold_the_suppression_and_the_emp(monkeypatch):
    """Step N2b: the 'hit' phase runs DOT -> DamageContained -> SecondaryDamage -> Suppression -> Paralyze, whatever
    the weapon's field order, and only those (no launch, aim or victim handler)."""
    contained = [dict(damage=5.0, type='CANNON', maximum=1, include=[], exclude=[])]
    w = dict(reversed(list(dict(_weapon(), emp_seconds=[2.0], suppression=[(30.0, 40.0, 1.0)], sd=3.0,
                                contained=contained, dot=[dict(damage=1.0)], projectile='Shell',
                                line=dict(dynamic=False)).items())))
    hits = ['DOT', 'DamageContained', 'SecondaryDamage', 'Suppression', 'Paralyze']
    effects = registry.effects(w)
    assert [k for k, _ in effects] == ['Projectile', *hits, 'LineDamage', 'Damage']
    seen = []

    class Recorder:
        def __init__(self, kind, phase):
            self.kind, self.phase = kind, phase

        def apply(self, context, payload):
            seen.append(self.kind)

    monkeypatch.setattr(registry, '_HANDLERS', {k: Recorder(k, h.phase) for k, h in registry.HANDLERS.items()})
    assert registry.run('hit', types.SimpleNamespace(effects=effects)) is False
    assert seen == hits


def test_a_victim_takes_its_damage_then_the_leech_claims_then_the_strip():
    """Step N2: a victim's effects run Damage -> LeechPercentMaxHealth -> LeechHealth -> StripMaxHealthPercent."""
    w = dict(reversed(list(dict(_weapon(), strip_max_health=[(0.1, 'CANNON')], leech_health=0.5,
                                leech_percent=0.2).items())))
    assert [k for k, _ in registry.effects(w)] == \
        ['Damage', 'LeechPercentMaxHealth', 'LeechHealth', 'StripMaxHealthPercent']
    assert dict(registry.effects(w))['LeechHealth'] == (0.5, 10.0, 'CANNON')


def test_registration_order_does_not_decide_the_run(monkeypatch):
    """Registered the other way round, the same effects run in the same order."""
    handlers = dict(registry.HANDLERS)
    monkeypatch.setattr(registry, '_HANDLERS', dict(reversed(list(handlers.items()))))
    w = dict(_weapon(), projectile='Shell', line=dict(dynamic=False))
    assert [k for k, _ in registry.effects(w)] == ['Projectile', 'LineDamage', 'Damage']


def test_a_kind_registers_once_and_only_under_its_order_pair(monkeypatch):
    monkeypatch.setattr(registry, '_HANDLERS', dict(registry.HANDLERS))
    with pytest.raises(ValueError, match='twice'):
        registry.nugget('Damage', 'victim')(type('Again', (), {}))
    with pytest.raises(ValueError, match='ORDER'):
        registry.nugget('Damage', 'launch')(type('Wrong', (), {}))


def test_run_stops_at_a_launch_that_takes_the_hit_over(monkeypatch):
    seen = []

    class Taker:
        phase = 'launch'

        def payload(self, w):
            return 1

        def apply(self, context, payload):
            seen.append('launch')
            return True

    monkeypatch.setattr(registry, '_HANDLERS', {**registry.HANDLERS, 'Projectile': Taker()})
    ctx = types.SimpleNamespace(effects=[('Projectile', 1), ('Damage', (1.0, 'CANNON'))])
    assert registry.run('launch', ctx) is True and seen == ['launch']


def test_accumulate_keeps_the_first_attacker_and_the_insertion_order():
    hurt = {}
    a, b = types.SimpleNamespace(serial=2), types.SimpleNamespace(serial=1)
    registry.accumulate(hurt, a, 1.0, 'x')
    registry.accumulate(hurt, b, 0.0, 'y')
    registry.accumulate(hurt, a, 2.0, 'z')
    assert list(hurt) == [2, 1] and hurt[2] == [a, 3.0, 'x'] and hurt[1] == [b, 0.0, 'y']
