"""The template data port (docs/engine/sim-modules.md 3, 6): the helpers a module's data class reads its XML block
with. The port itself -- blocks(template, tag) -> [(attributes text, inner text)], from the nearest template up the
inheritance chain that has the tag -- is handed to World by its host (today Sim: simunits.module_blocks); step P moves
simunits' readers behind it. attr / num / secs are simunits' _attr / _num / _secs, kept there for its own readers
until then."""
import re


def attr(head, name, default=None):
    """An attribute of a block's attributes text, else `default`."""
    m = re.search(rf'\b{name}="([^"]*)"', head)
    return m.group(1) if m else default


def words(head, name, default=''):
    """An attribute's space-separated words, a frozenset: `default`'s words when the attribute is not written, none
    when it is written empty -- DeathTypes="" takes no death, as simunits._dies_of read it (review h P3)."""
    v = attr(head, name)
    return frozenset((default if v is None else v).split())


def num(v, default=0.0):
    """A number attribute; a macro (=$UNLIMITED_CLIP_SIZE ...) or nothing: the default."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def secs(v):
    """A duration attribute ('0.5s') in seconds; nothing: 0."""
    return num(v.rstrip('s')) if v else 0.0


def names(head, inner, name):
    """The names a block lists under `name`: an attribute (space-separated) and child elements
    (<TriggeredBy>X</TriggeredBy>, several allowed)."""
    found = set((attr(head, name) or '').split())
    for text in re.findall(rf'<{name}>([^<]*)</{name}>', inner or ''):
        found |= set(text.split())
    return frozenset(found)


def child(inner, tag):
    """The attributes text of a block's first <tag ...> child element; '' when none."""
    m = re.search(rf'<{tag}\b([^>]*?)/?>', inner or '')
    return m.group(1) if m else ''


def blocks(text, tag):
    """(attributes text, inner text) of every <tag ...>...</tag> (or self-closed) element of a block's inner text:
    the nested blocks (a toggle's ToggleStates). simunits._blocks, kept there for its own readers until step P."""
    for m in re.finditer(rf'<{tag}\b(.*?)(/>|>(.*?)</{tag}>)', text or '', re.S):
        yield m.group(1), m.group(3) or ''
