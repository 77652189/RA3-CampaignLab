r"""Where things live, worked out from this file's place (no absolute paths in the code).

  <LAB>\                      e.g. Documents\RA3Modding (moved there from the desktop, 2026-10-18)
    RA3-CampaignLab\          ROOT: this repository; WORK = ROOT\work holds the big local files (not in git)
    RA3-ChineseVoice\         the voice mod (another line, another repository)
    shared\                   both lines: locks\ (test bench lock, GPU leases), gpu_limit.json
    envs\                     Python environments (ra3gen_env for the AI concept route, tools_venv)
    sdk\RA3ModSDK3\           Mod SDK v3.0 (1.12 layouts), the one the builders use; CNV_SDK overrides it
    sdk\RA3ModSDK\            the 1.10-era SDK the first probes (make_campnew, make_campnew3) were built with

CNV_WORK overrides WORK. A line's own worktree next to the main checkout (<LAB>\RA3-CampaignLab-<line>) that has
no work\ of its own uses the main checkout's, so no junction and no environment variable is needed (2026-11-10). A
work\ holding nothing but logs\ is not one of its own: writing a long output to work\logs\ (AGENTS.md) creates it,
and taking it for the line's own lost every file the simulator and the bench read (line A, 11-13: an empty unit
table cached, the bench's game copy not found).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAB = os.path.dirname(ROOT)
MAIN = os.path.join(LAB, 'RA3-CampaignLab')


def _linked(path):
    """A symbolic link or a junction (os.path.isjunction is Python 3.12+; a junction resolves elsewhere)."""
    if os.path.islink(path):
        return True
    isjunction = getattr(os.path, 'isjunction', None)
    if isjunction:
        return isjunction(path)
    return os.path.normcase(os.path.realpath(path)) != os.path.normcase(os.path.abspath(path))


def only_logs(path):
    """A real directory (not a link) whose entries are at most logs\\: what writing a log makes, not a work\\."""
    try:
        return os.path.isdir(path) and not _linked(path) and set(os.listdir(path)) <= {'logs'}
    except OSError:
        return False


def _work(root=None, main=None, env=None):
    root, main = root or ROOT, main or MAIN
    env = os.environ if env is None else env
    if env.get('CNV_WORK'):
        return env['CNV_WORK']
    own = os.path.join(root, 'work')
    sibling = os.path.basename(root).startswith('RA3-CampaignLab-') and os.path.isdir(os.path.join(main, 'work'))
    return os.path.join(main, 'work') if sibling and (not os.path.exists(own) or only_logs(own)) else own


WORK = _work()
SHARED = os.path.join(LAB, 'shared')
ENVS = os.path.join(LAB, 'envs')
SDK3 = os.environ.get('CNV_SDK', os.path.join(LAB, 'sdk', 'RA3ModSDK3'))
SDK_OLD = os.path.join(LAB, 'sdk', 'RA3ModSDK')
# the engine model (ADR 0018): a local, never-pushed repository beside this one; absent on a clean clone
ENGINE_MODEL = os.environ.get('CNV_ENGINE_MODEL', os.path.join(LAB, 'RA3-EngineModel'))
# the Steam game (read only: never write into it); CNV_GAME overrides it
GAME = os.environ.get('CNV_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\Command and Conquer Red Alert 3')
