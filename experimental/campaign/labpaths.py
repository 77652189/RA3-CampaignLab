r"""Where things live, worked out from this file's place (no absolute paths in the code).

  <LAB>\                      e.g. Documents\RA3Modding (moved there from the desktop, 2026-10-18)
    RA3-CampaignLab\          ROOT: this repository; WORK = ROOT\work holds the big local files (not in git)
    RA3-ChineseVoice\         the voice mod (another line, another repository)
    shared\                   both lines: locks\ (test bench lock, GPU leases), gpu_limit.json
    envs\                     Python environments (ra3gen_env for the AI concept route, tools_venv)
    sdk\RA3ModSDK3\           Mod SDK v3.0 (1.12 layouts), the one the builders use; CNV_SDK overrides it
    sdk\RA3ModSDK\            the 1.10-era SDK the first probes (make_campnew, make_campnew3) were built with

CNV_WORK overrides WORK. A line's own worktree next to the main checkout (<LAB>\RA3-CampaignLab-<line>) that has
no work\ of its own uses the main checkout's, so no junction and no environment variable is needed (2026-11-10).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAB = os.path.dirname(ROOT)
MAIN = os.path.join(LAB, 'RA3-CampaignLab')


def _work():
    if os.environ.get('CNV_WORK'):
        return os.environ['CNV_WORK']
    own = os.path.join(ROOT, 'work')
    sibling = os.path.basename(ROOT).startswith('RA3-CampaignLab-') and os.path.isdir(os.path.join(MAIN, 'work'))
    return os.path.join(MAIN, 'work') if sibling and not os.path.exists(own) else own


WORK = _work()
SHARED = os.path.join(LAB, 'shared')
ENVS = os.path.join(LAB, 'envs')
SDK3 = os.environ.get('CNV_SDK', os.path.join(LAB, 'sdk', 'RA3ModSDK3'))
SDK_OLD = os.path.join(LAB, 'sdk', 'RA3ModSDK')
# the engine model (ADR 0018): a local, never-pushed repository beside this one; absent on a clean clone
ENGINE_MODEL = os.environ.get('CNV_ENGINE_MODEL', os.path.join(LAB, 'RA3-EngineModel'))
# the Steam game (read only: never write into it); CNV_GAME overrides it
GAME = os.environ.get('CNV_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\Command and Conquer Red Alert 3')
