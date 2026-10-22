r"""One entry point for the everyday steps, so a session runs fixed commands instead of writing a fresh inline
script each time (inline scripts are where backslashes got eaten and files got garbled).

  python -I -X utf8 cnv.py build 30 [CNV_EASY=1 ...]   build make_campnew30.py (env settings after it), then draw
                                                         its map (work/maps/<mod>.png)
  python -I -X utf8 cnv.py map CampNew30 [--around X Y R] [--bench-view] [--px N]       top-down map picture
  python -I -X utf8 cnv.py bench CampNew30 -s 120 --shots 30,60,90 [--actions '...'] [--visible]
                                                         test bench run (-Nav); shots kept in
                                                         work/testbench/runs/<mod>_<time>/ with a contact sheet
  python -I -X utf8 cnv.py sheet <folder> [-o out.png]  contact sheet of the PNGs in a folder
  python -I -X utf8 cnv.py where X Y [--view VX VY]     world point -> bench screen (start camera, or after the
                                                         camera was moved to VX VY by a minimap click) + minimap
  python -I -X utf8 cnv.py launcher CampNew30           (re)write Mods\CampNew30\Play_CampNew30.bat
  python -I -X utf8 cnv.py install CampNew30            a build staged while RA3 ran (work\staging) -> Mods
  python -I -X utf8 cnv.py status                       is RA3 running, who holds the bench / GPU locks
  python -I -X utf8 cnv.py make a8 [--check jump] [--no-build]   the decoupled builds (experimental/cnv/build.py:
                                                         units / maps / missions / checks declared apart); with
                                                         --check, a bench run judged on its counters: PASS / FAIL

Bench actions ('sec:kind:args;...'): click:x,y  rclick:x,y  drag:x0,y0,x1,y1  key:vk  wheel:n  (run_bench.ps1).
"""
import argparse
import datetime
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CAMPAIGN = os.path.join(ROOT, 'experimental', 'campaign')
TESTBENCH = os.path.join(ROOT, 'experimental', 'testbench')
sys.path[:0] = [ROOT, CAMPAIGN, TESTBENCH]
import labpaths  # noqa: E402

MODS = os.path.join(os.path.expanduser('~'), 'Documents', 'Red Alert 3', 'Mods')
RUNS = os.path.join(labpaths.WORK, 'testbench', 'runs')
SHOTS = os.path.join(labpaths.WORK, 'testbench', 'RA3', 'shots')


def game_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return 'ra3_1.' in out or 'ra3.exe' in out or 'ra3ep1' in out      # Uprising too


def mod_dir(mod):
    for base in (MODS, os.path.join(labpaths.WORK, 'staging')):
        if os.path.exists(os.path.join(base, mod, mod + '_1.0.skudef')):
            return os.path.join(base, mod)
    raise SystemExit(f'no built mod {mod} (looked in {MODS} and work\\staging)')


def cmd_build(a):
    script = os.path.join(CAMPAIGN, f'make_campnew{a.mission}.py' if a.mission.isdigit() else a.mission)
    env = dict(os.environ)
    for kv in a.env:
        k, _, v = kv.partition('=')
        env[k] = v
    r = subprocess.run([sys.executable, '-I', '-X', 'utf8', script], env=env)
    if r.returncode:
        raise SystemExit(r.returncode)
    if a.mission.isdigit():
        a.source, a.out, a.px, a.around, a.bench_view = f'CampNew{a.mission}', None, 4, None, False
        cmd_map(a)


def cmd_map(a):
    import maprender
    out = a.out or os.path.join(maprender.OUT_DIR, os.path.splitext(os.path.basename(a.source))[0] + '.png')
    print(maprender.render(maprender.load(a.source), out, a.px, a.around, a.bench_view,
                           title=os.path.basename(a.source)))


