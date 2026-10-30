"""The de-AI polishing pass on a flow script's lines (style.md section 4): write the brief for Gemini, then write the
rewrites the writer picked back into the script. The answer is a draft; flowcheck runs after.

    python docs/design/flow/flowpolish.py brief a4 FOLDER          # FOLDER/brief.md for experimental/outsource/agy_task.py
    python docs/design/flow/flowpolish.py apply a4 ANSWER PICKED   # PICKED: the chosen line ids, one per line

The answer lists one line per row as `id | 原文 | 改写 | 理由 | 分` (改写 is 不改 when it stays).
"""
import csv
import pathlib
import random
import re
import sys

import flowcheck as fc

RETAIL = fc.VOICE_GLOSSARY.parent
REFS = 120                      # retail official lines sent along as the reference voice


def lines(p, name):
    """(id, key, text, where) of everything the player reads or hears that is polished: spoken lines (key: the
    speaker), objective texts (key: 说明) and on-screen text (key: 文字). Retail EVA lines (kept word for word) and
    objective titles (menu phrases) are left out."""
    eva = (fc.retail_eva() or {}).get(p.get('阵营')) or {}
    out = []
    for where, who, text in fc.lines_in(p, name):
        if who == '播报' and fc.PUNCT.sub('', str(text)) in eva:
            continue
        out.append((who, text, where))
    for i, seg in enumerate(p.get('段') or []):
        for g in seg.get('目标') or []:
            if g.get('说明'):
                out.append(('说明', g['说明'], f'{name}/段[{i}]/目标/{g.get("题")}'))
        for e in seg.get('事件') or []:
            if e.get('文字'):
                out.append(('文字', e['文字'], f'{name}/段[{i}]/事件/{e.get("时机")}'))
    return [(f'L{k + 1:03d}', who, text, where) for k, (who, text, where) in enumerate(out)]


def refs(seed):
    """A fixed sample of the retail official Chinese subtitles (zh_official), the voice to aim at."""
    rows = []
    for name in ('movie.csv', 'mission.csv'):
        path = RETAIL / name
        if path.exists():
            with path.open(encoding='utf-8-sig', newline='') as f:
                rows += [r['zh_official'] for r in csv.DictReader(f) if r.get('zh_official')]
    random.Random(seed).shuffle(rows)
    return [re.sub(r'\[[0-9.]+\]', '', r) for r in rows[:REFS]]


