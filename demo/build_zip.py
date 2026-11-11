"""Pack the simulator demo into one stand-alone zip (work/demo/ra3sim_demo.zip): the Python sources the demo imports,
mission A4's plan, and the two unit-data caches. No game files, no private engine model, nothing from work/re.

    python demo/build_zip.py
"""
import glob
import os
import zipfile
import sys
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'experimental', 'campaign')))
import labpaths  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(labpaths.WORK, 'demo', 'ra3sim_demo.zip')
TOP = 'ra3sim_demo'
PATTERNS = [
    'demo/run_demo.py', 'demo/voice_snapshot.py',
    'experimental/cnv/*.py', 'experimental/cnv/devices/*.py', 'experimental/cnv/maps/*.py',
    'experimental/cnv/missions/*.py', 'experimental/cnv/units/*.py',
    'experimental/campaign/*.py', 'experimental/music/*.py', 'experimental/voice/pack.py', 'ra3voice/*.py',
    'docs/story/plans/a4.md', 'docs/story/plans/a4.en.json',
    'work/sim_combat_v2.json', 'work/sim_units_v3.json',
    'work/demo/SIM_README.txt',
]
FORBIDDEN = ('work/re', 'EngineModel', 'ra3model')
# the few of the Mod SDK's own unit/data files the plan compiler reads (EA's, from the SDK the user already has; the
# demo points CNV_SDK at sdk3/ when it is there). The clean-folder run finds any that is missing.
SDK_FILES = [
    'Allied/Structures/AlliedBarracks.xml', 'Allied/Structures/AlliedConstructionYard.xml',
    'Allied/Units/AlliedEngineer.xml', 'Allied/Units/AlliedMiner.xml', 'GlobalData/GlobalDefines.xml',
    'GlobalData/Locomotor.xml', 'GlobalData/LogicCommandSet.xml', 'SkirmishAI/Personalities/JapanBalanced.xml',
    'Sounds/Voice.xml', 'Soviet/Structures/SovietBunker.xml',
]


def main():
    files = sorted({os.path.relpath(p, ROOT).replace(os.sep, '/') for pat in PATTERNS
                    for p in glob.glob(os.path.join(ROOT, pat))})
    bad = [f for f in files if any(x in f for x in FORBIDDEN)]
    assert not bad, bad
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(os.path.join(ROOT, f), f'{TOP}/{f}')
        sdk = os.path.join(os.environ.get('CNV_SDK', os.path.join(os.path.dirname(ROOT), 'sdk', 'RA3ModSDK3')), 'SageXML')
        for f in SDK_FILES:
            z.write(os.path.join(sdk, *f.split('/')), f'{TOP}/sdk3/SageXML/{f}')
        # the voice repository's answers (voice_snapshot.py), made on a machine that has it; not in git
        z.write(os.path.join(labpaths.WORK, 'demo', 'voice_snapshot.json'), f'{TOP}/demo/voice_snapshot.json')
        # the readme also sits at the top of the folder, where it is found first
        z.write(os.path.join(labpaths.WORK, 'demo', 'SIM_README.txt'), f'{TOP}/SIM_README.txt')
    print(f'{OUT}: {len(files)} files, {os.path.getsize(OUT) / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
