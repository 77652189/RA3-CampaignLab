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
import re
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
        by_event, self.retail = {}, {}
        for lv in self.levels:
            with open(os.path.join(pack.DELIVERED, 'zh', str(lv).upper(), 'manifest.json'), encoding='utf-8') as f:
                entries = json.load(f)
            by_event.update({e['event']: e for e in entries if e.get('event')})
            self.retail.update({(e['who'], e['text']): e['eva'] for e in entries if e.get('eva') and not e.get('event')})
        known = self._retail_events() if self.retail else None
        for ev in sorted(set(self.retail.values())):
            if known is not None and ev not in known:
                self.missing.append(f'{ev} (retail announcer): not a retail audio event')
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

    def eva(self, who, text):
        """The retail event of an announcer line that is retail's own (a manifest entry with `eva` and no `event`:
        'Aeva_CritUnitUnderAtt'), or None. It is played as it is in both editions: the international one runs on the
        English retail game, the Chinese one on the Chinese voice mod, which dubs the same retail event."""
        return self.retail.get((str(who), str(text)))

    def _retail_events(self):
        """The retail AudioEvent ids (the SDK's SageXML/Sounds/Voice.xml), the names an eva line may play."""
        from experimental.campaign import labpaths
        path = os.path.join(labpaths.SDK3, 'SageXML', 'Sounds', 'Voice.xml')
        if not os.path.exists(path):
            return None
        with open(path, encoding='utf-8', errors='replace') as f:
            return set(re.findall(r'<AudioEvent id="(\w+)"', f.read()))

    def _make(self):
        if self.made is None:
            self.made = self.pack.make(self.levels, lang=self.lang, folder=self.folder, items=self.items)
        return self.made

    include = property(lambda self: self._make().include)
    files = property(lambda self: self._make().files)
    check = property(lambda self: self._make().check)
