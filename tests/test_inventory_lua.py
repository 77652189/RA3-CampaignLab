"""Source evidence for LUAEventList's presentation-only inventory classification.

Inspect the installed retail Lua, not the SDK's older copy. This is a static
reader audit, not a bench comparison or a claim about arbitrary mod Lua.
"""
import importlib.util
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory', ROOT / 'experimental/cnv/inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
import labpaths  # noqa: E402
from ra3voice import big, refpack  # noqa: E402


def test_lua_event_lists_only_reach_model_visibility_readers():
    sdk = Path(labpaths.SDK3)
    game = Path(labpaths.GAME) / 'Data'
    if not (game / 'Misc.big').is_file() or not (sdk / 'SageXML').is_dir():
        pytest.skip('needs installed retail Lua and SDK object declarations')

    # Base assets followed by patch overrides; no writes into the game directory.
    archives = [game / 'Misc.big'] + sorted(
        game.glob('Core[0-9]*.big'), key=lambda p: int(p.stem[4:]))
    names = ['data\\scripts\\scriptevents.xml', 'data\\scripts\\scripts.lua']
    assets = {}
    for archive in archives:
        assets.update(big.read_files(archive, names))
    assert set(assets) == set(names)
    texts = {n: (refpack.decompress(b) if refpack.is_refpack(b) else b).decode('utf-8')
             for n, b in assets.items()}
    lists = {e.get('Name'): e for e in ET.fromstring(texts[names[0]])
             if e.tag.rsplit('}', 1)[-1] == 'EventList'}

    # Keep complete function bodies (including nested if/end), up to the next
    # top-level declaration. Last definition wins, as it does in retail Lua.
    lua = re.sub(r'--[^\r\n]*', '', texts[names[1]])
    declarations = list(re.finditer(r'^function\s+(\w+)\([^\r\n]*\)', lua, re.M))
    assert declarations
    functions = {m[1]: lua[m.end():declarations[i + 1].start() if i + 1 < len(declarations) else len(lua)]
                 for i, m in enumerate(declarations)}

    refs = set()
    count = 0
    for path in (sdk / 'SageXML').rglob('*.xml'):
        text = path.read_text(encoding='utf-8', errors='replace')
        for module in re.findall(r'<LUAEventList\b[^>]*?/>', text, re.S):
            element = ET.fromstring(module)
            assert set(element.attrib) == {'id', 'EventListName'}, path
            refs.add(element.attrib['EventListName'])
            count += 1
    assert count and refs
    # Retail Vindicator names an absent list; it cannot reach a handler through
    # that name. Do not silently treat any newly missing list as presentation.
    assert refs - lists.keys() == {'AlliedInfantryFightingFunctions'}
    reached = set()

    def visit(name, chain=()):
        assert name not in chain, (name, chain)
        element = lists[name]
        if element.get('Inherit'):
            visit(element.attrib['Inherit'], chain + (name,))
        for handler in element:
            assert handler.tag.rsplit('}', 1)[-1] == 'EventHandler'
            reached.add(handler.attrib['ScriptFunctionName'])

    for name in refs & lists.keys():
        visit(name)
    assert reached
    calls = set()
    for name in reached:
        assert name in functions, name
        body = re.sub(r'"[^"\r\n]*"|\'[^\'\r\n]*\'', '""', functions[name])
        used = set(re.findall(r'\b(\w+)\s*\(', body))
        assert used <= {'ObjectHideSubObjectPermanently', 'tostring'}, (name, used)
        calls.update(used)
    assert 'ObjectHideSubObjectPermanently' in calls
    # C&C3 functions that grant upgrades / set status exist in the file but are
    # deliberately excluded only because no RA3 module's list reaches them.
    assert 'OnGDIFirehawkCreated' not in reached
    assert inventory.NOTES[inventory.MODULE, 'Behaviors/LUAEventList'][0] == inventory.NA
    print(f'LUAEventList: {count} declarations, {len(refs)} list names, '
          f'{len(reached)} reachable handlers; calls={sorted(calls)}')
