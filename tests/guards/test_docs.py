"""Guard the public document set, ADR index, contribution rules, music constraints and plan authority."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOCS = ROOT / 'docs'
ADR = DOCS / 'adr'

ROOT_DOCS = {'README.md', 'AGENTS.md'}
WORKFLOW_ROOT_DOCS = {'HANDOFF.md', 'CLAUDE.md'}
ACTIVE_DOCS = {'architecture.md', 'issues.md', 'plan.md', 'requirements.md'}

ENGINE_DOCS = {'script-semantics.md', 'know-how.md', 'terrain.md', 'pathing.md', 'upgrades.md', 'spawn.md', 'air.md', 'aircraft.md',
               'missile.md', 'weapons.md', 'garrison.md', 'stealth.md',
               'production.md', 'mining.md', 'construction.md', 'specialpower.md', 'sell.md', 'heal.md', 'stance.md', 'transform.md', 'vision.md', 'runoffmap.md', 'teleport.md', 'crush.md', 'aiopen.md', 'aistate.md', 'aispecial.md', 'aimicro.md', 'aitactics.md', 'ainamed.md', 'aiswitches.md', 'aiteamstate.md', 'uprising-gap.md', 'weaponset.md', 'sim-layers.md', 'sim-modules.md', 'testing.md'}   # reverse-engineering notes stay in work/re/ (repo is public)
# generated on demand by experimental/cnv/inventory.py, inventory_levels.py --write, inventory_ai.py levels --write;
# gitignored, never committed (ADR 0030): in docs/engine only when this checkout generated them
GENERATED_ENGINE_PAGES = {'inventory.md', 'inventory-levels.md', 'inventory-levels-a.md'}
PLAN_MAX_KB = 40       # status only (2026-10-28 it was 115 KB of history and know-how: archive/, engine/)


def _md(root):
    assert root.is_dir(), f'扫描目标不存在，测试会静默通过：{root}'
    return {p.name for p in root.glob('*.md') if p.is_file()}


def test_root_docs_are_the_reviewed_set():
    assert _md(ROOT) - WORKFLOW_ROOT_DOCS == ROOT_DOCS


def test_docs_folder_is_the_reviewed_set():
    assert _md(DOCS) == ACTIVE_DOCS


MUSIC_DOCS = {'handoff.md'}
MUSIC_HARD_CONSTRAINTS = [
    '靠自己做出来的才是可靠的',
    '符合剧情和情景',
    '紧张（处于劣势）和激烈（处于优势）',
]


def test_music_docs_are_the_reviewed_set():
    assert _md(DOCS / 'music') == MUSIC_DOCS


def test_music_hard_constraints_present_in_its_handoff():
    text = (DOCS / 'music' / 'handoff.md').read_text(encoding='utf-8')
    for phrase in MUSIC_HARD_CONSTRAINTS:
        assert phrase in text, phrase


def test_adr_files_match_the_index():
    files = _md(ADR) - {'README.md'}
    assert files, 'no ADR files'
    index = (ADR / 'README.md').read_text(encoding='utf-8')
    linked = set(re.findall(r'\]\((\d{4}-[^)]+\.md)\)', index))
    assert linked == files


def test_plan_is_the_state_authority():
    assert '进度状态的唯一权威' in (DOCS / 'plan.md').read_text(encoding='utf-8')


def test_plan_holds_status_not_history():
    # history goes to docs/archive (not read), what we know of the engine and tools to docs/engine/know-how.md
    size = (DOCS / 'plan.md').stat().st_size
    assert size <= PLAN_MAX_KB * 1024, f'plan.md is {size // 1024} KB: move history to archive/, know-how to engine/'


def test_engine_docs_are_the_reviewed_set():
    assert _md(DOCS / 'engine') - GENERATED_ENGINE_PAGES == ENGINE_DOCS


def test_generated_inventory_pages_are_ignored_not_committed():
    """ADR 0030: 110 of 352 commits from 11-15 only regenerated these pages, and parallel lines conflicted on them."""
    rules = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '/docs/engine/inventory*.md' in rules
    tracked = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--', 'docs/engine'], capture_output=True,
                             text=True, encoding='utf-8', check=True).stdout.split()
    assert not {Path(t).name for t in tracked} & GENERATED_ENGINE_PAGES


def test_local_data_stays_ignored():
    rules = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '/work/' in rules


def test_agents_md_is_rules_and_map_only():
    """Keep the public contribution rules short and verify their map paths."""
    agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
    assert len(agents.splitlines()) <= 60, 'AGENTS.md over 60 lines: move area know-how into that area\'s file'
    for head in ('## 红线', '## 提交', '## 干活', '## 地图'):
        assert head in agents, head
    paths = re.findall(r'`((?:docs|experimental|tests)/[^`\s<*]+?\.(?:md|py))', agents)
    assert paths, 'AGENTS.md map names no repo paths'
    for p in paths:
        assert (ROOT / p).is_file(), p
