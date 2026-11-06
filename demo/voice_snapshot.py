"""The demo's stand-in for the voice repository.

Compiling a plan asks the sibling voice repository which recording each spoken line plays, how long it is (a scene waits
for it) and whether the line has a talking-head clip. A clean laptop has none of that, so `make()` (run once, where the
voice repository is) saves those answers to work/demo/voice_snapshot.json -- no audio, no clips, only the routing rows,
the lengths in seconds and the names of the lines that have a clip -- and `install()` makes the plan compiler read them
instead. The demo always uses the snapshot, so its numbers are the same on every machine.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = [os.path.join(ROOT, 'demo', 'voice_snapshot.json'), os.path.join(ROOT, 'work', 'demo', 'voice_snapshot.json')]
KEYS = ('event', 'who', 'audio_lang', 'exists', 'interim', 'subtitle_lang', 'subtitle')
LEVELS = ('A4', 'ICEENG')


def make(out=CANDIDATES[1], level='a4'):
    """Needs the voice repository beside this one (and its recordings, for their lengths)."""
    import wave
    import clips
    import langs
    import plan
    snap = dict(route={}, groups={}, lengths={}, clips=[])
    for lv in LEVELS:
        snap['groups'][lv] = langs.unit_groups(lv)
        for lang in ('zh', 'intl'):
            rows = []
            for e in langs.route(lv, lang):
                row = {k: e[k] for k in KEYS}
                row['wav'] = f'snapshot/{e["event"]}.wav' if e['wav'] else None
                rows.append(row)
                if e['wav'] and lang == 'zh' and os.path.exists(e['wav']):
                    with wave.open(e['wav']) as w:
                        snap['lengths'][e['event']] = w.getnframes() / w.getframerate()
                if e['wav'] and lang == 'zh' and clips.Clips({e['event']: e['wav']}, []).find(e['event']):
                    snap['clips'].append(e['event'])
            snap['route'][f'{lv}/{lang}'] = rows
    c = plan.Compiler(plan.load(level))
    assert c.voice is not None and c.voice.items            # the real thing compiles before it is frozen
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=0)
    return out


def find():
    return next((p for p in CANDIDATES if os.path.exists(p)), None)


def install(path):
    import clips
    import langs
    import voice_link
    snap = json.load(open(path, encoding='utf-8'))
    langs.route = lambda level, lang: snap['route'][f'{str(level).upper()}/{lang}']
    langs.unit_groups = lambda level: snap['groups'].get(str(level).upper(), {})

    def length(self, who, text):
        ev = self.find(who, text)
        return snap['lengths'].get(ev) if ev else None

    def clip(self, ev):
        if (self.only is not None and ev not in self.only) or ev not in snap['clips']:
            return None
        self.clips[ev] = f'snapshot/{ev}.vp6'
        return ev
    voice_link.Later.length = length
    clips.Clips.find = clip


if __name__ == '__main__':
    sys.path[:0] = [os.path.join(ROOT, 'experimental', 'cnv'), os.path.join(ROOT, 'experimental', 'campaign')]
    print(make())
