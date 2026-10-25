"""docs/story/levels.md and the code's interfaces say the same thing: a card per level (build.LEVELS), and in each the
map, the cast (part, side, sites), the marks, the facts, the abilities, the objectives and the checks the code publishes -- the
design written in the names the code exposes, so neither drifts from the other.

A level with a plan (docs/story/plans/<level>.md, plan.py) is its plan: its card only points there, and the plan is
what is held to the code -- it compiles, everything it names is published, its 检查 are the build's checks."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import build  # noqa: E402
import parts  # noqa: E402
import plan  # noqa: E402

CARDS = ROOT / 'docs' / 'story' / 'levels.md'
SIDES = {'我': 'p1', '敌': 's1'}


def cards():
    assert CARDS.is_file(), f'扫描目标不存在，测试会静默通过：{CARDS}'
    text = CARDS.read_text(encoding='utf-8')
    heads = list(re.finditer(r'^## \S+ .+? · `(\w+)`$', text, re.M))
    assert heads, 'no level cards'
    return {h.group(1): text[h.end():(heads[k + 1].start() if k + 1 < len(heads) else len(text))]
            for k, h in enumerate(heads)}


def planned():
    assert Path(plan.PLANS).is_dir(), f'扫描目标不存在，测试会静默通过：{plan.PLANS}'
    return set(plan.levels())


def ticks(s):
    return re.findall(r'`([^`]+)`', s)


def item(card, label):
    """A card's "- label：..." line, with the indented "  - ..." lines under it (objectives in stages)."""
    m = re.search(rf'^- {label}：(.*)$((?:\n  - .*)*)', card, re.M)
    assert m, f'card has no "{label}" line'
    return m.group(1) + m.group(2)


def test_a_card_per_level():
    assert set(cards()) == set(build.LEVELS) and set(build.LEVELS) <= set(build.MISSIONS)
    assert planned() <= set(build.LEVELS)


def test_planned_levels_point_to_their_plan():
    for key in planned():
        card = cards()[key]
        assert f'(plans/{key}.md)' in item(card, '策划案'), key
        assert not re.search(r'^\| `', card, re.M), f'{key}: a planned level keeps its cast in the plan, not the card'


def test_plans_compile_against_the_published_interfaces():
    for key in planned():
        d = plan.load(key)
        m, _, _ = build.resolve(key, '')
        assert d['地图'] == m.map.__name__.split('.')[-1], key
        assert not parts.contract(parts.merged(m)), key
        assert set(d.get('检查') or {}) == set(build.MISSIONS[key][1]), key


def test_cards_match_the_published_interfaces():
    for key, card in cards().items():
        if key in planned():
            continue
        m, _, _ = build.resolve(key, '')
        assert ticks(item(card, '地图')) == [m.map.__name__.split('.')[-1]], key
        rows = [[c.strip() for c in line.strip('|').split('|')] for line in card.splitlines() if line.startswith('| `')]
        # a row may list several parts that play alike (`truck 1` `truck 2` ...)
        cast = {part: (SIDES[r[2]], set(ticks(r[3]))) for r in rows for part in ticks(r[0])}
        assert cast == {k: (r.side, set(r.sites)) for k, r in m.cast.items()}, key
        assert set(ticks(item(card, '路点'))) == set(m.marks), key
        assert set(ticks(item(card, '时间'))) == set(m.facts), key
        for ability in ticks(item(card, '能力')):
            part, what = ability.split('.')
            assert m.ability(part, what), (key, ability)
        # objectives: each one's on-screen title and the parts / marks its marker points at; bonus ones say 奖励
        goals = item(card, '目标')
        assert set(ticks(goals)) == ({m.strings[g.title] for g in m.objectives} |
                                     {p for g in m.objectives for p in g.show}), key
        assert {t for t in re.findall(r'奖励 `([^`]+)`', goals)} == \
            {m.strings[g.title] for g in m.objectives if g.bonus}, key
        checks = re.search(r'^- 检查：\n((?:  - .*\n?)+)', card, re.M)
        assert checks, f'{key}: no 检查 list'
        named = [ticks(line)[0] for line in checks.group(1).splitlines()]
        assert set(named) == set(build.MISSIONS[key][1]), key
