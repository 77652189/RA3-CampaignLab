"""experimental/outsource/codex_app.py: the pure parts -- line framing, the brief check, auto-answers, the
codex_watch-shaped events. No Codex process, no model."""
import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('codex_app', os.path.join(ROOT, 'experimental', 'outsource', 'codex_app.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_one_json_object_per_line_without_the_jsonrpc_field():
    msg = {'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'x', 'version': '1'}}}
    line = app.encode(msg)
    assert line.endswith(b'\n') and line.count(b'\n') == 1
    assert app.decode(line) == msg
    assert app.decode('{"text": "多行\\n文本"}') == {'text': '多行\n文本'}
    assert app.decode(b'') is None and app.decode('not json') is None and app.decode('[1]') is None


def test_kind_tells_responses_server_requests_and_notifications_apart():
    assert app.kind({'id': 3, 'result': {}}) == 'response'
    assert app.kind({'id': 3, 'error': {'message': 'x'}}) == 'response'
    assert app.kind({'id': 0, 'method': 'item/commandExecution/requestApproval', 'params': {}}) == 'request'
    assert app.kind({'method': 'turn/completed', 'params': {}}) == 'notification'


def test_brief_needs_files_and_tests_sections():
    assert app.check_brief('Goal.\nFiles:\n- a.py\nTests:\n- pytest -q tests/test_a.py\n') == ['a.py']
    assert app.check_brief('Files: none\nTests: none\n') == []
    with pytest.raises(ValueError):
        app.check_brief('Goal only.\nTests: none\n')
    with pytest.raises(ValueError):
        app.check_brief('Files: none\n')


def test_first_prompt_adds_the_rules_with_the_bench_choice():
    sandboxed = app.first_prompt('Brief.', 60, bench=False, full=False)
    assert sandboxed.startswith('Brief.') and 'about 20 minutes' in sandboxed and app.ct.NO_BENCH in sandboxed
    full = app.first_prompt('Brief.', 30, bench=True, full=True)
    assert app.ct.BENCH in full and 'WITHOUT a sandbox' in full and app.ct.NO_BENCH not in full


def test_approvals_are_answered_at_once_per_mode():
    m = 'item/commandExecution/requestApproval'
    assert app.auto_answer(m, full=True) == ({'decision': 'accept'}, None)
    assert app.auto_answer(m, full=False) == ({'decision': 'decline'}, None)
    assert app.auto_answer('item/fileChange/requestApproval', full=False)[0] == {'decision': 'decline'}
    assert app.auto_answer('execCommandApproval', full=True)[0] == {'decision': 'approved'}
    assert 'denied' in app.auto_answer('applyPatchApproval', full=False)[0]['decision']
    assert app.auto_answer('mcpServer/elicitation/request', full=True)[0] == {'action': 'decline'}
    result, error = app.auto_answer('item/tool/call', full=True)
    assert result is None and error['code'] == -32601


def test_events_take_the_codex_exec_shape_codex_watch_reads():
    ev = app.watch_event('item/completed', {'item': {'type': 'agentMessage', 'text': '做完了', 'phase': 'final_answer'}})
    assert ev['type'] == 'item.completed' and ev['item']['type'] == 'agent_message' and ev['item']['text'] == '做完了'
    ev = app.watch_event('item/completed', {'item': {'type': 'commandExecution', 'command': 'pytest -q', 'exitCode': 0}})
    assert ev['item'] == {'type': 'command_execution', 'command': 'pytest -q', 'exit_code': 0, 'status': None}
    ev = app.watch_event('item/completed', {'item': {'type': 'fileChange', 'changes': [{'path': 'a.py', 'kind': 'add'}]}})
    assert ev['item']['changes'][0]['path'] == 'a.py'
    assert app.watch_event('item/agentMessage/delta', {'delta': 'x'}) is None
    assert app.watch_event('item/completed', {'item': {'type': 'reasoning'}}) is None


def test_turn_usage_is_the_difference_of_thread_totals():
    before = {'inputTokens': 100, 'cachedInputTokens': 40, 'outputTokens': 10, 'reasoningOutputTokens': 5}
    now = {'inputTokens': 350, 'cachedInputTokens': 200, 'outputTokens': 60, 'reasoningOutputTokens': 25}
    assert app.usage_delta(now, before) == {'input_tokens': 250, 'cached_input_tokens': 160, 'output_tokens': 50,
                                            'reasoning_output_tokens': 20}
    assert app.usage_delta(None, None)['input_tokens'] == 0


def test_outside_flags_git_status_lines_not_under_the_globs():
    touched = [' M experimental/cnv/sim.py', '?? tests/test_new.py', ' M docs/x.md']
    assert app.outside(touched, ['experimental/cnv/*.py', 'tests/test_*.py']) == [' M docs/x.md']
