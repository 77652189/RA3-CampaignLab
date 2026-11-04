"""The video pack (experimental/video/pack.py): our .vp6 clips declared like retail's (a Video and a VideoEventList of the
same id) and carried in the mod's big under data\\movies, as retail's sit on disk."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
sys.path.insert(0, str(ROOT))
from experimental.video import pack  # noqa: E402


def test_a_clip_is_declared_as_a_video_and_a_video_event_list_of_one_id():
    x = pack.xml(['CNVTEST01'])
    assert '<Video id="CNVTEST01" Filename="CNVTEST01" Volume="190" />' in x
    assert '<VideoEventList id="CNVTEST01">' in x and '<Movie MovieAsset="CNVTEST01" />' in x


def test_the_pack_puts_the_clip_in_the_big_where_retails_are_and_checks_it_is_there(tmp_path, monkeypatch):
    clip = tmp_path / 'a.vp6'
    clip.write_bytes(b'MVhd')
    monkeypatch.setattr(pack.labpaths, 'SDK3', str(tmp_path / 'sdk'))
    p = pack.make({'CNVTEST01': str(clip)})
    assert p.files == [('data\\movies\\CNVTEST01.vp6', b'MVhd')] and p.events == {'CNVTEST01'}
    assert (tmp_path / 'sdk' / 'Mods' / 'CNVVideo' / 'Data' / 'video.xml').exists()
    p.check(p.files)
    with pytest.raises(SystemExit):
        p.check([])


def test_a_later_pack_writes_video_xml_only_when_the_build_takes_it(tmp_path, monkeypatch):
    clip = tmp_path / 'a.vp6'
    clip.write_bytes(b'MVhd')
    monkeypatch.setattr(pack.labpaths, 'SDK3', str(tmp_path / 'sdk'))
    p = pack.Later({'CNVTEST01': str(clip)})
    xml = tmp_path / 'sdk' / 'Mods' / 'CNVVideo' / 'Data' / 'video.xml'
    assert p.events == {'CNVTEST01'} and not xml.exists()      # made outside build_mod's lock: nothing written yet
    assert p.include == 'DATA:CNVVideo/Data/video.xml' and xml.exists()
