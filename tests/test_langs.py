"""Language editions (experimental/cnv/langs.py): mod names, the voice line's routing of each line (ADR 0013), the lines an
edition lacks listed (never silently missing), the plan's strings translated or listed."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import langs  # noqa: E402


def test_the_two_editions_are_two_mods_with_legal_names():
    assert langs.mod_name('a4', 'zh') == 'CampA4'
    assert langs.mod_name('a4', 'intl') == 'CampA4En'
    assert langs.voice_folder('zh') != langs.voice_folder('intl')
    with pytest.raises(ValueError):
        langs.edition('fr')
    for lv in ('a4', 's1', 'j7'):
        for lang in langs.EDITIONS:
            name = langs.mod_name(lv, lang)
            assert len(name) <= 15 and re.fullmatch(r'[A-Za-z0-9]+', name)


def row(event, who, audio_lang, exists, subtitle, interim=False, lang='zh'):
    return dict(event=event, who=who, audio_lang=audio_lang, wav=f'C:/w/{audio_lang}/{event}.wav' if audio_lang else None,
                exists=exists, interim=interim, subtitle_lang=lang, subtitle=subtitle)


@pytest.fixture
def routed(monkeypatch):
    """A4 as the voice line routes it: 沃斯 (an intelligence officer) in zh for the Chinese edition and English for the
    international one, 司令 (a story role) English in both, a retail announcer line, and the engineer's two voice lines."""
    zh = {'A4': [row('CNV_A4_001', '沃斯', 'zh', True, '一'), row('CNV_A4_002', '司令', 'en', False, '二'),
                 row('CNV_A4_003', '司令', 'zh', True, '三', interim=True),
                 row('Aeva_CritUnitLost', '播报', None, True, '关键单位损失。')],
          'ICEENG': [row('CNV_ICEENG_001', '冰幕工兵', 'zh', True, ''), row('CNV_ICEENG_002', '冰幕工兵', 'zh', True, '')]}
    intl = {'A4': [row('CNV_A4_001', '沃斯', 'en', True, 'One', lang='en'), row('CNV_A4_002', '司令', 'en', False, 'Two', lang='en'),
                   row('CNV_A4_003', '司令', 'en', True, '', lang='en'),
                   row('Aeva_CritUnitLost', '播报', None, True, 'Critical unit lost.', lang='en')],
            'ICEENG': [row('CNV_ICEENG_001', '冰幕工兵', 'en', True, '', lang='en'),
                       row('CNV_ICEENG_002', '冰幕工兵', 'en', False, '', lang='en')]}
    monkeypatch.setattr(langs, 'route', lambda level, lang: (zh if lang == 'zh' else intl)[level])
    monkeypatch.setattr(langs, 'unit_groups', lambda level: {
        'CNV_ICEENG_001': 'CNV_Unit_Select', 'CNV_ICEENG_002': 'CNV_Unit_Move'} if level == 'ICEENG' else {})


def test_the_chinese_edition_builds_what_is_routed_and_lists_what_is_not_there(routed):
    got = langs.Resolved(['A4', 'ICEENG'], 'zh')
    assert [(i[0], i[2], i[3]) for i in got.items] == [
        ('CNV_A4_001', '一', None), ('CNV_A4_003', '三', None),
        ('CNV_ICEENG_001', '', 'CNV_Unit_Select'), ('CNV_ICEENG_002', '', 'CNV_Unit_Move')]
    assert got.missing == ['CNV_A4_002 (司令): no audio en', 'CNV_A4_003 (司令): plays the interim zh recording']
    assert got.said == {('沃斯', '一'): 'CNV_A4_001', ('司令', '三'): 'CNV_A4_003'}
    assert got.retail == {('播报', '关键单位损失。'): 'Aeva_CritUnitLost'}


def test_the_international_edition_finds_lines_by_their_chinese_words_and_lists_the_missing(routed):
    got = langs.Resolved(['A4', 'ICEENG'], 'intl')
    assert [(i[0], i[2]) for i in got.items if not i[3]] == [('CNV_A4_001', 'One')]      # 003: no subtitle, no audio problem
    assert got.said[('沃斯', '一')] == 'CNV_A4_001'                    # the plan's key is the Chinese text, not the subtitle
    assert got.missing == ['CNV_A4_002 (司令): no audio en', 'CNV_A4_003 (司令): no subtitle en',
                           'CNV_ICEENG_002 (冰幕工兵): no audio en']
    assert got.retail == {('播报', '关键单位损失。'): 'Aeva_CritUnitLost'}


def test_the_engineers_voice_events_are_named_from_the_lines_table(monkeypatch):
    groups = langs.unit_groups('ICEENG')
    assert groups['CNV_ICEENG_001'] == 'CNV_IceEngineer_VoiceSelect'
    assert set(groups.values()) >= {'CNV_IceEngineer_VoiceIceWall', 'CNV_IceEngineer_VoiceCapture'}
    assert langs.unit_groups('A4') == {}


def test_the_plans_own_strings_are_translated_or_listed(tmp_path, monkeypatch):
    (tmp_path / 'zz.en.json').write_text(json.dumps({'下一声号角': 'Next horn'}), encoding='utf-8')
    monkeypatch.setattr(langs, 'PLANS', str(tmp_path))
    out, left = langs.translate({'SCRIPT:A': '下一声号角', 'SCRIPT:B': '没译的', 'SCRIPT:C': '1:23'}, 'zz', 'intl')
    assert out == {'SCRIPT:A': 'Next horn', 'SCRIPT:B': '没译的', 'SCRIPT:C': '1:23'}
    assert left == ['SCRIPT:B: 没译的']                               # only a string that has Chinese in it is listed
    assert langs.translate({'SCRIPT:A': '下一声号角'}, 'zz', 'zh') == ({'SCRIPT:A': '下一声号角'}, [])


def test_a4_plan_has_an_english_edition_that_lists_what_it_lacks():
    import plan
    en, zh = plan.mission('a4', lang='intl'), plan.mission('a4')
    assert (en.name, zh.name) == ('CampA4En', 'CampA4')
    assert en.strings['MISSIONOBJ:CNVA4_T1'] == 'Escort the convoy through the Snow Festival grounds'
    assert zh.missing and all('no audio en' in x or 'caption only' in x for x in zh.missing)   # 司令 / 科尔 not recorded yet
    voiced = [x for x in en.missing if x.startswith('voice ')]
    assert voiced and all('no audio' in x or 'no subtitle' in x for x in voiced)
    # the plan's non-speech strings are all translated (a speaker's line waits for its recording and English subtitle)
    speakers = ('沃斯', '司令', '科尔', '播报', '冰幕工兵')
    assert not [x for x in en.missing if x.startswith('string ') and not any(f': {w}：' in x for w in speakers)]


def test_a_retail_announcer_line_plays_the_retail_event_in_both_editions():
    """A routed line with no audio language (retail's own announcer line) is played as that retail event, with no
    caption; it is checked against the retail audio events and listed if it is not one."""
    import plan
    for lang in ('zh', 'intl'):
        m = plan.mission('a4', lang=lang)
        rule = next(s for s in m.scripts if ('PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT', 'Aeva_CritUnitLost') in s.do)
        assert all(a[0] != 'SHOW_MILITARY_CAPTION' for a in rule.do)
        assert not [x for x in m.missing if 'retail announcer' in x]
