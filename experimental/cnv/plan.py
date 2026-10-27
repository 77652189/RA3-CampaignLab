"""Level plans: a level's gameplay written as a plan a designer (or a player) edits -- docs/story/plans/<level>.md,
prose with ```yaml blocks -- and compiled into the mission (parts.Mission) the build makes. Change the plan, build,
and the game plays the change; nothing in the plan is a coordinate or a script. For a level with a plan the plan is
its card (docs/story/levels.md points to it).

The plan's language -- its sections, conditions, actions, the difficulty notation -- is written for the people who
edit plans, in Chinese, in docs/story/plans/README.md (plan_vocab reads its word list from there, with the devices,
unit names and a map's sites). Numbers that change with the difficulty change only those (retail: the phase
structure never does); the scripts get the header's difficulty bits, retail's only switch (map-language.md 7).

A condition compiles to alternatives, [[script condition, ...], ...]: any one alternative, all of its conditions;
`X + t` is a timer started once X first holds. What happens once is latched in a flag.

  python -I -X utf8 experimental/cnv/plan.py a4        the plan as a beat sheet, its design check and contract
"""
import dataclasses
import importlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import glossary                                 # noqa: E402
from parts import NOT, Goal, Mission, Script, square   # noqa: E402

PLANS = os.path.join(ROOT, 'docs', 'story', 'plans')
LEVELS = ('简单', '普通', '困难')
TAGS = ('easy', 'normal', 'hard')          # in script names: the map stores names as Latin-1
ALL = (True, True, True)
ONE = ((True, False, False), (False, True, False), (False, False, True))
SPACING = 60.0                                  # between units placed together
DEFAULT_AREA = 150.0                            # half-side of a site's trigger area when the site has no radius
CAPTION = 6.0                                   # seconds a caption stays
REVEAL_FIRST, REVEAL_GAP = 2.0, 4.0             # a phase's objectives: the first this long after it starts, then apart
AUTOSAVE = 'AUTOSAVE:CNVCAMPAIGN'


class PlanError(ValueError):
    pass


MUSIC = os.path.join(ROOT, 'experimental', 'music')


def music_names():
    """The level music a plan may name (音乐: <名字>): the modules of experimental/music that publish CUES (the
    plan's words for their events) and pack() (the build's music pack). Read from the sources, nothing imported."""
    out = []
    for f in sorted(os.listdir(MUSIC)):
        if f.endswith('.py'):
            with open(os.path.join(MUSIC, f), encoding='utf-8') as fh:
                src = fh.read()
            if '\nCUES = ' in src and '\ndef pack(' in src:
                out.append(f[:-3])
    return out


# ---------------------------------------------------------------- reading
def path(level):
    return os.path.join(PLANS, f'{level}.md')


def levels():
    """The levels that have a plan: the files here with a ```yaml block (a draft in prose only is not one yet)."""
    return sorted(f[:-3] for f in os.listdir(PLANS) if f.endswith('.md') and '\n```yaml\n' in open(
        os.path.join(PLANS, f), encoding='utf-8').read())


def load(level_or_path):
    """The plan's data: every ```yaml block of the file, merged (a key in two blocks is an error)."""
    import yaml
    p = level_or_path if level_or_path.endswith('.md') else path(level_or_path)
    with open(p, encoding='utf-8') as f:
        text = f.read()
    out = {}
    for block in re.findall(r'^```yaml\n(.*?)^```', text, re.M | re.S):
        data = yaml.safe_load(block) or {}
        if not isinstance(data, dict):
            raise PlanError(f'{p}: a yaml block must be a mapping, got {type(data).__name__}')
        for k, v in data.items():
            if k in out:
                raise PlanError(f'{p}: {k!r} written twice')
            out[k] = v
    return out


def per(v):
    """A value easy/normal/hard: '3000/2000/1500' or [3000, 2000, 1500] -> its three; one value -> three times."""
    if isinstance(v, (list, tuple)):
        vs = list(v)
    elif isinstance(v, str) and '/' in v:
        vs = [x.strip() for x in v.split('/')]
    else:
        vs = [v]
    if len(vs) == 1:
        vs = vs * 3
    if len(vs) != 3:
        raise PlanError(f'{v!r}: one value, or three (简单/普通/困难)')
    return tuple(vs)


def seconds(v):
    """'3:00' 180, '90' 90, '90秒' 90, '4分钟' 240, 1.5 1.5."""
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace('秒', '')
    if '~' in s:
        raise PlanError(f'{v!r}: a random time (a~b) only after a condition, `X + 0:15~0:30`')
    if s.endswith('分钟'):
        return float(s[:-2]) * 60
    if ':' in s:
        mi, sec = s.split(':')
        return int(mi) * 60 + float(sec)
    return float(s)


def number(v):
    return float(str(v).strip().lstrip('+'))


def counts(v):
    return tuple(int(number(x)) for x in per(v))


def times(v):
    return tuple(seconds(x) for x in per(v))


def spans(v):
    """Per difficulty (earliest, latest): '0:15~0:30' a random time between (retail SET_RANDOM_MSEC_TIMER), a plain
    time both the same. '0:15~0:30/0:10~0:20/5' by difficulty."""
    out = []
    for x in per(v):
        lo, _, hi = str(x).partition('~')
        a, b = seconds(lo), seconds(hi) if hi else seconds(lo)
        if b < a:
            raise PlanError(f'{v!r}: a random time is earliest~latest')
        out.append((a, b))
    return tuple(out)


def by_level(values):
    """[(difficulty bits, value)]: one entry when the three are the same, else one per difficulty."""
    if values[0] == values[1] == values[2]:
        return [(ALL, values[0])]
    return [(ONE[k], v) for k, v in enumerate(values)]


def start_time(c):
    """The three times when a condition is `开局 + t` (or any of several with one such: then the latest, the player
    may bring it forward), else None."""
    if isinstance(c, dict):
        ts = [t for t in map(start_time, c.get('任一', [])) if t]
        return ts[0] if len(ts) == 1 else None
    if isinstance(c, str):
        mm = re.match(r'^开局\s*\+\s*(.+)$', c.strip())
        if mm:
            return times(mm.group(1))
    return None


