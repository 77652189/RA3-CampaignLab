"""Decode every stream of the retail track.mus to work/music/retail/wav/NNN.wav (stream index from 0) for study.

Needs extract.py first. Uses the vgmstream-cli the voice line already keeps (RA3-ChineseVoice/third_party/vgmstream);
nothing of it is copied here. Run: python -I experimental/music/decode_retail.py [first] [last]
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from experimental.campaign import labpaths  # noqa: E402

RETAIL = os.path.join(labpaths.WORK, 'music', 'retail')
WAV = os.path.join(RETAIL, 'wav')
CLI = os.path.join(labpaths.LAB, 'RA3-ChineseVoice', 'third_party', 'vgmstream', 'vgmstream-cli.exe')


def prepare():
    """vgmstream wants a bare .mpf next to a .mus of the same name."""
    mpf, mus = os.path.join(RETAIL, 'track.mpf'), os.path.join(RETAIL, 'track.mus')
    if not os.path.exists(mpf):
        d = open(os.path.join(RETAIL, 'map.bin'), 'rb').read()
        open(mpf, 'wb').write(d[d.find(b'xDFP'):])
    if not os.path.exists(mus):
        os.link(os.path.join(RETAIL, 'track.cdata'), mus)
    return mpf


def decode(mpf, i):
    out = os.path.join(WAV, f'{i:03d}.wav')
    if os.path.exists(out):
        return
    r = subprocess.run([CLI, '-i', '-s', str(i + 1), '-o', out, mpf], capture_output=True, text=True)
    if r.returncode:
        print(i, r.stdout[-200:], r.stderr[-200:])


def main():
    first = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    last = int(sys.argv[2]) if len(sys.argv) > 2 else 714
    os.makedirs(WAV, exist_ok=True)
    mpf = prepare()
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda i: decode(mpf, i), range(first, last + 1)))
    print('decoded', len(os.listdir(WAV)))


if __name__ == '__main__':
    main()
