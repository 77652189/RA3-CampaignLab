"""Language editions of a level (2026-11-01, the user: one go, both): `build.py a4 --lang zh|intl`.

  zh    the Chinese edition: Chinese subtitles, Chinese dub. Mod CampA4.
  intl  the international edition: English subtitles, each speaker dubbed in the language of their side (Allies and
        Futuretech English, Soviets Russian, Empire Japanese). Mod CampA4En (mod names: at most 15 characters, no
        underscore, memory mod-name-length).

The voice line's interface (RA3-ChineseVoice docs/campaign_voice.md, "多语言"): one id per line, an event named the same
in every language (CNV_A4_007), audio per language in work/campaign/<language>/<LEVEL>/<event>.wav, a line's texts in
lines/campaign/<level>.json under `text` by language. The subtitle language and the dub language are separate: the intl
edition's subtitle is `en` text, its audio the speaker's own language's folder (the voice line's docs win where they
say more; a manifest entry's `voice_lang` overrides the side table below).

What is not there yet is never silently missing: `lines()` returns what it could not find and the build prints it.
The plan's own strings (objectives, captions of undubbed lines, labels) come from docs/story/plans/<level>.en.json
(Chinese string -> English), the same way; a string without a translation stays Chinese and is listed.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOICE = os.path.join(os.path.dirname(ROOT), 'RA3-ChineseVoice')
DELIVERED = os.path.join(VOICE, 'work', 'campaign')
LINE_TABLES = os.path.join(VOICE, 'lines', 'campaign')
PLANS = os.path.join(ROOT, 'docs', 'story', 'plans')
CAST = os.path.join(ROOT, 'docs', 'design', 'flow', 'cast.md')

EDITIONS = {
    'zh': dict(suffix='', subtitle='zh', voice_by_side=None),
    'intl': dict(suffix='En', subtitle='en',
                 voice_by_side={'盟军': 'en', '未来科技': 'en', '苏联': 'ru', '帝国': 'ja'}),
}


def edition(lang):
    if lang not in EDITIONS:
        raise ValueError(f'language {lang!r}: one of {sorted(EDITIONS)}')
    return EDITIONS[lang]


def mod_name(level, lang='zh'):
    """CampA4 / CampA4En: at most 15 characters, letters and digits only."""
    name = f'Camp{level.upper()}{edition(lang)["suffix"]}'
    assert len(name) <= 15 and re.fullmatch(r'[A-Za-z0-9]+', name), f'mod name {name!r}'
    return name


def voice_folder(lang='zh'):
    """The SDK folder of the edition's voice pack (separate per edition, so one never builds over the other)."""
    return 'CNVVoice' + edition(lang)['suffix']


def cast_sides():
    """{speaker key: side} from the first table of docs/design/flow/cast.md (键 | 名字 | 阵营 | ...)."""
    out = {}
    with open(CAST, encoding='utf-8') as f:
        for line in f:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 3 and line.startswith('|') and cells[0] not in ('键', '---') and cells[2] in (
                    '盟军', '苏联', '帝国', '未来科技'):
                out[cells[0]] = cells[2]
    return out


def voice_lang(lang, who, faction, entry=None):
    """The language `who` is dubbed in, in edition `lang`. A speaker with no side in the cast table (the announcer,
    a unit's voice) speaks the player's `faction`."""
    by_side = edition(lang)['voice_by_side']
    if by_side is None:
        return 'zh'
    if entry and entry.get('voice_lang'):
        return entry['voice_lang']
    side = cast_sides().get(who, faction)
    return by_side.get(side, by_side['盟军'])


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def subtitle_texts(level, sub):
    """{event: text} of the line table's `sub`-language texts (lines/campaign/<level>.json: id A4_007 -> CNV_A4_007)."""
    path = os.path.join(LINE_TABLES, level.lower() + '.json')
    if not os.path.exists(path):
        return {}
    return {'CNV_' + e['id']: e['text'][sub] for e in read_json(path).get('lines', [])
            if isinstance(e.get('text'), dict) and e['text'].get(sub)}


def lines(levels, lang, faction):
    """([(event, wav, subtitle text, group)], [what is missing]) for `levels` in edition `lang`.

    The events are the Chinese manifest's (work/campaign/zh/<LEVEL>/manifest.json: an event is named the same in every
    language); an announcer line that plays a retail event (no `event`) has no file of ours. Each line's audio is in
    its speaker's dub language's folder, its subtitle the table's text in the edition's subtitle language (a unit's
    voice line, with a group, has no subtitle). Not found: left out and listed, so the plan shows its caption."""
    ed = edition(lang)
    items, missing = [], []
    for lv in levels:
        LV = str(lv).upper()
        zh = read_json(os.path.join(DELIVERED, 'zh', LV, 'manifest.json'))
        texts = subtitle_texts(LV, ed['subtitle'])
        for e in zh:
            ev = e.get('event')
            if not ev:
                continue
            vl = voice_lang(lang, e['who'], faction, e)
            wav = os.path.join(DELIVERED, vl, LV, ev + '.wav')
            group = e.get('group')
            text = e['text'] if ed['subtitle'] == 'zh' else texts.get(ev)
            gone = [what for what, ok in ((f'audio {vl}', os.path.exists(wav)),
                                          ('subtitle ' + ed['subtitle'], group or text)) if not ok]
            if gone:
                missing.append(f'{ev} ({e["who"]}): no ' + ' and no '.join(gone))
                continue
            items.append((ev, wav, text or '', group))
    return items, missing


def translations(level):
    """{Chinese string: English} of docs/story/plans/<level>.en.json (empty when there is none)."""
    path = os.path.join(PLANS, level.lower() + '.en.json')
    return read_json(path) if os.path.exists(path) else {}


def translate(strings, level, lang):
    """(strings in the edition's subtitle language, [the keys left in Chinese]): `strings` is the mission's {key: text}."""
    if edition(lang)['subtitle'] == 'zh':
        return dict(strings), []
    table, out, left = translations(level), {}, []
    for k, v in strings.items():
        out[k] = table.get(v, v)
        if v not in table and re.search(r'[一-鿿]', v):
            left.append(f'{k}: {v}')
    return out, left
