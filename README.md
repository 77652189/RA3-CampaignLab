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

## Docs

[HANDOFF.md](HANDOFF.md) · [docs/plan.md](docs/plan.md) · [docs/architecture.md](docs/architecture.md) ·
[docs/requirements.md](docs/requirements.md) · [docs/adr/](docs/adr/README.md) (mostly in Chinese)

Not affiliated with or endorsed by Electronic Arts. No game files are included; you need your own copy of the
game. GPL-3.0.
