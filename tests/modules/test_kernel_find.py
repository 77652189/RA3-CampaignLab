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
