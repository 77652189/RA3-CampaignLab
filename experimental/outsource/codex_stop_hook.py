"""Codex `Stop` hook: each finished Codex turn appends one JSON line to the coordinator's inbox, so a Claude
coordinator watching that file learns at once that a Codex line stopped (AGENTS.md: Codex lines run as Codex App
sessions; the coordinator sends work with `codex queue` and reads this inbox for the way back).

Codex passes the event as JSON on stdin (session_id, turn_id, cwd, last_assistant_message, stop_hook_active, ...).
The line is a notice, not acceptance: the coordinator still checks the line's commits and handoff.
Never blocks Codex: prints nothing, always exits 0; its own failures go to errors.log next to the inbox.

  ~/.codex/config.toml:  [[hooks.Stop]] ... command = "python -I -X utf8 <this file>"
"""
import datetime
import json
import os
import sys

INBOX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                     'shared', 'inbox')
INBOX = os.environ.get('CNV_INBOX', INBOX)
PREFIX = 'RA3-CampaignLab-'


def lane(cwd):
    """RA3-CampaignLab-codexc -> codexc; anything else -> the folder name."""
    name = os.path.basename(os.path.normpath(cwd or ''))
    return name[len(PREFIX):] if name.startswith(PREFIX) else name


def main():
    os.makedirs(INBOX, exist_ok=True)
    try:
        ev = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace') or '{}')
        msg = ev.get('last_assistant_message') or ''
        row = {'event': 'turn_stopped', 'lane': lane(ev.get('cwd')),
               'session_id': ev.get('session_id'), 'turn_id': ev.get('turn_id'), 'cwd': ev.get('cwd'),
               'time': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               'stop_hook_active': ev.get('stop_hook_active'), 'message': msg[:1500]}
        with open(os.path.join(INBOX, 'codex.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except Exception as e:  # never let the hook stop Codex
        with open(os.path.join(INBOX, 'errors.log'), 'a', encoding='utf-8') as f:
            f.write('%s %r\n' % (datetime.datetime.now().isoformat(timespec='seconds'), e))
    return 0


if __name__ == '__main__':
    sys.exit(main())
