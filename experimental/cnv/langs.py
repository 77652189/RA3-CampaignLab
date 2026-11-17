"""Language editions of a level (the user 2026-11-01: one go, both; ADR 0013 for who speaks what):
`build.py a4 --lang zh|intl`.

  zh    the Chinese edition: Chinese subtitles. The announcer, the intelligence officers (沃斯, 卡佳, 千岁) and a new
        unit's voice speak Chinese; the story roles speak their side's native language (a recording shared with intl).
        Mod CampA4.
  intl  the international edition: English subtitles, the same story-role recordings, the announcer / officers / unit
        voices in their native language too (Allies and Futuretech English, Soviets Russian, Empire Japanese). Mod
        CampA4En (mod names: at most 15 characters, no underscore, memory mod-name-length).

Which recording a line plays and which subtitle it shows is the voice line's to say, so it is asked, not worked out here:
RA3-ChineseVoice `tools/campaign_lines.py route <LEVEL> --version zh|intl` (docs/campaign_voice.md section 7) gives per
line {event, who, audio_lang, wav, exists, interim, subtitle_lang, subtitle}. An event is named the same in every
language. A retail announcer line (`audio_lang` None) is the retail event itself, played as it is.

What is not there yet is never silently missing: `resolve()` lists every line whose recording or subtitle is not
delivered (it is left out, the plan shows its caption) and every one that plays an interim recording. The plan's own
strings (objectives, captions of undubbed lines, labels) come from docs/story/plans/<level>.en.json (Chinese string ->
English) in the international edition, the same way; a string without a translation stays Chinese and is listed.
"""
import functools
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOICE = os.path.join(os.path.dirname(ROOT), 'RA3-ChineseVoice')
LINE_TABLES = os.path.join(VOICE, 'lines', 'campaign')
PLANS = os.path.join(ROOT, 'docs', 'story', 'plans')

EDITIONS = {                                    # label: what the launcher calls an edition ('' for the default one)
    'zh': dict(suffix='', subtitle='zh', label='', strings_base='CNVoice_text.big'),
    'intl': dict(suffix='En', subtitle='en', label='国际版', strings_base='Lang-English11.big'),
}
# a unit's voice lines (lines/campaign/u_<unit>.json, `where` = the kind): level key -> (table file, the unit's event prefix)
UNIT_TABLES = {'ICEENG': ('u_ice_engineer', 'CNV_IceEngineer')}


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


@functools.lru_cache(maxsize=None)
def route(level, lang):
    """The voice line's routing of `level` ('A4', 'ICEENG') in edition `lang`: [{event, who, audio_lang, wav, exists,
    interim, subtitle_lang, subtitle}] in table order (tools/campaign_lines.py route)."""
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(VOICE, 'tools', 'campaign_lines.py'), 'route',
                        str(level).upper(), '--version', lang], cwd=VOICE, capture_output=True, text=True,
                       encoding='utf-8')
    if r.returncode:
        raise RuntimeError(f'campaign_lines.py route {level} --version {lang} failed: {r.stderr.strip()[-300:]}')
    return json.loads(r.stdout)


def unit_groups(level):
    """{event: the unit voice event the line belongs to} for a unit's lines ('' for a level's), from the table's
    `where` (iceWall / voiceSelect ... -> CNV_IceEngineer_VoiceIceWall / _VoiceSelect ...)."""
    if str(level).upper() not in UNIT_TABLES:
        return {}
    table, prefix = UNIT_TABLES[str(level).upper()]
    with open(os.path.join(LINE_TABLES, table + '.json'), encoding='utf-8') as f:
        return {'CNV_' + o['id']: f'{prefix}_' + _kind(o['where']) for o in json.load(f)['lines']}


def _kind(where):
    """voiceSelect -> VoiceSelect, iceWall -> VoiceIceWall (the unit's voice event kinds all begin with Voice)."""
    kind = where if where.startswith('voice') else 'voice' + where[0].upper() + where[1:]
    return kind[0].upper() + kind[1:]


class Resolved:
    """What edition `lang` has of `levels`: items [(event, wav, subtitle, group)] to build into the pack; missing
    [what is not delivered / interim]; said {(who, Chinese words): event} for the plan to find a line by; retail
    {(who, Chinese words): retail event} for a retail announcer line."""

    def __init__(self, levels, lang):
        ed = edition(lang)
        self.items, self.missing, self.said, self.retail = [], [], {}, {}
        for lv in levels:
            groups = unit_groups(lv)
            zh = {e['event']: e for e in route(lv, 'zh')}
            for e in route(lv, lang):
                ev, who, key = e['event'], e['who'], None
                key = (who, zh[ev]['subtitle'] if ev in zh else e['subtitle'])
                if e['audio_lang'] is None:                     # retail's own announcer line
                    self.retail[key] = ev
                    continue
                group = groups.get(ev)
                gone = [what for what, ok in ((f'audio {e["audio_lang"]}', e['exists']),
                                              (f'subtitle {ed["subtitle"]}', group or e['subtitle'])) if not ok]
                if gone:
                    self.missing.append(f'{ev} ({who}): no ' + ' and no '.join(gone))
                    continue
                if e['interim']:
                    self.missing.append(f'{ev} ({who}): plays the interim {e["audio_lang"]} recording')
                self.items.append((ev, e['wav'], e['subtitle'] if not group else '', group))
                if not group:
                    self.said[key] = ev


def translations(level):
    """{Chinese string: English} of docs/story/plans/<level>.en.json (empty when there is none)."""
    path = os.path.join(PLANS, level.lower() + '.en.json')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


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
