"""The factory (docs/engine/sim-modules.md 3): XML module tag -> module class, filled at import by @module and read
through the read-only TAGS. A thing's modules are made from its template's blocks of the registered tags; a block's
data is parsed once a world (World.data, by template, tag and index)."""
import types

from engine.kernel import module as _module

_TAGS = {}
TAGS = types.MappingProxyType(_TAGS)


def module(*tags):
    """Class decorator: register a Module class under one or more XML tags (at import, a module file's top level)."""
    def register(cls):
        if not (isinstance(cls, type) and issubclass(cls, _module.Module)):
            raise TypeError(f'{cls!r} is not a Module class')
        for tag in tags:
            if tag in _TAGS:
                raise ValueError(f'{tag} is registered twice ({_TAGS[tag].__name__}, {cls.__name__})')
            _TAGS[tag] = cls
        cls.TAGS = tuple(tags)
        return cls
    return register


def align(tags=TAGS):
    """The registered module classes' ALIGN lines in one dict (sim.ALIGN takes them: a new family writes its
    assumptions in its own file, no centre file changes)."""
    out = {}
    for cls in tags.values():
        out.update(cls.ALIGN)
    return out


def build(thing, blocks, data, tags=TAGS, world=None):
    """The modules of a thing: for each registered tag, one instance per block of it in the template.
    blocks(template, tag) -> [(head, inner)] (the template data port); data: the world's parse cache
    {(template, tag, index): ModuleData}; tags: the registry (a test passes its own); world: the World the modules
    live in (Module.world)."""
    out = []
    for tag, cls in tags.items():
        for k, (head, inner) in enumerate(blocks(thing.template, tag)):
            key = (thing.template, tag, k)
            if key not in data:
                data[key] = cls.DATA.parse(head, inner).seal()
            out.append(cls(thing, data[key], world))
    return tuple(out)
