"""The XML object modules (docs/engine/sim-modules.md 7): one file a family, each class registered under its tags
with @factory.module. A module file imports only the kernel, engine.ports.templates and the standard library.

Importing this package imports every module file in it (by name, so the registry's order is the same every run):
a new family is its file here and nothing else -- no centre file names it (step K1.5). Only files of this folder,
relative to it (tests/test_kernel.py rule 6 lets import_module through in this one shape)."""
import importlib
import pkgutil

for _info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
    importlib.import_module('.' + _info.name, __name__)
del _info
