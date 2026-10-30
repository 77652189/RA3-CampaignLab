"""A voice pack: our dubbed lines in the shape a mod build takes them (the interface with the mission builds, like
experimental/music/pack.py; the voice line's side is RA3-ChineseVoice docs/campaign_voice.md).

The voice line delivers RA3-ChineseVoice/work/campaign/<lang>/<level>/CNV_<id>.wav + manifest.json. Each line becomes an
AudioFile (the SDK's own encoder makes it XAS) and an AudioEvent of the same name, as retail's mission dialogue does
(SageXML/Sounds/MissionDialogue.xml): a script plays it with PLAY_SOUND_EFFECT('CNV_A4_007') and waits with
HAS_FINISHED_AUDIO('CNV_A4_007'); its subtitle is the string DIALOGEVENT:CNV_A4_007.

  pack = make(['a4'], lang='zh') or make(test=True): the one line CNV_TEST_001, for the bench probe
  pack.include                  'DATA:CNVVoice/Data/voice.xml'   (the static mod.xml, type="all")
  pack.files                    [(big path, bytes)]   the encoded audio (cdata)
  pack.events                   the event names (what PLAY_SOUND_EFFECT / HAS_FINISHED_AUDIO may name)
  pack.strings                  {'DIALOGEVENT:CNV_A4_007': text}  (for the mission's string table)
  pack.check(files)             the spliced streams hold our AudioFiles and the big their audio

The encoded audio is not part of the spliced streams (splice_assets takes manifest / bin / relo / imp only), so
make() compiles voice.xml on its own first, under the SDK build lock, and takes the cdata from that build; the
mission build compiles the same XML into its stream (same input, same instance hashes, so the same cdata names).
In the game (voice_bench 2026-10-29): a new AudioFile's audio is read from data\\static.12\\cdata (the top patch stream
splice_assets adds new instances to; with the audio in data\\static\\cdata only, the line "finished" in 4 frames), the
subtitle shows by itself, HAS_FINISHED_AUDIO fires.
"""
import json
import os
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field

from experimental.campaign import labpaths

FOLDER = 'CNVVoice'
VOICE = os.path.join(labpaths.LAB, 'RA3-ChineseVoice')
DELIVERED = os.path.join(VOICE, 'work', 'campaign')
BUILT = os.path.join(VOICE, 'work', 'sdkb')     # short: the SDK's audio encoder fails past 260 characters
CDATA_DIRS = ('data\\static.12\\cdata',)
TEST = ('CNV_TEST_001', os.path.join(VOICE, 'work', 'voice_design', 'allied_eva', 'ref_0.wav'),
        '冰墙已就位。侦测到敌军正在集结。车队即将出发。')

# retail's BaseSoundEffect with BaseMissionEvaDialogue over it, written out: a mod stream cannot inherit from an
# instance it only references (BinaryAssetBuilder: "attempts to inherit from ... non-existing instance")
DIALOGUE = ('Volume="75" MinVolume="70" ShrunkenPitchModifier="2.0" ShrunkenVolumeModifier="85" Priority="CRITICAL" '
            'Limit="1" MinRange="300" MaxRange="1000" PlayPercent="100" Type="UI PLAYER VOICE" ReverbEffectLevel="100" '
            'ZoomedInOffscreenVolumePercent="50" ZoomedInOffscreenMinVolumePercent="100" '
            'ZoomedInOffscreenOcclusionPercent="20" SubmixSlider="VOICE" Control="FADE_ON_KILL"')
DIALOGUE_SLIDERS = ''.join(f'\t\t<VolumeSliderMultiplier Slider="{s}" Multiplier="{m}" />\n'
                           for s, m in (('VOICE', '0.4'), ('SOUNDFX', '0.7'), ('MUSIC', '0.7'), ('AMBIENT', '0.7')))


@dataclass
class Pack:
    include: str
    files: list = field(default_factory=list)
    events: set = field(default_factory=set)
    strings: dict = field(default_factory=dict)

    def check(self, files):
        """files: the mod's [(big path, bytes)] after splice_assets; exits unless every AudioFile of ours is in a
        spliced manifest and its audio in the big."""
        from ra3voice import manifest, refpack
        got = dict(files)
        unpack = lambda b: refpack.decompress(b) if refpack.is_refpack(b) else b
        found = set()
        for path, data in got.items():
            if path.endswith('.manifest'):
                for a in manifest.parse(unpack(data)):
                    if a.name.startswith('AudioFile:CNV_'):
                        found.add(a.short_name)
                        leaf = f'{a.type_id:08x}.{a.type_hash:08x}.{a.inst_id:08x}.{a.inst_hash:08x}.cdata'
                        if not any(f'{d}\\{leaf}' in got for d in CDATA_DIRS):
                            sys.exit(f'voice: no audio in the big for {a.name}')
        missing = self.events - found
        if missing:
            sys.exit(f'voice: not in the spliced streams: {sorted(missing)[:5]} ...')
        print(f'voice: {len(found)} lines spliced, audio in the big')


