"""A4's music (experimental/music/a4.py) and the jump rules it is played by (ownmap.timeline): the map sends every
mission event to its section, a playthrough goes through the transitions the story needs, jumps without PREP land
on a segment's end and PREP cuts at once; the synthesizer's loops have no seam."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from experimental.music import a4, ownmap, pfdx, synth  # noqa: E402

RETAIL = ROOT / 'work' / 'music' / 'retail'


@pytest.fixture(scope='module')
def music():
    if not (RETAIL / 'map.bin').exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    names = json.loads((RETAIL / 'event_hashes.json').read_text())
    base = pfdx.parse((RETAIL / 'map.bin').read_bytes(), names)
    b, secs, lengths = a4.music_map(base)
    m = pfdx.parse(pfdx.build(b.build([(k, ms) for k, ms in enumerate(lengths)])), names)
    owner = [name for name, _ in a4.stream_ms()]
    return m, secs, owner


def _play(m, secs, owner, fires, seconds):
    return [(t0, t1, owner[s]) for t0, t1, s in ownmap.timeline(m, secs['prep'].entry, fires, seconds)]


def test_every_mission_event_goes_to_its_section(music):
    m, secs, _ = music
    by_name = {e.name: e for e in m.events}
    for event, section, prep in a4.EVENTS.values():
        if section is None:
            continue                                    # calm: test_calm_goes_back_to_the_convoy_s_leg
        acts = by_name[event].actions
        assert acts[-1] == (ownmap.TRACK, ownmap.GOTO, 0x00FF0000 | secs[section].entry), event
        assert (acts[0][1] == ownmap.PREP) == prep, event


def test_playthrough_follows_the_story(music):
    m, secs, owner = music
    fires = [(t, a4.EVENTS[k][0]) for t, k, _ in a4.PLAYTHROUGH if k != 'start']
    order = []
    for _, _, s in _play(m, secs, owner, fires, a4.PLAYTHROUGH_SECONDS):
        if not order or order[-1] != s:
            order.append(s)
    assert order == ['prep', 'prep>escort', 'escort', 'ambush', 'fierce', 'fierce>tense', 'tense', 'tense>fierce',
                     'fierce', 'battle>escort', 'escort', 'harbour', 'fierce', 'fierce>tense', 'tense', 'tense>fierce',
                     'fierce', 'battle>final', 'final', 'victory']


def test_calm_goes_back_to_the_convoy_s_leg(music):
    """Threat1_1 (the game: the fighting is over) goes to escort or final, whichever leg the mission last named:
    the map keeps it in a variable (SET), Threat1_1 asks it (IF / ELSE)."""
    m, secs, owner = music
    ev = {k: a4.EVENTS[k][0] for k in ('escort', 'final', 'ambush', 'calm')}
    for leg in ('escort', 'final'):
        rows = _play(m, secs, owner, [(1.0, ev[leg]), (12.0, ev['ambush']), (30.0, ev['calm'])], 60)
        assert rows[-1][2] == leg and any(s == 'battle>' + leg for _, _, s in rows), leg


def test_the_game_s_advantage_events_switch_the_battle_music(music):
    """The dynamic system's events (fired by the game, not the mission) go between the two battle loops through
    their transitions, from either side."""
    m, secs, owner = music
    names = {k: a4.EVENTS[k][0] for k in ('ambush', 'winning', 'losing', 'even')}
    fires = [(1.0, names['ambush']), (20.0, names['losing']), (40.0, names['winning']), (60.0, names['losing']),
             (80.0, names['even'])]
    order = []
    for _, _, s in _play(m, secs, owner, fires, 100):
        if not order or order[-1] != s:
            order.append(s)
    assert order == ['prep', 'ambush', 'fierce', 'fierce>tense', 'tense', 'tense>fierce', 'fierce', 'fierce>tense',
                     'tense', 'tense>fierce', 'fierce']


def test_plain_jumps_wait_for_the_segment_and_prep_cuts(music):
    m, secs, owner = music
    seg = a4.SEG_BARS * a4.BAR
    rows = _play(m, secs, owner, [(12.3, a4.EVENTS['escort'][0])], 40)
    t = next(t0 for t0, _, s in rows if s == 'prep>escort')
    assert t == pytest.approx(15.0) and t % seg == pytest.approx(0)       # 12.3 s waits for the segment ending at 15
    rows = _play(m, secs, owner, [(12.3, a4.EVENTS['ambush'][0])], 40)
    assert next(t0 for t0, _, s in rows if s == 'ambush') == pytest.approx(12.3)
    assert next(t0 for t0, _, s in rows if s == 'fierce') == pytest.approx(12.3 + a4.BAR)


def test_victory_stops_the_music(music):
    m, secs, owner = music
    rows = _play(m, secs, owner, [(3.0, a4.EVENTS['win'][0])], 120)
    assert rows[-1][2] == 'victory' and rows[-1][1] < 20


SCRIPT_EVENTS = ROOT.parent / 'sdk' / 'RA3ModSDK3' / 'SageXML' / 'PathMusic' / 'ScriptPathMusicEvents.xml'


def test_every_cue_is_an_event_a_script_can_fire():
    """PATH_MUSIC_PLAY_EVENT plays only the events of the sdk's script set (bench 2026-10-26, CampA4Win: four cues
    on events outside it did nothing, the win cue on S_EndMissionWin played)."""
    if not SCRIPT_EVENTS.exists():
        pytest.skip('needs the mod SDK (sdk/RA3ModSDK3)')
    import re
    script = set(re.findall(r'<Event>([^<]+)</Event>', SCRIPT_EVENTS.read_text(encoding='utf-8')))
    assert {a4.EVENTS[key][0] for key in a4.CUES.values()} <= script
    fired_by_the_game = {a4.EVENTS[k][0] for k in ('combat', 'losing', 'even', 'winning', 'calm')}
    assert not fired_by_the_game & {a4.EVENTS[key][0] for key in a4.CUES.values()}


def test_the_shell_plays_retail_music_as_retail_does():
    """The menus, briefing and score screen keep retail's music (a4.SHELL, ownmap.Builder.keep): each shell event
    reaches copies of the retail nodes it reached, every one of them, the same graph by branches, playing streams
    after ours that are the retail streams of the originals; none of our sections is reached, none reaches ours."""
    if not (RETAIL / 'map.bin').exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    base = pfdx.parse((RETAIL / 'map.bin').read_bytes(), json.loads((RETAIL / 'event_hashes.json').read_text()))
    b, secs, lengths = a4.music_map(base)
    ours = len(a4.stream_ms())
    first_kept = max(s.exit for s in b.sections) + 1                       # our nodes come first
    assert all(n.stream is None or n.stream < ours for n in b.m.nodes[:first_kept])
    assert all(n.stream is None or n.stream >= ours for n in b.m.nodes[first_kept:])

    def reach(m, start):
        seen, todo = {}, [start]
        while todo:
            i = todo.pop()
            if i == 0xFFFF or i in seen:
                continue
            n = m.nodes[i]
            seen[i] = n
            todo += [t for _, _, t in n.branches] + ([n.ref] if n.is_segment else [])
        return seen

    for name in a4.SHELL:
        old = [a for a in next(e for e in base.events if e.name == name).actions]
        new = next(e for e in b.m.events if e.name == name).actions
        assert [(h, op) for h, op, _ in old] == [(h, op) for h, op, _ in new], name
        for (_, op, x), (_, _, y) in zip(old, new):
            if op != ownmap.GOTO:
                assert x == y
                continue
            a, c = reach(base, x & 0xFFFF), reach(b.m, y & 0xFFFF)
            assert len(a) == len(c) and min(c) >= first_kept, name
            for i, j in zip(sorted(a), sorted(c)):
                p, q = a[i], c[j]
                assert (p.kind, len(p.branches), [(lo, hi) for lo, hi, _ in p.branches]) == \
                       (q.kind, len(q.branches), [(lo, hi) for lo, hi, _ in q.branches])
                if p.is_segment:
                    assert b.kept[q.stream - ours] == p.stream and lengths[q.stream] == base.samples[p.stream][1]
    assert len(lengths) == ours + len(b.kept)


def test_kept_streams_are_the_retail_streams_the_map_names():
    """extract.retail_streams reads the stream the retail sample table points at (its SNS offset / 0x80)."""
    from experimental.music import extract, mus
    if not (RETAIL / 'track.cdata').exists():
        pytest.skip('run experimental/music/extract.py first (needs the game)')
    base = pfdx.parse((RETAIL / 'map.bin').read_bytes(), json.loads((RETAIL / 'event_hashes.json').read_text()))
    rows = mus.read_directory((RETAIL / 'track.cdata').read_bytes())
    kept = a4.music_map(base)[0].kept
    for s, (snr, sns) in zip(kept, extract.retail_streams(kept)):
        assert rows[s]['sns'] // 0x80 == base.samples[s][0]
        assert mus.duration_ms(snr) == base.samples[s][1] and len(sns) == rows[s]['sns_size']


def test_sections_are_mixed_to_the_retail_balance():
    """synth.match: a section's broad spectrum ends up within a few dB of its retail kind's (a4.REFERENCE) in the
    bands both have music in, its stereo no wider than the reference's."""
    tilt = lambda v: np.convolve(np.pad(v, 2, mode='edge'), np.array([1, 2, 3, 2, 1]) / 9, 'valid')
    for name in ('tense', 'fierce'):
        bands, side_mid = a4.REFERENCE[a4.REFERENCE_OF[name]]
        got, sm = synth.profile(a4.render(name))
        mids = slice(3, 25)                                          # 50 Hz .. 8 kHz
        assert np.abs(tilt(got)[mids] - tilt(np.array(bands))[mids]).max() < 4.0, name
        assert sm < side_mid + 1.0, name


