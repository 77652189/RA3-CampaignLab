Read and follow [CLAUDE.md](CLAUDE.md): the same rules hold for Codex sessions in this repository (commit identity, no pushes unless the brief says so).

Codex works here as an engine line. You do not see the coordinator's conversation or Claude's memory, so what you need is in these files -- read the ones your brief touches before you change code:

- Goal and bar: [docs/adr/README.md](docs/adr/README.md) (ADR 0026: every engine part benched by usage, >= 90 %); the inventory is `python -I -X utf8 experimental/cnv/inventory.py`.
- Bench know-how: [docs/engine/know-how.md](docs/engine/know-how.md) (how the bench runs, its traps). Weapon and module probes: your own notes in `work/re/handoff-c.md` (empty clip loaded in ClipReloadTime, order after the load, NO_ATTACK after the burst, float timers, at most 4 counter lines).
- Bench tools: the ra3bench MCP (cnv_show, cnv_check, cnv_map, bench_look, bench_inspect, bench_counters, ...) and `experimental/testbench/run_queue.py`. Numbers first, but when a reading does not explain itself, look at the frames before guessing.
- How to work a puzzle: one hypothesis table per problem in the handoff (hypothesis, run that tells it apart, result); read it before each round; two unexplained rounds in a row -> stop and report.
- Never delete a folder that holds a directory junction (`work/extsdk`, worktrees' `work`, `.claude/worktrees/RA3-ChineseVoice`): a recursive delete goes through the link and wipes its target (2026-11-10 that wiped `work/` and the SDK). Unlink first (`python work/re/scripts/extsdk_setup.py --unlink`), or ask.
- Reverse-engineering output (addresses, decompiled notes) stays in `work/re/` only -- it is a private repository; never put it in tracked files of this public one.
