r"""Codex as a conversation: one Codex thread kept across rounds through the local `codex app-server` protocol, so the
coordinator can follow up after a turn, steer or interrupt a running turn and read what it is doing -- where
codex_task.py runs `codex exec` once and forgets the thread.

  python -I -X utf8 experimental/outsource/codex_app.py start BRIEF.md --dir WORKTREE [--full] [--bench]
                    [--effort medium] [--model gpt-6.1-sol] [--minutes 60] [--read-dir D]
  ... send THREAD "message"   a new turn when the thread is idle; while a turn runs, steers it (turn/steer: the text
                              joins the running turn, which keeps its id)
  ... interrupt THREAD        stops the running turn (turn/interrupt); the thread stays, `send` goes on from there
  ... status [THREAD]         running / idle / stopped / dead, the last thing Codex said, token usage (all sessions
                              when THREAD is left out; a unique prefix of the id is enough)
  ... stop THREAD             interrupts a running turn, ends the app-server and the background process
  ... resume THREAD [...]     a new background process on a stopped thread (thread/resume), same brief and options
                              (--full / --effort / --model / --minutes override); idle until `send`

`start` checks the brief like codex_task.py ("Files:" and "Tests:" sections), sends brief + codex_task.RULES as the
first turn, and prints the thread id. Files next to the brief: <brief>.events.jsonl (codex_watch.py follows it:
codex-exec-style lines, agent messages as item.completed / agent_message), <brief>.answer.md (the last turn's final
answer, or its progress notes when it was cut off, plus the files changed in --dir since the session began, those
outside "Files:", and the turn's tokens), <brief>.raw.jsonl (every protocol message but the streaming deltas) and
<brief>.server.log (the app-server's stderr). Each finished turn is logged to shared/outsource/log.jsonl.

Protocol (taken from `codex app-server generate-json-schema`, codex-cli 0.167): JSON-RPC 2.0 without the "jsonrpc"
field, one JSON object per line on stdio. initialize {clientInfo} -> `initialized` notification -> thread/start
{cwd, model, sandbox, approvalPolicy} (or thread/resume {threadId, ...}) -> turn/start {threadId, input:[{type:text}],
effort, sandboxPolicy}; turn/steer {threadId, expectedTurnId, input}; turn/interrupt {threadId, turnId}. The server
notifies turn/started, item/completed {item: agentMessage|commandExecution|fileChange|...}, thread/tokenUsage/updated,
error {error, willRetry}, turn/completed {turn: {status completed|interrupted|failed, error}}. approvalPolicy is
"never", so the server should not ask; if it does (item/commandExecution/requestApproval, item/fileChange/
requestApproval, ...) auto_answer() replies at once -- accept under --full, decline in the sandbox -- never a human.

IPC: an inbox folder. Each session owns shared/outsource/app/<stamp>/ with state.json (written by the background
process, replaced atomically), inbox/ (the CLI drops one <ns>.json command file, written then renamed so it is never
read half done) and outbox/ (the reply to that command). Why not a socket: on Windows a localhost port needs picking,
can collide or trip the firewall, and dies silently with the process; files need nothing, survive the CLI exiting,
and leave a readable trail. The cost is a 0.5 s poll, nothing next to a model turn.

Experimental API: app-server and its schema are marked [experimental] and change between Codex builds -- when a call
fails, regenerate the schema and compare the method names above.
"""
import argparse, ctypes, datetime, fnmatch, glob, json, os, queue, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import codex_task as ct  # noqa: E402  (RULES, files_allowed, changed, codex, bench_dirs, LOG)

APPS = os.path.join(os.path.dirname(ct.LOG), 'app')
POLL = 0.5


# ---------------------------------------------------------------- pure parts (tests/test_codex_app.py)

def encode(msg):
    return (json.dumps(msg, ensure_ascii=False) + '\n').encode('utf-8')


def decode(line):
    """One protocol line -> dict, or None for a blank or broken line."""
    if isinstance(line, bytes):
        line = line.decode('utf-8', 'replace')
    try:
        msg = json.loads(line)
    except ValueError:
        return None
    return msg if isinstance(msg, dict) else None


def kind(msg):
    if 'method' in msg:
        return 'request' if 'id' in msg else 'notification'
    return 'response'


