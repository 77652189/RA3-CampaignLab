import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
from engine.kernel import interfaces, module, world  # noqa: E402


class DamageModule(module.Module, interfaces.Damage):
    pass


class BodyModule(module.Module, interfaces.Body):
    pass


def test_kernel_find_after_attach():
    thing = module.Thing()
    kernel = world.World(tags={'Damage': DamageModule})
    first = kernel.attach(thing, 'Damage')
    assert thing.find(interfaces.Damage) == (first,)

    second = kernel.attach(thing, 'Damage')
    assert thing.find(interfaces.Damage) == (first, second)


def test_kernel_find_after_replacing_modules():
    thing = module.Thing()
    first, second = DamageModule(thing, None), DamageModule(thing, None)
    thing.modules = (first,)
    assert thing.find(interfaces.Damage) == (first,)

    thing.modules = (second,)
    assert thing.find(interfaces.Damage) == (second,)
    assert vars(thing) == {'modules': (second,)}

    thing.modules = ()
    assert thing.modules == thing.find(interfaces.Damage) == ()
    assert not vars(thing)


def test_kernel_find_rejects_two_one_modules():
    thing = module.Thing()
    kernel = world.World(tags={'Body': BodyModule})
    assert thing.find(interfaces.Body) is None
    first = kernel.attach(thing, 'Body')
    assert thing.find(interfaces.Body) is first

    kernel.attach(thing, 'Body')
    with pytest.raises(ValueError, match='^Body: 2 modules on one thing$'):
        thing.find(interfaces.Body)


def test_kernel_find_copies_mutable_module_list():
    thing = module.Thing()
    first, second = DamageModule(thing, None), DamageModule(thing, None)
    modules = [first]
    thing.modules = modules
    assert thing.find(interfaces.Damage) == (first,)

    modules[0] = second
    assert thing.modules == thing.find(interfaces.Damage) == (first,)

    thing.modules = modules
    assert thing.modules == thing.find(interfaces.Damage) == (second,)


def test_kernel_find_forwards_reuse_lookup_and_read_live_state(monkeypatch):
    class Forwarded(module.Thing):
        hp = module.forward(interfaces.Body, lambda m: m.hp, 100.0)
        damage_sources = module.forward(interfaces.Damage, lambda ms: tuple(m.source for m in ms), ('default',))

    calls = []
    find = module.Thing.find

    def count_find(thing, interface):
        calls.append(interface)
        return find(thing, interface)

    monkeypatch.setattr(module.Thing, 'find', count_find)
    thing = Forwarded()
    first, second = BodyModule(thing, None), BodyModule(thing, None)
    ear_a, ear_b = DamageModule(thing, None), DamageModule(thing, None)
    first.hp, second.hp = 12, 34
    ear_a.source, ear_b.source = 'a', 'b'

    assert (thing.hp, thing.damage_sources) == (100.0, ('default',))
    thing.modules = (first, ear_b, ear_a)
    assert thing.find(interfaces.Body) is first
    assert (thing.hp, thing.damage_sources) == (12, ('b', 'a'))
    first.hp = 10
    assert (thing.hp, thing.damage_sources) == (10, ('b', 'a'))
    assert calls == [interfaces.Body, interfaces.Damage]
    with pytest.raises(AttributeError, match='has no setter'):
        thing.hp = 0

    thing.modules = (second,)
    assert (thing.hp, thing.damage_sources) == (34, ('default',))
    thing.modules = (ear_a,)
    assert (thing.hp, thing.damage_sources) == (100.0, ('a',))
    thing.modules = ()
    assert (thing.hp, thing.damage_sources) == (100.0, ('default',))
    assert vars(thing) == {}
