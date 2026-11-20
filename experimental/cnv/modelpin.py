r"""The private engine model pinned by version (ADR 0030 item 1): the simulator (sim.engine_model) and the AI and the
proxy player (package, which simai.model and simproxy.proxy load through) refuse to load RA3-EngineModel
unless its HEAD is the commit experimental/cnv/inventory_model.rev names. One public commit then fixes the model the
simulator runs, so a bisect, a full run and the refactor's frame-by-frame record compare like with like (11-17: the
B228 public commit read red against a model checkout that was another commit).

Where the model is not on this computer (a clean clone) nothing is checked: the simulator runs without it
(model=False) as before. CNV_ENGINE_MODEL (labpaths.ENGINE_MODEL) pointing at another model worktree is checked the
same way. Only HEAD is compared: uncommitted edits in the model's working tree are not looked at.
"""
import importlib.util
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REV_FILE = os.path.join(HERE, 'inventory_model.rev')
_SEEN = {}


class ModelPinError(RuntimeError):
    """The model on disk is not the pinned commit: stop rather than run another version quietly."""


def pinned(rev_file=REV_FILE):
    """The full commit id inventory_model.rev pins."""
    with open(rev_file, encoding='utf-8') as f:
        return f.read().split()[0]


def head(root):
    """The model checkout's HEAD commit, or None where root is not a git checkout (or git is not there)."""
    try:
        r = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def message(root, want, got, rev_file=REV_FILE):
    rel = os.path.relpath(rev_file, os.path.dirname(os.path.dirname(HERE)))
    return (f'私有引擎模型版本不对（ADR 0030）：{root} 的 HEAD 是 {got or "（不是 git 工作区）"}，'
            f'公开仓库 {rel} 钉的是 {want}。\n'
            f'  只是模型落后：git -C "{root}" pull --ff-only（不在 main 上或超前了：'
            f'git -C "{root}" fetch origin && git -C "{root}" checkout {want}）\n'
            f'  你改了模型、要用新版本：模型提交推送后在公开仓库跑 '
            f'python -I -X utf8 experimental/cnv/inventory_ai.py pin（或 pin <提交号>），'
            f'把 {rel} 和用到它的公开改动一起提交推送。\n'
            f'  用别的模型工作区：设 CNV_ENGINE_MODEL，那个工作区的 HEAD 同样要等于钉住的提交。')


def check(root, rev_file=REV_FILE):
    """Raise ModelPinError unless the model checkout at root is at the pinned commit. Each (root, pin) is asked of
    git once per process; a refusal is raised again on every later load."""
    root = os.path.abspath(root)
    want = pinned(rev_file)
    key = (os.path.normcase(root), want)
    if key not in _SEEN:
        got = head(root)
        _SEEN[key] = None if got == want else message(root, want, got, rev_file)
    if _SEEN[key]:
        raise ModelPinError(_SEEN[key])


def package(folder):
    """The engine model's ra3model package, loaded by file as sim.engine_model does (nothing added to sys.path, guard
    G4): its submodules then import by name through the package's own path. Only the commit inventory_model.rev
    pins loads (check, ADR 0030): simai.model and simproxy.proxy come through here (R3 13f-2d: moved from
    simproxy, so the skirmish AI, a layered module, loads its model without importing the proxy player)."""
    check(os.path.dirname(os.path.abspath(folder)))
    if 'ra3model' in sys.modules:
        return sys.modules['ra3model']
    spec = importlib.util.spec_from_file_location('ra3model', os.path.join(folder, '__init__.py'),
                                                  submodule_search_locations=[folder])
    mod = importlib.util.module_from_spec(spec)
    sys.modules['ra3model'] = mod
    spec.loader.exec_module(mod)
    return mod