def check_brief(text):
    """The globs the brief allows; refuses a brief without "Files:" and "Tests:" like codex_task.py."""
    allowed = ct.files_allowed(text)
    if 'Tests:' not in text or allowed is None:
        raise ValueError('the brief needs a "Files:" section (the paths / globs it may change, or "none") and a '
                         '"Tests:" section naming the exact test commands')
    return allowed


def first_prompt(brief, minutes, bench, full):
    return brief + ct.RULES.format(aim=int(minutes / 3), limit=int(minutes),
                                   bench=(ct.BENCH + (ct.FULL if full else '')) if bench else ct.NO_BENCH)


def auto_answer(method, full):
    """(result, error) for a request the server sends us; no human ever answers."""
    yes = full
    if method in ('item/commandExecution/requestApproval', 'item/fileChange/requestApproval'):
        return {'decision': 'accept' if yes else 'decline'}, None
    if method in ('execCommandApproval', 'applyPatchApproval'):
        return {'decision': 'approved' if yes else {'denied': {'rejection': 'no human approver: stay in the sandbox'}}}, None
    if method == 'item/permissions/requestApproval':
        return {'permissions': {}}, None                      # grants nothing beyond the sandbox
    if method == 'item/tool/requestUserInput':
        return {'answers': {}}, None
    if method == 'mcpServer/elicitation/request':
        return {'action': 'decline'}, None
    return None, {'code': -32601, 'message': f'{method} is not supported by codex_app.py'}


def watch_event(method, params):
    """A notification in codex exec's --json shape (what codex_watch.py reads), or None."""
    if method == 'item/completed':
        it = params.get('item') or {}
        t = it.get('type')
        if t == 'agentMessage':
            return {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': it.get('text', ''),
                                                       'phase': it.get('phase')}}
        if t == 'commandExecution':
            return {'type': 'item.completed', 'item': {'type': 'command_execution', 'command': it.get('command', ''),
                                                       'exit_code': it.get('exitCode'), 'status': it.get('status')}}
        if t == 'fileChange':
            return {'type': 'item.completed', 'item': {'type': 'file_change', 'changes': [
                {'path': c.get('path', ''), 'kind': c.get('kind')} for c in it.get('changes') or []]}}
        if t == 'mcpToolCall':
            return {'type': 'item.completed', 'item': {'type': 'mcp_tool_call', 'tool': it.get('tool'),
                                                       'arguments': it.get('arguments')}}
        return None
    if method == 'turn/started':
        return {'type': 'turn.started', 'turn_id': (params.get('turn') or {}).get('id')}
    if method == 'error':
        return {'type': 'error', 'item': {'type': 'error', 'message': (params.get('error') or {}).get('message'),
                                          'will_retry': params.get('willRetry')}}
    return None


def usage_delta(now, before):
    """Tokens one turn spent, from the thread totals (TokenUsageBreakdown) at its end and its start."""
    now, before = now or {}, before or {}
    d = lambda k: (now.get(k) or 0) - (before.get(k) or 0)  # noqa: E731
    return {'input_tokens': d('inputTokens'), 'cached_input_tokens': d('cachedInputTokens'),
            'output_tokens': d('outputTokens'), 'reasoning_output_tokens': d('reasoningOutputTokens')}


def outside(touched, allowed):
    return [t for t in touched if not any(fnmatch.fnmatch(t[3:].strip().strip('"'), g) for g in allowed)]


# ---------------------------------------------------------------- the background process

def write_json(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    for _ in range(20):                       # Windows: a reader holding the file makes replace fail for a moment
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05)


def read_json(path):
    for _ in range(20):
        try:
            with open(path, encoding='utf-8') as fh:
                return json.load(fh)
        except (OSError, ValueError):
            if not os.path.exists(path):
                return None
            time.sleep(0.05)
    return None


