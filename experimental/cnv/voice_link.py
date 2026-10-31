"""A plan's dubbed lines (`语音: [A4, ICEENG]` at the top of a plan): the voice line's delivered manifests
(RA3-ChineseVoice/work/campaign/zh/<LEVEL>/manifest.json, read without compiling) say which lines exist; the pack
itself (experimental/voice/pack.make, ~25 s under the SDK build lock) is made only when a build takes its include,
files or check, as voice_bench.LazyPack does.

find(who, text): the mission-dialogue event of the line `who` says (text as in the lines table), or None -- the plan
then shows the subtitle alone, as it did before there was a voice. A unit voice (a line with a group) is the unit's own
event, not the plan's: it is in `events` (the contract) but never found by find().
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Later:
    def __init__(self, levels, lang='zh'):
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from experimental.voice import pack
        self.pack, self.levels, self.lang, self.made = pack, list(levels), lang, None
        self.events, self.strings, self.said = set(), {}, {}
        for lv in self.levels:
            path = os.path.join(pack.DELIVERED, lang, str(lv).upper(), 'manifest.json')
            if not os.path.exists(path):
                raise FileNotFoundError(f'语音 {lv}: no delivered lines at {path}')
            with open(path, encoding='utf-8') as f:
                for e in json.load(f):
                    ev = e.get('event')
                    if not ev:
                        continue                            # an announcer line that plays a retail event
                    self.events.add(ev)
                    if not e.get('group'):
                        self.strings[f'DIALOGEVENT:{ev}'] = e['text']
                        self.said[(e['who'], e['text'])] = ev

    def find(self, who, text):
        return self.said.get((str(who), str(text)))

    def _make(self):
        if self.made is None:
            self.made = self.pack.make(self.levels, lang=self.lang)
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)
