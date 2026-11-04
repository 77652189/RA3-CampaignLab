"""The music maps' builds. The mission modules themselves (music_bench, music_dyn, music_route) pull in
experimental/music, which no other build needs, so they declare nothing and are imported only when one of these
builds is made (registry.py reads a module's source for a top-level MISSION, it does not import the rest)."""
import importlib


def _music_bench(name='music_bench'):
    return importlib.import_module(f'missions.{name}')


# the builds this module makes (cnv/registry.py): build name -> mission factory
MISSION = {
    'music': lambda: _music_bench().mission(),
    'musicdyn': lambda: _music_bench('music_dyn').mission(),
    'musicdynspy': lambda: _music_bench('music_dyn').mission(name='CampMusDynS', spy=True),
    'musicdyntr': lambda: _music_bench('music_dyn').mission(name='CampMusDynT', tracer=True),
    'musicroute': lambda: _music_bench('music_route').mission(),
    'musicrouteswap': lambda: _music_bench('music_route').mission(name='CampMusRouteW', swap=True),
    'musicroutecover': lambda: _music_bench('music_route').mission(name='CampMusRouteC', cover=True),
}
