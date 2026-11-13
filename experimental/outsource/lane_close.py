r"""Close one item of a Codex engine line in one command: rebase on origin/main, run the closing tests, push.

  python -I -X utf8 experimental/outsource/lane_close.py c|e [tests/test_x.py ...]

Run it from the line's own worktree after committing. The closing tests are the files named on the command line
(the ones the item touched -- narrowed to the test functions the item changed in them, the whole file when it
changed a shared helper), the two guards (tests/test_architecture.py, tests/test_docs.py) and -- only when the
item changed the inventory or its generated pages -- the inventory tests. The output goes to
work/logs/<lane>_close_<stamp>.log; the screen gets the last lines only. Exit 0 = pushed; 1 = red tests (fix and run
again); 2 = uncommitted changes or a rebase conflict (resolve as AGENTS.md says, then run again); 3 = push refused. A refused push (another line landed first) is retried by itself after a rebase, without
rerunning the tests, unless what landed touched a file the item changed.
"""
import ast, datetime, glob, importlib.util, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('labpaths', os.path.join(os.path.dirname(HERE), 'campaign', 'labpaths.py'))
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)

GUARDS = ['tests/test_architecture.py', 'tests/test_docs.py',
          'tests/test_no_program_addresses.py']   # 11-13 an address reached simai.py past a Claude line's close
INVENTORY_PATHS = ('experimental/cnv/inventory', 'docs/engine/inventory')
GENERATORS = [['experimental/cnv/inventory.py'], ['experimental/cnv/inventory_levels.py', '--write'],
              ['experimental/cnv/inventory_ai.py', 'levels', '--write']]   # AGENTS.md's order
# the architecture guards that build or walk the levels (each 5-100 s): they judge content, so they run only when the
# item touched content (a map, a level mission, a play, a device, the story); the coordinator's
# full runs cover them otherwise
CONTENT_PATHS = ('experimental/cnv/maps/', 'experimental/cnv/missions/', 'experimental/cnv/plays/',
                 'experimental/cnv/devices/', 'docs/story/')
CONTENT_GUARDS = ['test_g3b_everything_said_comes_from_the_one_queue', 'test_g10_every_camera_move_aims_at_a_view_point',
                  'test_g12_ore_and_oil_come_from_relations', 'test_g13_a_cast_point_is_level_open_ground',
                  'test_g14_a_demonstration_is_staged_in_the_picture', 'test_g15_raised_ground_says_what_it_is_for',
                  'test_ge7_music_resumes_after_a_cue_and_endings_leave_the_end_to_the_library']


def git(*args, check=False):
    r = subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode:
        sys.exit(f'git {" ".join(args)} failed:\n{r.stdout}{r.stderr}')
    return r


def inventory_tests():
    """tests/test_inventory*.py that can run here (one needs the voice repo's module: skipped when it is absent)."""
    out = []
    for f in sorted(glob.glob('tests/test_inventory*.py')):
        if f.replace('\\', '/').endswith('test_inventory_lua.py') and importlib.util.find_spec('ra3voice') is None:
            continue
        out.append(f.replace('\\', '/'))
    return out


def rebase_on_main():
    """Rebase on origin/main. A conflict only in the generated pages (two lines both regenerated them) is settled
    here -- take main's copy and let regenerate() rewrite them -- so it no longer stops the close. True = done."""
    r = git('rebase', '-q', 'origin/main')
    for _ in range(20):
        if not r.returncode:
            return True
        conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.split()
        if not conflicts or not all(c.startswith('docs/engine/inventory') for c in conflicts):
            return False
        git('checkout', '--ours', '--', *conflicts)   # during a rebase "ours" is main
        git('add', '--', *conflicts)
        empty = not git('diff', '--cached', '--quiet').returncode   # a regenerate-only commit with nothing left
        r = git('rebase', '--skip') if empty else git('-c', 'core.editor=true', 'rebase', '--continue')
    return False


def regenerate():
    """The generated pages go stale whenever main moved under the item: regenerate them, never hand-edit."""
    for gen in GENERATORS:
        subprocess.run([sys.executable, '-I', '-X', 'utf8', *gen], capture_output=True)
    git('add', '--', 'docs/engine', check=True)
    # staged text, not `status`: a rewrite that only changes line endings stages nothing and an empty commit
    # failed the whole close (exit 1)
    if git('diff', '--cached', '--quiet', '--', 'docs/engine').returncode:
        msg = 'Regenerate the inventory pages on top of main'
        again = git('log', '-1', '--format=%s').stdout.strip() == msg   # a rerun after a refused push: one commit
        git('commit', '-q', *(['--amend', '--no-edit'] if again else ['-m', msg]), check=True)
        print('清单页面已按最新 main 重新生成并提交')
    else:
        git('checkout', '--', 'docs/engine')   # nothing but line endings: leave the tree clean


