"""The campaign shell probe (experimental/cnv/shell.py, ADR 0014): a retail APT screen with our picture in it keeps every other
byte of the stream, the template edits land where intended, and the mod's name is one the game starts with."""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'cnv'))
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experimental' / 'video'))
import apt_textures  # noqa: E402
import package  # noqa: E402  (experimental/cnv)
import make_campnew2 as c2  # noqa: E402
import shell  # noqa: E402

B = chr(92)
ARCHIVE = Path(c2.splice_assets.DATA) / 'Apt.big'
needs_game = pytest.mark.skipif(not ARCHIVE.exists(), reason='no game install')


def test_the_mod_name_is_one_the_game_starts_with():
    assert len(shell.NAME) <= 15 and re.fullmatch(r'[A-Za-z0-9]+', shell.NAME)


@needs_game
def test_a_picture_written_over_a_texture_changes_nothing_else_in_the_stream():
    from PIL import Image
    prefix = 'data' + B + 'aptui' + B + 'a01_objective_briefing.'
    size = apt_textures.textures('Apt.big', prefix)['apt_A01_Objective_Briefing_2']
    files = dict(apt_textures.patch('Apt.big', prefix, {'apt_A01_Objective_Briefing_2': Image.new('RGBA', size, (255, 0, 0, 255))}))
    for ext in ('manifest', 'relo', 'imp'):              # sizes unchanged: the stream's tables are the retail ones
        retail = apt_textures.mapxml._archive_get('Apt.big')(prefix + ext)
        assert files[prefix + ext] == (apt_textures.mapxml.refpack.decompress(retail)
                                       if apt_textures.mapxml.refpack.is_refpack(retail) else retail)
    assert len(files[prefix + 'bin']) == 4497584 and b'\xff\x00\x00\xff' not in files[prefix + 'bin'][:140]


@needs_game
def test_a_picture_of_the_wrong_size_is_refused():
    from PIL import Image
    prefix = 'data' + B + 'aptui' + B + 'a01_objective_briefing.'
    with pytest.raises(AssertionError):
        apt_textures.patch('Apt.big', prefix, {'apt_A01_Objective_Briefing_2': Image.new('RGBA', (8, 8))})


def test_the_template_takes_allies_1s_place_with_the_shell_fields(tmp_path, monkeypatch):
    sdk = Path(c2.SDK)
    if not (sdk / 'SageXML' / 'GlobalData' / 'CampaignTemplates.xml').exists():
        pytest.skip('no SDK')
    monkeypatch.setattr(c2, 'SRC_DIR', str(tmp_path))
    monkeypatch.setattr(c2, 'SHELL', {'attrs': {'OverviewTalkingHead': 'HEADX', 'IntroMovie:FileName': 'INTROX',
                                                'IntroMovie:Description': 'MissionDesc:CNV01'}})
    c2.sources()
    xml = (tmp_path / f'{c2.NAME}.xml').read_text(encoding='ascii')
    assert 'OverviewTalkingHead="HEADX"' in xml and 'FileName="INTROX"' in xml
    intro = re.search(r'<IntroMovie.*?</IntroMovie>', xml, re.S).group(0)
    assert 'MissionDesc:CNV01' in intro and 'AFS01' not in intro
    assert 'CommanderDescription:Coop_AlliedSquadronLeader' in xml             # the AICommander's Description is not the intro's
    camp = re.search(r'<CampaignTemplate.*?</CampaignTemplate>', xml, re.S).group(0)
    missions = re.findall(r'<Mission>([^<]*)</Mission>', camp)
    assert missions == ['Allies_New'] + [f'Allies_S{k}' for k in range(2, 10)]         # every slot is ours, unlocked
    assert xml.count('<Prerequisite>0</Prerequisite>') == 9
    assert 'A01_Objective_Briefing' in xml                                    # the briefing screens are Allies_1's: free to repaint


