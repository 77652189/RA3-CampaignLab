"""Run one cnv check from the command line, the way ra3bench's cnv_check does (same code, own process): handy when
bench_mcp.py changed and the MCP server still runs the old one.
    python -I -X utf8 run_check.py <mission> <check> [--no-build] [--keep]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench_mcp  # noqa: E402

if __name__ == '__main__':
    name, check = sys.argv[1], sys.argv[2]
    run = bench_mcp._cnv_run if '--x1' in sys.argv else bench_mcp._cnv_check    # x1: the game at its own speed
    print(run(name, check, '--no-build' not in sys.argv, '--keep' in sys.argv))
