"""The playtest edition (ADR 0025): CampShell as built (`build.py a4 --shell [--lang intl]`), started from the playtest's
own copy of the game, whose Data\\d3d9.dll is the bench's capture shim (experimental/testbench). The mod is the release
one, byte for byte; the dev switches live in the shim and are on only when this script starts the game:

  Ctrl+Alt+=  faster (x1 -> x2 -> x4 -> x8)    Ctrl+Alt+-  slower    Ctrl+Alt+0  back to x1
  Ctrl+Alt+Space  skip the scene: it runs at x8 until the letterbox bars go, then the speed from before
  (the small squares in the top left corner: the speed when it is not x1; cyan while skipping)

  python -I -X utf8 experimental/cnv/playtest.py            the Chinese edition (CampShell)
  python -I -X utf8 experimental/cnv/playtest.py intl       the international edition (CampShellEn)
  python -I -X utf8 experimental/cnv/playtest.py -win       other arguments go on to the game (-win: a window)
  python -I -X utf8 experimental/cnv/playtest.py --prepare  only make / refresh the copy (the game must be closed)

The copy: work/testbench/RA3play (RA3_PLAY_DIR to change), made by make_bench.ps1 (hard links to Steam's big files,
the Steam folder itself is never written). Its shim is refreshed from experimental/testbench/d3d9.dll when it differs.
Speed changes the game's clocks only, not its sound (ADR 0007): at x2 and above lines may overlap.
The third switch, jump to phase N, waits for the level line's phase checkpoint list (docs/simui/handoff.md).
"""
import hashlib
import os
import shutil
import subprocess
import sys
import time
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'campaign')))
import labpaths  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTBENCH = os.path.join(ROOT, 'experimental', 'testbench')
SHIM = os.path.join(TESTBENCH, 'd3d9.dll')
COPY = os.environ.get('RA3_PLAY_DIR') or os.path.join(labpaths.WORK, 'testbench', 'RA3play')
MODS = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
EDITIONS = {'zh': 'CampShell', 'intl': 'CampShellEn'}
KEYS = ('Ctrl+Alt+= 加速（1→2→4→8 倍）  Ctrl+Alt+- 减速  Ctrl+Alt+0 回 1 倍\n'
        'Ctrl+Alt+空格 跳过场（8 倍跑到黑边消失，再回原速；再按一次停止）\n'
        '左上角小方块 = 当前倍速（一格一倍增；青色 = 正在跳过场）')
GAME_NAMES = ('ra3.exe', 'ra3_1.13.game', 'ra3ep1.exe')


def running():
    """The names of RA3 processes running now (any copy: Steam's, the bench's, this one's)."""
    out = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True, text=True, errors='replace').stdout
    names = [line.split('","')[0].strip('"') for line in out.splitlines() if line]
    return sorted({n for n in names if n.lower() in GAME_NAMES or n.lower().startswith('ra3_')})


def sha1(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def prepare(copy=COPY):
    """Make the copy if there is none, and put the current shim in it. The game must be closed. What was done, as text."""
    if not os.path.exists(SHIM):
        raise SystemExit(f'playtest: no shim at {SHIM}: build it first (experimental/testbench/build.bat)')
    done = []
    if not os.path.exists(os.path.join(copy, 'Data', 'RA3_1.13.game')):
        r = subprocess.run(['pwsh', '-NoProfile', '-File', os.path.join(TESTBENCH, 'make_bench.ps1'), '-Bench', copy],
                           capture_output=True, text=True, errors='replace')
        if r.returncode:
            raise SystemExit('playtest: the copy was not made: ' + (r.stderr or r.stdout).strip()[-400:])
        done.append(r.stdout.strip().splitlines()[-1])
    dll = os.path.join(copy, 'Data', 'd3d9.dll')
    if not os.path.exists(dll) or sha1(dll) != sha1(SHIM):
        if os.path.exists(dll):
            os.remove(dll)                      # a real copy in the bench copy, but delete-then-create anyway
        shutil.copyfile(SHIM, dll)
        done.append('shim refreshed in ' + dll)
    return '\n'.join(done) or 'copy ready, shim current'


def command(copy, sku, extra=()):
    """(the game's command line, its environment additions): as the bench starts its copy (harness.Session.start),
    full screen unless -win is passed on, the clocks hooked at x1 and the dev keys on."""
    args = [os.path.join(copy, 'Data', 'RA3_1.13.game'), '-config', os.path.join(copy, 'RA3_chinese_t_1.13.SkuDef'),
            '-runver', '1.13', '-modConfig', sku] + list(extra)
    env = dict(CNV_SPEED='1', CNV_DEV_KEYS='1', CNV_SHOT_DIR=os.path.join(copy, 'playshots'))
    return args, env


def skudef(edition):
    mod = EDITIONS[edition]
    return os.path.join(MODS, mod, f'{mod}_1.0.skudef')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    edition = 'intl' if 'intl' in argv else 'zh'
    extra = [a for a in argv if a not in ('zh', 'intl', '--prepare')]
    busy = running()
    if busy:
        raise SystemExit(f'playtest: RA3 is running ({", ".join(busy)}): close it first (a bench game too)')
    print(prepare())
    if '--prepare' in argv:
        return
    sku = skudef(edition)
    if not os.path.exists(sku):
        raise SystemExit(f'playtest: no {sku}: build it (build.py a4 --shell' + (' --lang intl' if edition == 'intl' else '') + ')')
    args, add = command(COPY, sku, extra)
    os.makedirs(add['CNV_SHOT_DIR'], exist_ok=True)
    p = subprocess.Popen(args, cwd=COPY, env=dict(os.environ, **add))
    time.sleep(5)
    if p.poll() is not None:
        raise SystemExit(f'playtest: the game closed at once (exit {p.returncode}); is Steam up? '
                         f'log: {os.path.join(add["CNV_SHOT_DIR"], "cnv_testbench.log")}')
    print(f'{EDITIONS[edition]} 试玩版已启动（pid {p.pid}）\n{KEYS}\n'
          f'日志：{os.path.join(add["CNV_SHOT_DIR"], "cnv_testbench.log")}')


if __name__ == '__main__':
    main()
