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


def num(v, default=0.0):
    """A number attribute; a macro (=$UNLIMITED_CLIP_SIZE ...) or nothing: the default."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def secs(v):
    """A duration attribute ('0.5s') in seconds; nothing: 0."""
    return num(v.rstrip('s')) if v else 0.0
