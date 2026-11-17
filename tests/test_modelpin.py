"""ADR 0030 item 1: the private engine model loads only at the commit experimental/cnv/inventory_model.rev pins
(modelpin.check). sim.engine_model, and simproxy._package (simai.model and simproxy.proxy load through it), refuse
any other HEAD with both commit ids and how to fix it; a clean clone without the model is not checked."""
import os
import subprocess

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import labpaths  # noqa: E402
import modelpin  # noqa: E402
import sim  # noqa: E402
import simproxy  # noqa: E402


def _git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, check=True).stdout.strip()


def _model(tmp_path):
    """A one-commit git checkout holding the files the loaders look for; returns (root, its HEAD)."""
    root = tmp_path / 'RA3-EngineModel'
    for rel in ('ra3model/__init__.py', 'ra3model/scripts.py', 'ra3model/ai/player.py',
                'ra3model/proxy/world.py'):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text('raise AssertionError("the pin check runs before the model loads")\n')
    _git(tmp_path, 'init', '-q', str(root))
    _git(root, 'add', '-A')
    _git(root, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-q', '-m', 'm')
    return root, _git(root, 'rev-parse', 'HEAD')


def _rev(tmp_path, rev):
    f = tmp_path / f'{rev[:12]}.rev'
    f.write_text(rev + '\n', encoding='utf-8')
    return str(f)


def _one_off(rev):
    return rev[:-1] + ('0' if rev[-1] != '0' else '1')


def test_the_pinned_head_loads_and_one_digit_off_stops_with_both_commits(tmp_path):
    root, head = _model(tmp_path)
    modelpin.check(str(root), _rev(tmp_path, head))                  # the pinned commit: no error
    wrong = _one_off(head)
    with pytest.raises(modelpin.ModelPinError) as e:
        modelpin.check(str(root), _rev(tmp_path, wrong))
    assert head in str(e.value) and wrong in str(e.value) and 'inventory_ai.py pin' in str(e.value)


def test_a_model_folder_that_is_no_git_checkout_stops(tmp_path):
    (tmp_path / 'plain').mkdir()
    with pytest.raises(modelpin.ModelPinError):
        modelpin.check(str(tmp_path / 'plain'), _rev(tmp_path, 'f' * 40))


def test_the_simulator_and_the_ai_loaders_ask_the_pin_before_loading(tmp_path, monkeypatch):
    root, head = _model(tmp_path)
    monkeypatch.setattr(modelpin, 'REV_FILE', _rev(tmp_path, _one_off(head)))
    monkeypatch.setattr(labpaths, 'ENGINE_MODEL', str(root))
    with pytest.raises(modelpin.ModelPinError):
        sim.engine_model()
    with pytest.raises(modelpin.ModelPinError):
        simproxy._package(os.path.join(str(root), 'ra3model'))


def test_the_pin_file_names_one_full_commit():
    rev = modelpin.pinned()
    assert len(rev) == 40 and int(rev, 16) >= 0