class Session:
    def __init__(self, sdir):
        self.sdir = sdir
        self.cfg = read_json(os.path.join(sdir, 'cfg.json'))
        c = self.cfg
        self.base = os.path.splitext(c['brief'])[0]
        self.paths = {k: self.base + s for k, s in (('events', '.events.jsonl'), ('answer', '.answer.md'),
                                                    ('raw', '.raw.jsonl'), ('server', '.server.log'))}
        mode = 'a' if c.get('resume') else 'w'
        self.ev = open(self.paths['events'], mode, encoding='utf-8')
        self.raw = open(self.paths['raw'], mode, encoding='utf-8')
        self.allowed = c['allowed']
        self.q, self.next_id, self.results = queue.Queue(), 0, {}
        self.thread = self.turn_id = None
        self.total, self.turn_t0, self.notes, self.final, self.error = None, 0, [], None, None
        self.turns = c.get('turns', 0)          # a resumed thread keeps counting
        self.state = {'pid': os.getpid(), 'status': 'starting', 'dir': c['dir'], 'brief': c['brief'],
                      'full': c['full'], 'model': c['model'], 'effort': c['effort'], 'turns': self.turns,
                      **self.paths}
        self.save()

    def save(self, **kw):
        self.state.update(kw, updated=datetime.datetime.now().isoformat(timespec='seconds'))
        write_json(os.path.join(self.sdir, 'state.json'), self.state)

    def event(self, obj):
        self.ev.write(json.dumps(obj, ensure_ascii=False) + '\n')
        self.ev.flush()

    # -- wire
    def spawn(self):
        exe = ct.codex()
        if not exe:
            raise RuntimeError('Codex desktop not installed (no codex.exe under %LOCALAPPDATA%\\OpenAI\\Codex\\bin)')
        self.proc = subprocess.Popen([exe, 'app-server', '-c', 'windows.sandbox="mxc"'], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=open(self.paths['server'], 'ab'),
                                     cwd=self.cfg['dir'], creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for raw in self.proc.stdout:
            msg = decode(raw)
            if msg is not None:
                self.q.put(msg)
        self.q.put(None)

    def send(self, msg):
        self.proc.stdin.write(encode(msg))
        self.proc.stdin.flush()

    def request(self, method, params):
        self.next_id += 1
        self.send({'id': self.next_id, 'method': method, 'params': params})
        return self.next_id

    def call(self, method, params, timeout=180):
        rid, end = self.request(method, params), time.time() + timeout
        while rid not in self.results:
            if time.time() > end:
                raise RuntimeError(f'{method}: no reply in {timeout} s')
            self.pump(POLL)
        r = self.results.pop(rid)
        if 'error' in r:
            raise RuntimeError(f'{method}: {r["error"].get("message")}')
        return r.get('result') or {}

    def pump(self, timeout):
        try:
            msg = self.q.get(timeout=timeout)
        except queue.Empty:
            return
        if msg is None:
            raise EOFError('the app-server exited')
        k, method, params = kind(msg), msg.get('method'), msg.get('params') or {}
        if k == 'response':
            self.results[msg.get('id')] = msg
            return
        if 'elta' not in (method or ''):                     # streaming deltas would swamp the raw log
            self.raw.write(json.dumps(msg, ensure_ascii=False) + '\n')
            self.raw.flush()
        if k == 'request':
            result, error = auto_answer(method, self.cfg['full'])
            self.send({'id': msg['id'], **({'result': result} if error is None else {'error': error})})
            self.event({'type': 'approval', 'method': method, 'answer': result or error})
            return
        ev = watch_event(method, params)
        if ev:
            self.event(ev)
        if method == 'turn/started':
            self.turn_id = (params.get('turn') or {}).get('id')
        elif method == 'item/completed':
            it = params.get('item') or {}
            if it.get('type') == 'agentMessage':
                self.notes.append(it.get('text', '').strip())
                if it.get('phase') == 'final_answer':
                    self.final = it.get('text', '').strip()
                self.save(last_message=self.notes[-1][-1500:])
        elif method == 'thread/tokenUsage/updated':
            self.total = (params.get('tokenUsage') or {}).get('total')
        elif method == 'error':
            self.error = (params.get('error') or {}).get('message')
        elif method == 'turn/completed':
            self.finish_turn(params.get('turn') or {})

    # -- turns
    def sandbox_policy(self):
        if self.cfg['full']:
            return {'type': 'dangerFullAccess'}
        return {'type': 'workspaceWrite', 'writableRoots': [os.path.abspath(d) for d in self.cfg['read_dirs']],
                'networkAccess': False}

    def start_turn(self, text):
        self.notes, self.final, self.error, self.usage0 = [], None, None, self.total
        self.event({'type': 'user_message', 'text': text[:2000]})
        r = self.call('turn/start', {'threadId': self.thread, 'input': [{'type': 'text', 'text': text}],
                                     'effort': self.cfg['effort'], 'sandboxPolicy': self.sandbox_policy()})
        self.turns += 1
        self.turn_id, self.turn_t0 = (r.get('turn') or {}).get('id') or self.turn_id, time.time()
        self.save(status='running', turn_id=self.turn_id, turns=self.turns)
        return self.turn_id

    def finish_turn(self, turn):
        e = turn.get('error') or {}
        status, err = turn.get('status'), e.get('message') or self.error
        code = e.get('codexErrorInfo')          # e.g. usageLimitExceeded: the quota, not the task
        ended = 'ok' if status == 'completed' else (status + (f' ({code})' if isinstance(code, str) else '')
                                                    + (f': {err[:300]}' if err else ''))
        usage = usage_delta(self.total, self.usage0)
        after = ct.changed(self.cfg['dir'])
        touched = sorted(set(after) - set(self.before)) if after is not None and self.before is not None else []
        out = outside(touched, self.allowed)
        if out and ended == 'ok':
            ended = 'changed files outside "Files:"'
        self.event({'type': 'turn.completed', 'usage': usage} if status == 'completed' else
                   {'type': 'turn.failed', 'error': {'status': status, 'message': err}, 'usage': usage})
        answer = self.final or (self.notes[-1] if self.notes and status == 'completed' else None)
        body = answer if answer else (f'(no final answer: {ended})\n\nProgress notes, in order:\n\n'
                                      + '\n\n'.join(self.notes))
        with open(self.paths['answer'], 'w', encoding='utf-8') as fh:
            fh.write(f'(thread {self.thread}, turn {self.turns}: {ended})\n\n{body}\n\n---\nFiles changed in '
                     f'{self.cfg["dir"]} since the session began (git status):\n' + '\n'.join(touched) + '\n'
                     + (('OUTSIDE "Files:":\n' + '\n'.join(out) + '\n') if out else '') + f'Usage: {usage}\n')
        seconds = round(time.time() - self.turn_t0)
        os.makedirs(os.path.dirname(ct.LOG), exist_ok=True)
        with open(ct.LOG, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='seconds'), 'tool': 'codex_app',
                                 'thread': self.thread, 'turn': self.turns, 'dir': self.cfg['dir'],
                                 'brief': self.cfg['brief'], 'task': self.cfg['task'], 'model': self.cfg['model'],
                                 'effort': self.cfg['effort'], 'seconds': seconds, 'usage': usage,
                                 'changed': len(touched), 'outside': out, 'ended': ended,
                                 'out': self.paths['answer']}, ensure_ascii=False) + '\n')
        self.turn_id = None
        self.save(status='idle', turn_id=None, last_turn={'ended': ended, 'seconds': seconds, 'usage': usage},
                  usage_total=self.total)

    # -- commands from the CLI
    def handle(self, cmd):
        c = cmd.get('cmd')
        if c == 'send':
            if self.turn_id:
                self.call('turn/steer', {'threadId': self.thread, 'expectedTurnId': self.turn_id,
                                         'input': [{'type': 'text', 'text': cmd['text']}]})
                self.event({'type': 'user_message', 'text': cmd['text'][:2000], 'steer': True})
                return f'steered the running turn {self.turn_id}'
            return f'started turn {self.start_turn(cmd["text"])}'
        if c == 'interrupt':
            if not self.turn_id:
                return 'idle: nothing to interrupt'
            self.call('turn/interrupt', {'threadId': self.thread, 'turnId': self.turn_id})
            return f'interrupt sent to turn {self.turn_id}'
        if c == 'stop':
            if self.turn_id:
                self.call('turn/interrupt', {'threadId': self.thread, 'turnId': self.turn_id})
                end = time.time() + 30
                while self.turn_id and time.time() < end:
                    self.pump(POLL)
            raise SystemExit('stop')
        return f'unknown command {c!r}'

    def inbox(self):
        box = os.path.join(self.sdir, 'inbox')
        for name in sorted(n for n in os.listdir(box) if n.endswith('.json')):
            path = os.path.join(box, name)
            cmd = read_json(path) or {}
            os.remove(path)
            try:
                reply = self.handle(cmd)
            except SystemExit:
                write_json(os.path.join(self.sdir, 'outbox', name), {'reply': 'stopped'})
                raise
            except RuntimeError as e:
                reply = f'error: {e}'
            write_json(os.path.join(self.sdir, 'outbox', name), {'reply': reply})

    def run(self):
        c = self.cfg
        self.before = ct.changed(c['dir'])
        self.spawn()
        self.call('initialize', {'clientInfo': {'name': 'codex_app', 'title': 'RA3-CampaignLab coordinator',
                                                'version': '1'}})
        self.send({'method': 'initialized'})
        common = {'cwd': c['dir'], 'model': c['model'], 'approvalPolicy': 'never',
                  'sandbox': 'danger-full-access' if c['full'] else 'workspace-write'}
        if c.get('resume'):
            r = self.call('thread/resume', {'threadId': c['resume'], 'excludeTurns': True, **common})
        else:
            r = self.call('thread/start', common)
        self.thread = (r.get('thread') or {}).get('id')
        self.event({'type': 'thread.started', 'thread_id': self.thread})
        self.save(status='idle', thread=self.thread, sandbox=r.get('sandbox'), approval=r.get('approvalPolicy'))
        if not c.get('resume'):
            try:
                self.start_turn(first_prompt(open(c['brief'], encoding='utf-8').read(), c['minutes'], c['bench'],
                                             c['full']))
            except RuntimeError as e:          # refused outright: stay idle, `send` can try again
                self.event({'type': 'turn.failed', 'error': {'message': str(e)}})
                self.save(last_turn={'ended': f'turn/start refused: {e}'})
        while True:
            self.pump(POLL)
            self.inbox()
            if self.turn_id and time.time() - self.turn_t0 > c['minutes'] * 60 and self.state.get('safety') != self.turn_id:
                self.call('turn/interrupt', {'threadId': self.thread, 'turnId': self.turn_id})
                self.save(safety=self.turn_id)           # the safety stop, once per turn

    def close(self, status):
        proc = getattr(self, 'proc', None)
        if proc and proc.poll() is None:
            try:
                proc.stdin.close()
                proc.wait(10)
            except (OSError, subprocess.TimeoutExpired):
                proc.kill()
        self.save(status=status, turn_id=None)


