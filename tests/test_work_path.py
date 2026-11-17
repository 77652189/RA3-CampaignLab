"""WORK (the big local folder): a line's worktree next to the main checkout uses the main checkout's work\\, and
CNV_WORK overrides it, so no directory junction is needed (a junction + recursive delete wiped work\\ on 2026-11-10)."""
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
    'experimental/simui/game.py': "VOICE_LINE points into RA3-ChineseVoice\\work (other repo)",
    'demo/voice_snapshot.py': 'ships standalone inside the demo zip, which does not carry labpaths.py; keeps the CNV_WORK expression inline',
    'experimental/outsource/codex_task.py': "bench_dirs() names the MAIN checkout's work (LAB/RA3-CampaignLab/work) as a writable dir for the Codex sandbox on purpose; CNV_WORK still overrides",
    'tests/test_work_path.py': 'this file spells the patterns',
}
HAND = re.compile(r"""os\.path\.join\([^\n]*?,\s*['"]work['"]|['"]work['"]\s*/|/\s*['"]work['"]""")


def _work_for(monkeypatch, root, main):
    monkeypatch.delenv('CNV_WORK', raising=False)
    monkeypatch.setattr(labpaths, 'ROOT', str(root))
    monkeypatch.setattr(labpaths, 'MAIN', str(main))
    return labpaths._work()


def test_main_checkout_uses_its_own_work(monkeypatch, tmp_path):
    main = tmp_path / 'RA3-CampaignLab'
    (main / 'work').mkdir(parents=True)
    assert _work_for(monkeypatch, main, main) == str(main / 'work')


def test_line_worktree_without_work_uses_the_main_checkouts(monkeypatch, tmp_path):
    main, line = tmp_path / 'RA3-CampaignLab', tmp_path / 'RA3-CampaignLab-codexe'
    (main / 'work').mkdir(parents=True)
    line.mkdir()
    assert _work_for(monkeypatch, line, main) == str(main / 'work')


def test_line_worktree_with_its_own_work_keeps_it(monkeypatch, tmp_path):
    main, line = tmp_path / 'RA3-CampaignLab', tmp_path / 'RA3-CampaignLab-codexc'
    (main / 'work').mkdir(parents=True)
    (line / 'work').mkdir(parents=True)
    assert _work_for(monkeypatch, line, main) == str(line / 'work')


def test_other_folder_names_keep_root_work(monkeypatch, tmp_path):
    main, other = tmp_path / 'RA3-CampaignLab', tmp_path / 'agent-x'
    (main / 'work').mkdir(parents=True)
    other.mkdir()
    assert _work_for(monkeypatch, other, main) == str(other / 'work')


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
            if HAND.search(line) or "environ.get('CNV_WORK')" in line:
                bad.append(f'{f}:{n}: {line.strip()[:120]}')
    assert not bad, 'build the work path from labpaths.WORK / CNV_WORK:\n' + '\n'.join(bad)
