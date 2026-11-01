"""Language editions (experimental/cnv/langs.py): mod names, each speaker's dub language by side, the lines an edition
lacks listed (never silently missing), the plan's strings translated or listed."""
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


def test_each_side_is_dubbed_in_its_own_language_in_the_international_edition():
    assert langs.voice_lang('zh', '沃斯', '盟军') == 'zh'
    assert langs.voice_lang('intl', '沃斯', '盟军') == 'en'            # Allies
    assert langs.voice_lang('intl', '科尔', '盟军') == 'en'            # Futuretech
    assert langs.voice_lang('intl', '施泰因', '苏联') == 'en'          # a German Allied officer, in a Soviet level
    assert langs.voice_lang('intl', '别列津', '苏联') == 'ru'
    assert langs.voice_lang('intl', '黑田', '帝国') == 'ja'
    assert langs.voice_lang('intl', '播报', '苏联') == 'ru'            # the announcer and a unit speak the player's side
    assert langs.voice_lang('intl', '冰幕工兵', '盟军') == 'en'
    assert langs.voice_lang('intl', '沃斯', '盟军', {'voice_lang': 'de'}) == 'de'   # the voice line's word wins


@pytest.fixture
def delivered(tmp_path, monkeypatch):
    """A delivered A4: three Chinese lines (one an announcer's retail event), English audio for the first only, the
    English subtitle text for the first and the third."""
    zh = tmp_path / 'work' / 'zh' / 'A4'
    en = tmp_path / 'work' / 'en' / 'A4'
    zh.mkdir(parents=True)
    en.mkdir(parents=True)
    (zh / 'manifest.json').write_text(json.dumps([
        {'event': 'CNV_A4_001', 'who': '沃斯', 'text': '一', 'seconds': 1.0},
        {'event': 'CNV_A4_002', 'who': '沃斯', 'text': '二', 'seconds': 1.0},
        {'event': 'CNV_A4_003', 'who': '冰幕工兵', 'text': '三', 'seconds': 1.0, 'group': 'CNV_Unit_Select'},
        {'eva': 'Aeva_Retail', 'who': '播报', 'text': '原版'}], ensure_ascii=False), encoding='utf-8')
    (en / 'CNV_A4_001.wav').write_bytes(b'x')
    (en / 'CNV_A4_003.wav').write_bytes(b'x')
    tables = tmp_path / 'lines'
    tables.mkdir()
    (tables / 'a4.json').write_text(json.dumps({'lines': [
        {'id': 'A4_001', 'text': {'zh': '一', 'en': 'One'}}, {'id': 'A4_002', 'text': {'zh': '二'}},
        {'id': 'A4_003', 'text': {'zh': '三'}}]}), encoding='utf-8')
    monkeypatch.setattr(langs, 'DELIVERED', str(tmp_path / 'work'))
    monkeypatch.setattr(langs, 'LINE_TABLES', str(tables))
    return tmp_path


def test_a_line_without_audio_or_subtitle_is_left_out_and_listed(delivered):
    items, missing = langs.lines(['a4'], 'intl', '盟军')
    got = {ev: (Path(wav).parent.parent.name, text, group) for ev, wav, text, group in items}
    assert got == {'CNV_A4_001': ('en', 'One', None),
                   'CNV_A4_003': ('en', '', 'CNV_Unit_Select')}      # a unit voice has no subtitle to lack
    assert missing == ['CNV_A4_002 (沃斯): no audio en and no subtitle en']


def test_the_chinese_edition_takes_the_chinese_manifest_as_it_is(delivered):
    (delivered / 'work' / 'zh' / 'A4' / 'CNV_A4_001.wav').write_bytes(b'x')
    items, missing = langs.lines(['a4'], 'zh', '盟军')
    assert [i[0] for i in items] == ['CNV_A4_001'] and items[0][2] == '一'
    assert len(missing) == 2 and all('audio zh' in x for x in missing)


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
    assert zh.missing == []
    assert en.strings['MISSIONOBJ:CNVA4_T1'] == 'Escort the convoy through the Snow Festival grounds'
    voiced = [x for x in en.missing if x.startswith('voice ')]
    assert voiced and all('no audio' in x or 'no subtitle' in x for x in voiced)
    # the plan's non-speech strings are all translated (a speaker's line waits for the voice line's English text)
    speakers = ('沃斯', '司令', '科尔', '播报', '冰幕工兵')
    assert not [x for x in en.missing if x.startswith('string ') and not any(f': {w}：' in x for w in speakers)]
