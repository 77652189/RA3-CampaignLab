"""The optional talking-head clip of a dubbed line (experimental/cnv/clips.py): no mp4 beside the recording is no clip and
no failure; an mp4 with a current .vp6 is the line's clip (the movie id is the line's event); a plan with a clip plays
it in the radar window with the line."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
import clips  # noqa: E402


def test_a_line_without_an_mp4_has_no_clip_and_nothing_goes_missing(tmp_path):
    wav = tmp_path / 'CNV_A4_090.wav'
    wav.write_bytes(b'')
    missing = []
    c = clips.Clips({'CNV_A4_090': str(wav)}, missing)
    assert c.find('CNV_A4_090') is None and c.find('CNV_A4_001') is None
    assert not c and missing == []


def test_an_mp4_with_a_current_vp6_is_the_lines_clip(tmp_path):
    (tmp_path / 'video').mkdir()
    wav = tmp_path / 'CNV_A4_090.wav'
    wav.write_bytes(b'')
    mp4, vp6 = tmp_path / 'video' / 'CNV_A4_090.mp4', tmp_path / 'video' / 'CNV_A4_090.vp6'
    mp4.write_bytes(b'')
    vp6.write_bytes(b'x')
    os.utime(mp4, (1, 1))
    os.utime(vp6, (2, 2))
    c = clips.Clips({'CNV_A4_090': str(wav)}, [])
    assert c.find('CNV_A4_090') == 'CNV_A4_090' and c.clips == {'CNV_A4_090': str(vp6)} and c


def test_an_mp4_that_cannot_be_converted_is_listed_not_a_failed_build(tmp_path):
    (tmp_path / 'video').mkdir()
    wav = tmp_path / 'CNV_A4_090.wav'
    wav.write_bytes(b'')
    (tmp_path / 'video' / 'CNV_A4_090.mp4').write_bytes(b'not a video')
    missing = []
    c = clips.Clips({'CNV_A4_090': str(wav)}, missing)
    assert c.find('CNV_A4_090') is None and len(missing) == 1 and missing[0].startswith('video of CNV_A4_090')