def serve(sdir):
    s = Session(sdir)
    try:
        s.run()
    except SystemExit:
        s.close('stopped')
    except EOFError as e:
        s.close(f'dead: {e}')
    except Exception as e:  # noqa: BLE001 -- the reason must reach state.json, the CLI reads nothing else
        s.close(f'error: {type(e).__name__}: {e}')
        raise


# ---------------------------------------------------------------- the CLI

def alive(pid):
    k = ctypes.windll.kernel32                 # os.kill(pid, 0) on Windows would send CTRL_C_EVENT
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259                    # STILL_ACTIVE


def sessions():
    """(dir, state) of each thread's newest session, newest first; a live-looking one whose process is gone shows
    as dead."""
    out, seen = [], set()
    for sdir in sorted(glob.glob(os.path.join(APPS, '*')), reverse=True):
        st = read_json(os.path.join(sdir, 'state.json'))
        if not st or (st.get('thread') and st['thread'] in seen):
            continue
        seen.add(st.get('thread'))
        if st.get('status') in ('starting', 'idle', 'running') and not alive(st.get('pid', 0)):
            st['status'] = 'dead (background process gone)'
        out.append((sdir, st))
    return out


def find(thread):
    hits = [(d, s) for d, s in sessions() if (s.get('thread') or '').startswith(thread)]
    if not hits:
        sys.exit(f'no session for thread {thread}')
    return hits[0]


