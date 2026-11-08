"""Cold-start check: what this project needs outside the repository, one line per item, and what to do about it.

    python -I -X utf8 experimental/testbench/doctor.py [--verbose]

OK / WARN / MISSING / BROKEN per item; exit 1 when anything is MISSING or BROKEN (WARN: regenerable or optional).
Read only: it writes nothing, starts no game, takes no lock (it only runs each env's python once to print its version,
and tasklist to see Steam).
Rebuilding each item: README.md, Requirements section."""
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
_spec = importlib.util.spec_from_file_location('labpaths', os.path.join(ROOT, 'experimental', 'campaign', 'labpaths.py'))
labpaths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(labpaths)

BENCH = os.environ.get('RA3_BENCH_DIR') or os.path.join(labpaths.WORK, 'testbench', 'RA3')   # same rule as slots.py
LOCKS = os.path.join(os.environ.get('RA3_SHARED') or labpaths.SHARED, 'locks')
BENCH_FILES = [os.path.join('Data', 'RA3_1.13.game'), 'RA3_chinese_t_1.13.SkuDef']          # what harness.py launches
ENV_NAMES = ['bench_mcp', 'ra3gen_env', 'tools_venv']
ENV_HOWTO = 'recreate it from experimental/testbench/envs/{0}.txt (README, Requirements)'

results = []        # (status, name, detail, hint)


def add(status, name, detail='', hint=''):
    results.append((status, name, detail, hint))


def check_path(name, path, hint, must_be_dir=False):
    ok = os.path.isdir(path) if must_be_dir else os.path.isfile(path)
    add('OK' if ok else 'MISSING', name, path, '' if ok else hint)
    return ok


def env_python(env):
    for rel in ('python.exe', os.path.join('Scripts', 'python.exe')):      # conda: root; venv: Scripts
        p = os.path.join(labpaths.ENVS, env, rel)
        if os.path.isfile(p):
            return p
    return None


