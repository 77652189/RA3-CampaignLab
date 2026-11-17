"""Four isolated infiltration lanes, with open water for the naval lane."""
import make_campnew18 as c18
import platmap
import platprops
from platmap import Layout, poly
from maps import island
from parts import Site

SITES = dict(island.SITES)
for name, x, y in (('air', 800, 400), ('infantry', 2300, 400),
                   ('ship', 3800, 3400), ('port', 800, 1800)):
    SITES[name] = Site(x, y, 100, 'retail infiltration host')
    SITES[name + ' friend'] = Site(x + 500, y, 100, 'friendly refusal control')
for name, x, y in (('air marker', 2300, 1800), ('infantry marker', 2300, 2700),
                   ('ship marker', 3800, 4700), ('ship wrong', 3800, 2200),
                   ('port marker', 800, 2300), ('port far', 800, 4400)):
    SITES[name] = Site(x, y, 50, 'discovery control outside the entry spy vision')
PLAYERS, TEAMS = island.PLAYERS, island.TEAMS
_LAYOUT = Layout(shapes=[
    poly([(-300, -300), (5300, -300), (5300, 3050), (-300, 3050)], 1, 'land lanes'),
    poly([(-300, 3100), (5300, 3100), (5300, 5300), (-300, 5300)], 0, 'naval lane')])


def terrain(m):
    c18.generate(m)
    previews, _ = platmap.apply(m, _LAYOUT)
    c18.PREVIEWS.update(previews)


def ground():
    w, h, b = platmap.CONTAINER
    e, _ = platmap.heights(_LAYOUT, w, h, b)
    return platprops.Ground(e=e)


like = island.like
