"""WORK (the big local folder) can be redirected with CNV_WORK, so a git worktree reads the main checkout's
work\\ without a directory junction (a junction + recursive delete wiped work\\ on 2026-11-10)."""
import importlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import labpaths  # noqa: E402

# Files allowed to spell out a 'work' folder by hand, each with the reason.
ALLOW = {
    'experimental/campaign/labpaths.py': 'the one definition',
    'experimental/voice/pack.py': "VOICE is the other repository (RA3-ChineseVoice); its work\\ is not this repo's WORK",
    'experimental/simui/game.py': "VOICE_LINE points into RA3-ChineseVoice\\work (other repo); the REPO/work line uses CNV_WORK",
    'tests/test_work_path.py': 'this file spells the patterns',
}
HAND = re.compile(r"""os\.path\.join\([^\n]*?,\s*['"]work['"]|['"]work['"]\s*/|/\s*['"]work['"]""")


def test_default_is_root_work(monkeypatch):
    monkeypatch.delenv('CNV_WORK', raising=False)
    try:
        importlib.reload(labpaths)
        assert labpaths.WORK == os.path.join(labpaths.ROOT, 'work')
    finally:
        importlib.reload(labpaths)


def test_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv('CNV_WORK', str(tmp_path))
    try:
        importlib.reload(labpaths)
        assert labpaths.WORK == str(tmp_path)
    finally:
        monkeypatch.undo()
        importlib.reload(labpaths)


def test_no_hand_built_work_path():
    files = subprocess.run(['git', 'ls-files', '*.py'], cwd=ROOT, capture_output=True, text=True,
                           check=True).stdout.split()
    bad = []
    for f in files:
        if f in ALLOW:
            continue
        for n, line in enumerate((ROOT / f).read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if HAND.search(line) and 'CNV_WORK' not in line:
                bad.append(f'{f}:{n}: {line.strip()[:120]}')
    assert not bad, 'build the work path from labpaths.WORK / CNV_WORK:\n' + '\n'.join(bad)