def python_version(py):
    try:
        r = subprocess.run([py, '-I', '-c', 'import sys; print(sys.version.split()[0])'], capture_output=True, text=True,
                           timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    return (r.stdout.strip(), '') if r.returncode == 0 else (None, (r.stderr or r.stdout).strip()[-200:])


STEAM_HOWTO = 'restart Steam and wait for its library to show (the game shows "Failed to initialize Steam" till then)'


def steam_log():
    """Steam's login log (logs/steamui_login.txt under the Steam folder the registry names), or None."""
    root = r'C:\Program Files (x86)\Steam'
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as k:
            root = winreg.QueryValueEx(k, 'SteamPath')[0]
    except (OSError, ImportError):
        pass
    p = os.path.join(root, 'logs', 'steamui_login.txt')
    return p if os.path.isfile(p) else None


def steam_state(tail):
    """(status, detail) from the end of steamui_login.txt: OK when the last login state set is Success and no
    "Timed out waiting for library ready" came after it (bench 2026-11-08: after a boot Steam logged that for minutes
    and every game start failed on a Steam box)."""
    state, stuck = None, False
    for line in tail.splitlines():
        if 'SetLoginState:' in line:
            state = line.split('SetLoginState:', 1)[1].split(' - ')[0].strip()
            stuck = False
        elif 'Timed out waiting for library ready' in line:
            stuck = True
    if state is None and not stuck:
        return 'WARN', 'no login state in the log tail'
    if stuck:
        return 'BROKEN', 'Steam timed out waiting for its library (WaitingForLibraryReady)'
    if state != 'Success':
        return 'BROKEN', f'Steam login state {state}'
    return 'OK', 'login state Success'


def steam_running():
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq steam.exe', '/NH'], capture_output=True, text=True,
                           timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return 'steam.exe' in r.stdout.lower()


def check_steam():
    log = steam_log()
    if log is None:
        add('WARN', 'Steam ready', 'no logs/steamui_login.txt found', 'cannot tell: start Steam once')
        return
    if steam_running() is False:
        add('BROKEN', 'Steam ready', 'steam.exe is not running', 'start Steam (the game needs it)')
        return
    with open(log, 'rb') as f:
        f.seek(max(0, os.path.getsize(log) - 8192))
        tail = f.read().decode('utf-8', 'replace')
    status, detail = steam_state(tail)
    add(status, 'Steam ready', f'{log}: {detail}', '' if status == 'OK' else STEAM_HOWTO)


def main():
    verbose = '--verbose' in sys.argv

    # SDK3 and its builder
    if check_path('SDK3', labpaths.SDK3, 'put Mod SDK v3.0 (1.12 layouts) at ' + labpaths.SDK3 + ' or set CNV_SDK',
                  must_be_dir=True):
        check_path('SDK3 BinaryAssetBuilder', os.path.join(labpaths.SDK3, 'tools', 'BinaryAssetBuilder.exe'),
                   'the SDK folder is incomplete: unpack the whole Mod SDK v3.0 again')

    # the Steam game (read only source of the bench copy)
    check_path('game (Steam)', labpaths.GAME, 'install Red Alert 3 from Steam or set CNV_GAME', must_be_dir=True)
    check_steam()

    # bench copy
    miss = [f for f in BENCH_FILES if not os.path.isfile(os.path.join(BENCH, f))]
    shim = os.path.isfile(os.path.join(BENCH, 'Data', 'd3d9_next.dll'))
    if miss or not shim:
        add('MISSING', 'bench game copy', BENCH + ' lacks ' + ', '.join(miss + ([] if shim else ['Data\\d3d9_next.dll'])),
            'pwsh experimental/testbench/make_bench.ps1 (needs experimental/testbench/d3d9.dll: build.bat first; game closed)')
    else:
        add('OK', 'bench game copy', BENCH)

    # shared
    check_path('shared/locks', LOCKS, 'create the folder ' + LOCKS + ' (empty is fine)', must_be_dir=True)
    check_path('shared/gpu_limit.json', os.path.join(labpaths.SHARED, 'gpu_limit.json'),
               'copy gpu_limit.json from the other machine/line, or create it (see RA3-ChineseVoice)')

    # envs
    for env in ENV_NAMES:
        py = env_python(env)
        if not py:
            add('MISSING', 'env ' + env, os.path.join(labpaths.ENVS, env), ENV_HOWTO.format(env))
            continue
        ver, err = python_version(py)
        if ver:
            add('OK', 'env ' + env, f'{py} (python {ver})')
        else:
            add('BROKEN', 'env ' + env, f'{py}: {err}', 'delete and ' + ENV_HOWTO.format(env))

    # voice repo
    check_path('voice repo', os.path.join(labpaths.LAB, 'RA3-ChineseVoice'),
               'git clone https://github.com/77652189/RA3-ChineseVoice next to this repository', must_be_dir=True)

    # MCP server command
    mcp = os.path.join(ROOT, '.mcp.json')
    try:
        with open(mcp, encoding='utf-8') as f:
            srv = json.load(f)['mcpServers']['ra3bench']
        cmd = srv['command']
        script = [a for a in srv.get('args', []) if a.lower().endswith('.py')]
        bad = [p for p in [cmd] + script if not os.path.isfile(p)]
        if bad:
            add('MISSING', 'MCP ra3bench (.mcp.json)', ', '.join(bad),
                'fix the paths in .mcp.json (command = envs/bench_mcp python, script = experimental/testbench/bench_mcp.py)')
        else:
            add('OK', 'MCP ra3bench (.mcp.json)', cmd)
    except (OSError, KeyError, ValueError) as e:
        add('BROKEN', 'MCP ra3bench (.mcp.json)', f'{type(e).__name__}: {e}', 'restore .mcp.json from git')

    # fingerprint baseline (regenerable)
    base = os.path.join(labpaths.WORK, 'fingerprint', 'baseline.json')
    if os.path.isfile(base):
        add('OK', 'fingerprint baseline', base)
    else:
        add('WARN', 'fingerprint baseline', base,
            'regenerable: python -I -X utf8 experimental/testbench/fingerprint.py record baseline (needs a built SDK and no game running)')

    # tools the build calls: labpaths names none beyond the SDK (ffmpeg is not used by the build)

    worst = 0
    for status, name, detail, hint in results:
        line = f'{status:<7} {name}'
        if status != 'OK':
            line += ' -> ' + hint
        if verbose or status != 'OK' and detail:
            line += f'\n          [{detail}]'
        print(line)
        if status in ('MISSING', 'BROKEN'):
            worst = 1
    bad = sum(1 for r in results if r[0] in ('MISSING', 'BROKEN'))
    print(f'doctor: {len(results)} items, {bad} missing/broken' if bad else f'doctor: {len(results)} items, all there')
    return worst


if __name__ == '__main__':
    sys.exit(main())
