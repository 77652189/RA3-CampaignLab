"""The campaign shell probe (experimental/cnv/shell.py, ADR 0014): a retail APT screen with our picture in it keeps every other
byte of the stream, the template edits land where intended, and the mod's name is one the game starts with."""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
sys.path.insert(0, str(ROOT))
import apt_textures  # noqa: E402
import make_campnew2 as c2  # noqa: E402
import shell  # noqa: E402

B = chr(92)
ARCHIVE = Path(c2.splice_assets.DATA) / 'Apt.big'
needs_game = pytest.mark.skipif(not ARCHIVE.exists(), reason='no game install')


def test_the_mod_name_is_one_the_game_starts_with():
    assert len(shell.NAME) <= 15 and re.fullmatch(r'[A-Za-z0-9]+', shell.NAME)


@needs_game
def test_a_picture_written_over_a_texture_changes_nothing_else_in_the_stream():
    from PIL import Image
    prefix = 'data' + B + 'aptui' + B + 'a01_objective_briefing.'
    size = apt_textures.textures('Apt.big', prefix)['apt_A01_Objective_Briefing_2']
    files = dict(apt_textures.patch('Apt.big', prefix, {'apt_A01_Objective_Briefing_2': Image.new('RGBA', size, (255, 0, 0, 255))}))
    for ext in ('manifest', 'relo', 'imp'):              # sizes unchanged: the stream's tables are the retail ones
        retail = apt_textures.mapxml._archive_get('Apt.big')(prefix + ext)
        assert files[prefix + ext] == (apt_textures.mapxml.refpack.decompress(retail)
                                       if apt_textures.mapxml.refpack.is_refpack(retail) else retail)
    assert len(files[prefix + 'bin']) == 4497584 and b'\xff\x00\x00\xff' not in files[prefix + 'bin'][:140]


@needs_game
def test_a_picture_of_the_wrong_size_is_refused():
    from PIL import Image
    prefix = 'data' + B + 'aptui' + B + 'a01_objective_briefing.'
    with pytest.raises(AssertionError):
        apt_textures.patch('Apt.big', prefix, {'apt_A01_Objective_Briefing_2': Image.new('RGBA', (8, 8))})


def test_the_template_takes_allies_1s_place_with_the_shell_fields(tmp_path, monkeypatch):
    sdk = Path(c2.SDK)
    if not (sdk / 'SageXML' / 'GlobalData' / 'CampaignTemplates.xml').exists():
        pytest.skip('no SDK')
    monkeypatch.setattr(c2, 'SRC_DIR', str(tmp_path))
    monkeypatch.setattr(c2, 'SHELL', {'attrs': {'OverviewTalkingHead': 'HEADX', 'IntroMovie:FileName': 'INTROX',
                                                'IntroMovie:Description': 'MissionDesc:CNV01'}})
    c2.sources()
    xml = (tmp_path / f'{c2.NAME}.xml').read_text(encoding='ascii')
    assert 'OverviewTalkingHead="HEADX"' in xml and 'FileName="INTROX"' in xml
    intro = re.search(r'<IntroMovie.*?</IntroMovie>', xml, re.S).group(0)
    assert 'MissionDesc:CNV01' in intro and 'AFS01' not in intro
    assert 'CommanderDescription:Coop_AlliedSquadronLeader' in xml             # the AICommander's Description is not the intro's
    camp = re.search(r'<CampaignTemplate.*?</CampaignTemplate>', xml, re.S).group(0)
    missions = re.findall(r'<Mission>([^<]*)</Mission>', camp)
    assert missions == ['Allies_New'] + [f'Allies_S{k}' for k in range(2, 10)]         # every slot is ours, unlocked
    assert xml.count('<Prerequisite>0</Prerequisite>') == 9
    assert 'A01_Objective_Briefing' in xml                                    # the briefing screens are Allies_1's: free to repaint


