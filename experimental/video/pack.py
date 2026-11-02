"""A video pack: our own .vp6 clips in the shape a mod build takes them (the interface with the mission builds, like
experimental/music/pack.py and experimental/voice/pack.py). The level line's experiment of 2026-11-01: can a mission
play a movie of ours, in the radar window (MOVIE_PLAY_RADAR, 288x288) and full screen (MOVIE_PLAY_FULLSCREEN, 1280x720)?

Retail's way (SDK SageXML/Video): a `<Video id="A01TH01" Filename="A01TH01" Volume="190"/>` and a
`<VideoEventList id="A01TH01"><EventList><Movie MovieAsset="A01TH01"/>`; the file is Data\\Movies\\A01TH01.vp6 (EA's
MVhd container, vp60 video; the radar clips 288x288, 23.976 fps, no audio chunks: retail plays the sound as a mission
dialogue line next to it). Ours: the same two declarations in the mod's static stream, the .vp6 in the mod's big under
`data\\movies\\<id>.vp6` (where retail's is on disk).

  pack = make({'CNVTEST01': path-to-vp6, ...})
  pack.include   'DATA:CNVVideo/Data/video.xml'
  pack.files     [(big path, bytes)]
  pack.events    the ids (what MOVIE_PLAY_* / HAS_FINISHED_VIDEO may name)
  pack.strings   {}   pack.check(files): the big holds every clip
"""
import os
from dataclasses import dataclass, field

from experimental.campaign import labpaths

FOLDER = 'CNVVideo'
MOVIES = 'data\\movies'


@dataclass
class Pack:
    include: str
    files: list = field(default_factory=list)
    events: set = field(default_factory=set)
    strings: dict = field(default_factory=dict)

    def check(self, files):
        have = {p.lower() for p, _ in files}
        missing = [e for e in sorted(self.events) if f'{MOVIES}\\{e}.vp6'.lower() not in have]
        if missing:
            raise SystemExit(f'video: not in the big: {missing}')
        print(f'video: {len(self.events)} clips in the big')


def xml(ids, volume=190):
    body = ''.join(f'\t<Video id="{i}" Filename="{i}" Volume="{volume}" />\n'
                   f'\t<VideoEventList id="{i}">\n\t\t<EventList>\n\t\t\t<Movie MovieAsset="{i}" />\n\t\t</EventList>\n'
                   '\t</VideoEventList>\n' for i in ids)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n{body}</AssetDeclaration>\n'


def make(clips, folder=FOLDER):
    """clips: {id: path of a .vp6}. Writes <SDK>/Mods/<folder>/Data/video.xml and returns the Pack."""
    data = os.path.join(labpaths.SDK3, 'Mods', folder, 'Data')
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, 'video.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml(clips))
    files = []
    for i, path in clips.items():
        with open(path, 'rb') as f:
            files.append((f'{MOVIES}\\{i}.vp6', f.read()))
    return Pack(f'DATA:{folder}/Data/video.xml', files, set(clips))
