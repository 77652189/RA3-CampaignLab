"""Doc guards (canon): the doc set is a deliberate list, ADR files match the index, hard constraints stay in the
handoff, the handoff's state block keeps its fields and allowed values, and plan.md stays the state authority."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / 'docs'
ADR = DOCS / 'adr'

ROOT_DOCS = {'README.md', 'HANDOFF.md'}
ACTIVE_DOCS = {'architecture.md', 'plan.md', 'requirements.md'}

HARD_CONSTRAINTS = [
    '需要任何内容直接下载就行，不要停下来，你最多可以用50G硬盘',
    '只要不乱删文件就行',
    '可以，限流开始做吧',
    '游戏运行时不往 Mods 写',
    '不改 Steam 游戏目录里的文件',
    '不解密 Corona mod',
    '回复用通俗中文',
]
STATE_FIELDS = {
    'slice': None,                                              # free text
    'blocked_on': {'none', 'voice-session', 'user'},
    'next_gate': {'test-map', 'coordinate-calibration', 'demo'},
}


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


def test_local_data_stays_ignored():
    rules = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert '/work/' in rules
