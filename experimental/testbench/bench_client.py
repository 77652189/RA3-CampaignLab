"""Run a list of ra3bench MCP calls over stdio, for a session that has not loaded the MCP (or a scripted test).

  ../envs/bench_mcp/Scripts/python.exe -I -X utf8 experimental/testbench/bench_client.py steps.json [out_dir]
  ... bench_client.py '[["bench_start", {"mod": "CampNew38", "look": false}], ["bench_watch", {"seconds": 30}]]'

Each step is [tool, {args}]. Text replies are printed; images are saved to out_dir (default: the scratch folder
work/testbench/client/) as <step>_<tool>.<ext>. bench_stop runs at the end whatever happens.
"""
import asyncio
import base64
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


async def run(steps, out):
    params = StdioServerParameters(command=sys.executable, args=['-I', '-X', 'utf8', os.path.join(HERE, 'bench_mcp.py')],
                                   cwd=ROOT)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            try:
                for k, (name, args) in enumerate(steps, 1):
                    res = await s.call_tool(name, args)
                    texts = []
                    for c in res.content:
                        if c.type == 'text':
                            texts.append(c.text)
                        elif c.type == 'image':
                            p = os.path.join(out, f'{k:02d}_{name}.{c.mime_type.split("/")[1]}')
                            with open(p, 'wb') as f:
                                f.write(base64.b64decode(c.data))
                            texts.append(f'[image -> {p}]')
                    print(f'{k} {name} {json.dumps(args)} => ' + ' | '.join(texts), flush=True)
                    if name == 'bench_start' and texts and texts[0].startswith('BENCH:'):
                        break                   # later steps can still read the frames archived so far
            finally:
                if not steps or steps[-1][0] != 'bench_stop':
                    print('bench_stop =>', (await s.call_tool('bench_stop', {})).content[0].text, flush=True)


def main():
    a = sys.argv[1]
    steps = json.load(open(a, encoding='utf-8')) if os.path.exists(a) else json.loads(a)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'work', 'testbench', 'client')
    os.makedirs(out, exist_ok=True)
    asyncio.run(run(steps, out))


if __name__ == '__main__':
    main()