def brief(level, folder):
    path = fc.HERE / f'{level.lower()}.md'
    p = fc.plan_of(path)
    todo = lines(p, path.name)
    speakers = {who for _, who, _, _ in todo}
    cast = [ln for ln in (fc.HERE / 'cast.md').read_text(encoding='utf-8').splitlines()
            if ln.startswith('| ') and ln.split('|')[1].strip() in speakers]
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    text = [
        f'# 任务：给红警 3 战役 mod 第 {p["关"]} 关「{p["关名"]}」的中文台词去 AI 腔',
        '',
        '下面先是文风规则（照它判断什么算 AI 腔、什么不算），再是说话人的性格、原版官方中文的参照句，最后是要润色的台词。',
        '',
        '## 要你做的',
        '',
        '你是一个从小玩红警 3 官方中文版的中国玩家，替我们挑出读起来"像 AI 写的"句子。逐句看下面"台词"一节的每一句：',
        '- 先打自然度 1～5 分：5 分 = 和原版官方中文一样像人话，3 分 = 读得懂但一听就是写出来的，1 分 = 典型 AI 腔。',
        '- 4 分及以下的必须给出改写，并用一句话说明犯了文风规则第几条；5 分的改写写"不改"。',
        '- 不要整关都打 5 分。挑剔一点：四字词、排比、"进行"、完整到啰嗦的句子、说明书式的解释、千篇一律的节奏，都要扣分。',
        '- "说话人"一栏是"说明"的，是任务目标下面那段说明文字；是"文字"的，是屏幕上的提示框。这两种不必像口语，但也要短、直、不啰嗦。',
        '硬规矩（违反的改写作废）：',
        '- 台词一句不超过三十个字（不算标点）；不用阿拉伯数字、英文字母、括号；数字写汉字。',
        '- 目标说明最多两句，但"为什么、做什么、在哪、要当心什么"一样都不能丢；不要改成攻略体（获取、掌握、迫退、瘫痪这类词）。',
        '- 不加配音容易读错的多音字（得、还、为、行、重、长、着、干、乐、弹），原句里有的可以换掉。',
        '- 不把具体指示换成空话（"留着防空"不能改成"注意防空"），不改打法（"算好车到的时候再冻"不能改成"等车到了再冻"）。',
        '- 说话人不变，一行还是一行：不合并、不拆分、不调换顺序。',
        '- 意思和信息不变：地名（一号广场、北坡口……）、兵种名（冰幕工兵、天狗机甲……）、要玩家做的动作都要保留，不换近义词。',
        '- 照说话人的性格写（例如黑尔本来就像发布会、别列津爱说"同志们"），不要把所有人改成一个口气。',
        '- 只给答案，不要改任何文件。',
        '',
        '输出：只输出一张 markdown 表，每句一行，列是 `id | 原文 | 改写 | 理由 | 分`，id 照抄，顺序照抄，一句都不能漏。',
        '',
        '## 文风规则',
        '',
        (fc.HERE / 'style.md').read_text(encoding='utf-8'),
        '',
        '## 说话人（角色表）',
        '',
        '| 键 | 名字 | 阵营 | 身份 | 说话的样子 | 出场 |',
        '|---|---|---|---|---|---|',
        *cast,
        '',
        f'## 这一关的背景',
        '',
        f'- 一句话：{p.get("一句话")}',
        f'- 体验目标：{p.get("体验目标")}',
        '',
        '## 原版官方中文的参照句（学它的短和直，不学它的翻译腔）',
        '',
        *[f'- {r}' for r in refs(p['关'])],
        '',
        '## 台词',
        '',
        '| id | 说话人 | 原文 | 在哪 |',
        '|---|---|---|---|',
        *[f'| {i} | {who} | {text} | {where.split(" ", 1)[-1] if " " in where else where} |'
          for i, who, text, where in todo],
    ]
    (folder / 'brief.md').write_text('\n'.join(text), encoding='utf-8')
    print(f'{len(todo)} lines -> {folder / "brief.md"}')


def answer(path):
    """{id: (原文, 改写, 理由)} from the answer's table (a fifth column, the score, may follow)."""
    out = {}
    for ln in pathlib.Path(path).read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        if len(cells) >= 4 and re.fullmatch(r'L\d{3}', cells[0]):
            out[cells[0]] = (cells[1], cells[2], cells[3])
    return out


def apply(level, answer_path, picked_path):
    path = fc.HERE / f'{level.lower()}.md'
    p = fc.plan_of(path)
    todo = {i: (who, text) for i, who, text, _ in lines(p, path.name)}
    got = answer(answer_path)
    picked = [x.strip() for x in pathlib.Path(picked_path).read_text(encoding='utf-8').split() if x.strip()]
    src = path.read_text(encoding='utf-8')
    done = 0
    for i in picked:
        who, text = todo[i]
        new = got[i][1]
        if new in ('不改', '', text):
            continue
        old = f'{who}: {text}'
        if who in ('说明', '文字'):
            old = f'{who}: {text}'                  # an objective's text or on-screen text: the key is the field
        if old not in src:
            print(f'{i}: "{old}" not found in {path.name} -- skipped')
            continue
        src = src.replace(old, f'{who}: {new}')
        done += 1
    path.write_text(src, encoding='utf-8')
    print(f'{done} lines rewritten in {path.name}; run flowcheck next')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    cmd, *args = sys.argv[1:]
    {'brief': brief, 'apply': apply}[cmd](*args)