def spawn_daemon(sdir):
    log = open(os.path.join(sdir, 'daemon.log'), 'ab')
    flags = 0x8 | 0x200                         # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    for extra in (0x01000000, 0):               # CREATE_BREAKAWAY_FROM_JOB, if the caller's job allows it
        try:
            return subprocess.Popen([sys.executable, '-I', '-X', 'utf8', os.path.abspath(__file__), '_serve', sdir],
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True,
                                    creationflags=flags | extra)
        except OSError:
            if not extra:
                raise


def launch(cfg, wait=240):
    sdir = os.path.join(APPS, datetime.datetime.now().strftime('%Y%m%d-%H%M%S-') + str(time.time_ns() % 10 ** 6))
    for sub in ('inbox', 'outbox'):
        os.makedirs(os.path.join(sdir, sub))
    write_json(os.path.join(sdir, 'cfg.json'), cfg)
    spawn_daemon(sdir)
    end = time.time() + wait
    while time.time() < end:
        st = read_json(os.path.join(sdir, 'state.json')) or {}
        if st.get('thread') or st.get('status', '').startswith(('error', 'dead', 'stopped')):
            break
        time.sleep(POLL)
    st = read_json(os.path.join(sdir, 'state.json')) or {}
    if not st.get('thread'):
        sys.exit(f'did not start: {st.get("status", "no state")} (see {sdir}\\daemon.log and {st.get("server", "")})')
    print(st['thread'])
    print(f'events -> {st["events"]}\nanswer -> {st["answer"]}')