@pytest.mark.skipif(not a4.RECORDED, reason='the recorded instruments (sampler.available())')
def test_the_choir_is_heard(monkeypatch):
    """The user heard no choir at first (2026-10-28: it sat 20-34 dB under the rest): where it sings, its loudest
    half-second is within 8 dB of everything else."""
    from experimental.music import sampler
    real = sampler.choir
    for name in ('prep', 'tense', 'fierce', 'final'):
        full = a4.render(name)
        monkeypatch.setattr(sampler, 'choir', lambda *a, **k: real(*a, **k) * 0.0)
        rest = a4.render(name)
        monkeypatch.setattr(sampler, 'choir', real)
        w = int(0.5 * synth.RATE)
        db = lambda x: 10 * np.log10((x ** 2).mean() + 1e-20)
        assert max(db(full[i:i + w] - rest[i:i + w]) - db(rest[i:i + w])
                   for i in range(0, len(full) - w, w)) > -8, name


def test_streams_are_as_long_as_the_map_says():
    x = a4.render('ambush')
    assert len(x) * 1000 // synth.RATE == dict(a4.stream_ms())['ambush']


def test_a_loop_has_no_seam():
    """The section played twice: the step across its end is no bigger than steps inside it."""
    x = a4.render('prep')
    steps = np.abs(np.diff(x, axis=0)).max(axis=1)
    assert np.abs(x[0] - x[-1]).max() <= np.percentile(steps, 99.9)
