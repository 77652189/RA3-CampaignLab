"""Our units built where retail builds their kind (a plan's 可造: {兵营: [冰幕工兵]}): copies of retail's production
buildings whose command set is retail's list plus a build button for each of ours, and a copy of the construction
yard that builds those copies instead of retail's.

Retail's own command sets are not overridden (a map-stream copy of a static-stream instance is untested, CampNew26):
the copies get ids of their own, the mission places them for the player instead of retail's (plan.py), and the yard's
copy builds the copies, so a barracks the player builds later has our units too. What builds retail's yard (the MCV
unpacking, the crane) still makes retail's: missions that give the player one are not covered yet.

Nothing in retail requires a barracks, a war factory or an airfield by name, except the yard's tech-upgrade beam (a
looks-only line drawn to them) and Japan's base defence (JapanBarracks): Japan's buildings are cores, not covered.

Published: building(retail, units, id) and yard(retail, copies, id), each a Unit; what they were made from.
"""
import os
import re

import make_campnew2 as c2
from parts import Unit
from units.icewall import sub1

SAGE = os.path.join(c2.SDK, 'SageXML')
FACTIONS = ('Allied', 'Soviet')
_sets = None


def retail_xml(id):
    """Retail's GameObject file for a structure id (Allied/Structures/AlliedBarracks.xml ...)."""
    for f in FACTIONS:
        p = os.path.join(SAGE, f, 'Structures', id + '.xml')
        if os.path.exists(p):
            return open(p, encoding='utf-8').read()
    raise ValueError(f'{id}: not a retail structure of {FACTIONS} (Japan builds from cores: not covered)')


def commands(set_id):
    """A retail LogicCommandSet's commands, in order, its inheritFrom first."""
    global _sets
    if _sets is None:
        x = open(os.path.join(SAGE, 'GlobalData', 'LogicCommandSet.xml'), encoding='utf-8').read()
        _sets = re.sub(r'<!--.*?-->', '', x, flags=re.S)
    mm = re.search(rf'<LogicCommandSet\s+id="{set_id}"(?:\s+inheritFrom="([^"]+)")?\s*>(.*?)</LogicCommandSet>',
                   _sets, re.S)
    assert mm, f'no retail LogicCommandSet {set_id}'
    return (commands(mm.group(1)) if mm.group(1) else []) + re.findall(r'<Cmd>([^<]+)</Cmd>', mm.group(2))


def _copy(retail, id):
    x = retail_xml(retail)
    x = sub1(x, f'id="{retail}"', f'id="{id}"')
    x = x.replace(f'EditorName="{retail}"', f'EditorName="{id}"')
    return x


def _set(id, cmds):
    return f'\t<LogicCommandSet id="{id}">\n' + ''.join(f'\t\t<Cmd>{c}</Cmd>\n' for c in cmds) + '\t</LogicCommandSet>\n'


def _command(kind, cmd, obj):
    return f'\t<LogicCommand Type="{kind}" id="{cmd}">\n\t\t<Object>{obj}</Object>\n\t</LogicCommand>\n'


def _append(x, decl, includes):
    x = sub1(x, '</AssetDeclaration>', decl + '</AssetDeclaration>')
    inc = ''.join(f'\n\t\t<Include type="all" source="DATA:CNVUnits/Data/{f}.xml" />' for f in includes)
    return sub1(x, '<Includes>', '<Includes>' + inc) if inc else x


def building(retail, units, id):
    """retail's building (AlliedBarracks ...) with a build button for each of `units` (Unit ids) after its own."""
    x = _copy(retail, id)
    old = re.search(r'\bCommandSet="([^"]+)"', x).group(1)
    assert len(re.findall(r'\bCommandSet="', x)) == 1, f'{retail}: more command sets than one (an upgrade swaps it)'
    mine = f'{id}CommandSet'
    x = sub1(x, f'CommandSet="{old}"', f'CommandSet="{mine}"')
    own = [f'Command_Construct{u}' for u in units]
    decl = ''.join(_command('UNIT_BUILD', c, u) for c, u in zip(own, units)) + _set(mine, commands(old) + own)
    x = _append(x, decl, units)
    return Unit(id, x, link=[f'LogicCommandSet:{mine}'] + [f'LogicCommand:{c}' for c in own],
                what=f'{retail} 的复制，生产列表多了 {"、".join(units)}', params=dict(retail=retail, units=list(units)))


def yard(retail, copies, id):
    """retail's construction yard building `copies` ({retail building: its copy's id}) in their places."""
    x = _copy(retail, id)
    sets = re.findall(r'\bCommandSet="([^"]+)"', x)     # its own, and the one its tech upgrade swaps in
    own = {r: f'Command_Construct{c}' for r, c in copies.items()}
    decl = ''.join(_command('CONSTRUCTION_YARD_CONSTRUCT', own[r], c) for r, c in copies.items())
    links = [f'LogicCommand:{c}' for c in own.values()]
    for s in dict.fromkeys(sets):
        cmds = [own.get(c[len('Command_Construct'):], c) if c.startswith('Command_Construct') else c
                for c in commands(s)]
        missing = [r for r in copies if own[r] not in cmds]
        assert not missing, f'{retail} ({s}) does not build {missing}'
        x = x.replace(f'CommandSet="{s}"', f'CommandSet="{id}{s}"')
        decl += _set(f'{id}{s}', cmds)
        links.append(f'LogicCommandSet:{id}{s}')
    x = _append(x, decl, list(copies.values()))
    return Unit(id, x, link=links, what=f'{retail} 的复制，造的是 {"、".join(copies.values())}',
                params=dict(retail=retail, copies=dict(copies)))
