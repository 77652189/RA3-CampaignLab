r"""Where things live, worked out from this file's place (no absolute paths in the code).

  <LAB>\                      e.g. Documents\RA3Modding (moved there from the desktop, 2026-10-18)
    RA3-CampaignLab\          ROOT: this repository; WORK = ROOT\work holds the big local files (not in git)
    RA3-ChineseVoice\         the voice mod (another line, another repository)
    shared\                   both lines: locks\ (test bench lock, GPU leases), gpu_limit.json
    envs\                     Python environments (ra3gen_env for the AI concept route, tools_venv)
    sdk\RA3ModSDK3\           Mod SDK v3.0 (1.12 layouts), the one the builders use; CNV_SDK overrides it
    sdk\RA3ModSDK\            the 1.10-era SDK the first probes (make_campnew, make_campnew3) were built with
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAB = os.path.dirname(ROOT)
WORK = os.path.join(ROOT, 'work')
SHARED = os.path.join(LAB, 'shared')
ENVS = os.path.join(LAB, 'envs')
SDK3 = os.environ.get('CNV_SDK', os.path.join(LAB, 'sdk', 'RA3ModSDK3'))
SDK_OLD = os.path.join(LAB, 'sdk', 'RA3ModSDK')