# ---------------------------------------------------------------- compiling
@dataclasses.dataclass
class Phase:
    name: str
    k: int
    flag: str
    spec: dict


class Compiler:
    """One plan -> one Mission. A condition compiles to alternatives, [[script condition, ...], ...]: any one
    alternative, all of its conditions; what happens once something held is latched in a flag."""

    def __init__(self, data, name=None):
        self.d = data
        self.level = str(data.get('关卡', 'x'))
        self.tag = re.sub(r'[^A-Za-z0-9]', '', self.level).upper()
        mapmod = importlib.import_module(f'maps.{data["地图"]}')
        sides = data.get('阵营', {})
        self.faction = {'p1': sides.get('我', '盟军'), 's1': sides.get('敌', '苏联')}
        self.side = {'我': 'p1', '敌': 's1'}
        # more sides (其他: {name: faction}): the map's idle players s2, s3 ..., neutral to both at the start
        for k, (who, faction) in enumerate((sides.get('其他') or {}).items(), 2):
            self.side[who], self.faction[f's{k}'] = f's{k}', faction
        self.m = Mission(name=name or f'Camp{self.tag}', map=mapmod)
        self.n = 0
        self.conds = {}             # condition text -> alternatives
        self.timers = {}            # condition text with a time -> (timer, its started flag)
        self.shown = {}             # timer -> countdown label key
        self.until = {}             # timer -> the condition that puts its countdown away sooner (直到)
        self.ai_awake = f'CNV_{self.tag}_AI_Awake'                  # 1 once 敌方AI woke (敌方AI 醒来)
        self.devices = {}
        self.dev_units = {}         # unit name a device publishes -> its Unit
        self.made = {}              # retail template -> the player's copy that builds ours too (可造)
        self.phases, self.waves, self.goals = [], {}, {}
        self.last = []              # the scripts the last when() made
        self.counted = {}           # group -> the counter of its losses (摧毁 <group> <n> 个)
        self.music = self.load_music(data.get('音乐'))

    def load_music(self, name):
        """音乐: <名字> -> the music module (experimental/music/<名字>.py), its pack made only when built."""
        if name is None:
            return None
        names = music_names()
        if str(name) not in names:
            raise PlanError(f'音乐 {name!r}: no such music; experimental/music has {names}')
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        mod = importlib.import_module(f'experimental.music.{name}')
        from experimental.music import pack
        self.m.music = pack.Later(mod.pack, {mod.EVENTS[key][0] for key in mod.CUES.values()})
        return mod

    def cue(self, word):
        """音乐 <提示词>: play that event of the level's music."""
        if not self.music:
            raise PlanError(f'音乐 {word}: the plan names no music (音乐: <名字> at the top; {music_names()})')
        cues = self.music.CUES
        if word not in cues:
            raise PlanError(f'音乐 {word!r}: {self.d["音乐"]} has {list(cues)}')
        return [('PATH_MUSIC_PLAY_EVENT', self.music.EVENTS[cues[word]][0])]

    # ---- names
    def uid(self, what=''):
        self.n += 1
        return f'{what}{self.n}'

    def text(self, kind, s):
        key = f'{kind}:CNV{self.tag}_{self.uid("T")}'
        self.m.strings[key] = str(s)
        return key

    def area(self, site):
        name = f'CNV {self.tag} Area {site}'
        if name not in self.m.areas:
            w = self.m.where(site)
            self.m.areas[name] = square(w.x, w.y, w.r or DEFAULT_AREA)
        return name

    def mark(self, site):
        """A waypoint at a site, published as a mark under the site's name (unless a mark of that name is)."""
        if site in self.m.marks:
            return self.m.marks[site]
        name = f'CNV {self.tag} At {site}'
        self.m.waypoint(site, name, site)
        return name

    def unit(self, name, side='p1'):
        if name in self.dev_units:
            return self.dev_units[name].id
        from units import roster
        if name in roster.NAMES:                    # one of ours a plan names like retail's (units/roster.py)
            made = roster.make(name)
            have = {u.id for u in self.m.units}
            self.m.units += [u for u in made if u.id not in have]
            t = made[0].id
            return self.made.get(t, t) if side == 'p1' else t
        t = glossary.template(name, self.faction[side])
        return self.made.get(t, t) if side == 'p1' else t

    def setup_production(self):
        """可造: {兵营: [冰幕工兵, ...]}: the player's buildings of that kind are copies that build ours too, and so
        is the construction yard (it builds the copies): placed, given or built later (units/production.py)."""
        from units import production
        wants = self.d.get('可造') or {}
        if not wants:
            return
        copies = {}
        for where, names in wants.items():
            retail = glossary.template(where, self.faction['p1'])
            ours = [self.unit(n) for n in names]
            plain = [n for n, u in zip(names, ours) if u not in {x.id for x in self.m.units}]
            if plain:
                raise PlanError(f'可造 {where}: {plain} are retail units (retail already builds them) or no unit '
                                'of ours a device or 开局 publishes')
            u = production.building(retail, ours, f'CNV{self.tag}{retail}')
            self.m.units.append(u)
            copies[retail] = u.id
        cy = glossary.template('建造厂', self.faction['p1'])
        y = production.yard(cy, copies, f'CNV{self.tag}{cy}')
        self.m.units.append(y)
        self.made = {**copies, cy: y.id}

    def part_names(self, part):
        """The named objects of a cast part or a group of them ('engineer' -> engineer 1, engineer 2 ...)."""
        m = self.m
        if part in m.cast and m.cast[part].name:
            return [m.cast[part].name]
        group = [r.name for r in m.roles(part) if r.name]
        if not group:
            raise PlanError(f'no named part {part!r}: the cast is {sorted(m.cast)}')
        return group

    def parts(self, part):
        """Cast parts a name stands for: itself, or the group's parts."""
        if part in self.m.cast:
            return [part]
        return [k for k in self.m.cast if re.fullmatch(re.escape(part) + r' \d+', k)]

    # ---- conditions
    def cond(self, c):
        """Alternatives for a condition: a string, a list (all of them), {任一: [...]} (any)."""
        if isinstance(c, dict):
            if set(c) != {'任一'}:
                raise PlanError(f'condition {c!r}: a mapping must be {{任一: [...]}}')
            return [alt for x in c['任一'] for alt in self.cond(x)]
        if isinstance(c, list):
            alts = [[]]
            for x in c:
                alts = [a + b for a in alts for b in self.cond(x)]
            return alts
        s = str(c).strip()
        if s not in self.conds:
            self.conds[s] = self._cond(s)
        return self.conds[s]

    def _cond(self, s):
        mm = re.match(r'^(.*?)\s*\+\s*([^+]+)$', s)
        if mm and not s.startswith('还没'):        # `还没 X + t` is 还没 (X + t), not (还没 X) + t
            return self.wait(mm.group(1), mm.group(2), s)
        w = s.split()
        head, rest = w[0], ' '.join(w[1:])
        p1, s1 = self.m.player('p1'), self.m.player('s1')
        if head == '开局':
            if rest:
                raise PlanError(f'{s!r}: 开局 takes nothing after it (a time is `开局 + 0:30`)')
            return [[]]
        if s == '敌方AI 醒来':                      # latched by its wake (compile_ai)
            if not self.d.get('敌方AI'):
                raise PlanError(f'{s!r}: the plan has no 敌方AI')
            return [[('FLAG', self.ai_awake, 1)]]
        if not rest and '.' not in head:
            raise PlanError(f'{s!r}: {head} needs what it is about (plan.py, README.md 条件)')
        if ' 进入 ' in s and head not in ('还没', '段', '目标'):
            # one of the plan's own (a role, or any of a group) in a site -- retail: the Shogun Executioner on a
            # bridge (Odessa), a scout at a village (Iga); 进入 <site> alone is any of the player's
            part, site = s.split(' 进入 ', 1)
            return [[('NAMED_INSIDE_AREA', n, self.area(site.strip()))] for n in self.part_names(part.strip())]
        if head == '段':
            name, what = (rest[:-2].strip(), rest[-2:]) if rest.endswith(('开始', '结束')) else (rest, '开始')
            ph = self.phase(name)
            if what == '结束':
                if ph.k + 1 >= len(self.phases):
                    raise PlanError(f'段 {name} 结束: it is the last phase')
                return [[('FLAG', self.phases[ph.k + 1].flag, 1)]]
            return [[('FLAG', ph.flag, 1)]]
        if head == '进入':
            return [[('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', p1, self.area(rest))]]
        if head == '敌人清空':
            # none of the enemy's left there. Not a kind-in-area count: the engine counts every player's with it
            # (bench 2026-10-25, probe/count: the enemy's CAN_ATTACK in a field held only the player's three came
            # out 3 -- the festival harbour's "enemy" bridge was the neutral bridge), so the player's own army in the
            # harbour kept it from ever holding; the has-units test is the enemy's alone
            return [[('SKIRMISH_PLAYER_HAS_UNITS_IN_AREA', s1, self.area(rest), NOT)]]
        if head == '摧毁':
            mm = re.match(r'^(.+?)\s+(\d+)\s*个$', rest)
            if mm:                                  # n of a group, whichever (retail: Havana's launch sites)
                return [[('COUNTER', self.losses(mm.group(1)), 3, int(mm.group(2)))]]
            return [[('NAMED_DESTROYED', n) for n in self.part_names(rest)]]
        if head == '冻住':                           # frozen now (retail: Iga's objectives, freeze, never kill)
            return [[('UNIT_HAS_OBJECT_STATUS', n, 'UNDER_FROZEN')] for n in self.part_names(rest)]
        if head == '攻击':
            return [[('NAMED_ATTACKED_BY_PLAYER', n, p1)] for n in self.part_names(rest)]
        if head == '占领':
            return [[('NAMED_OWNED_BY_PLAYER', p1, n) for n in self.part_names(rest)]]
        if head == '血量':
            hm = re.match(r'^(.+?)\s*<\s*(\d+)%?$', rest)
            if not hm:
                raise PlanError(f'{s!r}: write 血量 <part> < <percent>')
            return [[('UNIT_HEALTH', n, 0, int(hm.group(2)))] for n in self.part_names(hm.group(1))]
        if head in ('建成', '没有'):
            tmpl = self.unit(rest).lower()          # retail writes the type in lower case here
            self.m.spawns.add(tmpl)
            return [[('PLAYER_HAS_OBJECT_COMPARISON', p1, 3, 1, tmpl) if head == '建成' else
                     ('PLAYER_HAS_OBJECT_COMPARISON', p1, 2, 0, tmpl)]]
        if head == '还没':
            # the opposite of something that, once it happened, stays happened (a phase begun, a goal done, a
            # device's latched event): its one flag still 0
            alts = self.cond(rest)
            if len(alts) != 1 or not alts[0] or any(c[0] != 'FLAG' or c[2] != 1 for c in alts[0]):
                raise PlanError(f'{s!r}: 还没 works on what latches once (段 …, 目标 … 完成, 进攻 … 开始, a device '
                                f'event that stays): {rest!r} is not one')
            return [[('FLAG', c[1], 0)] for c in alts[0]]
        if head == '目标':
            title, _, what = rest.rpartition(' ')
            if what not in ('完成', '失败'):
                raise PlanError(f'{s!r}: 目标 <title> 完成 / 失败')
            return [[('FLAG', self.goal_flag(self.goal(title), what), 1)]]
        if head == '进攻':
            name = rest[:-2].strip() if rest.endswith('开始') else rest
            if name not in self.waves:
                raise PlanError(f'{s!r}: no wave {name!r}: {sorted(self.waves)}')
            return [[('FLAG', self.waves[name]['on'], 1)]]
        if '.' in head:
            dev, event = head.split('.', 1)
            if dev not in self.devices:
                raise PlanError(f'{s!r}: no device {dev!r}: {sorted(self.devices)}')
            return self.devices[dev].cond(event, w[1:])
        raise PlanError(f'{s!r}: no such condition (plan.py lists them)')

    def losses(self, part):
        """A counter of how many of a group (or of parts listed with 、) are destroyed: one script per member adds 1
        when it falls."""
        counter = self.counted.get(part)
        if not counter:                             # numbered: names written in Chinese would all come out alike
            counter = self.counted[part] = f'CNV_{self.tag}_Lost_{len(self.counted) + 1}'
            names = [n for p in re.split(r'[、,，]', part) for n in self.part_names(p.strip())]
            if len(names) < 2:
                raise PlanError(f'摧毁 {part} <n> 个: {part!r} is one part -- a group, or parts listed with 、')
            self.m.scripts += [Script(f'CNV {self.tag} - Lost {n}', [('NAMED_DESTROYED', n)],
                                      [('INCREMENT_COUNTER', 1, counter)]) for n in names]
        return counter

    def wait(self, base, t, s):
        """`base + t`: a timer started once base first holds; true once it has run out."""
        k = self.uid()
        timer, started = f'CNV {self.tag} Wait {k}', f'CNV_{self.tag}_Wait_{k}'
        self.timers[s] = (timer, started)
        for a, alt in enumerate(self.cond(base)):
            for levels, (lo, hi) in by_level(spans(t)):
                start = ('SET_MILLISECOND_TIMER', timer, lo) if lo == hi else ('SET_RANDOM_MSEC_TIMER', timer, lo, hi)
                self.m.scripts.append(Script(f'CNV {self.tag} - Wait {k}.{a + 1}' + ('' if levels == ALL else
                                                                                       f' {TAGS[levels.index(True)]}'),
                                             alt + [('FLAG', started, 0)], [start, ('SET_FLAG', started, 1)],
                                             levels=levels))
        return [[('FLAG', started, 1), ('TIMER_EXPIRED', timer)]]

    def when(self, label, c, actions, once=True, gate=(), levels=ALL):
        """Scripts doing `actions` when c holds (and the `gate` conditions): once -- the first time only."""
        alts = self.cond(c)
        done = f'CNV_{self.tag}_Did_{self.uid()}'
        self.last = []
        for k, alt in enumerate(alts):
            latch = [('FLAG', done, 0)] if once and len(alts) > 1 else []
            self.last.append(Script(f'CNV {self.tag} - {label}' + (f' ({k + 1})' if len(alts) > 1 else ''),
                                    list(gate) + alt + latch,
                                    actions + ([('SET_FLAG', done, 1)] if once and len(alts) > 1 else []),
                                    once=once, levels=levels))
        self.m.scripts += self.last
        return self.last

    # ---- actions
    def actions(self, acts):
        out = []
        for a in acts or []:
            out += self.action(a)
        return out

    def action(self, a):
        m, p1 = self.m, self.m.player('p1')
        if isinstance(a, str):
            head, _, rest = a.strip().partition(' ')
            if head == '通报':
                return [('SHOW_MILITARY_CAPTION', self.text('SCRIPT', rest.strip()), CAPTION)]
            if head == '存档':
                m.strings.setdefault(AUTOSAVE, '新战役（自动存档）')
                return [('CAMPAIGN_CREATE_AUTO_SAVE', AUTOSAVE)]
            if head == '胜利':                       # with the level's music, its win music first
                return (self.cue('胜利') if self.music else []) + [('SET_FLAG', 'Mission Won', 1)]
            if head == '音乐':
                return self.cue(rest.strip())
            if head == '战况音乐':                   # the game's own combat music states (sdk SageXML/PathMusic)
                if rest.strip() != '开':
                    raise PlanError(f'action {a!r}: 战况音乐 开 (there is no off: the game has no such action)')
                if not self.music:
                    raise PlanError(f'action {a!r}: the plan names no music (音乐: <名字> at the top)')
                return [('PATH_MUSIC_ENABLE_SPECIFIC_DYNAMIC_SYSTEM', self.music.DYNAMIC_SYSTEM)]
            if '.' in head:
                dev, what = head.split('.', 1)
                if dev not in self.devices:
                    raise PlanError(f'action {a!r}: no device {dev!r}: {sorted(self.devices)}')
                return self.devices[dev].action(what, rest.split())
            raise PlanError(f'action {a!r}: no such action (plan.py lists them)')
        if not isinstance(a, dict):
            raise PlanError(f'action {a!r}: a string or a mapping')
        if '通报' in a:
            return [('SHOW_MILITARY_CAPTION', self.text('SCRIPT', a['通报']), float(a.get('秒', CAPTION)))]
        if '镜头' in a:
            return [('MOVE_CAMERA_TO', self.mark(a['镜头']), float(a.get('秒', 3.0)), 0.0, 1.0, 1.0)]
        if '给' in a:
            return self.give(a['给'], a['在'])
        if '资金' in a:
            return [('PLAYER_GIVE_MONEY', p1, int(number(a['资金'])))]
        if '边界' in a:
            borders = list(getattr(m.map, 'BORDERS', {}))
            if a['边界'] not in borders:
                raise PlanError(f'边界 {a["边界"]!r}: map {m.map.__name__} has {borders}')
            return [('MAP_SWITCH_BORDER', borders.index(a['边界']))]
        if '倒计时' in a:
            key = str(a['倒计时']).strip()
            self.cond(key)
            if key not in self.timers:
                raise PlanError(f'倒计时 {key!r}: a condition with a time (… + 3:00)')
            timer = self.timers[key][0]
            self.shown[timer] = self.text('SCRIPT', a.get('文字', ''))
            if a.get('直到') is not None:            # put away sooner (what it counts to came early): never shown after
                self.cond('还没 ' + str(a['直到']).strip())         # one that latches: its flag still 0
                self.until[timer] = str(a['直到']).strip()
            return []
        if '摧毁' in a:
            return [('NAMED_KILL', n) for n in self.part_names(a['摧毁'])]
        if '无敌' in a or '取消无敌' in a:           # retail: UNATTACKABLE, nothing can aim at it
            on = '无敌' in a
            return [('UNIT_CHANGE_OBJECT_STATUS', n, 'UNATTACKABLE', int(on))
                    for n in self.part_names(a['无敌' if on else '取消无敌'])]
        if '出动' in a:                             # placed troops sent off (retail: an ambush set out on time)
            if not (a.get('打') or a.get('守')):
                raise PlanError(f'action {a!r}: 出动 <role> with 打 <site / role / 猎杀> or 守 <site>')
            if a.get('打') in self.devices:
                raise PlanError(f'action {a!r}: 出动 can not 打 a device (a wave can)')
            return self.orders(a, self.part_names(a['出动']), dict(names=[]))
        if '转给我' in a:
            return [('NAMED_TRANSFER_OWNERSHIP_PLAYER', n, p1) for n in self.part_names(a['转给我'])]
        if '翻脸' in a:                             # a side of 其他 turns on the player (and the player on it)
            x = self.side.get(a['翻脸'])
            if x in (None, 'p1', 's1'):
                raise PlanError(f'翻脸 {a["翻脸"]!r}: a side of 阵营 其他 ({sorted(self.side)})')
            return [('PLAYER_RELATES_PLAYER', m.player(x), p1, 'Enemy'), ('PLAYER_RELATES_PLAYER', p1, m.player(x), 'Enemy')]
        if '失败' in a:
            return (self.cue('失败') if self.music else []) + [
                ('SHOW_MILITARY_CAPTION', self.text('SCRIPT', a['失败']), 10.0), ('SET_FLAG', 'Mission Lost', 1)]
        raise PlanError(f'action {a!r}: no such action (plan.py lists them)')

    def give(self, units, site):
        """Units created for the player at a site (reinforcements)."""
        out, k = [], self.uid()
        for name, n in units.items():
            tmpl = self.unit(name)
            self.m.spawns.add(tmpl)
            for j in range(int(n)):
                out.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', f'UNIT - CNV {self.tag} Give {k}-{tmpl}-{j + 1}', tmpl,
                            self.m.team('p1'), self.mark(site)))
        return out

    # ---- the plan's sections
    def phase(self, name):
        hit = [p for p in self.phases if p.name == name]
        if not hit:
            raise PlanError(f'no phase {name!r}: {[p.name for p in self.phases]}')
        return hit[0]

    def goal(self, title):
        if title not in self.goals:
            raise PlanError(f'no objective {title!r}: {sorted(self.goals)}')
        return self.goals[title]

    def goal_flag(self, g, what):
        return f'CNV_{self.tag}_{g.name.split(" ")[0]}_{"Done" if what == "完成" else "Failed"}'

    def place(self):
        m, start = self.m, self.d.get('开局') or {}
        if '资金' in start:
            for levels, v in by_level(counts(start['资金'])):
                m.scripts.append(Script(f'CNV {self.tag} - Money' + ('' if levels == ALL else
                                                                     f' {TAGS[levels.index(True)]}'),
                                        [], [('PLAYER_SET_MONEY', m.player('p1'), v)], levels=levels))
        extra = [s for s in self.side.values() if s not in ('p1', 's1')]
        if extra:
            rel = [('PLAYER_RELATES_PLAYER', m.player(a), m.player(b), 'Neutral')
                   for x in extra for a, b in ((x, 'p1'), ('p1', x), (x, 's1'), ('s1', x))]
            m.scripts.append(Script(f'CNV {self.tag} - Sides', [], rel))
        for spec in start.get('部队') or []:
            who = spec.get('阵营', '我')
            if who not in self.side:
                raise PlanError(f'部队 {spec}: 阵营 {who!r} is none of {sorted(self.side)} (more sides: 阵营: 其他)')
            side = self.side[who]
            tmpl = self.unit(spec['单位'], side)
            ns = counts(spec.get('数量', 1))
            n = max(ns)
            dx0, dy0 = spec.get('偏移', (0, 0))
            role = spec.get('角色', '')
            levels = self.difficulty(spec, f'部队 {spec}')
            if not role and (spec.get('守') or len(set(ns)) > 1 or levels != ALL or spec.get('无敌')):
                role = f'{tmpl} {self.uid()}'           # named: a script orders or deletes them
            base = role if role.isascii() else f'Part {self.uid()}'
            parts = [f'{role} {j + 1}' if role and n > 1 else role for j in range(n)]
            objs = [f'UNIT - CNV {self.tag} {base} {j + 1}' if n > 1 else f'UNIT - CNV {self.tag} {base}'
                    for j in range(n)] if role else [''] * n
            for j, part in enumerate(parts):
                dx = dx0 + ((j % 4) - (min(n, 4) - 1) / 2) * SPACING
                dy = dy0 - (j // 4) * SPACING
                m.put(tmpl, spec['在'], dx, dy, side=side, name=objs[j],
                      role=part, angle=spec.get('朝向'))
            for lv, k in enumerate(ns):                 # retail: placed for the hardest, deleted on the easier
                k = k if levels[lv] else 0              # 难度: on the others, none at all
                if k < n:
                    gone = objs[k:]
                    m.scripts.append(Script(f'CNV {self.tag} - Fewer {base} {TAGS[lv]}', [],
                                            [('NAMED_DELETE', g) for g in gone], levels=ONE[lv]))
            if spec.get('无敌'):
                m.scripts.append(Script(f'CNV {self.tag} - Unattackable {base}', [],
                                        [('UNIT_CHANGE_OBJECT_STATUS', g, 'UNATTACKABLE', 1) for g in objs]))
            if spec.get('守') and role:
                for nm in self.part_names(role):
                    m.scripts.append(Script(f'CNV {self.tag} - Guard {nm}', [],
                                            [('UNIT_GUARD_AREA', nm, self.area(spec['守']))]))

    def setup_devices(self):
        from devices import registry
        DEVICES = registry()
        for name, spec in (self.d.get('机关') or {}).items():
            kind = spec.get('类型')
            if kind not in DEVICES:
                raise PlanError(f'机关 {name}: no device type {kind!r}: {sorted(DEVICES)}')
            dev = DEVICES[kind](self, name, spec)
            self.devices[name] = dev
            self.m.units += [u for u in dev.units if u not in self.m.units]
            self.dev_units.update(dev.names)

    def setup_goals(self):
        mains = bonuses = 0
        for title, spec in (self.d.get('目标') or {}).items():
            bonus = bool(spec.get('奖励'))
            if bonus:
                bonuses += 1
                name = f'Bonus{bonuses:02d} - CNV {self.tag}'
            else:
                mains += 1
                name = f'Objective{mains:02d} - CNV {self.tag}'
            g = Goal(name, self.text('MISSIONOBJ', title), self.text('MISSIONOBJ', spec.get('说明', title)),
                     bonus=bonus, at=None)
            g.spec, g.title_text = spec, title
            g.revealed = f'CNV_{self.tag}_{name.split(" ")[0]}_Shown'
            self.goals[title] = g
            self.m.objectives.append(g)

    def compile_goals(self):
        for g in self.m.objectives:
            offs, show = [], []
            for item in g.spec.get('标记') or []:
                part, off = next(iter(item.items())) if isinstance(item, dict) else (item, None)
                ps = self.parts(part)
                if not ps:
                    self.mark(part)                 # a site: a waypoint marks it
                    ps = [part]
                show += ps
                offs.append((ps, off))
            g.show = tuple(show)
            gate = [('FLAG', g.revealed, 1), ('FLAG', self.goal_flag(g, '完成'), 0),
                    ('FLAG', self.goal_flag(g, '失败'), 0)]
            if g.spec.get('完成'):
                self.when(f'Goal {g.name.split()[0]} done', g.spec['完成'],
                          self.m.done(g.name) + [('SET_FLAG', self.goal_flag(g, '完成'), 1)], gate=gate)
            if g.spec.get('失败'):
                self.when(f'Goal {g.name.split()[0]} failed', g.spec['失败'],
                          self.m.failed(g.name) + [('SET_FLAG', self.goal_flag(g, '失败'), 1)], gate=gate)
            for j, (ps, off) in enumerate(offs):
                if off:
                    self.when(f'Goal {g.name.split()[0]} marker {j + 1}', off, self.m.markers(g.name, on=False, only=ps),
                              gate=gate)

    def setup_phases(self):
        for k, spec in enumerate(self.d.get('段') or []):
            self.phases.append(Phase(spec['名字'], k, f'CNV_{self.tag}_Phase_{k + 1}', spec))

    def compile_phases(self):
        for ph in self.phases:
            spec = ph.spec
            acts = [('SET_FLAG', ph.flag, 1)]
            if spec.get('边界'):
                acts += self.action({'边界': spec['边界']})
            for i, title in enumerate(spec.get('目标') or []):
                # retail: one at a time, a few seconds apart, each with its own announcement (map-language.md 1)
                g = self.goal(title)
                self.when(f'Phase {ph.k + 1} goal {i + 1}', f'段 {ph.name} + {REVEAL_FIRST + REVEAL_GAP * i:g}',
                          self.m.reveal(g.name) + [('SET_FLAG', g.revealed, 1)])
            acts += self.actions(spec.get('开场'))
            if spec.get('存档'):
                acts += self.action('存档')
            if ph.k == 0:
                if self.d.get('边界'):                  # the playable area the mission starts with
                    acts = self.action({'边界': self.d['边界']}) + acts
                self.m.scripts.append(Script(f'CNV {self.tag} - Phase 1', [], acts))
            else:
                prev = self.phases[ph.k - 1]
                if not prev.spec.get('结束'):
                    raise PlanError(f'段 {prev.name}: no 结束 -- how does 段 {ph.name} start?')
                self.when(f'Phase {ph.k + 1}', prev.spec['结束'], acts, gate=[('FLAG', prev.flag, 1)])

    def setup_waves(self):
        for k, spec in enumerate(self.d.get('进攻') or []):
            self.waves[spec['名字']] = dict(spec=spec, k=k + 1, on=f'CNV_{self.tag}_Wave_{k + 1}_On', names=[])

    def wave(self, name, w):
        """Wave by wave: each sends its troops (a script per wave and difficulty), then sets the timer for the next;
        a counter keeps them in order and stops them at 最多; with 来源 only while one of those still stands."""
        spec, k, m = w['spec'], w['k'], self.m
        sent, timer = f'CNV_{self.tag}_Wave_{k}_Sent', f'CNV {self.tag} Wave {k}'
        every = spec.get('每隔')
        most = int(spec.get('最多', 99 if every else 1))
        self.when(f'Wave {k} start', spec['开始'],
                  [('SET_FLAG', w['on'], 1), ('SET_COUNTER', sent, 0), ('SET_MILLISECOND_TIMER', timer, 0.0)])
        troops = {u: counts(n) for u, n in (spec.get('兵') or {}).items()}
        extra = spec.get('加码') or {}
        more = {u: counts(n) for u, n in (extra.get('兵') or {}).items()}
        more_flag = f'CNV_{self.tag}_Wave_{k}_More'
        # stepped up: more troops a wave, and / or waves sooner (retail: Havana's launches, Miyako's recharge)
        stepped = bool(more) or extra.get('每隔') is not None
        if stepped:
            self.when(f'Wave {k} more', extra['当'], [('SET_FLAG', more_flag, 1)])
        alive = [[('NAMED_NOT_DESTROYED', n)] for p in spec.get('来源') or [] for n in self.part_names(p)] or [[]]
        if spec.get('直到') is not None:            # no more waves once it holds (one that latches: the AI took over)
            alive = [alt + self.cond('还没 ' + str(spec['直到']).strip())[0] for alt in alive]
        wp = self.mark(spec['从'])
        gaps = times(every) if every else (0.0,) * 3
        sooner = times(extra['每隔']) if extra.get('每隔') is not None else gaps
        if extra.get('每隔') is not None and not every:
            raise PlanError(f'进攻 {spec["名字"]}: 加码 每隔 on a wave without 每隔')
        warn = [('SHOW_MILITARY_CAPTION', self.text('SCRIPT', spec['预警']), CAPTION)] if spec.get('预警') else []
        for i in range(1, most + 1):
            for lv, levels in enumerate(ONE):
                for bonus in ([False, True] if stepped else [False]):
                    names, acts = [], []
                    for group, tag in ((troops, ''), (more if bonus else {}, 'x')):
                        for u, ns in group.items():
                            tmpl = self.unit(u, 's1')
                            m.spawns.add(tmpl)
                            for j in range(ns[lv]):
                                obj = f'UNIT - CNV {self.tag} W{k}-{i} {tmpl} {tag}{j + 1}'
                                names.append(obj)
                                acts.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', obj, tmpl, m.team('s1'), wp))
                    if not names:
                        continue
                    acts += self.orders(spec, names, w) + [('INCREMENT_COUNTER', 1, sent)] + warn
                    if every:
                        acts.append(('SET_MILLISECOND_TIMER', timer, (sooner if bonus else gaps)[lv]))
                    gate = [('FLAG', w['on'], 1), ('TIMER_EXPIRED', timer), ('COUNTER', sent, 2, i - 1)]
                    if stepped:
                        gate.append(('FLAG', more_flag, int(bonus)))
                    for a, alt in enumerate(alive):
                        m.scripts.append(Script(f'CNV {self.tag} - Wave {k} {i}{"+" if bonus else ""} {TAGS[lv]}'
                                                + (f' ({a + 1})' if len(alive) > 1 else ''),
                                                gate + alt, acts, levels=levels))
        target = spec.get('打')
        if target in self.devices and not spec.get('守'):
            m.scripts += self.devices[target].attack(sorted(set(w['names'])))

    def orders(self, spec, names, w):
        w['names'] += names
        target = spec.get('打')
        if spec.get('守'):
            return [('UNIT_GUARD_AREA', n, self.area(spec['守'])) for n in names]
        if not target or target == '猎杀':
            return [('NAMED_HUNT', n) for n in names]
        if target in self.devices:
            return []                               # the device's attack scripts (after all the waves are made)
        if self.parts(target):
            group = self.parts(target)
            if len(group) == 1:
                t = self.part_names(target)[0]
                return [('NAMED_ATTACK_NAMED', n, t) for n in names]
            # a group: attack-move to where it stands (one named target would leave them idle once it fell)
            return [('ATTACK_MOVE_NAMED_UNIT_TO', n, self.mark(self.m.cast[group[0]].site)) for n in names]
        return [('ATTACK_MOVE_NAMED_UNIT_TO', n, self.mark(target)) for n in names]

    def compile_rules(self):
        for k, r in enumerate(self.d.get('规则') or []):
            # once only: a script not done once runs every frame its condition holds (review 2026-10-24: a 给 made
            # the same named unit frame after frame), and "each time it holds again" needs its opposite; again and
            # again is `每隔`: while it holds, then once every so often (retail: a nag every 9 s, Iga)
            if r.get('次数', 1) != 1:
                raise PlanError(f'规则 {k + 1}: 次数 {r["次数"]!r} -- a rule happens once, or again every so often '
                                f'while it holds (每隔)')
            levels = self.difficulty(r, f'规则 {k + 1}')
            if r.get('每隔') is None:
                self.when(f'Rule {k + 1}', r['当'], self.actions(r.get('做')), levels=levels)
                continue
            timer, acts = f'CNV {self.tag} Rule {k + 1}', self.actions(r.get('做'))
            self.m.scripts.append(Script(f'CNV {self.tag} - Rule {k + 1} clock', [],
                                         [('SET_MILLISECOND_TIMER', timer, 0.0)]))     # run out: the first is now
            for lv, gap in by_level(times(r['每隔'])):
                on = tuple(a and b for a, b in zip(lv, levels))
                if not any(on):
                    continue
                for a, alt in enumerate(self.cond(r['当'])):
                    self.m.scripts.append(Script(
                        f'CNV {self.tag} - Rule {k + 1} again' + ('' if lv == ALL else f' {TAGS[lv.index(True)]}')
                        + (f' ({a + 1})' if len(self.cond(r['当'])) > 1 else ''),
                        alt + [('TIMER_EXPIRED', timer)], acts + [('SET_MILLISECOND_TIMER', timer, gap)],
                        once=False, levels=on))

    def difficulty(self, spec, what):
        """The difficulties a rule or a placed force is for: `难度: 困难` / `难度: [普通, 困难]`; all if not written
        (retail: a script's three header switches)."""
        d = spec.get('难度')
        if d is None:
            return ALL
        names = [d] if isinstance(d, str) else list(d)
        bad = [x for x in names if x not in LEVELS]
        if bad or not names:
            raise PlanError(f'{what}: 难度 {d!r} -- one or more of {LEVELS}')
        return tuple(x in names for x in LEVELS)

    def compile_ai(self):
        """敌方AI: a skirmish AI of the enemy's faction with a personality of the level's own (enemy_ai.py), on a
        player of its own beside 敌 -- the retail way (Miyako: Takara's AI on Japan_1, her scripted turrets and
        guards on Japan_3, allies): what the plan moves (the carrier, guards) stays 敌's, out of the AI's reach --
        bench 2026-10-25, a7/jumps: with 敌 itself the AI, the carrier left home at 18 s, the AI asleep, and
        UNIT_AI_TRANSFER off did not keep it. Asleep with no money until 唤醒; then 接管 (敌's buildings and
        troops it is to run: the east bank's barracks, factory, airfield) passes to it, with its base and money.
        Woken, it fights on its own (bench 2026-10-25, ai_plan/capped: first contact ~60 s after, its army ~150 s;
        SKIRMISH_AI_TRANSFER_ALL changed nothing), so when it wakes is the plan's one lever."""
        spec = self.d.get('敌方AI')
        if not spec:
            return
        import enemy_ai
        m, faction = self.m, self.faction['s1']
        known = {'性格', '偏好', '上限', '基地', '资金', '唤醒', '接管', '修理', '重建', '技能'}
        if set(spec) - known:
            raise PlanError(f'敌方AI: {sorted(set(spec) - known)} -- it takes {sorted(known)}')
        for need in ('基地', '唤醒'):
            if not spec.get(need):
                raise PlanError(f'敌方AI: no {need}')
        free = [k for k in m.map.PLAYERS if k not in self.side.values() and k != 'p1']
        if not free:
            raise PlanError(f'敌方AI: no player left on map {m.map.__name__} (阵营 其他 took them)')
        side = free[0]
        self.side['敌AI'] = side                    # published as the side in m.sides with an aiPersonality
        ai, s1, p1 = m.player(side), m.player('s1'), m.player('p1')
        pid = f'CNV_AIP_{self.tag}'
        try:
            xml = enemy_ai.personality(pid, faction, spec.get('性格', '平衡'),
                                       {self.unit(u, 's1'): number(k) for u, k in (spec.get('偏好') or {}).items()})
        except ValueError as e:
            raise PlanError(f'敌方AI: {e}')
        for u, n in (spec.get('上限') or {}).items():
            # retail ("tatsu has limited barracks"): not buildable while it has that many, again when fewer; a
            # personality's SpecificUnitCap did not hold for a power plant (bench 2026-10-25)
            tmpl = self.unit(u, 's1')
            n, low = int(number(n)), tmpl.lower()       # retail writes the type in lower case here
            m.spawns.add(low)
            m.scripts += [Script(f'CNV {self.tag} - AI cap {tmpl}', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, n, low)],
                                 [('ALLOW_DISALLOW_ONE_BUILDING', ai, low, 0)], once=False),
                          Script(f'CNV {self.tag} - AI cap {tmpl} off', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 0, n, low)],
                                 [('ALLOW_DISALLOW_ONE_BUILDING', ai, low, 1)], once=False)]
        m.sides[side] = {'playerFaction': enemy_ai.PLAYER_TEMPLATE[faction],
                         'aiPersonality': f'AIPersonalityDefinition:{pid}'}
        m.assets.append((f'{pid}.xml', xml, f'AIPersonalityDefinition:{pid}'))
        awake = self.ai_awake
        # 敌's ally, the player's enemy, whatever the container map said; no money till it wakes. The Friend did not
        # keep 敌's guards (守 east gate) off the AI's barracks, nor did playerAllies both ways in the map's player list
        # (bench 2026-10-26, a7/east: lost at s100 either way; with the guards deleted it stood) -- why is open, so a
        # plan hands the base's troops to the AI with 接管 too (retail Miyako "give units to tatsu")
        m.scripts.append(Script(f'CNV {self.tag} - AI asleep', [], [
            ('PLAYER_RELATES_PLAYER', ai, s1, 'Friend'), ('PLAYER_RELATES_PLAYER', s1, ai, 'Friend'),
            ('PLAYER_RELATES_PLAYER', ai, p1, 'Enemy'), ('PLAYER_RELATES_PLAYER', p1, ai, 'Enemy'),
            ('PLAYER_SET_MONEY', ai, 0)]))
        given = [('NAMED_TRANSFER_OWNERSHIP_PLAYER', n, ai) for part in spec.get('接管') or []
                 for n in self.part_names(part)]
        yes = lambda k, default: int(str(spec.get(k, default)) in ('是', 'True', '1'))     # noqa: E731
        self.when('AI wake', spec['唤醒'],
                  given + [('UNIT_AI_TRANSFER_ALL', ai, 1), ('SKIRMISH_AI_MAKE_BASE', ai, self.mark(spec['基地'])),
                           ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', ai, 20),
                           ('SKIRMISH_AI_USE_REPAIRS', ai, yes('修理', '否')),
                           ('SKIRMISH_AI_USE_REBUILD_SYSTEM', ai, yes('重建', '否')), ('SET_FLAG', awake, 1)]
                  # no secret protocols unless 技能 (retail "prevent naomi from buying specials"; bench 2026-10-25:
                  # with them its first blow at the player's base was a power)
                  + ([] if yes('技能', '否') else [('PLAYER_SET_MAX_PLAYER_POWER_POINTS', ai, 0),
                                                  ('PLAYER_SET_PLAYER_POWER_POINTS', ai, 0)]))
        m.ai_wake = [s.name for s in self.last]
        for levels, v in by_level(counts(spec.get('资金', 0))):
            m.scripts.append(Script(f'CNV {self.tag} - AI money' + ('' if levels == ALL else
                                                                   f' {TAGS[levels.index(True)]}'),
                                    [('FLAG', awake, 1)], [('PLAYER_SET_MONEY', ai, v)], levels=levels))

    def compile_endings(self):
        m = self.m
        if self.d.get('胜利'):
            m.endings += [s.name for s in self.when('Win', self.d['胜利'], self.action('胜利'))]
        for k, lose in enumerate(self.d.get('失败') or []):
            m.endings += [s.name for s in self.when(f'Lose {k + 1}', lose['当'],
                                                    self.action({'失败': lose.get('原因', '任务失败')}))]

    def compile_countdowns(self):
        for timer, label in self.shown.items():
            started = next(st for t, st in self.timers.values() if t == timer)
            until = self.until.get(timer)
            not_yet = self.cond('还没 ' + until)[0] if until else []
            self.m.scripts += [Script(f'CNV {self.tag} - Countdown {timer}', [('FLAG', started, 1)] + not_yet,
                                      [('DISPLAY_COUNTDOWN_TIMER', timer, label)]),
                               Script(f'CNV {self.tag} - Countdown {timer} off',
                                      [('FLAG', started, 1), ('TIMER_EXPIRED', timer)],
                                      [('HIDE_COUNTDOWN_TIMER', timer)])]
            self.m.scripts += [Script(f'CNV {self.tag} - Countdown {timer} put away' + (f' ({k + 1})' if k else ''),
                                      [('FLAG', started, 1)] + alt, [('HIDE_COUNTDOWN_TIMER', timer)])
                               for k, alt in enumerate(self.cond(until) if until else [])]
            self.m.countdowns.append(timer)

    def compile(self):
        self.setup_phases()
        self.setup_waves()
        self.setup_devices()
        self.setup_production()
        self.place()
        for dev in self.devices.values():
            dev.place()
        self.setup_goals()
        self.compile_goals()
        self.compile_phases()
        for name, w in self.waves.items():
            self.wave(name, w)
        self.compile_rules()
        self.compile_ai()
        self.compile_endings()
        for dev in self.devices.values():
            self.m.scripts += dev.scripts()
        for dev in self.devices.values():
            self.m.scripts += dev.last()
        self.compile_countdowns()
        for ph in self.phases[1:]:                  # facts: a phase's start, when it is a time from the start
            t = start_time(self.phases[ph.k - 1].spec.get('结束'))
            if t:
                self.m.facts[f'段 {ph.name}'] = t[1]
        for dev in self.devices.values():
            self.m.facts.update(dev.facts())
        return self.m


def mission(level, name=None):
    """The level's mission, compiled from its plan."""
    return Compiler(load(level), name).compile()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('level')
    import plancheck
    print(plancheck.report(ap.parse_args().level))
