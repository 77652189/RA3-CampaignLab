"""Exercise the library command on a tiny SDK and probe exports."""

import json

from experimental.mapgen import library


def test_library_groups_inherits_and_reports_missing_sources(tmp_path, monkeypatch, capsys):
    sdk, work = tmp_path / "sdk", tmp_path / "probes"
    sage = sdk / "SageXML"

    def write(path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def xml(relative, content):
        write(sage / relative, f'<AssetDeclaration xmlns="uri:ea.com:eala:asset">{content}</AssetDeclaration>')

    xml("BaseObjects/Base.xml", """
        <GameObject id="Intermediate" inheritFrom="base"/>
        <GameObject id="Base"><Geometry IsSmall="false">
            <PlacementShape Type="BOX" MajorRadius="14" MinorRadius="8"/>
            <Shape Type="BOX" MajorRadius="10" MinorRadius="6">
                <Offset x="2" y="-3" z="0"/>
            </Shape>
            <Shape Type="CYLINDER" MajorRadius="4"/>
        </Geometry></GameObject>""")
    xml("Civilian/First_AA/Buildings/Home.xml", '<GameObject id="AA_Home" inheritFrom="INTERMEDIATE"/>')
    xml("Civilian/Second_BB/Optimized_Props/Wall.xml", '<GameObject id="AA_Wall"/>')
    xml("Civilian/Second_BB/Destructible_Props/Crate.xml", '<GameObject id="BB_Crate"/>')
    xml("Terrain/Terrain.xml", """
        <TerrainAsset id="Paving" WBFolder="First" Class="Road" Texture="Paving.tga"/>
        <TerrainAsset id="Grass" WBFolder="First" Class="Grass" Texture="Grass.tga"/>""")

    # The mid-height crossing is at y=-10. The 16 aligned pieces give 15 spacings of 100.
    write(work / "mapgen_probe/cliffs.json", json.dumps([
        {"t": "aa_wall", "src": "game", "map": "sample", "x": x, "y": 0, "a": 0,
         "sx": {"-20": 78.4, "20": 78.4}, "sy": {"-20": 0, "0": 78.4, "20": 78.4}}
        for x in range(0, 1600, 100)
    ]))
    write(work / "mapgen_probe/setpieces.json", '{"units": {}, "groups": [{"id": "sample", "style_kit": "Second_BB"}]}')
    monkeypatch.setattr(library.labpaths, "SDK3", sdk)
    monkeypatch.setattr(library.labpaths, "WORK", work)
    library.main()
    output = work / "mapgen/library.json"
    data = json.loads(output.read_bytes())
    assert [(issue["kind"], issue["source"]) for issue in data["issues"]] == [
        ("missing_source", "work/logs/e266_prop_blocking.json"),
    ]
    assert "missing_source work/logs/e266_prop_blocking.json" in capsys.readouterr().out

    assert set(data["kits"]) == {"First_AA", "Second_BB"}
    house, = data["kits"]["First_AA"]["buildings"]
    geometry = house["geometry"]
    assert house["template"] == "AA_Home"
    assert house["source"] == "sdk/SageXML/Civilian/First_AA/Buildings/Home.xml"
    assert geometry["source"] == "sdk/SageXML/BaseObjects/Base.xml"
    assert geometry["footprint"] == [{"Type": "BOX", "MajorRadius": 14, "MinorRadius": 8}]
    assert geometry["shapes"] == [
        {"Type": "BOX", "MajorRadius": 10, "MinorRadius": 6, "Offset": {"x": 2, "y": -3, "z": 0}},
        {"Type": "CYLINDER", "MajorRadius": 4},
    ]
    second = data["kits"]["Second_BB"]
    assert [entry["template"] for entry in second["props"]] == ["AA_Wall"]
    assert [entry["template"] for entry in second["destructibles"]] == ["BB_Crate"]
    cliff, = second["cliffs"]
    assert (cliff["height_steps"], cliff["length"], cliff["offset_y"]) == (1, 100, -10)
    assert cliff["evidence"] == "measured_from_maps"
    assert [t["id"] for t in data["texture_kits"]["First"]["Road"]] == ["Paving"]
    assert [t["id"] for t in data["texture_kits"]["First"]["Grass"]] == ["Grass"]
    assert data["setpieces"]["groups"][0]["source"] == "work/mapgen_probe/setpieces.json"

    write(work / "logs/e266_prop_blocking.json", json.dumps([
        {"template": "AA_Wall", "cls": "all", "foot": "blocked", "vehicle": "blocked", "crush": "-",
         "basis": "台上（sample）"},
    ]))
    library.main()
    fresh = output.read_bytes()
    data = json.loads(fresh)
    assert not data["issues"]
    assert data["blocking"]["aa_wall"]["cls"] == "all"
    assert data["blocking"]["aa_wall"]["evidence"] == "benched"
    library.main()
    assert output.read_bytes() == fresh
