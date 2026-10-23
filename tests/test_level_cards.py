"""docs/story/levels.md and the code's interfaces say the same thing: a card per level (build.LEVELS), and in each the
map, the cast (part, side, sites), the marks, the facts, the abilities, the objectives and the checks the code publishes -- the
design written in the names the code exposes, so neither drifts from the other."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
import build  # noqa: E402

CARDS = ROOT / 'docs' / 'story' / 'levels.md'
SIDES = {'我': 'p1', '敌': 's1'}


def cards():
    assert CARDS.is_file(), f'扫描目标不存在，测试会静默通过：{CARDS}'
    text = CARDS.read_text(encoding='utf-8')
    heads = list(re.finditer(r'^## \S+ .+? · `(\w+)`$', text, re.M))
    assert heads, 'no level cards'
    return {h.group(1): text[h.end():(heads[k + 1].start() if k + 1 < len(heads) else len(text))]
            for k, h in enumerate(heads)}


def ticks(s):
    return re.findall(r'`([^`]+)`', s)


def item(card, label):
    m = re.search(rf'^- {label}：(.*)$', card, re.M)
    assert m, f'card has no "{label}" line'
    return m.group(1)


def test_a_card_per_level():
    assert set(cards()) == set(build.LEVELS) and set(build.LEVELS) <= set(build.MISSIONS)


def test_cards_match_the_published_interfaces():
    for key, card in cards().items():
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
