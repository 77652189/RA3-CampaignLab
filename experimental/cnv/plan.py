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
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import glossary                                 # noqa: E402
import langs                                    # noqa: E402
from ctx import CHAT, FUNC, Ctx                 # noqa: E402
from contract import ENDING_LIBRARY_AT, MUSIC_DYNAMIC, unresumed_cues   # noqa: E402
from parts import NOT, Goal, Mission, Script, square   # noqa: E402
from plantime import (ALL, ONE, TAGS, PlanError, by_level, counts, number, per, seconds, spans,   # noqa: E402,F401
                      times)                                                                # re-exported: tests, checks

PLANS = os.path.join(ROOT, 'docs', 'story', 'plans')
LEVELS = ('简单', '普通', '困难')
SPACING = 60.0                                  # between units placed together
PACE_ARRIVE = 250.0                             # half-side of the area a 齐步 force is released in (a wave stops short of the point)
DEFAULT_AREA = 150.0                           # half-side of a site's trigger area when the site has no radius
CHRONO_FLASH = 'fxprop_chronoflash'             # retail's chrono flash prop (its FX plays on create, lives 1 s)
EASE = 1.0                                     # seconds a pan eases in / out (retail's most used eased pan: 1/1)
PAN_SPEED = 250.0                               # map units a second at most between two sites of a 过场
VIEW_HALF = (950.0, 540.0)                      # half the ground the screen shows at the default zoom (~1900 x 1080 map
                                                # units, sapporo 'view start', user 2026-11-03): a camera centre nearer
                                                # the playable border than this shows the black beyond it (K5)
CAPTION_TURN = 4.0                             # seconds a caption-only line holds the floor outside a 过场
CAPTION_TAIL = 0.3                              # a dubbed line's caption stays this long after its recording ends
EVA_TURN = 2.5                                 # ... a retail announcer line (its length is not known)
SPEECH_GAP = 0.6                              # seconds of quiet after a dubbed line in a 过场
CAPTION = 6.0                                  # seconds a caption stays
REVEAL_FIRST, REVEAL_GAP = 2.0, 4.0             # a phase's objectives: the first this long after it starts, then apart
RELATIONS = {'盟友': 'Friend', '中立': 'Neutral', '敌人': 'Enemy'}     # 阵营 其他's 对我 / 对敌
# a relation argument carries its index as well as its name, and the game reads the index (retail's 290
# PLAYER_RELATES_PLAYER: 0 Enemy, 1 Neutral, 2 Friend). Written by name alone it was 0: every Friend and Neutral we
# wrote was Enemy (bench 2026-10-28, a4 idle: the player's tanks shot the allied convoy; 2026-10-26, a7: the guards
# shot the "friendly" AI's barracks)
RELATION_INDEX = {'Enemy': 0, 'Neutral': 1, 'Friend': 2}


def relates(a, b, relation):
    """PLAYER_RELATES_PLAYER: player a's view of player b."""
    return ('PLAYER_RELATES_PLAYER', a, b, (RELATION_INDEX[relation], 0.0, relation))
CAMERA_MOVE, FOLLOW = 3.0, 4.0                 # a 镜头's move, a 跟随's hold (seconds) when the plan gives none
FOLLOW_AT = 300.0                               # CAMERA_FOLLOW_NAMED's distance (retail: 300 behind Yuriko, 13 of 17)
LOOK_MAX = 600.0
LOOK_MIN = 400.0                               # a 过场 镜头's own reveal at its site: at least this radius (the camera sees ~500)
SIGHT = 300.0                                  # 揭开's radius when the site has none (retail: 100 .. 750, mostly 200 / 300)
FLASHES = 5                                     # NAMED_FLASH's count (retail: 5 at the hand-back, Stalingrad)
INFO_SECONDS = 20.0                             # an info box stays this long (retail A01: 20)
INFO_ICON = 'Button_AlliedEngineer_on'          # its picture: a retail build button (A01's hospital box shows this one)
AUTOSAVE = 'AUTOSAVE:CNVCAMPAIGN'


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


