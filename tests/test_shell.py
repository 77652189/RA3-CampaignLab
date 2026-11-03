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
    assert missions == ['Allies_New'] + [f'Allies_{k}' for k in range(2, 10)]
    assert 'A01_Objective_Briefing' in xml                                    # the briefing screens are Allies_1's: free to repaint
