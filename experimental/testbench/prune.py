"""Delete test-bench leftovers that can be rebuilt.

  python -I -X utf8 experimental/testbench/prune.py           # dry run: what would go
  python -I -X utf8 experimental/testbench/prune.py --apply   # delete

What goes (user 2026-11-08: "用不上的自动删"):
- Documents/Red Alert 3/Mods/Camp*: test mods the bench builds per mission/check,
  when no file inside changed for MOD_DAYS. cnv_check rebuilds them on demand.
  Mods the player uses (KEEP) and every non-Camp mod are never touched.
- work/testbench/runs/*: archived frames of bench runs older than RUN_DAYS.
"""
import os, shutil, sys, time

MOD_DAYS = 2
RUN_DAYS = 7
KEEP = ("CampShell", "CampA4Demo")  # prefixes the player launches by hand

HOME = os.path.expanduser("~")
MODS = os.path.join(HOME, "Documents", "Red Alert 3", "Mods")
RUNS = os.path.join(os.path.dirname(__file__), "..", "..", "work", "testbench", "runs")


def newest_and_size(path):
    newest, size = os.path.getmtime(path), 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                st = os.stat(os.path.join(root, f))
            except OSError:
                continue
            newest = max(newest, st.st_mtime)
            size += st.st_size
    return newest, size


def candidates():
    now = time.time()
    if os.path.isdir(MODS):
        for name in os.listdir(MODS):
            p = os.path.join(MODS, name)
            if not os.path.isdir(p) or not name.startswith("Camp") or name.startswith(KEEP):
                continue
            newest, size = newest_and_size(p)
            if now - newest > MOD_DAYS * 86400:
                yield p, size
    if os.path.isdir(RUNS):
        for name in os.listdir(RUNS):
            p = os.path.join(RUNS, name)
            if not os.path.isdir(p):
                continue
            newest, size = newest_and_size(p)
            if now - newest > RUN_DAYS * 86400:
                yield p, size


def main():
    apply = "--apply" in sys.argv
    n = total = failed = 0
    for p, size in candidates():
        if apply:
            try:
                shutil.rmtree(p)
            except OSError:
                failed += 1
                continue
        n += 1
        total += size
    verb = "deleted" if apply else "would delete"
    print(f"{verb} {n} folders, {total / 2**30:.1f} GB" + (f", {failed} failed (in use?)" if failed else ""))


if __name__ == "__main__":
    main()
