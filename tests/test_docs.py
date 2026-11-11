"""Doc guards (canon): the doc set is a deliberate list, ADR files match the index, hard constraints stay in the
handoff, the handoff's state block keeps its fields and allowed values, and plan.md stays the state authority."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
ADR = DOCS / 'adr'

ROOT_DOCS = {'README.md', 'HANDOFF.md', 'CLAUDE.md', 'AGENTS.md'}   # AGENTS.md: the one rule file for every harness (red lines + map, 2026-11-10); CLAUDE.md: imports it + Claude-only mechanics
ACTIVE_DOCS = {'architecture.md', 'issues.md', 'plan.md', 'requirements.md'}

HARD_CONSTRAINTS = [
    '需要任何内容直接下载就行，不要停下来，你最多可以用50G硬盘',
    '只要不乱删文件就行',
    '可以，限流开始做吧',
    '游戏运行时不往 Mods 写',
    '不改 Steam 游戏目录里的文件',
    '不解密 Corona mod',
    '回复用通俗中文',
    '总之让我听不到就可以',
    '就只在国内发布吧，不上N网',
    '只用来做mod，研究学习里面的内容，不公开',
    '我希望尽可能把引擎的算法还原成python代码',
]
STATE_FIELDS = {
    'slice': None,                                              # free text
    'blocked_on': {'none', 'voice-session', 'user'},
    'next_gate': {'test-map', 'coordinate-calibration', 'demo', 'playtest'},
}
ENGINE_DOCS = {'script-semantics.md', 'know-how.md', 'terrain.md', 'pathing.md', 'upgrades.md', 'spawn.md', 'air.md', 'aircraft.md',
               'missile.md', 'weapons.md', 'garrison.md', 'stealth.md',
               'production.md', 'mining.md', 'construction.md', 'specialpower.md', 'sell.md', 'heal.md', 'stance.md', 'transform.md', 'vision.md', 'runoffmap.md', 'teleport.md', 'crush.md', 'aiopen.md', 'aistate.md', 'aispecial.md', 'aimicro.md', 'aitactics.md', 'inventory.md', 'ainamed.md', 'inventory-levels.md', 'inventory-levels-a.md', 'aiswitches.md', 'aiteamstate.md', 'uprising-gap.md', 'weaponset.md'}   # reverse-engineering notes stay in work/re/ (repo is public)
PLAN_MAX_KB = 40        # status only (2026-10-28 it was 115 KB of history and know-how: archive/, engine/)


def _md(root):
    assert root.is_dir(), f'扫描目标不存在，测试会静默通过：{root}'
    return {p.name for p in root.glob('*.md') if p.is_file()}


def test_root_docs_are_the_reviewed_set():
    assert _md(ROOT) == ROOT_DOCS


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


def test_hard_constraints_present_in_handoff():
    text = (ROOT / 'HANDOFF.md').read_text(encoding='utf-8')
    for phrase in HARD_CONSTRAINTS:
        assert phrase in text, phrase


def test_handoff_state_block_fields_and_values():
    text = (ROOT / 'HANDOFF.md').read_text(encoding='utf-8')
    block = re.search(r'```yaml\n(.*?)```', text, re.S)
    assert block, 'no yaml state block'
    state = {}
    for line in block.group(1).splitlines():
        m = re.match(r'(\w+):\s*([^#\s]+)', line)
        if m:
            state[m.group(1)] = m.group(2)
    assert set(state) == set(STATE_FIELDS)
    for key, allowed in STATE_FIELDS.items():
        assert allowed is None or state[key] in allowed, (key, state[key])


def test_plan_is_the_state_authority():
    assert '进度状态的唯一权威' in (DOCS / 'plan.md').read_text(encoding='utf-8')


def test_plan_holds_status_not_history():
    # history goes to docs/archive (not read), what we know of the engine and tools to docs/engine/know-how.md
    size = (DOCS / 'plan.md').stat().st_size
    assert size <= PLAN_MAX_KB * 1024, f'plan.md is {size // 1024} KB: move history to archive/, know-how to engine/'


def test_engine_docs_are_the_reviewed_set():
    assert _md(DOCS / 'engine') == ENGINE_DOCS


def test_local_data_stays_ignored():
    rules = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '/work/' in rules


def test_agents_md_is_rules_and_map_only():
    """AGENTS.md is the one rule file every harness reads (user 2026-11-10): red lines + map, kept short;
    CLAUDE.md only imports it and adds Claude-only mechanics; every repo path the map names exists."""
    agents = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
    assert len(agents.splitlines()) <= 60, 'AGENTS.md over 60 lines: move area know-how into that area\'s file'
    for head in ('## 红线', '## 提交', '## 干活', '## 地图'):
        assert head in agents, head
    claude = (ROOT / 'CLAUDE.md').read_text(encoding='utf-8').splitlines()
    assert claude[0].strip() == '@AGENTS.md'
    assert len(claude) <= 15, 'CLAUDE.md is an adapter; rules go in AGENTS.md'
    paths = re.findall(r'`((?:docs|experimental|tests)/[^`\s<*]+?\.(?:md|py))', agents)
    assert paths, 'AGENTS.md map names no repo paths'
    for p in paths:
        assert (ROOT / p).is_file(), p
