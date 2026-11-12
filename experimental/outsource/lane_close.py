r"""Close one item of a Codex engine line in one command: rebase on origin/main, run the closing tests, push.

  python -I -X utf8 experimental/outsource/lane_close.py c|e [tests/test_x.py ...]

Run it from the line's own worktree after committing. The closing tests are the files named on the command line
(the ones the item touched), the two guards (tests/test_architecture.py, tests/test_docs.py) and -- only when the
item changed the inventory or its generated pages -- the inventory tests. The output goes to
work/logs/<lane>_close_<stamp>.log; the screen gets the last lines only. Exit 0 = pushed; 1 = red tests (fix and run
again); 2 = uncommitted changes or a rebase conflict (resolve as AGENTS.md says, then run again); 3 = push refused.
"""
import datetime, glob, importlib.util, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('labpaths', os.path.join(os.path.dirname(HERE), 'campaign', 'labpaths.py'))
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)

GUARDS = ['tests/test_architecture.py', 'tests/test_docs.py']
INVENTORY_PATHS = ('experimental/cnv/inventory', 'docs/engine/inventory')
GENERATORS = [['experimental/cnv/inventory.py'], ['experimental/cnv/inventory_levels.py', '--write'],
              ['experimental/cnv/inventory_ai.py', 'levels', '--write']]   # AGENTS.md's order
# the architecture guards that build or walk the levels (each 5-100 s): they judge content, so they run only when the
# item touched content (a map, a mission -- bench missions too --, a play, a device, the story); the coordinator's
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
    if git('rebase', '-q', 'origin/main').returncode:
        conflicts = git('diff', '--name-only', '--diff-filter=U').stdout.split()
        print('rebase 冲突（生成的清单取一边重跑三个生成器，其余照 AGENTS.md）：', ' '.join(conflicts) or '?')
        sys.exit(2)
    inv = any(c.startswith(INVENTORY_PATHS) for c in changed)
    if inv:   # the generated pages go stale whenever main moved under the item: regenerate them, never hand-edit
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
    tests = list(dict.fromkeys(touched + GUARDS + (inventory_tests() if inv else [])))
    skip = [] if any(c.startswith(CONTENT_PATHS) for c in changed) else [
        a for g in CONTENT_GUARDS for a in ('--deselect', f'tests/test_architecture.py::{g}')]
    stamp = datetime.datetime.now().strftime('%m%d_%H%M')
    log = os.path.join(_paths.WORK, 'logs', f'{lane}_close_{stamp}.log')
    with open(log, 'w', encoding='utf-8') as f:
        r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *tests, *skip],
                           stdout=f, stderr=subprocess.STDOUT)
    tail = open(log, encoding='utf-8', errors='replace').read().strip().splitlines()[-6:]
    print(f'收尾测试（{len(tests)} 个文件，日志 {log}）：')
    print('\n'.join(tail))
    if r.returncode:
        sys.exit(1)
    p = git('push', 'origin', 'HEAD:main')
    if p.returncode:
        print('推送被拒（别人刚推过），再跑一次本命令：\n' + p.stderr.strip()[-400:])
        sys.exit(3)
    print('已推 main：' + git('log', '--oneline', '-1').stdout.strip())


if __name__ == '__main__':
    main()