def test_the_built_mission_takes_its_own_slot_and_every_slot_has_its_labels(tmp_path, monkeypatch):
    sdk = Path(c2.SDK)
    if not (sdk / 'SageXML' / 'GlobalData' / 'CampaignTemplates.xml').exists():
        pytest.skip('no SDK')
    monkeypatch.setattr(c2, 'SRC_DIR', str(tmp_path))
    monkeypatch.setattr(c2, 'SHELL', {'slot': 4, 'attrs': {'AICommander:Description': 'CommanderDescription:CNV04'},
                                      'others': {k: {'AICommander:Description': f'CommanderDescription:CNV0{k}'} for k in (1, 2, 3, 5, 6, 7, 8, 9)},
                                      'no_portrait': True})
    c2.sources()
    xml = (tmp_path / f'{c2.NAME}.xml').read_text(encoding='ascii')
    camp = re.search(r'<CampaignTemplate.*?</CampaignTemplate>', xml, re.S).group(0)
    assert re.findall(r'<Mission>([^<]*)</Mission>', camp) == ['Allies_S1', 'Allies_S2', 'Allies_S3', 'Allies_New'] + \
        [f'Allies_S{k}' for k in range(5, 10)]
    for k in range(1, 10):
        assert xml.count(f'DisplayName="MissionName:CNV0{k}"') == 1 and f'CommanderDescription:CNV0{k}"' in xml
    commanders = re.findall(r'<AICommander\b[^>]*>', xml)
    assert len(commanders) >= 9 and not any('Portrait=' in c for c in commanders)
    assert xml.count(c2.NEW_DIR + c2.NEW_STEM + '.map') == 1                  # only the built mission has our map
    assert 'CAMP_A04_Gibraltar_Hayes' not in xml and 'CAMP_A01_' in xml       # slot 4 is ours, slot 1 is retail's map


def test_the_nine_missions_have_names_and_two_objectives_each():
    info = shell.missions()
    assert sorted(info) == list(range(1, 10))
    for k, m in info.items():
        assert m['title'] and 0 < len(m['short']) <= 6 and len(m['objectives']) == 2 and 0 < len(m['briefing']) <= 100, k
    assert shell.slot_of('CampA4') == 4 and shell.slot_of('CampA7East') == 7
    assert shell.label(4) == 'CNV04' and shell.intro_id(4) == 'CNVINTRO04'
    assert len(shell.intro_id(9)) == len('CNVINTRO01')                           # video ids keep their length


@needs_game
def test_the_hollowed_co_op_panel_is_the_retail_stream_with_nothing_to_draw():
    prefix = 'data' + B + 'aptui' + B + shell.PANEL + '.'
    files = dict(apt_textures.hollow('Apt.big', prefix))
    get = apt_textures.mapxml._archive_get('Apt.big')
    for ext in ('manifest', 'relo', 'imp'):                                  # nothing moves: the stream's tables are retail's
        retail = get(prefix + ext)
        assert files[prefix + ext] == (apt_textures.mapxml.refpack.decompress(retail)
                                       if apt_textures.mapxml.refpack.is_refpack(retail) else retail)
    retail_bin = get(prefix + 'bin')
    if apt_textures.mapxml.refpack.is_refpack(retail_bin):
        retail_bin = apt_textures.mapxml.refpack.decompress(retail_bin)
    assert len(files[prefix + 'bin']) == len(retail_bin) and b's tc:' in retail_bin
    assert b's tc:' not in files[prefix + 'bin'] and b'RenderImage' in files[prefix + 'bin']   # no shape text left, the movie's names stay


def test_the_briefing_narration_events_are_renamed_to_ours_with_the_same_length_and_a_label_each():
    old = b'MA04_AlliedIntel02'
    new = shell.new_event(old)
    assert len(new) == len(old) and new == b'CNV_SHELL_I_040200' and shell.EVENT.fullmatch(old) and not shell.EVENT.fullmatch(new)
    assert shell.new_event(b'MA07_AlliedIntel10', 4) == b'CNV_SHELL_I_040500'        # the template's 5th line in slot 4
    info = shell.missions()
    strings = shell.narration_strings(info)
    assert strings['DIALOGEVENT:CNV_SHELL_I_040200'].endswith(info[4]['objectives'][0])


def _briefing(k):
    """Slot k's objective briefing as the shell builds it: (its movie, its .apt, the .apt + constants bytes)."""
    import apt_movie
    info = shell.missions()
    targets = shell.site_targets('sapporo', info[4]['targets']) if k == 4 else None
    files = dict(shell.objective_briefing(k, info[k]['short'], k == 4, targets=targets))
    prefix = shell.APT + f'a{k:02d}_objective_briefing.'
    (h, E, chunks, bufs), _ = apt_textures.mapxml.read_stream(prefix, lambda n: files[n])
    kinds = {apt_textures.mapxml.sa.cstr(bufs[2], e[6]).split(b':')[0]: c[0] for e, c in zip(E, chunks)}
    a, c = kinds[b'AptAptData'], kinds[b'AptConstData']
    (ao, al), (co, cl) = apt_movie.apt_of(a), apt_movie.apt_of(c)
    return apt_movie.movie(a[ao:ao + al], c[co:co + cl]), a[ao:ao + al], a + c


