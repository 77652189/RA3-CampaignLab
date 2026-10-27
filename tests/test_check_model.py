"""check_model.py: a good model passes, and each check catches a model broken on purpose (a checker that has never
caught anything proves nothing -- game-asset-aesthetic-test's blocky-qa rule)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'experimental' / 'campaign'))
sys.path.insert(0, str(ROOT / 'experimental' / 'units'))
import check_model  # noqa: E402
import w3x  # noqa: E402

TEX = ('Probe', 'Probe_NRM', 'Probe_SPM')
UNIT = '<Turret TurretNameKey="Bone_Turret" TurretPitch="Bone_turret_pitch"/><WeaponLaunchBone BoneName="Muzzle"/>'


def box(x0, y0, z0, x1, y1, z1):
    v, n, uv, t = w3x.box(x0, y0, z0, x1, y1, z1)
    return v, n, [(min(max(a, 0.0), 1.0), min(max(b, 0.0), 1.0)) for a, b in uv], t


def model(tmp_path, parts=None, pivots=None, edit=None):
    pivots = pivots or [('Bone_Turret', 0, (0.0, 0.0, 4.0)), ('Bone_Turret_Pitch', 1, (1.0, 0.0, 1.0)),
                        ('Muzzle', 2, (4.0, 0.0, 0.0))]
    parts = parts or [('Hull', 0, box(-5, -3, 0, 5, 3, 4)), ('Turret', 1, box(-2, -2, 0, 2, 2, 2)),
                      ('Barrel', 2, box(0, -0.3, -0.3, 4, 0.3, 0.3))]
    text = w3x.rig_model('Probe', pivots, parts, TEX)
    if edit:
        text = edit(text)
    art = tmp_path / 'Art'
    (art / 'PR').mkdir(parents=True)
    for t in TEX:
        (art / 'PR' / f'{t}.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<AssetDeclaration xmlns="uri:ea.com:eala:asset">'
            f'<Texture id="{t}" File="{t}.tga"/></AssetDeclaration>\n', encoding='utf-8')
    path = art / 'PR' / 'Probe.w3x'
    path.write_text(text, encoding='utf-8')
    return str(path), str(art)


def findings(tmp_path, unit=UNIT, **kw):
    path, art = model(tmp_path, **kw)
    return check_model.check(path, unit, budget=200, art=art)


def errors(found):
    return [m for lv, m in found if lv == 'error']


def test_good_model_passes(tmp_path):
    assert findings(tmp_path) == []


def test_missing_bone_named_by_the_unit(tmp_path):
    found = findings(tmp_path, pivots=[('Bone_Turret', 0, (0.0, 0.0, 4.0)), ('Pitch', 1, (1.0, 0.0, 1.0)),
                                       ('Muzzle', 2, (4.0, 0.0, 0.0))])
    assert any('bone Bone_turret_pitch' in m for m in errors(found))


def test_no_collision_box(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace(
        '\t\t<SubObject SubObjectID="OBBOX01" BoneIndex="0">\n'
        '\t\t\t<RenderObject><CollisionBox>PROBE.OBBOX01</CollisionBox></RenderObject>\n\t\t</SubObject>\n', ''))
    assert any('cannot be clicked' in m for m in errors(found))


def test_triangle_index_out_of_range(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace('<V>0</V>', '<V>999</V>', 1))
    assert any('index past' in m for m in errors(found))


def test_missing_texture(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace('<Value>Probe_SPM</Value>', '<Value>Probe_SPEC</Value>', 1))
    assert any('texture Probe_SPEC not declared' in m for m in errors(found))


def test_broken_include(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace('ART:Probe_NRM.xml', 'ART:Probe_NORMAL.xml'))
    assert any('include ART:Probe_NORMAL.xml not found' in m for m in errors(found))


def test_unparsable(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace('</W3DContainer>', ''))
    assert any('does not parse' in m for m in errors(found))


def test_z_fighting_between_parts(tmp_path):
    # a plate lying exactly on the hull's top face (z = 4): same plane, same facing, overlapping
    plate = box(-1, -1, 3.5, 1, 1, 4)
    found = findings(tmp_path, parts=[('Hull', 0, box(-5, -3, 0, 5, 3, 4)), ('Plate', 0, plate),
                                      ('Turret', 1, box(-2, -2, 0.5, 2, 2, 2)),
                                      ('Barrel', 2, box(0, -0.3, -0.3, 4, 0.3, 0.3))])
    assert any('z-fighting' in m and 'HULL' in m and 'PLATE' in m for _, m in found)


def test_no_z_fighting_when_lifted(tmp_path):
    plate = box(-1, -1, 3.5, 1, 1, 4.1)          # 0.1 above the hull top: no shared plane
    found = findings(tmp_path, parts=[('Hull', 0, box(-5, -3, 0, 5, 3, 4)), ('Plate', 0, plate),
                                      ('Turret', 1, box(-2, -2, 0.5, 2, 2, 2)),
                                      ('Barrel', 2, box(0, -0.3, -0.3, 4, 0.3, 0.3))])
    assert not any('z-fighting' in m for _, m in found)


def test_texcoords_outside_atlas(tmp_path):
    found = findings(tmp_path, edit=lambda t: t.replace('<TexCoords>\n\t\t\t<T X="', '<TexCoords>\n\t\t\t<T X="3', 1))
    assert any('outside 0..1' in m for lv, m in found if lv == 'warn')


def test_over_budget(tmp_path):
    big = [('Hull', 0, w3x.merge(*[box(-5 + k, -3, 0, -4.5 + k, 3, 4) for k in range(20)]))]
    found = findings(tmp_path, parts=big + [('Turret', 1, box(-2, -2, 0.5, 2, 2, 2)),
                                            ('Barrel', 2, box(0, -0.3, -0.3, 4, 0.3, 0.3))])
    assert any('over the budget' in m for _, m in found)