def lines(levels, lang='zh'):
    """[(event, wav, text)] of the delivered lines of `levels` in `lang` (work/campaign/<lang>/<LEVEL>/manifest.json;
    announcer lines that play a retail announcer event have no file of ours and are left out). An event is named the
    same in every language: another language is a pack of its own (a patch), its audio and subtitles over ours."""
    out = []
    for lv in levels:
        here = os.path.join(DELIVERED, lang, lv.upper())
        with open(os.path.join(here, 'manifest.json'), encoding='utf-8') as f:
            for e in json.load(f):
                if e.get('event'):
                    out.append((e['event'], os.path.join(here, e['event'] + '.wav'), e['text']))
    return out


def xml(items, folder=FOLDER):
    body = ''.join(f'\t<AudioFile id="{ev}" File="AUDIO:{folder}/{ev}.wav" PCCompression="XAS" '
                   f'SubtitleStringName="DIALOGEVENT:{ev}" />\n'
                   f'\t<AudioEvent id="{ev}" {DIALOGUE}>\n{DIALOGUE_SLIDERS}\t\t<Sound>{ev}</Sound>\n\t</AudioEvent>\n'
                   for ev, _, _ in items)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">\n{body}</AssetDeclaration>\n'


RATE = 48000    # every retail voice and dialogue AudioFile is 48 kHz. A 24 kHz line of ours (its header said 24000,
                # correctly) took ~3x its length to finish in the game (voice_bench_12 2026-10-29: 212 frames for 4.8 s);
                # suspected the engine's handling of other rates, so we give it retail's


def to_48k(src, dst):
    """The voice line's 16-bit mono WAV -> 16-bit mono at RATE (what the encoder takes)."""
    import numpy as np
    from math import gcd
    from scipy.signal import resample_poly
    with wave.open(src) as w:
        assert (w.getsampwidth(), w.getnchannels()) == (2, 1), f'{src}: not 16-bit mono'
        sr, x = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64)
    if sr != RATE:
        g = gcd(sr, RATE)
        x = resample_poly(x, RATE // g, sr // g)
    with wave.open(dst, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(np.clip(np.round(x), -32768, 32767).astype('<i2').tobytes())


def make(levels=(), test=False, lang='zh', folder=FOLDER):
    """Copy the WAVs under <SDK>/Audio/<folder>, write <SDK>/Mods/<folder>/Data/voice.xml, compile it alone (for the
    encoded audio) and return the Pack."""
    items = ([TEST] if test else []) + lines(levels, lang)
    audio = os.path.join(labpaths.SDK3, 'Audio', folder)
    data = os.path.join(labpaths.SDK3, 'Mods', folder, 'Data')
    os.makedirs(audio, exist_ok=True)
    os.makedirs(data, exist_ok=True)
    for ev, wav, _ in items:
        to_48k(wav, os.path.join(audio, ev + '.wav'))
    with open(os.path.join(data, 'voice.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(xml(items, folder))
    with open(os.path.join(data, 'mod.xml'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<AssetDeclaration xmlns="uri:ea.com:eala:asset" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                '\t<Tags></Tags>\n\t<Includes>\n'
                '\t\t<Include type="reference" source="DATA:static.xml" />\n'
                '\t\t<Include type="reference" source="DATA:global.xml" />\n'
                '\t\t<Include type="reference" source="DATA:audio.xml" />\n'
                f'\t\t<Include type="all" source="DATA:{folder}/Data/voice.xml" />\n'
                '\t</Includes>\n</AssetDeclaration>\n')
    _compile(os.path.join(data, 'mod.xml'), folder)
    cdata = os.path.join(BUILT, 'mods', folder.lower(), 'data', 'mod', 'cdata')
    files = [(f'{d}\\{name}', open(os.path.join(cdata, name), 'rb').read())
             for name in sorted(os.listdir(cdata)) if name.endswith('.cdata') for d in CDATA_DIRS]
    events = {ev for ev, _, _ in items}
    assert len(files) == len(events) * len(CDATA_DIRS), f'voice: {len(files)} audio files for {len(events)} lines'
    return Pack(f'DATA:{folder}/Data/voice.xml', files, events, {f'DIALOGEVENT:{ev}': text for ev, _, text in items})


def _compile(mod_xml, folder):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'testbench'))
    import slots
    # one SDK build at a time; a mission build calls make() while it holds the lock itself, and waiting for it then
    # waits for ourselves (bench 2026-10-29: voice_bench sat on the lock for an hour)
    held = slots._held(os.path.join(slots.LOCKS, 'sdk-build.json'))
    release = (lambda: None) if held and held.get('pid') == os.getpid() else slots.build_lock(f'voice pack {folder}')
    try:
        shutil.rmtree(os.path.join(BUILT, 'mods', folder.lower()), ignore_errors=True)
        r = subprocess.run([os.path.join(labpaths.SDK3, 'tools', 'BinaryAssetBuilder.exe'), mod_xml,
                            f'/od:{BUILT}', f'/iod:{BUILT}', '/ls:true', '/gui:false', '/pc:true', '/vf:false', '/el:0'],
                           cwd=labpaths.SDK3, capture_output=True, text=True, errors='replace')
    finally:
        release()
    log = os.path.join(BUILT, f'_build_{folder}.log')
    with open(log, 'w', encoding='utf-8') as f:
        f.write(r.stdout + r.stderr)
    if r.returncode or 'BinaryAssetBuilder complete' not in r.stdout:
        sys.exit('voice: BinaryAssetBuilder failed, see ' + log)