def sheet(folder, out, cols=4, width=400):
    from PIL import Image, ImageDraw
    files = sorted(glob.glob(os.path.join(folder, '*.png')))
    files = [f for f in files if os.path.abspath(f) != os.path.abspath(out)]
    if not files:
        raise SystemExit(f'no PNGs in {folder}')
    first = Image.open(files[0])
    h = int(width * first.height / first.width)
    rows = (len(files) + cols - 1) // cols
    s = Image.new('RGB', (width * cols, (h + 16) * rows), 'white')
    d = ImageDraw.Draw(s)
    for k, f in enumerate(files):
        x, y = (k % cols) * width, (k // cols) * (h + 16)
        s.paste(Image.open(f).convert('RGB').resize((width, h)), (x, y))
        d.text((x + 3, y + h + 2), os.path.basename(f), fill='black')
    s.save(out)
    return out


def cmd_sheet(a):
    print(sheet(a.folder, a.out or os.path.join(a.folder, 'sheet.png')))


def cmd_bench(a):
    if game_running():
        raise SystemExit('RA3 is running (the user may be playing, or another bench run): not starting the bench')
    skudef = os.path.join(mod_dir(a.mod), a.mod + '_1.0.skudef')
    for old in glob.glob(os.path.join(SHOTS, '*.png')):
        os.remove(old)                          # this run's frames only (the folder is the bench's scratch space)
    args = ['pwsh', '-NoProfile', '-File', os.path.join(TESTBENCH, 'run_bench.ps1'), '-Nav', '-Mod', skudef,
            '-Seconds', str(a.seconds), '-Shots', a.shots]
    if a.actions:
        args += ['-Actions', a.actions]
    if a.visible:
        args += ['-Visible']
    r = subprocess.run(args, capture_output=True, text=True, errors='replace')
    for line in r.stdout.splitlines():
        if line.startswith(('NAV', 'RESULT', 'ABORT', 'ERROR')) or 'crash' in line.lower():
            print(line)
    shots = sorted(glob.glob(os.path.join(SHOTS, '*.png')))
    if not shots:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit('no shots')
    run = os.path.join(RUNS, f'{a.mod}_{datetime.datetime.now():%m%d_%H%M%S}')
    os.makedirs(run)
    for f in shots:
        shutil.copy2(f, run)
    print('shots:', run)
    print('sheet:', sheet(run, os.path.join(run, 'sheet.png')))


def cmd_where(a):
    import calib
    if a.view:
        u, v = calib.world_to_screen_at(a.x, a.y, tuple(a.view))
        mu, mv = calib.world_to_minimap(*a.view)
        print(f'screen {u},{v} after a minimap left-click at {mu},{mv} (camera to {a.view[0]:g},{a.view[1]:g})')
    else:
        print('screen', *calib.world_to_screen(a.x, a.y), '(start camera)')
    print('minimap', *calib.world_to_minimap(a.x, a.y))


def cmd_launcher(a):
    import make_campnew4
    if game_running():
        raise SystemExit('RA3 is running: not writing into the Mods folder')
    print(make_campnew4.write_launcher(mod_dir(a.mod), a.mod))


def cmd_install(a):
    """A build staged while RA3 ran (work\\staging\\<mod>) goes into the Mods folder (its files replace the older
    build's files of the same names)."""
    if game_running():
        raise SystemExit('RA3 is running: not writing into the Mods folder')
    src = os.path.join(labpaths.WORK, 'staging', a.mod)
    if not os.path.isdir(src):
        raise SystemExit(f'nothing staged for {a.mod}')
    dst = os.path.join(MODS, a.mod)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src, f), os.path.join(dst, f))
        print('->', os.path.join(dst, f))


def cmd_status(a):
    print("RA3 running" if game_running() else "RA3 not running", flush=True)
    subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'ra3voice', 'reslock.py'), 'status'])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('build')
    p.add_argument('mission', help='campaign number (30 -> make_campnew30.py) or a script name')
    p.add_argument('env', nargs='*', help='KEY=VALUE settings for the build')
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser('map')
    p.add_argument('source')
    p.add_argument('-o', '--out')
    p.add_argument('--px', type=int, default=4)
    p.add_argument('--around', type=float, nargs=3, metavar=('X', 'Y', 'R'))
    p.add_argument('--bench-view', action='store_true')
    p.set_defaults(fn=cmd_map)
    p = sub.add_parser('bench')
    p.add_argument('mod')
    p.add_argument('-s', '--seconds', type=int, default=60)
    p.add_argument('--shots', default='5,30,55')
    p.add_argument('--actions', default='')
    p.add_argument('--visible', action='store_true')
    p.set_defaults(fn=cmd_bench)
    p = sub.add_parser('sheet')
    p.add_argument('folder')
    p.add_argument('-o', '--out')
    p.set_defaults(fn=cmd_sheet)
    p = sub.add_parser('where')
    p.add_argument('x', type=float)
    p.add_argument('y', type=float)
    p.add_argument('--view', type=float, nargs=2, metavar=('VX', 'VY'))
    p.set_defaults(fn=cmd_where)
    p = sub.add_parser('launcher')
    p.add_argument('mod')
    p.set_defaults(fn=cmd_launcher)
    p = sub.add_parser('install')
    p.add_argument('mod')
    p.set_defaults(fn=cmd_install)
    p = sub.add_parser('status')
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser('make')
    p.add_argument('rest', nargs=argparse.REMAINDER, help='build.py arguments: <name> [--check c] [--no-build]')
    p.set_defaults(fn=lambda a: sys.exit(subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(
        ROOT, 'experimental', 'cnv', 'build.py')] + a.rest).returncode))
    a = ap.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()
