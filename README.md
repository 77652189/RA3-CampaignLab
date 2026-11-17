# RA3 CampaignLab

Tools and experiments for building **new content for Command & Conquer: Red Alert 3 from scratch**: new campaign
maps, new units and the pipeline behind them. Companion to the AI Chinese voice mod
[RA3-ChineseVoice](https://github.com/77652189/RA3-ChineseVoice).

What works (each verified in the game on an automated test bench):

- **Maps**: generate a map from code (terrain, water, ground textures with blending, objects, waypoints, scripts,
  objectives, lighting), compile and link its asset stream with the Mod SDK, and load it as a campaign mission.
- **Units**: model in Blender from Python, bake textures, rig to a retail unit's bones, export W3X, give it its own
  logic, production button, portrait, Chinese name and gameplay (e.g. a toggle ability).
- **Test bench**: an isolated copy of the game, driven in the background (clicks, box select, keys, screenshots),
  muted and parked off screen; detects the game's crash box.

Everything lives under `experimental/` — it is research code, not a polished mod.

## Requirements

- Red Alert 3 (Steam, patch 1.12 / 1.13), Windows
- RA3 Mod SDK **v3.0** (1.12 layouts) at `<parent folder>\sdk\RA3ModSDK3` (see `experimental/campaign/labpaths.py`)
- Python 3.11+ with Pillow; Blender 5.x for the unit scripts
- The folder layout this repository expects next to itself: `shared\` (locks, `gpu_limit.json`), `envs\`, `sdk\`

### From scratch

Let `<LAB>` be the folder that holds this repository (e.g. `Documents\RA3Modding`). Put these next to it:

1. `<LAB>\sdk\RA3ModSDK3\` — the Mod SDK v3.0 (`tools\BinaryAssetBuilder.exe` must be inside). `CNV_SDK` overrides the path.
2. `<LAB>\RA3-ChineseVoice\` — `git clone https://github.com/77652189/RA3-ChineseVoice`.
3. `<LAB>\shared\` with an empty `locks\` folder and a `gpu_limit.json` such as `{"duty": 0.7, "vram_gb": 10}` (format in `ra3voice/throttle.py`).
4. `<LAB>\envs\` with three Python environments, each rebuilt from its lock file in `experimental/testbench/envs/`:
   - `bench_mcp` and `tools_venv`: `python -m venv <LAB>\envs\<name>`, then
     `<LAB>\envs\<name>\Scripts\python.exe -m pip install -r experimental/testbench/envs/<name>.txt`
   - `ra3gen_env` (conda, Python 3.11): `conda create -p <LAB>\envs\ra3gen_env python=3.11`, then
     `pip install -r experimental/testbench/envs/ra3gen_env.txt --extra-index-url https://download.pytorch.org/whl/cu128`.
     The lock lists pip packages only; conda-only packages are not in it.
5. `.mcp.json` points the `ra3bench` MCP server at `envs\bench_mcp`; fix the paths there if your `<LAB>` is elsewhere.
6. The bench copy of the game (needs the game installed, closed, on the same drive): build the capture shim
   (`experimental\testbench\build.bat`), then `pwsh experimental/testbench/make_bench.ps1`.
   It makes `work\testbench\RA3` from hard links, so it costs almost no disk.

Then check everything in one command: `python -I -X utf8 experimental/testbench/doctor.py`
(one line per item: OK / MISSING / BROKEN plus what to do; `--verbose` shows paths). It only reads, never writes.

## Docs

[HANDOFF.md](HANDOFF.md) · [docs/plan.md](docs/plan.md) · [docs/architecture.md](docs/architecture.md) ·
[docs/requirements.md](docs/requirements.md) · [docs/adr/](docs/adr/README.md) (mostly in Chinese)

Not affiliated with or endorsed by Electronic Arts. No game files are included; you need your own copy of the
game. GPL-3.0.