@needs_game
@pytest.mark.parametrize('k', range(1, 10))
def test_every_objective_briefing_zooms_onto_objective_1_points_arrows_and_ends_on_the_whole_map_with_both_marked(k):
    """I11 (K9): retail's structure in every slot -- the whole map, a zoom with arrows onto objective 1, back to the whole map
    with a route of arrows and both objectives marked inside the window; its five lines are this slot's and labelled."""
    import apt_movie
    m, apt, data = _briefing(k)
    inv = {v: n for n, v in m['imports'].items()}
    maps, marks, arrows = [], {}, []
    for it in apt_movie.placements(m, apt):
        if it.flags & apt_movie.HAS_MATRIX and it.char == 4 and it.depth == 2:
            maps.append((it.frame, it.matrix[0]))
        elif it.flags & apt_movie.HAS_CHARACTER and it.flags & apt_movie.HAS_MATRIX and inv.get(it.char, '').startswith('box'):
            marks[it.frame] = it.translate
        elif it.flags & apt_movie.HAS_CHARACTER and inv.get(it.char) == 'blue arrow thin':
            arrows.append(it.frame)
    whole = maps[-1][1]
    assert max(s for _, s in maps) > 1.5 * whole and abs(maps[0][1] - whole) < 0.02 * whole      # in, and back out
    assert any(200 <= f <= 470 for f in arrows) and any(f >= 479 for f in arrows)              # zoom arrows, route arrows
    w, h = shell.SCREEN
    assert len({f for f in marks if f >= 479}) >= 2 and all(20 < x < w - 20 and 20 < y < h - 20 for x, y in marks.values())
    played = set(re.findall(rb'CNV_SHELL_I_%02d\d\d00' % k, data))
    strings = shell.narration_strings(shell.missions())
    assert len(played) == 5 and all(f'DIALOGEVENT:{p.decode()}' in strings for p in played)
    assert not shell.EVENT.search(data)


@pytest.fixture
def edition():
    """Switch the shell's words to an edition for one test; the Chinese one again afterwards."""
    yield shell.use_lang
    shell.use_lang('zh')


def test_the_english_missions_are_the_chinese_ones_translated_slot_for_slot(edition):
    zh = shell.missions()
    edition('intl')
    en = shell.missions()
    assert sorted(en) == sorted(zh) and len(en) == 9
    for k, m in en.items():
        assert len(m['objectives']) == len(zh[k]['objectives']) == 2 and m['title'] and m['short'] and m['briefing'], k
        assert not re.search(r'[\u4e00-\u9fff]', ' '.join([m['title'], m['short'], m['briefing'], *m['objectives']])), k


def test_the_shell_made_for_the_international_edition_has_only_english_words(edition):
    sp = shell.make('x', 'CampA4En', 'intl')
    assert sp.slot == 4 and shell.TITLE.startswith('Sapporo') and shell.slot_of('CampA4En') == 4
    words = [v for k, v in sp.strings.items() if not k.startswith('DIALOGEVENT')] + list(sp.overrides.values())
    assert not [w for w in words if re.search(r'[\u4e00-\u9fff]', w)]
    assert sp.overrides['MONITOR:ONGUARD'] == ' ' and sp.overrides['MISSIONNAME:SOVIETS_3'].endswith('(placeholder)')
    assert 'APT:SOVIET_FACTION_DESCRIPTION' in sp.overrides and 'APT:JAPANESE_FACTION_DESCRIPTION' in sp.overrides


def test_the_chapter_thumbnails_are_a_file_per_slot_in_retail_map_folders_and_ours():
    files = dict(shell.thumbnails({k: ('占位', k == 4, (0, 0)) for k in range(1, 10)}))
    small = {n: v for n, v in files.items() if not n.endswith('_art.tga')}
    assert len(files) == 18 and len(small) == 9 and all(v[:3] == b'\x00\x00\x02' and v[12:16] == b'\x80\x00\x80\x00' for v in small.values())   # 128 x 128
    assert all(v[12:16] == b'\x00\x02\x00\x02' and v[16] == 24 for n, v in files.items() if n not in small)     # the art: 512 x 512, 24 bits
    assert B.join(['data', 'maps', 'official', 'camp_cnv01_probe', 'camp_cnv01_probe.tga']) in files
    assert B.join(['data', 'maps', 'official', 'camp_a01_brightonbeach_smith', 'camp_a01_brightonbeach_smith.tga']) in files
    assert not [n for n in files if 'gibraltar' in n]                                        # slot 4 is ours, retail's map is not replaced


