"""G3b (ADR 0016 phase 3, K1 + K2): replay every campaign level to check caption timing and strip depth."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CNV = 'experimental/cnv'

G3B_PROBE = '''
import sys
sys.path[:0] = [{cnv!r}, {root!r}]
import build, ctx, plan, sim, strip
levels = {{n: build.resolve(n, '')[:2] for n in sorted(build.LEVELS)}}
close, deep = [], []
for lv in build.LEVELS:
    s = sim.Sim(*levels[lv]).run({until})
    # E6: a 功能 caption is up within ctx.FUNC_LATE of its event (a scene's seconds do not count), in every level's run
    close += [(lv, f, round(a, 1)) for f, a, _ in s.late_captions()]
    deep += [(lv, d) for d in strip.too_deep(s)]
print('G3B close', close[:5])
print('G3B strip', deep[:5])
# I1 mutation: a queue that lets any number of lines into the strip (the product's state before 2026-11-05) is caught
ctx.STRIP_MAX = plan.STRIP_MAX = 99
m, t, _ = build.resolve('a4', '')  # recompile the queue under the raised limit
# An overlap during the first scene is already a witness. Otherwise finish the original run.
end = 200.0
opening = min(end, next((secs for name, secs in m.facts.items() if name.startswith('过场 ')), end))
s = sim.Sim(m, t).run(opening)
overlaps = strip.too_deep(s)
if not overlaps and opening < s.t <= end:
    overlaps = strip.too_deep(s.run(end))
print('G3B strip mutation', bool(overlaps))
'''


def test_g3b_everything_said_comes_from_the_one_queue():
    import sys
    probe = G3B_PROBE.format(cnv=str(ROOT / CNV), root=str(ROOT), until=900.0)
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', '-c', probe], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert 'G3B close []' in r.stdout, r.stdout.strip()
    assert 'G3B strip []' in r.stdout and 'G3B strip mutation True' in r.stdout, r.stdout.strip()