def command(thread, cmd, wait=120):
    sdir, st = find(thread)
    if st.get('status') not in ('starting', 'idle', 'running'):
        sys.exit(f'thread {st.get("thread")} is {st.get("status")}' + ('; `resume` it first' if cmd['cmd'] == 'send' else ''))
    name = f'{time.time_ns()}.json'
    tmp = os.path.join(sdir, 'inbox', name + '.part')
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(cmd, fh, ensure_ascii=False)
    os.replace(tmp, os.path.join(sdir, 'inbox', name))
    reply, end = os.path.join(sdir, 'outbox', name), time.time() + wait
    while time.time() < end:
        r = read_json(reply)
        if r:
            print(r['reply'])
            return
        time.sleep(POLL)
    sys.exit(f'no reply in {wait} s (state: {(read_json(os.path.join(sdir, "state.json")) or {}).get("status")})')


def show(st):
    u = st.get('usage_total') or {}
    print(f'{st.get("thread")}  {st.get("status")}  turns {st.get("turns", 0)}  {st.get("dir")}'
          + (f'  tokens in {u.get("inputTokens", 0):,} (cached {u.get("cachedInputTokens", 0):,}) out '
             f'{u.get("outputTokens", 0):,}' if u else ''))
    if st.get('last_turn'):
        print('  last turn:', st['last_turn'].get('ended'), f'({st["last_turn"].get("seconds")} s)')
    if st.get('safety'):
        print('  safety stop interrupted turn', st['safety'])
    if st.get('last_message'):
        print('  said:', st['last_message'].replace('\n', ' ')[:400])


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '_serve':
        return serve(sys.argv[2])
    ap = argparse.ArgumentParser(description='Codex app-server conversation for the coordinator')
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('start', 'resume'):
        p = sub.add_parser(name)
        p.add_argument('brief' if name == 'start' else 'thread')
        if name == 'start':
            p.add_argument('--dir', required=True)
            p.add_argument('--read-dir', action='append', default=[])
            p.add_argument('--bench', action='store_true')
        p.add_argument('--full', action='store_true', default=None)
        p.add_argument('--effort', choices=['low', 'medium', 'high'], default=None)
        p.add_argument('--model', default=None)
        p.add_argument('--minutes', type=float, default=None)
    p = sub.add_parser('send')
    p.add_argument('thread')
    p.add_argument('text')
    for name in ('interrupt', 'stop'):
        sub.add_parser(name).add_argument('thread')
    sub.add_parser('status').add_argument('thread', nargs='?')
    a = ap.parse_args()
    if a.cmd == 'start':
        brief_path = os.path.abspath(a.brief)
        brief = open(brief_path, encoding='utf-8').read()
        try:
            allowed = check_brief(brief)
        except ValueError as e:
            sys.exit(str(e))
        full = bool(a.full)
        bench = a.bench or full
        launch({'brief': brief_path, 'dir': os.path.abspath(a.dir), 'allowed': allowed, 'full': full, 'bench': bench,
                'read_dirs': a.read_dir + (ct.bench_dirs() if bench else []), 'effort': a.effort or 'medium',
                'model': a.model or 'gpt-6.1-sol', 'minutes': a.minutes or 60,
                'task': brief.strip().splitlines()[0][:120]})
    elif a.cmd == 'resume':
        sdir, st = find(a.thread)
        if st.get('status') in ('starting', 'idle', 'running'):
            sys.exit(f'thread {st["thread"]} is still {st["status"]}: use send')
        cfg = read_json(os.path.join(sdir, 'cfg.json'))
        cfg.update({k: v for k, v in (('full', a.full), ('effort', a.effort), ('model', a.model),
                                      ('minutes', a.minutes)) if v is not None}, resume=st['thread'],
                   turns=st.get('turns', 0))
        cfg['bench'] = cfg['bench'] or cfg['full']
        launch(cfg)
    elif a.cmd == 'send':
        command(a.thread, {'cmd': 'send', 'text': a.text})
    elif a.cmd in ('interrupt', 'stop'):
        command(a.thread, {'cmd': a.cmd})
    else:
        found = [find(a.thread)] if a.thread else sessions()
        for _, st in found:
            show(st)
        if not found:
            print('no sessions')


if __name__ == '__main__':
    main()