def test_the_launcher_has_two_edition_buttons_remembers_the_last_and_starts_that_mods_skudef(tmp_path):
    import launcher
    hta = Path(launcher.write_launcher(str(tmp_path))).read_bytes()
    assert hta[:3] == b'\xef\xbb\xbf'                                        # the BOM mshta needs for the Chinese
    text = hta.decode('utf-8-sig')
    assert '中文版' in text and '国际版' in text and 'last_edition.txt' in text and '"intl"' in text
    assert 'CampShellEn_1.0.skudef' not in text and 'MOD + "En_1.0.skudef"' in text and '@' not in text.replace('@SHORTCUT', '')
    assert launcher.MOD == shell.NAME


def test_the_commander_overview_shows_no_retail_commander_in_either_edition(edition):
    for lang in ('zh', 'intl'):
        sp = shell.make('x', 'CampA4', lang)
        assert sp.prefix_overrides == {'PERSONALITY:': '—'} and sp.overrides['APT:COCOMMANDER_NAME_TITLE'] == shell.T['notes_title']


@needs_game
def test_the_co_op_panel_no_longer_asks_the_engine_to_draw_the_commanders_picture():
    prefix = 'data' + B + 'aptui' + B + shell.PANEL + '.'
    files = dict(apt_textures.hollow('Apt.big', prefix, (shell.PORTRAIT_CALL, lambda old: old[:-1] + b'x')))
    (h, E, chunks, bufs), _ = apt_textures.mapxml.read_stream(prefix, lambda n: files[n])
    consts = [c[0] for k, c in enumerate(chunks) if apt_textures.mapxml.sa.cstr(bufs[2], E[k][6]).startswith(b'AptConstData:')][0]
    assert b'RenderImagx' in consts and b'RenderImage\x00' not in consts


@needs_game
def test_every_slots_world_map_points_at_its_own_place():
    """K9 / I10: the overview's marker is computed from the slot's `where`, for every slot (not a hand-placed point)."""
    import apt_movie
    for k, m in shell.missions().items():
        prefix = 'data' + B + 'aptui' + B + f'a{k:02d}_global_briefing.'
        (h, E, chunks, bufs), raw = apt_textures.mapxml.read_stream(prefix, apt_textures.mapxml._archive_get('Apt.big'))
        a, c = chunks[0][0], chunks[1][0]
        (ao, al), (co, cl) = apt_movie.apt_of(a), apt_movie.apt_of(c)
        apt, const = a[ao:ao + al], c[co:co + cl]
        new = shell.retarget(m['where'])(apt, const)
        assert len(new) == len(apt)
        got, want = shell.marked(apt_movie.movie(new, const), new), shell.grid(*m['where'])
        period = 360 * shell.GRID['px_lon']
        assert abs((got[0] - want[0] + period / 2) % period - period / 2) < 1 and abs(got[1] - want[1]) < 1, (k, got, want)


@needs_game
def test_the_chapter_lists_faction_icons_are_all_repainted():
    """K9 / I12: no pixel of a retail faction icon is left in either copy of the chapter list's component."""
    for stem, boxes in shell.ICON_BOXES.items():
        orig = apt_textures.originals('Apt.big', 'data' + B + 'aptui' + B + stem + '.')
        (tex, img), = orig.items()
        new = shell.faction_icons(img, boxes)
        alpha = img.getchannel('A').point(lambda v: 255 if v else 0)
        changed = [p for p in zip(img.convert('RGBA').getdata(), new.getdata(), alpha.getdata()) if p[2] and p[0] == p[1]]
        assert len(changed) < 0.02 * sum(1 for v in alpha.getdata() if v), stem


def test_the_talking_head_is_made_at_retails_size():
    import to_vp6  # noqa: F401  (experimental/video)
    assert to_vp6.SIZES['head'] == shell.HEAD_SIZE == (512, 288)


# package.build_mod (ADR 0016): the one outlet of packaging pours a ModSpec into the make_campnew pipeline and puts the
# pipeline's globals back afterwards, so two builds in one process do not carry into each other.


def test_with_more_appends_tuples_and_merges_dicts():
    spec = package.ModSpec(name='CampX', extra_own=(b'a',), strings={'A': '1', 'B': '2'}, slot=None)
    more = package.with_more(spec, extra_own=[b'b'], strings={'B': '3', 'C': '4'}, slot={'slot': 4})
    assert more.extra_own == (b'a', b'b') and list(more.strings.items()) == [('A', '1'), ('B', '3'), ('C', '4')]
    assert more.slot == {'slot': 4} and spec.extra_own == (b'a',) and spec.strings == {'A': '1', 'B': '2'}


