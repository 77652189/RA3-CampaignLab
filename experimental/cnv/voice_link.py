"""A plan's dubbed lines (`语音: [A4, ICEENG]` at the top of a plan): the voice line's delivered manifests
(RA3-ChineseVoice/work/campaign/zh/<LEVEL>/manifest.json, read without compiling) say which lines exist; the pack
itself (experimental/voice/pack.make, ~25 s under the SDK build lock) is made only when a build takes its include,
files or check, as voice_bench.LazyPack does.

find(who, text): the mission-dialogue event of the line `who` says (text as in the lines table), or None -- the plan
then shows the subtitle alone, as it did before there was a voice. A unit voice (a line with a group) is the unit's own
event, not the plan's: it is in `events` (the contract) but never found by find().

lang: the edition (langs.py): 'zh', or 'intl' -- English subtitles, each speaker dubbed in their side's language. A line
whose audio or subtitle text is not delivered in that edition is left out and listed in `missing` (the build prints it).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Later:
    def __init__(self, levels, lang='zh', faction='盟军'):
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from experimental.voice import pack
        import langs
        self.pack, self.levels, self.lang, self.made = pack, list(levels), lang, None
        self.events, self.strings, self.said = set(), {}, {}
        for lv in self.levels:
            path = os.path.join(pack.DELIVERED, 'zh', str(lv).upper(), 'manifest.json')
            if not os.path.exists(path):
                raise FileNotFoundError(f'语音 {lv}: no delivered lines at {path}')
        self.items, self.missing = langs.lines(self.levels, lang, faction)
        self.folder = langs.voice_folder(lang)
        by_event = {}
        for lv in self.levels:
            with open(os.path.join(pack.DELIVERED, 'zh', str(lv).upper(), 'manifest.json'), encoding='utf-8') as f:
                by_event.update({e['event']: e for e in json.load(f) if e.get('event')})
        self.groups = {group for _, _, _, group in self.items if group}     # the unit voice events the pack has
        for ev, _, text, group in self.items:
            self.events.add(ev)
            if not group:
                self.strings[f'DIALOGEVENT:{ev}'] = text
                e = by_event[ev]
                self.said[(e['who'], e['text'])] = ev

    def __bool__(self):                 # an edition with none of its lines delivered has no pack to build
        return bool(self.items)

    def find(self, who, text):
        return self.said.get((str(who), str(text)))

    def _make(self):
        if self.made is None:
            self.made = self.pack.make(self.levels, lang=self.lang, folder=self.folder, items=self.items)
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)
