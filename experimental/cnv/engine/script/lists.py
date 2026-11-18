"""A map's scripts as the public executor (engine/script/executor.py) runs them: per side a script list, each list's
items loose scripts and script groups (a group holds scripts and, in RA3, groups), any of them a subroutine
(docs/engine/script-semantics.md 1-2). The shapes are the ones the private model's loader gives too (its Content /
Script / Group / ScriptList), so retail.script_lists builds either executor's lists the same way.

Loaders: `from_cnv` our compiled scripts (one unnamed list); `from_mapfile` a .map's PlayerScriptsList (mapscript's
reader: `walk`, `string`, `content`), one list per side in file order."""
import dataclasses
import struct


@dataclasses.dataclass
class Content:
    """One condition or action: its name and arguments as plain values (str / int / float / tuple)."""
    name: str
    args: tuple = ()
    inverted: bool = False              # conditions only (block version >= 5; script-semantics.md 2)
    enabled: bool = True                # the export's first suffix word; INFERRED: a disabled one is skipped


@dataclasses.dataclass
class Script:
    name: str
    ors: list = dataclasses.field(default_factory=list)       # [[Content, ...] ANDed, ...] ORed; [] never true
    actions: list = dataclasses.field(default_factory=list)
    else_actions: list = dataclasses.field(default_factory=list)
    active: bool = True
    once: bool = True                   # deactivate upon success
    levels: tuple = (True, True, True)  # easy, normal, hard
    subroutine: bool = False
    interval: int = 0                   # seconds between evaluations (0 = every frame)


@dataclasses.dataclass
class Group:
    name: str
    items: list = dataclasses.field(default_factory=list)     # Script / Group
    active: bool = True
    subroutine: bool = False


@dataclasses.dataclass
class ScriptList:
    side: str                           # the player whose list it is ('' when unknown)
    items: list = dataclasses.field(default_factory=list)


def from_cnv(scripts, not_mark):
    """Our compiled scripts (model.Script: name / when / do / once / levels / active / sub / orelse): one unnamed
    list, one OR of the ANDed `when` each, an empty `when` written as CONDITION_TRUE (as parts.write_map does); a
    condition ending in `not_mark` an inverted Content."""
    out = []
    for s in scripts:
        when = [Content(c[0], tuple(c[1:-1]), inverted=True) if c and c[-1] == not_mark else
                Content(c[0], tuple(c[1:])) for c in s.when] or [Content('CONDITION_TRUE')]
        out.append(Script(s.name, [when], [Content(a[0], tuple(a[1:])) for a in s.do], once=s.once,
                          levels=tuple(s.levels), active=getattr(s, 'active', True),
                          subroutine=getattr(s, 'sub', False),
                          else_actions=[Content(a[0], tuple(a[1:])) for a in getattr(s, 'orelse', ())]))
    return [ScriptList('', out)]


def from_mapfile(m, sides=None):
    """A map's PlayerScriptsList (experimental/campaign/mapscript.MapFile) as ScriptLists, one per side in file order
    (sides: their player names, when known). Script header: 4 strings, then active, one-shot, easy, normal, hard,
    subroutine (u8 each), u32 evaluation interval (mapscript.new_script's layout); a group's: its name, active,
    subroutine."""
    def strings(head, n):
        p, out = 0, []
        for _ in range(n):
            s, p = m.string(head, p)
            out.append(s)
        return out, p

    def content(node):
        name, args, rest = m.content(node)
        vals = tuple(v for _, v in args)
        enabled = struct.unpack_from('<I', rest, 0)[0] if len(rest) >= 4 else 1
        inverted = struct.unpack_from('<I', rest, 4)[0] if node.name == 'Condition' and len(rest) >= 8 else 0
        return Content(name, vals, inverted=bool(inverted), enabled=bool(enabled))

    def item(n):
        if n.name == 'ScriptGroup':
            (name,), p = strings(n.head, 1)
            active, sub = (n.head[p], n.head[p + 1]) if len(n.head) >= p + 2 else (1, 0)
            return Group(name, [x for x in (item(k) for k in n.kids) if x], bool(active), bool(sub))
        if n.name == 'Script':
            (name, *_), p = strings(n.head, 4)
            # an older header without the switches (mapscript._script_marks): INFERRED a plain script
            active, once, e, nm, h, sub = n.head[p:p + 6] if len(n.head) >= p + 6 else (1, 1, 1, 1, 1, 0)
            interval = struct.unpack_from('<I', n.head, p + 6)[0] if len(n.head) >= p + 10 else 0
            s = Script(name, active=bool(active), once=bool(once), levels=(bool(e), bool(nm), bool(h)),
                       subroutine=bool(sub), interval=interval)
            for k in n.kids:
                if k.name == 'OrCondition':
                    s.ors.append([content(c) for c in k.kids if c.name == 'Condition'])
                elif k.name == 'ScriptAction':
                    s.actions.append(content(k))
                elif k.name == 'ScriptActionFalse':
                    s.else_actions.append(content(k))
            return s
        return None

    lists = []
    for _, n in m.walk():
        if n.name == 'PlayerScriptsList':
            for k, sl in enumerate(x for x in n.kids if x.name == 'ScriptList'):
                side = sides[k] if sides and k < len(sides) else ''
                lists.append(ScriptList(side, [x for x in (item(c) for c in sl.kids) if x]))
            break
    return lists
