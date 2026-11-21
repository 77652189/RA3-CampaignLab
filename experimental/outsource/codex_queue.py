r"""Keep Codex busy: run the briefs in a queue folder one after another, each in a fresh worktree, so Codex never
waits for the coordinator to notice it finished (11-18: it sat idle twice, ~2 h and ~1.5 h, after a result came in).

    python -I -X utf8 experimental/outsource/codex_queue.py QUEUE_DIR [--hours 12] [--minutes 120]

QUEUE_DIR holds briefs (*.md, the codex_task.py contract: a "Files:" and a "Tests:" section). The oldest by name
runs first (name them 01-..., 02-...). A brief may say `Effort: high` on a line of its own (default medium). Each
runs as `codex_task.py <brief> --dir ../RA3-CampaignLab-cx-<stem> --full` in a worktree made fresh from
origin/main, then moves to QUEUE_DIR/done/ with its answer beside it. Nothing is committed and no worktree is
removed: the coordinator reviews each result, commits from that worktree, then removes it. A new brief dropped into
the folder while this runs is picked up; with none left it waits (checking every 2 min) until --hours have passed.
The state -- running, done, waiting -- is in work/logs/<folder name>.json. Two folders, two runners: Codex works on
two briefs at once (user 11-19: "codex的任务可以适当多派一些"); give each brief a name no other folder uses (the
worktree is named after it).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
_spec = importlib.util.spec_from_file_location('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
labpaths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(labpaths)
STATE_DIR = os.path.join(labpaths.WORK, 'logs')


def save(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, os.path.basename(state['queue']) + '.json'), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def worktree(stem):
    path = os.path.normpath(os.path.join(ROOT, '..', f'RA3-CampaignLab-cx-{stem}'))
    if not os.path.exists(path):
        subprocess.run(['git', '-C', ROOT, 'fetch', '-q', 'origin'], check=True)
        subprocess.run(['git', '-C', ROOT, 'worktree', 'add', '-q', '--detach', path, 'origin/main'], check=True)
    return path


def run_one(brief, minutes, done_dir):
    stem = re.sub(r'[^A-Za-z0-9-]', '-', os.path.splitext(os.path.basename(brief))[0])[:40]
    text = open(brief, encoding='utf-8').read()
    effort = 'high' if re.search(r'^Effort:\s*high\s*$', text, re.M | re.I) else 'medium'
    tree = worktree(stem)
    log = os.path.join(STATE_DIR, f'codex_q_{stem}.log')
    t0 = time.time()
    with open(log, 'w', encoding='utf-8') as out:
        code = subprocess.run([sys.executable, '-I', '-X', 'utf8', os.path.join(HERE, 'codex_task.py'), brief,
                               '--dir', tree, '--full', '--minutes', str(minutes), '--effort', effort],
                              stdout=out, stderr=subprocess.STDOUT, cwd=ROOT).returncode
    os.makedirs(done_dir, exist_ok=True)
    base = os.path.splitext(brief)[0]
    for p in [brief] + glob.glob(base + '.answer.md') + glob.glob(base + '.events.jsonl') + glob.glob(base + '.stderr.txt'):
        shutil.move(p, os.path.join(done_dir, os.path.basename(p)))
    return {'brief': os.path.basename(brief), 'tree': tree, 'log': log, 'exit': code,
            'seconds': round(time.time() - t0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('queue')
    ap.add_argument('--hours', type=float, default=12)
    ap.add_argument('--minutes', type=int, default=120, help='each brief\'s safety stop (codex_task.py --minutes)')
    a = ap.parse_args()
    queue = os.path.abspath(a.queue)
    done_dir = os.path.join(queue, 'done')
    state = {'queue': queue, 'running': None, 'done': [], 'waiting_since': None}
    end = time.time() + a.hours * 3600
    while time.time() < end:
        briefs = sorted(glob.glob(os.path.join(queue, '*.md')))
        briefs = [b for b in briefs if not b.endswith('.answer.md')]
        if not briefs:
            state['running'], state['waiting_since'] = None, state['waiting_since'] or time.strftime('%Y-%m-%d %H:%M')
            save(state)
            time.sleep(120)
            continue
        state['running'], state['waiting_since'] = os.path.basename(briefs[0]), None
        save(state)
        state['done'].append(run_one(briefs[0], a.minutes, done_dir))
        save(state)
    state['running'] = None
    save(state)


if __name__ == '__main__':
    main()