def on_event(c):
    """Whether a rule's condition hangs on something that happens in the game, not just on the clock (`开局 + 0:30`): a
    list needs one such leaf (the others only narrow it), an `任一` needs every branch to (K2: a line said at a bare
    time is said over whatever the player is looking at)."""
    if isinstance(c, dict):
        return all(on_event(x) for x in c.get('任一', []))
    if isinstance(c, list):
        return any(on_event(x) for x in c)
    return not re.match(r'^开局\s*\+', str(c).strip())


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

    def __init__(self, data, name=None, lang='zh'):
        self.d = data
        self.lang = lang                # the edition (langs.py): zh, or intl (English subtitles, dubbed in each side's language)
        self.level = str(data.get('关卡', 'x'))
        self.tag = re.sub(r'[^A-Za-z0-9]', '', self.level).upper()
        mapmod = importlib.import_module(f'maps.{data["地图"]}')
        sides = data.get('阵营', {})
        self.faction = {'p1': sides.get('我', '盟军'), 's1': sides.get('敌', '苏联')}
        self.side = {'我': 'p1', '敌': 's1'}
        # more sides (其他: {name: faction}, or {name: {阵营, 对我, 对敌}}): the map's idle players s2, s3 ..., neutral
        # to both at the start unless 对我 / 对敌 say 盟友 or 敌人 (retail Odessa, Stalingrad: the transports a side of
        # their own, allied, the player can not order them)
        self.relation = {}          # side -> (to the player, to the enemy): 'Friend' / 'Neutral' / 'Enemy'
        for k, (who, spec) in enumerate((sides.get('其他') or {}).items(), 2):
            spec = spec if isinstance(spec, dict) else {'阵营': spec}
            rel = [RELATIONS.get(str(spec.get(x, '中立'))) for x in ('对我', '对敌')]
            if None in rel:
                raise PlanError(f'阵营 其他 {who}: 对我 / 对敌 is one of {sorted(RELATIONS)}')
            self.side[who], self.faction[f's{k}'] = f's{k}', spec.get('阵营')
            self.relation[f's{k}'] = tuple(rel)
        self.m = Mission(name=name or langs.mod_name(self.tag, lang), map=mapmod)
        self.ctx = Ctx(self)            # what a device (devices/) is given instead of this compiler and the mission
        self.m.missing = []             # what the edition lacks (audio, subtitle text, translations): the build lists it
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
        self.view = None            # the border a 过场's camera keeps to (view_point); None: every border the level uses
        self.counted = {}           # group -> the counter of its losses (摧毁 <group> <n> 个)
        self.troop_counters = {}    # kinds counted together -> their counter (兵少于 <n> <units>)
        self.music = self.load_music(data.get('音乐'))
        self.voice = self.load_voice(data.get('语音'), data.get('头像'))
        self.captioned = set()      # voice events a 功能 caption stands for: their recording carries no subtitle

    def load_voice(self, levels, heads=None):
        """语音: [A4, ICEENG] -> the delivered dubbed lines of those folders (voice_link.Later): a 通报 with 说 whose
        speaker and words are one of them plays it instead of showing a caption (the subtitle comes with the line).
        头像: [CNV_A4_008, ...] -> the lines that also show the speaker's talking head (clips.py); only these, never
        every line that has an mp4. No list, no heads."""
        if not levels:
            return None
        import voice_link
        self.m.voice = voice_link.Later(levels if isinstance(levels, list) else [levels], self.lang, list(heads or []))
        self.m.video = self.m.voice.clips
        self.m.missing += [f'voice {x}' for x in self.m.voice.missing]
        return self.m.voice

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
        acts = [('PATH_MUSIC_PLAY_EVENT', self.music.EVENTS[cues[word]][0])]
        if os.environ.get('CNV_MUSIC_CAPTIONS'):    # a build to listen with: the cue's word stays on screen (a
            shown = [f'CNV Music {k}' for k in range(len(cues))]        # counter, captions would hide each other)
            me = shown[list(cues).index(word)]
            acts += [('HIDE_COUNTER', c) for c in shown if c != me]
            acts.append(('DISPLAY_COUNTER', me, self.text('SCRIPT', f'音乐：{word}')))
        return acts

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
        if head == '过场':
            if not rest.endswith('结束'):
                raise PlanError(f'{s!r}: 过场 <phase> 结束 (the input handed back)')
            ph = self.phase(rest[:-2].strip())
            if not ph.spec.get('过场'):
                raise PlanError(f'{s!r}: 段 {ph.name} has no 过场')
            return [[('FLAG', self.scene_flag(ph), 1)]]
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
        if head == '兵少于':                         # `兵少于 3 标枪兵、多功能步兵车`: the player's, all of them together
            mm = re.match(r'^(\d+)\s*个?\s+(.+)$', rest)
            if not mm:
                raise PlanError(f'{s!r}: write 兵少于 <n> <unit>、<unit> (the kinds counted together)')
            return [[('COUNTER', self.troops(re.split(r'[、,，]', mm.group(2))), 0, int(mm.group(1)))]]
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

    def troops(self, names):
        """A counter of how many of the player's units of these kinds live: one script, every frame, counts each kind
        (SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER counts the player's alone, and what died or was deleted drops out at the
        next read: bench 2026-10-29, probe death) and adds the counts up (COUNTER_MATH_COUNTER, 0 adds). Retail's
        `all units` object list is expanded when retail compiles it, ours is read from the .map: not usable
        (docs/design/flow/mechanics.md, 兵少补援)."""
        kinds = sorted({self.unit(n.strip()).lower() for n in names if n.strip()})
        if not kinds:
            raise PlanError(f'兵少于 {names!r}: no unit named')
        key = '、'.join(kinds)
        if key not in self.troop_counters:
            total = f'CNV_{self.tag}_Troops_{len(self.troop_counters) + 1}'
            self.troop_counters[key] = total
            acts = [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', kinds[0], self.m.player('p1'), total)]
            for i, t in enumerate(kinds[1:], 1):
                part = f'{total}_{i}'
                acts += [('SET_PLAYER_OWNERSHIP_OF_TYPE_COUNTER', t, self.m.player('p1'), part),
                         ('COUNTER_MATH_COUNTER', total, 0, part)]
            self.m.spawns |= set(kinds)
            self.m.scripts.append(Script(f'CNV {self.tag} - Count troops {len(self.troop_counters)}', [], acts,
                                         once=False))
        return self.troop_counters[key]

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
            if not self.is_line(a):
                self.ctx.talk.anchored = True       # a line after a camera move or any act reports what that shows
        return out

    def action(self, a):
        m, p1 = self.m, self.m.player('p1')
        if isinstance(a, str):
            head, _, rest = a.strip().partition(' ')
            if head == '通报':
                return self.ctx.line((), self.text('SCRIPT', rest.strip()), CAPTION, turn=CAPTION_TURN, tier=CHAT)
            if head == '副指挥官':                   # the co-commander's panel (retail Cannes hides it at the start)
                if rest.strip() not in ('开', '关'):
                    raise PlanError(f'action {a!r}: 副指挥官 开 / 关 (the panel at the top left; Player_2 stays)')
                return [('SET_COOP_AI_COMMAND_UI_ENABLED', int(rest.strip() == '开'))]
            if head == '存档':
                m.strings.setdefault(AUTOSAVE, '新战役（自动存档）')
                return [('CAMPAIGN_CREATE_AUTO_SAVE', AUTOSAVE)]
            if head == '胜利':                       # the library's Mission Won plays S_EndMissionWin itself (E7-7)
                return [('SET_FLAG', 'Mission Won', 1)]
            if head == '音乐':
                return self.cue(rest.strip())
            if head == '战况音乐':                   # the game's own combat music states (sdk SageXML/PathMusic)
                # no off: any 音乐 cue suspends it (PATH_MUSIC_PLAY_EVENT, E7-6), and resume_music() switches it on
                # again after every cue that comes later
                if rest.strip() != '开':
                    raise PlanError(f'action {a!r}: 战况音乐 开 (a cue after it suspends it, the compiler switches it '
                                    f'on again after the cue; there is no off)')
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
            tier = FUNC if a.get('功能') in (True, '是') else CHAT      # 功能: 是 marks a line that must not be dropped
            words, who = str(a['通报']), a.get('说')
            if '原文' in a and not who:
                raise PlanError(f'action {a!r}: 原文 is a speaker\'s words: 说 <who> goes with it')
            shown = f'{who}：{words}' if who else words
            said = a.get('原文', words)
            dubbed = self.voice.find(who, said) if who and self.voice is not None else None
            if dubbed:                              # the dubbed line: its subtitle comes with it
                self.m.lines.append(dict(说话人=str(who), 原文=str(said), 通报=shown, 字串=dubbed))
                clip = self.voice.clips.find(dubbed)        # the speaker's talking head, when the voice line made one
                n = self.voice.length(who, said) or EVA_TURN
                # a line goes by one channel (E6): a 功能 line is a caption for the length of the recording, its voice has
                # no subtitle; any other dubbed line (and every one in a 过场) carries its own subtitle into the dialogue
                # panel and shows no caption
                words = self.text('SCRIPT', self.voice.strings[f'DIALOGEVENT:{dubbed}'])
                head = [('MOVIE_PLAY_RADAR', clip)] if clip else []
                as_caption = tier == FUNC and not self.ctx.talk.scene
                if dubbed in (self.m.subtitles if as_caption else self.captioned):
                    raise PlanError(f'action {a!r}: the recording {dubbed} is said twice, once as a caption (功能) and '
                                    f'once with its own subtitle: its subtitle is one or the other')
                if as_caption:
                    self.captioned.add(dubbed)
                    return self.ctx.line([('PLAY_SOUND_EFFECT', dubbed)], words, n + CAPTION_TAIL, head,
                                         turn=n + SPEECH_GAP, tier=tier)
                self.voice.subtitled.add(dubbed)
                self.m.subtitles[dubbed] = words
                return self.ctx.line([('PLAY_SOUND_EFFECT', dubbed)], None, 0.0, head, turn=n + SPEECH_GAP, tier=tier)
            retail = self.voice.eva(who, said) if who and self.voice is not None else None
            if retail:                              # retail's own announcer line: its event, no caption (as retail)
                self.m.lines.append(dict(说话人=str(who), 原文=str(said), 通报=shown, 字串=retail))
                return self.ctx.line([('PLAY_SOUND_AS_IF_IT_WAS_AN_EVA_EVENT', retail)], None, 0.0, turn=EVA_TURN, tier=tier)
            key = self.text('SCRIPT', shown)
            if who and self.voice is not None:      # said by someone, but no recording of it: listed (langs.py)
                self.m.missing.append(f'caption only, no recording of it: {shown}')
            if who:                                 # a flow-script line: the dubbed line is found by who and what
                self.m.lines.append(dict(说话人=str(who), 原文=str(a.get('原文', words)), 通报=shown, 字串=key))
            secs = float(a.get('秒', CAPTION))
            return self.ctx.line((), key, secs, turn=min(secs, CAPTION_TURN), tier=tier)
        if '镜头' in a:                             # to a site, or to one of the plan's own (retail: the statue)
            return self.camera(a, float(a.get('秒', CAMERA_MOVE)), EASE, EASE)
        if '跟随' in a:
            raise PlanError(f'action {a!r}: 跟随 only in a 过场 (it is stopped at the hand-back)')
        if '闪烁' in a:                             # retail: the hand-back flashes the player's MCV
            return [('NAMED_FLASH', n, FLASHES) for n in self.part_names(a['闪烁'])]
        if '信息框' in a:                           # an info box over a unit (retail A01: Peacekeepers, Javelins, Hospital)
            icon = str(a.get('图标', INFO_ICON))
            return [('NAMED_SHOW_INFOBOX', n, self.text('SCRIPT', str(a['文字'])), float(a.get('秒', INFO_SECONDS)), icon)
                    for n in self.part_names(a['信息框'])]
        if '揭开' in a:                             # lift the shroud there: for good, or a look that shrouds again
            site = str(a['揭开'])
            radius = float(a.get('半径') or self.m.where(site).r or SIGHT)
            if a.get('永久'):
                return [('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', self.mark(site), radius, p1, self.sight(site))]
            return [('MAP_REVEAL_AT_WAYPOINT', self.mark(site), radius, p1)]
        if '收回' in a:                             # undo a 揭开 永久, or the whole map's (揭全图 永久)
            what = str(a['收回'])
            if what == '全图':
                return [('MAP_REVEAL_ALL_UNDO_PERM', p1)]
            return [('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', self.sight(what))]
        if '揭全图' in a:
            if a['揭全图'] != '永久':
                raise PlanError(f'action {a!r}: 揭全图 看一眼 only in a 过场 (shrouded again at the hand-back); '
                                f'elsewhere 揭全图 永久, and 收回 全图 when it should go')
            return [('MAP_REVEAL_ALL_PERM', p1)]
        if '特效' in a:                             # a retail effect prop at a site (Cannes A02: the chrono flash, then
            if a['特效'] != '超时空':                #   the reinforcements)
                raise PlanError(f'action {a!r}: 特效 超时空 (the only effect there is)')
            self.m.spawns.add(CHRONO_FLASH)
            return [('CREATE_UNNAMED_ON_TEAM_AT_WAYPOINT', CHRONO_FLASH, self.m.team('p1'), self.mark(a['在']))]
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
        if '技能' in a:                             # a button of ours pressed (the jammer's jam, the burrower's
            parts = self.parts(a.get('角色', ''))     # burrow): what the unit publishes as an ability
            if not parts:
                raise PlanError(f'action {a!r}: {{技能: <ability>, 角色: <role>}}')
            return [('NAMED_USE_COMMANDBUTTON_ABILITY', self.m.cast[p].name, self.m.ability(p, a['技能']))
                    for p in parts]
        if '锁住' in a or '放开' in a:              # IMMOBILE: it does not move, whatever it is ordered (a lock's
            on = '锁住' in a                         # fleet: a structure on the water bars no ship, bench 2026-10-27)
            return [('UNIT_CHANGE_OBJECT_STATUS', n, 'IMMOBILE', int(on))
                    for n in self.part_names(a['锁住' if on else '放开'])]
        if '出动' in a:                            # placed troops sent off (retail: an ambush set out on time)
            if not (a.get('打') or a.get('守')):
                raise PlanError(f'action {a!r}: 出动 <role> with 打 <site / role / 猎杀> or 守 <site>')
            if a.get('打') in self.devices:
                raise PlanError(f'action {a!r}: 出动 can not 打 a device (a wave can)')
            if '齐步' in a:
                raise PlanError(f'action {a!r}: 齐步 is for 进攻 waves (units the script makes: their template is ours to '
                                f'choose); placed troops are not copies')
            return self.orders(a, self.part_names(a['出动']), dict(names=[]), self.m.cast[self.parts(a['出动'])[0]].side)
        if '禁造' in a or '准造' in a:              # the player may (not) build it (retail Brighton Beach)
            return self.bans(a['禁造' if '禁造' in a else '准造'], int('准造' in a))
        if '转给我' in a:
            return [('NAMED_TRANSFER_OWNERSHIP_PLAYER', n, p1) for n in self.part_names(a['转给我'])]
        if '翻脸' in a:                             # a side of 其他 turns on the player (and the player on it)
            x = self.side.get(a['翻脸'])
            if x in (None, 'p1', 's1'):
                raise PlanError(f'翻脸 {a["翻脸"]!r}: a side of 阵营 其他 ({sorted(self.side)})')
            return [relates(m.player(x), p1, 'Enemy'), relates(p1, m.player(x), 'Enemy')]
        if '失败' in a:
            # the library's Mission Lost plays S_EndMissionLose itself and ends the mission in 3 s (E7-7): the line
            # stays up no longer than that (contract.ending_line_fits holds the words to it: 9 CJK chars a second)
            return self.ctx.ending_begin() + [
                self.ctx.final(self.text('SCRIPT', a['失败']), ENDING_LIBRARY_AT['Mission Lost']),
                ('SET_FLAG', 'Mission Lost', 1)]
        raise PlanError(f'action {a!r}: no such action (plan.py lists them)')

    def camera(self, a, secs, ease_in, ease_out):
        """MOVE_CAMERA_TO / _NAMED (waypoint, seconds, stutter 0, ease in, ease out). Retail runs a pan linear or eased
        only at its ends (retailref: 144 of 240 moves 0/0/0, the rest 1-5 s eases on pans of 3-12 s)."""
        ps = self.parts(str(a['镜头']))
        if ps:
            return [('MOVE_CAMERA_TO_NAMED', self.m.cast[ps[0]].name, secs, 0.0, ease_in, ease_out)]
        return [('MOVE_CAMERA_TO', self.view_point(str(a['镜头'])), secs, 0.0, ease_in, ease_out)]

    def border_rect(self, name):
        borders = getattr(self.m.map, 'BORDERS', {})
        if name not in borders:
            raise PlanError(f'边界 {name!r}: map {self.m.map.__name__} has {list(borders)}')
        return borders[name]

    def border_at(self, ph):
        """The name of the playable area a phase runs in: its own 边界, else the last phase's, else the level's."""
        name = self.d.get('边界') or 'whole'
        for p in self.phases[:ph.k + 1]:
            name = p.spec.get('边界') or name
        return name

    def view_rect(self, names):
        """Where a camera centre may be while the playable area is (the intersection of) the named borders: inside
        them, VIEW_HALF from their edges (the middle when a border is narrower than the screen)."""
        x0, y0, x1, y1 = (None,) * 4
        for n in names:
            a, b, c, d = self.border_rect(n)
            x0, y0, x1, y1 = (a if x0 is None else max(x0, a), b if y0 is None else max(y0, b),
                              c if x1 is None else min(x1, c), d if y1 is None else min(y1, d))
        hx, hy = VIEW_HALF
        out = []
        for lo, hi, h in ((x0, x1, hx), (y0, y1, hy)):
            lo, hi = (lo + h, hi - h) if hi - lo > 2 * h else ((lo + hi) / 2,) * 2
            out += [lo, hi]
        return out[0], out[2], out[1], out[3]

    def view_point(self, site):
        """The waypoint a camera move aims at: the site, held inside the view rect of the playable area in force (K5).
        A 过场 aims by its phase's border (self.view); any other camera by every border the level uses, since a rule
        can fire in any phase. Published as `CNV <tag> Cam <site> <x> <y>` with its rect in m.views."""
        if self.view is not None:
            names = [self.view]
        else:
            names = sorted({self.d.get('边界') or 'whole'} | {p.spec['边界'] for p in self.phases if p.spec.get('边界')})
        rect = self.view_rect(names)
        x, y = self.m.waypoints[self.m.marks[site]] if site in self.m.marks else self.m.where(site).at()
        x, y = min(max(x, rect[0]), rect[2]), min(max(y, rect[1]), rect[3])
        name = f'CNV {self.tag} Cam {site} {x:.0f} {y:.0f}'      # (an asset id: letters, digits and spaces only)
        self.m.waypoints[name] = (x, y)
        self.m.views[name] = rect
        return name

    def pan_seconds(self, a, prev):
        """A 镜头's seconds: the plan's own, but never so short that the camera flies from the last site faster than
        PAN_SPEED map units a second (a 2 s pan across 800 units looked like a jerk)."""
        secs = float(a.get('秒', CAMERA_MOVE))
        site = str(a['镜头'])
        if prev is None or self.parts(site) or self.parts(prev) or site == prev:
            return secs
        s0, s1 = self.m.where(prev), self.m.where(site)
        return max(secs, math.hypot(s1.x - s0.x, s1.y - s0.y) / PAN_SPEED)

    def compile_talk(self):
        """The scripts that play every queued line (ctx.talk): one at a time, whoever asked."""
        self.m.scripts += self.ctx.talk_scripts()

    @staticmethod
    def is_line(step):
        """A 通报 (a line said or captioned): inside a 过场 it takes the floor like one outside (see say)."""
        if isinstance(step, dict):
            return '通报' in step
        return isinstance(step, str) and step.strip().startswith('通报')

    def chained(self, rest):
        """True when the next thing in a 过场 that takes time is another 镜头 (the pans run into each other)."""
        for s in rest:
            if isinstance(s, dict) and ('停' in s or '跟随' in s):
                return False
            if self.is_line(s):
                return False
            if isinstance(s, dict) and '镜头' in s:
                return True
        return False

    def bans(self, names, allow):
        """ALLOW_DISALLOW_ONE_BUILDING on the player for each (a building or a unit: retail Brighton Beach bans both
        at the start and lets them go as the story goes; the type in lower case, as retail writes it)."""
        if not isinstance(names, list) or not names:
            raise PlanError(f'禁造 / 准造 {names!r}: a list of buildings or units, [机场, ...]')
        out = []
        for u in names:
            try:
                low = self.unit(str(u)).lower()
            except (AssertionError, KeyError, ValueError) as e:
                raise PlanError(f'禁造 / 准造 {u!r}: no such building or unit ({e})')
            self.m.spawns.add(low)
            out.append(('ALLOW_DISALLOW_ONE_BUILDING', self.m.player('p1'), low, allow))
        return out

    def compile_bans(self):
        """禁造: [机场, ...] -- not to be built from the start (docs/design/a4-redesign.md P28: no airfield in the
        A4); {准造: [...]} in a rule lets one go."""
        if self.d.get('禁造') is not None:
            self.m.scripts.append(Script(f'CNV {self.tag} - Bans', [], self.bans(self.d['禁造'], 0)))

    def look_name(self, site):
        """The name a 过场 镜头's reveal at a site goes by (undone when the scene ends; not sight()'s, which a plan's own
        永久 揭开 may hold)."""
        return f'CNV {self.tag} Look {site}'

    def sight(self, site):
        """The name a permanent reveal at a site goes by (MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT undoes it)."""
        self.m.where(site)
        return f'CNV {self.tag} Sight {site}'

    def scene(self, ph):
        talk = self.ctx.talk
        talk.scene = talk.scened = True
        self.view = self.border_at(ph)
        try:
            return self.scene_steps(ph)
        finally:
            talk.scene, self.view = False, None

    def scene_steps(self, ph):
        """A phase's 过场 (retail: 36 of 40 missions open with one): the player's input off and the letterbox on
        from the phase's start; its steps one after another -- 镜头 (a move: its 秒), 跟随 (the camera on one of the
        plan's own for 秒), 停 (秒 of nothing), 揭全图 看一眼 (the whole map, shrouded again at the end), any other
        action at once (a caption, a device's, a 技能: what the camera is to see); then the input back. Returns the
        phase-start actions and the scene's length; the later steps are timed scripts on `段 <phase> + t`."""
        at, t, look, follow = {}, 0.0, False, False
        talk, said = self.ctx.talk, []               # said: (when, actions) of each line, a script of its own
        looked = []                                # sites a 镜头 lifted the shroud at: shrouded again at the hand-back
        steps, prev, joined = list(ph.spec['过场']), None, False
        for i, step in enumerate(steps):
            if isinstance(step, dict) and '停' in step:
                t += seconds(step['停'])
                continue
            if isinstance(step, dict) and '跟随' in step:
                ps = self.parts(str(step['跟随']))
                if not ps:
                    raise PlanError(f'过场 {step!r}: 跟随 one of the plan\'s own (a role)')
                at.setdefault(t, []).append(('CAMERA_FOLLOW_NAMED', self.m.cast[ps[0]].name, 0, FOLLOW_AT))
                t += float(step.get('秒', FOLLOW))
                at.setdefault(t, []).append(('CAMERA_STOP_FOLLOW',))
                follow = True
                continue
            if isinstance(step, dict) and step.get('揭全图') == '看一眼':
                at.setdefault(t, []).append(('MAP_REVEAL_ALL_PERM', self.m.player('p1')))
                look = True
                continue
            if isinstance(step, dict) and '镜头' in step:
                secs = self.pan_seconds(step, prev)
                nxt = self.chained(steps[i + 1:])
                # pans that run into each other are linear at the join: eased only at the first start and last stop
                at.setdefault(t, []).extend(self.camera(step, secs, 0.0 if joined else EASE, 0.0 if nxt else EASE))
                site = str(step['镜头'])
                if not self.parts(site) and site not in looked and step.get('不揭') not in (True, '是'):
                    # the camera sees what the player has not explored (user 2026-11-02: the north camp showed no
                    # buildings or troops): a reveal there while the scene runs, not the whole map
                    looked.append(site)
                    radius = float(step.get('半径') or 0) or min(max(self.m.where(site).r * 1.6, LOOK_MIN), LOOK_MAX)
                    at.setdefault(t, []).append(('MAP_REVEAL_PERMANENTLY_AT_WAYPOINT', self.mark(site), radius,
                                                 self.m.player('p1'), self.look_name(site)))
                t, prev, joined = t + secs, str(step['镜头']), nxt
                continue
            if self.is_line(step):
                # one line at a time, as outside a 过场 (user 2026-11-03: "一句说完了之后再继续说"): a line takes the floor
                # for its own turn (the recording and a gap, or the caption's own reading time; no floor longer than
                # that, E6) and the next starts after it. It is a script of its own that takes the queue's floor
                # (ctx.talk): what was being said when the scene began is finished first
                talk.turn = 0.0
                said.append((t, talk.floor(self.action(step), talk.turn)))
                t, joined = t + talk.turn, False
                continue
            at.setdefault(t, []).extend(self.action(step))
        if t <= 0:
            raise PlanError(f'段 {ph.name} 过场: it takes no time -- a 镜头, 跟随 or 停 gives it its length')
        fire, fire_end = self.ceasefire(ph) if ph.spec.get('停火') else ([], [])
        guard, guard_end = [], []
        for part in ph.spec.get('保护') or []:
            guard += [('UNIT_CHANGE_OBJECT_STATUS', n, 'UNATTACKABLE', 1) for n in self.part_names(part)]
            guard_end += [('UNIT_CHANGE_OBJECT_STATUS', n, 'UNATTACKABLE', 0) for n in self.part_names(part)]
        end = [('SET_FLAG', talk.scening, 0), ('ENABLE_INPUT',), ('CAMERA_LETTERBOX_END',)] + ([('CAMERA_STOP_FOLLOW',)] if follow else []) + \
            ([('MAP_REVEAL_ALL_UNDO_PERM', self.m.player('p1'))] if look else []) + \
            [('MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT', self.look_name(x)) for x in looked] + fire_end + guard_end + \
            [('SET_FLAG', self.scene_flag(ph), 1)]
        at.setdefault(t, []).extend(end)
        now = [('SET_FLAG', talk.scening, 1), ('DISABLE_INPUT',), ('CAMERA_LETTERBOX_BEGIN',)] + fire + guard + \
            at.pop(0.0, [])
        for k, (when, acts) in enumerate(sorted(at.items())):
            self.when(f'Phase {ph.k + 1} scene {k + 1}', f'段 {ph.name} + {when:g}', acts)
        for k, (when, acts) in enumerate(said):         # a line starts when its time is up and the floor is free
            self.when(f'Phase {ph.k + 1} line {k + 1}', f'段 {ph.name} + {when:g}' if when else f'段 {ph.name}', acts,
                      gate=[('FLAG', talk.busy, 0)])
        return now, t

    def ceasefire(self, ph):
        """A 过场 with 停火: 是 -- the sides at war with each other are neutral for its length (retail does this in 14
        of its scenes, PLAYER_RELATES_PLAYER 'Neutral'), so nobody is shot while the player cannot act; war again at
        the hand-back. War is the plan's own at the start: the enemy against the player and against every side of 阵营
        其他 that is its enemy (a later 翻脸 is not followed; the 敌方AI's side is compiled after the phases, and asleep
        while a scene runs, so it is left alone)."""
        m, p1, s1 = self.m, self.m.player('p1'), self.m.player('s1')
        pairs = [(s1, p1)] + [(s1, m.player(x)) for x, rel in self.relation.items() if rel[1] == 'Enemy'] + \
            [(m.player(x), p1) for x, rel in self.relation.items() if rel[0] == 'Enemy']
        pairs = list(dict.fromkeys(pairs))
        return ([relates(b, a, 'Neutral') for a, b in pairs] + [relates(a, b, 'Neutral') for a, b in pairs],
                [relates(b, a, 'Enemy') for a, b in pairs] + [relates(a, b, 'Enemy') for a, b in pairs])

    def scene_flag(self, ph):
        """1 once the phase's 过场 handed the input back (过场 <phase> 结束)."""
        return f'CNV_{self.tag}_Scene_{ph.k + 1}'

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
            rel = [relates(m.player(a), m.player(b), self.relation[x][k // 2])
                   for x in extra for k, (a, b) in enumerate(((x, 'p1'), ('p1', x), (x, 's1'), ('s1', x)))]
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
                m.scripts.append(Script(f'CNV {self.tag} - Guard {base}', [],
                                        self.ctx.order('guard', self.part_names(role), self.area(spec['守']), side)))

    def place_scenery(self):
        """布景: [{单位, 在: <地点>, 偏移: [[dx, dy], ...], 阵营: 平民, 朝向}] -- unnamed props placed by a site, one per
        offset (festival decoration: small ice sculptures, stalls). Units a device publishes (小冰雕) or retail templates."""
        for spec in self.d.get('布景') or []:
            who = spec.get('阵营', '平民')
            if who not in self.side:
                raise PlanError(f'布景 {spec}: 阵营 {who!r} is none of {sorted(self.side)}')
            tmpl = self.unit(spec['单位'], self.side[who])
            for dx, dy in spec.get('偏移') or [(0, 0)]:
                self.m.put(tmpl, spec['在'], float(dx), float(dy), side=self.side[who], angle=spec.get('朝向'))

    def setup_devices(self):
        from devices import registry
        DEVICES = registry()
        for name, spec in (self.d.get('机关') or {}).items():
            kind = spec.get('类型')
            if kind not in DEVICES:
                raise PlanError(f'机关 {name}: no device type {kind!r}: {sorted(DEVICES)}')
            dev = DEVICES[kind](self.ctx, name, spec)
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
            scene = 0.0
            if spec.get('过场'):
                now, scene = self.scene(ph)
                acts += now
                self.m.facts[f'过场 {ph.name}'] = scene
            timed = [t for t in spec.get('目标') or [] if not self.goal(t).spec.get('亮出')]
            for i, title in enumerate(timed):
                # retail: one at a time, a few seconds apart, each with its own announcement (map-language.md 1);
                # after the 过场, when the player has the input back
                g = self.goal(title)
                self.when(f'Phase {ph.k + 1} goal {i + 1}',
                          f'段 {ph.name} + {scene + REVEAL_FIRST + REVEAL_GAP * i:g}',
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

    def compile_shown(self):
        """Goals with 亮出 <condition>: revealed when it first holds (in a phase that lists them: once that phase began
        too) -- retail: 13 of 43 bonus goals only once the player got near (docs/design/teardowns/layout.md 3)."""
        for title, g in self.goals.items():
            c = g.spec.get('亮出')
            if c is None:
                continue
            within = [ph for ph in self.phases if title in (ph.spec.get('目标') or [])]
            self.when(f'Goal {g.name.split()[0]} shown', ([f'段 {within[0].name}'] if within else []) + [c],
                      self.m.reveal(g.name) + [('SET_FLAG', g.revealed, 1)])

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
        warn = [self.ctx.say(self.text('SCRIPT', spec['预警']), CAPTION)] if spec.get('预警') else []
        copies, arrive = self.pace_plan(spec, [*troops, *more], f'进攻 {spec["名字"]}') if spec.get('齐步') in (True, '是') else ({}, None)
        for i in range(1, most + 1):
            for lv, levels in enumerate(ONE):
                for bonus in ([False, True] if stepped else [False]):
                    names, acts, slowed = [], [], []
                    for group, tag in ((troops, ''), (more if bonus else {}, 'x')):
                        for u, ns in group.items():
                            tmpl = self.unit(u, 's1')
                            made = copies.get(tmpl)
                            if not made:
                                m.spawns.add(tmpl)
                            for j in range(ns[lv]):
                                obj = f'UNIT - CNV {self.tag} W{k}-{i} {tmpl} {tag}{j + 1}'
                                names.append(obj)
                                acts.append(('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', obj, made.id if made else tmpl,
                                             m.team('s1'), wp))
                                if made:
                                    slowed.append((obj, made.names['pace']))
                    if not names:
                        continue
                    acts += [('NAMED_RECEIVE_UPGRADE', up, obj) for obj, up in slowed]
                    acts += self.orders(spec, names, w) + [('INCREMENT_COUNTER', 1, sent)] + warn
                    if slowed:                  # released as the first of them gets there (one script each: it may fall)
                        free = [('NAMED_REMOVE_UPGRADE', up, obj) for obj, up in slowed]
                        for n, (obj, _) in enumerate(slowed):
                            m.scripts.append(Script(f'CNV {self.tag} - Pace {k} {i}{"+" if bonus else ""} {TAGS[lv]} {n + 1}',
                                                    [('NAMED_INSIDE_AREA', obj, arrive)], free, levels=levels))
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

    def pace_plan(self, spec, units, what):
        """齐步 for a force: ({template: the paced copy of it (a Unit, added to the mission)}, the area it is released in).
        The slowest mover of the force keeps its own speed, every faster one gets a copy slowed to it (units/pace.py);
        they are released when one gets inside the area round where the force is sent (打 / 守: a place or a role)."""
        from units import pace
        to = spec.get('守') or spec.get('打')
        if not to or to == '猎杀' or to in self.devices:
            raise PlanError(f'{what}: 齐步 needs 打 or 守 with a place or a role -- the force goes together to somewhere '
                            f'(the upgrades are taken away there)')
        group = self.parts(to)
        site = self.m.cast[group[0]].site if group else to
        w = self.m.where(site)
        area = f'CNV {self.tag} Pace {site}'
        self.m.areas.setdefault(area, square(w.x, w.y, max(w.r or 0.0, PACE_ARRIVE)))
        own = {u.id: u.xml for u in self.m.units}
        templates = [self.unit(u, 's1') for u in units]
        speeds = pace.movers(templates, own)
        copies = {}
        if len(speeds) > 1:
            slowest = min(speeds.values())
            for t, v in speeds.items():
                if slowest / v < pace.SAME:
                    unit = pace.paced(t, pace.percent(v, slowest), own.get(t))
                    if unit.id not in own:
                        self.m.units.append(unit)
                    copies[t] = unit
        return copies, area

    def orders(self, spec, names, w, side='s1'):
        w['names'] += names
        target = spec.get('打')
        order = lambda kind, at=None: self.ctx.order(kind, names, at, side)      # (a wave is the enemy's)
        if spec.get('守'):
            return order('guard', self.area(spec['守'])) if names else []    # (the area is made only for someone)
        if not target or target == '猎杀':
            return order('hunt')
        if target in self.devices:
            return []                               # the device's attack scripts (after all the waves are made)
        if self.parts(target):
            group = self.parts(target)
            if len(group) == 1:
                return order('attack', self.part_names(target)[0])
            # a group: attack-move to where it stands (one named target would leave them idle once it fell)
            return order('attack_move', self.mark(self.m.cast[group[0]].site))
        return order('attack_move', self.mark(target))

    def compile_rules(self):
        for k, r in enumerate(self.d.get('规则') or []):
            # once only: a script not done once runs every frame its condition holds (review 2026-10-24: a 给 made
            # the same named unit frame after frame), and "each time it holds again" needs its opposite; again and
            # again is `每隔`: while it holds, then once every so often (retail: a nag every 9 s, Iga)
            if r.get('次数', 1) != 1:
                raise PlanError(f'规则 {k + 1}: 次数 {r["次数"]!r} -- a rule happens once, or again every so often '
                                f'while it holds (每隔)')
            levels = self.difficulty(r, f'规则 {k + 1}')
            talk = self.ctx.talk
            talk.anchored = on_event(r['当'])          # a line in 做 needs an event in 当, or a 镜头 before it (actions)
            try:
                acts = self.actions(r.get('做'))
            except PlanError as e:
                raise PlanError(f'规则 {k + 1} (当 {r["当"]!r}): {e}')
            finally:
                talk.anchored = True
            if r.get('每隔') is None:
                ends = any(isinstance(a, dict) and '失败' in a for a in r.get('做') or [])    # says its own last line
                made = self.when(f'Rule {k + 1}', r['当'], acts, levels=levels,
                                 gate=self.ctx.ending_gate() if ends else ())
                self.m.endings += [s.name for s in made] if ends else []
                continue
            timer = f'CNV {self.tag} Rule {k + 1}'
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
        known = {'性格', '偏好', '上限', '分档', '基地', '资金', '唤醒', '接管', '修理', '重建', '技能'}
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
        # 分档: kinds held back at the start, let go when a step's condition holds (retail Stalingrad: the Soviet
        # AI's tanks and aircraft unlocked by time once it woke, faster the harder [S1 - Soviet Unit Restrictions])
        released = {}                               # template (lower case) -> the flag its step sets
        steps = spec.get('分档') or []
        for k, step in enumerate(steps, 1):
            if not isinstance(step, dict) or set(step) != {'当', '放开'}:
                raise PlanError(f'敌方AI 分档 {step!r}: each {{当: <condition>, 放开: [单位, ...]}}')
            for u in step['放开']:
                low = self.unit(u, 's1').lower()
                if low in released:
                    raise PlanError(f'敌方AI 分档: {u} is let go twice')
                released[low] = f'CNV_{self.tag}_AI_Step_{k}'
        if released:
            m.spawns.update(released)
            m.scripts.append(Script(f'CNV {self.tag} - AI held back', [],
                                    [('ALLOW_DISALLOW_ONE_BUILDING', ai, low, 0) for low in released]))
            for k, step in enumerate(steps, 1):
                lows = [low for low, f in released.items() if f == f'CNV_{self.tag}_AI_Step_{k}']
                self.when(f'AI step {k}', step['当'], [('ALLOW_DISALLOW_ONE_BUILDING', ai, low, 1) for low in lows]
                          + [('SET_FLAG', f'CNV_{self.tag}_AI_Step_{k}', 1)])
        for u, n in (spec.get('上限') or {}).items():
            # retail ("tatsu has limited barracks"): not buildable while it has that many, again when fewer; a
            # personality's SpecificUnitCap did not hold for a power plant (bench 2026-10-25)
            tmpl = self.unit(u, 's1')
            n, low = int(number(n)), tmpl.lower()       # retail writes the type in lower case here
            m.spawns.add(low)
            step = [('FLAG', released[low], 1)] if low in released else []      # not before its step lets it go
            m.scripts += [Script(f'CNV {self.tag} - AI cap {tmpl}', [('PLAYER_HAS_OBJECT_COMPARISON', ai, 3, n, low)],
                                 [('ALLOW_DISALLOW_ONE_BUILDING', ai, low, 0)], once=False),
                          Script(f'CNV {self.tag} - AI cap {tmpl} off',
                                 [('PLAYER_HAS_OBJECT_COMPARISON', ai, 0, n, low)] + step,
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
            relates(ai, s1, 'Friend'), relates(s1, ai, 'Friend'), relates(ai, p1, 'Enemy'), relates(p1, ai, 'Enemy'),
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
            # a main objective with no 完成 of its own (protect someone, hold out) is done by the win itself: ticked
            # before the mission ends (simstatic: a main objective nothing ticks is a wiring fault, 2026-10-27)
            held = [g for g in m.objectives if not g.bonus and not g.spec.get('完成')]
            tick = [a for g in held for a in m.done(g.name) + [('SET_FLAG', self.goal_flag(g, '完成'), 1)]]
            m.endings += [s.name for s in self.when('Win', self.d['胜利'], tick + self.action('胜利'),
                                                    gate=self.ctx.ending_gate())]
        for k, lose in enumerate(self.d.get('失败') or []):
            m.endings += [s.name for s in self.when(f'Lose {k + 1}', lose['当'],
                                                    self.action({'失败': lose.get('原因', '任务失败')}),
                                                    gate=self.ctx.ending_gate())]

    def resume_music(self):
        """E7-6: a music cue suspends the combat music for good, so once a script switches it on, every cue in a script
        that runs in or after that phase is followed by the switch-on again, in the same action list (cue first, then
        ENABLE: the order the bench heard work, music_dyn.py). contract.music_resumes holds the product to it; which
        scripts those are is contract.unresumed_cues (phase scripts and rules gated by a phase's flag; a rule waiting
        for a device's event alone is tied to no phase and is left as written)."""
        if not self.music:
            return
        for s, k in unresumed_cues(self.m.scripts):
            s.do.insert(k + 1, (MUSIC_DYNAMIC, self.music.DYNAMIC_SYSTEM))

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
        self.place_scenery()
        self.setup_goals()
        self.compile_bans()
        self.compile_goals()
        self.compile_phases()
        self.compile_shown()
        for name, w in self.waves.items():
            self.wave(name, w)
        self.compile_rules()
        self.compile_ai()
        self.compile_endings()
        for dev in self.devices.values():
            self.m.scripts += dev.scripts()
        for dev in self.devices.values():
            self.m.scripts += dev.last()
        self.resume_music()
        self.compile_countdowns()
        self.compile_talk()
        for ph in self.phases[1:]:                  # facts: a phase's start, when it is a time from the start
            t = start_time(self.phases[ph.k - 1].spec.get('结束'))
            if t:
                self.m.facts[f'段 {ph.name}'] = t[1]
        for dev in self.devices.values():
            self.m.facts.update(dev.facts())
        if self.d.get('简报'):                      # the briefing screen's mission name and summary (the container's own
            name = str(self.d.get('名字', self.level))      # are the pipeline's test texts)
            self.m.strings.update({'MissionName:CNV01': name, 'MissionName:CNV01_Short': name,
                                   'BriefingSummary:CNV01': str(self.d['简报'])})
        self.m.strings, left = langs.translate(self.m.strings, self.level, self.lang)
        self.m.missing += [f'string {x}' for x in left]
        if self.lang != 'zh':                       # our units' names and tips (the ice engineer's) are in the edition's
            units = []                              # language too; a copy, the unit may be shared with a Chinese build
            for u in self.m.units:
                text, left = langs.translate(u.strings, self.level, self.lang)
                units.append(dataclasses.replace(u, strings=text) if u.strings else u)
                self.m.missing += [f'unit string {x}' for x in left]
            self.m.units = units
        return self.m


def mission(level, name=None, lang='zh'):
    """The level's mission, compiled from its plan, in edition `lang` (langs.py)."""
    return Compiler(load(level), name, lang).compile()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('level')
    import plancheck
    print(plancheck.report(ap.parse_args().level))