def test_two_builds_in_one_process_do_not_carry_over(tmp_path, monkeypatch):
    import importlib
    chain = [importlib.import_module(n) for n in package.CHAIN]
    c2, c3, c4, c6, c7, c18 = chain
    if not os.path.isdir(c2.SDK):
        pytest.skip('no SDK')
    seen = []
    monkeypatch.setattr(package, 'sdk_build_lock', lambda name: (lambda: None))

    def main():                                 # what the pipeline would build from, instead of building it
        seen.append((c2.NAME, c2.OUT, list(c7.EXTRA_OWN), list(c7.EXTRA_ALL), dict(c3.STRINGS), c2.SHELL,
                     list(c4.EXTRA_FILES), list(c2.EXTRA_STATIC)))
        os.makedirs(c4.OUT)
    monkeypatch.setattr(c4, 'main', main)
    before = {m: dict(vars(m)) for m in chain}
    own_before, strings_before = list(c7.EXTRA_OWN), dict(c3.STRINGS)
    spec = package.ModSpec(name='CampX', extra_own=(b'GameObject:X',), extra_all=('DATA:x.xml',),
                           strings={'NAME:X': 'x'}, slot={'slot': 4}, big_files=(('data\\x', b'x'),))
    for k in range(2):
        package.build_mod(spec, str(tmp_path / f'out{k}'))
    assert seen[0][2:] == seen[1][2:], 'the second build saw what the first one added'
    assert seen[0][0] == 'CampX' and seen[0][2][-1] == b'GameObject:X' and seen[0][5] == {'slot': 4}
    assert seen[0][4]['NAME:X'] == 'x' and ('data\\x', b'x') in seen[0][6]
    for m in chain:                             # every global back to the object it was, with its contents
        now = vars(m)
        assert set(now) == set(before[m]), m.__name__
        assert all(now[k] is v for k, v in before[m].items() if k != 'main'), m.__name__
    assert c7.EXTRA_OWN == own_before and c3.STRINGS == strings_before


def test_a_spec_without_launcher_leaves_no_bat(tmp_path, monkeypatch):
    import importlib
    c2, c4 = importlib.import_module('make_campnew2'), importlib.import_module('make_campnew4')
    if not os.path.isdir(c2.SDK):
        pytest.skip('no SDK')
    monkeypatch.setattr(package, 'sdk_build_lock', lambda name: (lambda: None))

    def main():                                 # the pipeline writes its launcher next to the skudef
        os.makedirs(c4.OUT)
        open(os.path.join(c4.OUT, f'Play_{c4.NAME}.bat'), 'w').close()
    monkeypatch.setattr(c4, 'main', main)
    for launcher in (True, False):
        out = str(tmp_path / str(launcher))
        package.build_mod(package.ModSpec(name='CampX', launcher=launcher), out)
        assert os.path.isfile(os.path.join(out, 'Play_CampX.bat')) == launcher


def test_layers_go_on_in_order_after_the_mission():
    from missions import liberty_bench
    seen = []

    def layer(tag):
        def add(spec):
            seen.append((tag, len(spec.map_edits)))
            return package.with_more(spec, map_edits=(tag,))
        return add
    spec = package.spec_of(liberty_bench.mission(riders=True), layers=(layer('a'), layer('b')))
    assert seen == [('a', 1), ('b', 2)] and spec.map_edits[1:] == ('a', 'b')


def _written(spec):
    import make_campnew18 as c18
    from mapscript import MapFile
    m = MapFile(next(d for p, d in c18.c6._map_files() if p.lower().endswith('.map')))
    for e in spec.map_edits:
        e(m)
    objs = next(n for _, n in m.walk() if n.name == 'ObjectsList')
    return m.script_text(), m.trigger_areas(), len(objs.kids)


def test_a_check_as_a_layer_writes_the_map_the_merged_build_writes():
    """build.py --shell --check (ADR 0016 phase 2): the check rides on the plain mission as a layer, and the map it
    writes has the scripts, trigger areas and objects of the check merged into the mission (build.py --check)."""
    import build
    m, t, _ = build.resolve('a4', 'win')
    layer = package.check_layer(m, t)
    merged, layered = package.spec_of(m, t), package.spec_of(m, layers=(layer,))
    assert _written(layered) == _written(merged)
    assert layered.strings == merged.strings and layered.unit_files == merged.unit_files
    # only a shell build tells the bench a slot to walk into; the release build's sidecar stays as it was
    assert layer(package.ModSpec(name='x', slot={'slot': 4})).bench == {'slot': 4}
    assert merged.bench == {} and layered.bench == {}
