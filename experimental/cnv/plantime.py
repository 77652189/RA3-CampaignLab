"""The plan's pure words for numbers that change with the difficulty: easy/normal/hard triples, times, counts, and
the error a plan raises. Nothing here reads a plan or touches the compiler, so a device (devices/) takes these from
here, not from plan.py -- the devices are the compiler's inputs and must not import it back (ADR 0016, guard G9)."""

TAGS = ('easy', 'normal', 'hard')          # in script names: the map stores names as Latin-1
ALL = (True, True, True)
ONE = ((True, False, False), (False, True, False), (False, False, True))


class PlanError(ValueError):
    pass


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
