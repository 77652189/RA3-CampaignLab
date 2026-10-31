"""Fetch the part of VSCO-2 Community Edition (CC0, github.com/sgossner/VSCO-2-CE) that sampler.py plays into
work/music/vsco2: the string sections, the brass, the woodwinds, the harp, the glockenspiel, timpani, drums and
cymbals, the first round-robin take of each (about 770 MB), at a pinned commit, every file checked against the
tree's size.

  python -I -X utf8 experimental/music/fetch_samples.py
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from experimental.music import sampler  # noqa: E402

REPO, SHA = 'sgossner/VSCO-2-CE', '440300901dfe9275fd84e0b7763af1f8443ae62e'
WANT = re.compile(r'^(Strings/(Violin Section/(Spic|susVib|Trem)/|Viola Section/(spic|susvib)/|Cello Section/'
                  r'(spic|susvib|trem)/)|Brass/(F Horn/(sus|stac)/|Trumpet/(sus|stac)/|Tenor Trombone/(sus|stac)/|Tuba/)|'
                  r'Percussion/(Timpani/Timpani|BDrumNewhit|cymbal-crash|susCymb1-(cresc|hit_)|gongHit|'
                  r'Snare2-(HitSN|rollSN))|VSCO 1 Percussion/drums/tenor|LICENSE|README|'
                  r'Woodwinds/(Flute/(susvib|stac)/|Oboe/(Vib|Stacc)/|Clarinet/(susLong|stac)/|Bassoon/(sus|stac)/)|'
                  r'Strings/Harp/|Percussion/Glock/)')
SECOND_TAKES = re.compile(r'rr[2-9]|_2\.wav', re.I)


def tree():
    url = f'https://api.github.com/repos/{REPO}/git/trees/{SHA}?recursive=1'
    return [(e['size'], e['path']) for e in json.load(urllib.request.urlopen(url, timeout=60))['tree']
            if e['type'] == 'blob' and WANT.match(e['path']) and not SECOND_TAKES.search(e['path'])]


def get(row):
    size, path = row
    out = os.path.join(sampler.LIB, *path.split('/'))
    if os.path.exists(out) and os.path.getsize(out) == size:
        return None
    os.makedirs(os.path.dirname(out), exist_ok=True)
    url = f'https://raw.githubusercontent.com/{REPO}/{SHA}/' + urllib.parse.quote(path)
    err = 'size mismatch'
    for _ in range(3):
        try:
            data = urllib.request.urlopen(url, timeout=120).read()
            if len(data) == size:
                open(out, 'wb').write(data)
                return None
        except OSError as e:
            err = e
    return f'{path}: {err}'


def main():
    rows = tree()
    with ThreadPoolExecutor(8) as ex:
        bad = [r for r in ex.map(get, rows) if r]
    print('\n'.join(bad) or 'ok', len(rows) - len(bad), 'of', len(rows), 'files in', sampler.LIB)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