def narrow(test_file, base):
    """The tests of one touched file that this item changed, as node ids -- or the whole file when a change falls
    outside a test function (a helper or fixture the others share). The heavy replay files run whole for ~40 min
    (coordinator profile 11-13: a few skirmish replays at 3-5 min each); the coordinator's full run covers the rest."""
    diff = git('diff', '-U0', base, 'HEAD', '--', test_file).stdout
    if not diff.strip() or not os.path.exists(test_file):
        return [test_file]   # named but not changed by this item: the line asked for it, run it whole
    lines, at = set(), None   # new-side line numbers of the added / changed lines that say something
    for row in diff.splitlines():
        m = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', row)
        if m:
            at = int(m.group(1))
            if m.group(2) == '0':
                lines.add(at)    # a pure deletion: blame the line after it
            continue
        if at is None or row.startswith(('+++', '---')):
            continue
        if row.startswith('+'):
            if row[1:].strip():
                lines.add(at)
            at += 1
    tree = ast.parse(open(test_file, encoding='utf-8').read())
    spans = [(f.name, f.decorator_list[0].lineno if f.decorator_list else f.lineno, f.end_lineno)
             for f in tree.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith('test')]
    names = set()
    for ln in lines:
        hit = [name for name, a, b in spans if a <= ln <= b]
        if not hit:
            return [test_file]
        names.update(hit)
    return [f'{test_file}::{n}' for n in sorted(names)] or [test_file]


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('c', 'e', 'a', 'b', 'd'):
        sys.exit(__doc__)
    lane, touched = sys.argv[1], [t.replace('\\', '/') for t in sys.argv[2:]]
    dirty = git('status', '--porcelain', '--untracked-files=no').stdout.strip()
    if dirty:
        print('先提交再收尾，还有没提交的改动：\n' + dirty)
        sys.exit(2)
    git('fetch', '-q', 'origin', check=True)
    base = git('merge-base', 'HEAD', 'origin/main', check=True).stdout.strip()
    changed = git('diff', '--name-only', base, 'HEAD').stdout.split()
    if not rebase_on_main():
        conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.split()
        print('rebase 冲突（生成的清单取一边重跑三个生成器，其余照 AGENTS.md）：', ' '.join(conflicts) or '?')
        sys.exit(2)
    inv = any(c.startswith(INVENTORY_PATHS) for c in changed)
    if inv:
        regenerate()
    picked = [n for f in touched for n in (narrow(f, base) if '::' not in f and f.endswith('.py') else [f])]
    tests = list(dict.fromkeys(picked + GUARDS + (inventory_tests() if inv else [])))
    # an engine line's own bench mission (missions/*_bench.py) is not level content: the content guards cost ~6 min
    # of an 11-min close (c_close_1112_1634: g3b alone 201 s); the coordinator's full run still covers bench missions
    content = [c for c in changed if c.startswith(CONTENT_PATHS)
               and not (c.startswith('experimental/cnv/missions/') and c.endswith('_bench.py'))]
    skip = [] if content else [
        a for g in CONTENT_GUARDS for a in ('--deselect', f'tests/test_architecture.py::{g}')]
    stamp = datetime.datetime.now().strftime('%m%d_%H%M')
    log = os.path.join(_paths.WORK, 'logs', f'{lane}_close_{stamp}.log')
    with open(log, 'w', encoding='utf-8') as f:
        r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                            '--durations=12', '--durations-min=10', *tests, *skip],   # where a slow close goes
                           stdout=f, stderr=subprocess.STDOUT)
    tail = open(log, encoding='utf-8', errors='replace').read().strip().splitlines()[-6:]
    print(f'收尾测试（{len(tests)} 个文件，日志 {log}）：')
    print('\n'.join(tail))
    if r.returncode:
        sys.exit(1)
    # a refused push is another line landing first (11-12 E closed three times, ~4 min of tests each): rebase and
    # push again without rerunning the tests -- unless what landed touched a file this item changed
    for _ in range(4):
        p = git('push', 'origin', 'HEAD:main')
        if not p.returncode:
            break
        head = git('rev-parse', 'origin/main').stdout.strip()
        git('fetch', '-q', 'origin', check=True)
        landed = set(git('diff', '--name-only', head, 'origin/main').stdout.split())
        if not rebase_on_main():
            print('推送被拒后 rebase 冲突，照 AGENTS.md 解决后再跑本命令')
            sys.exit(2)
        if landed & (set(changed) - {c for c in changed if c.startswith('docs/engine/')}):
            print('推送被拒，别人刚改了本项也改的文件，再跑一次本命令（会重跑测试）：' + ' '.join(sorted(landed & set(changed))))
            sys.exit(3)
        if inv:
            regenerate()
        print('推送被拒（别人刚推过），已 rebase，不重跑测试，再推一次')
    else:
        print('推送连续被拒，再跑一次本命令：\n' + p.stderr.strip()[-400:])
        sys.exit(3)
    print('已推 main：' + git('log', '--oneline', '-1').stdout.strip())


if __name__ == '__main__':
    main()