def test_the_built_mission_takes_its_own_slot_and_every_slot_has_its_labels(tmp_path, monkeypatch):
    sdk = Path(c2.SDK)
    if not (sdk / 'SageXML' / 'GlobalData' / 'CampaignTemplates.xml').exists():
        pytest.skip('no SDK')
    monkeypatch.setattr(c2, 'SRC_DIR', str(tmp_path))
    monkeypatch.setattr(c2, 'SHELL', {'slot': 4, 'attrs': {'AICommander:Description': 'CommanderDescription:CNV04'},
                                      'others': {k: {'AICommander:Description': f'CommanderDescription:CNV0{k}'} for k in (1, 2, 3, 5, 6, 7, 8, 9)},
                                      'no_portrait': True})
    c2.sources()
    xml = (tmp_path / f'{c2.NAME}.xml').read_text(encoding='ascii')
    camp = re.search(r'<CampaignTemplate.*?</CampaignTemplate>', xml, re.S).group(0)
    assert re.findall(r'<Mission>([^<]*)</Mission>', camp) == ['Allies_S1', 'Allies_S2', 'Allies_S3', 'Allies_New'] + \
        [f'Allies_S{k}' for k in range(5, 10)]
    for k in range(1, 10):
        assert xml.count(f'DisplayName="MissionName:CNV0{k}"') == 1 and f'CommanderDescription:CNV0{k}"' in xml
    commanders = re.findall(r'<AICommander\b[^>]*>', xml)
    assert len(commanders) >= 9 and not any('Portrait=' in c for c in commanders)
    assert xml.count(c2.NEW_DIR + c2.NEW_STEM + '.map') == 1                  # only the built mission has our map
    assert 'CAMP_A04_Gibraltar_Hayes' not in xml and 'CAMP_A01_' in xml       # slot 4 is ours, slot 1 is retail's map


def test_the_nine_missions_have_names_and_two_objectives_each():
    info = shell.missions()
    assert sorted(info) == list(range(1, 10))
    for k, m in info.items():
        assert m['title'] and 0 < len(m['short']) <= 6 and len(m['objectives']) == 2 and 0 < len(m['briefing']) <= 100, k
    assert shell.slot_of('CampA4') == 4 and shell.slot_of('CampA7East') == 7
    assert shell.label(4) == 'CNV04' and shell.intro_id(4) == 'CNVINTRO04'
    assert len(shell.intro_id(9)) == len('CNVINTRO01')                           # video ids keep their length


@needs_game
def test_the_hollowed_co_op_panel_is_the_retail_stream_with_nothing_to_draw():
    prefix = 'data' + B + 'aptui' + B + shell.PANEL + '.'
    files = dict(apt_textures.hollow('Apt.big', prefix))
    get = apt_textures.mapxml._archive_get('Apt.big')
    for ext in ('manifest', 'relo', 'imp'):                                  # nothing moves: the stream's tables are retail's
        retail = get(prefix + ext)
        assert files[prefix + ext] == (apt_textures.mapxml.refpack.decompress(retail)
                                       if apt_textures.mapxml.refpack.is_refpack(retail) else retail)
    retail_bin = get(prefix + 'bin')
    if apt_textures.mapxml.refpack.is_refpack(retail_bin):
        retail_bin = apt_textures.mapxml.refpack.decompress(retail_bin)
    assert len(files[prefix + 'bin']) == len(retail_bin) and b's tc:' in retail_bin
    assert b's tc:' not in files[prefix + 'bin'] and b'RenderImage' in files[prefix + 'bin']   # no shape text left, the movie's names stay


def test_the_briefing_narration_events_are_renamed_to_ours_with_the_same_length_and_a_label_each():
    old = b'MA04_AlliedIntel02'
    new = shell.new_event(old)
    assert len(new) == len(old) and new == b'CNV_SHELL_I_040200' and shell.EVENT.fullmatch(old) and not shell.EVENT.fullmatch(new)
    strings = shell.narration_strings(shell.missions())
    assert 'DIALOGEVENT:CNV_SHELL_I_040200' in strings and strings['DIALOGEVENT:CNV_SHELL_I_040100'].startswith('（占位旁白）')


@needs_game
def test_the_objective_briefing_plays_no_retail_narration_after_the_rename():
    prefix = 'data' + B + 'aptui' + B + 'a04_objective_briefing.'
    files = dict(apt_textures.patch('Apt.big', prefix, {}, (shell.EVENT, shell.new_event)))
    data = files[prefix + 'bin']
    assert not shell.EVENT.search(data) and b'CNV_SHELL_I_010100' in data and b'$DIALOGEVENT:CNV_SHELL_I_040100' in data.upper()
