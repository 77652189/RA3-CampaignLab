"""experimental/testbench/slots.py: several bench games at once -- who holds which slot, whose game is whose, when a
build must stage. The process list is faked; the locks go to a temporary folder."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experimental', 'testbench'))
import slots  # noqa: E402

ME = os.getpid()


@pytest.fixture
def bench(tmp_path, monkeypatch):
    tasks = {ME: 'python.exe'}
    monkeypatch.setattr(slots, 'LOCKS', str(tmp_path))
    monkeypatch.setattr(slots, 'SLOTS', 2)
    monkeypatch.setattr(slots, '_tasks', lambda: dict(tasks))
    return tasks


def lock(i, pid, note='', game=None):
    data = dict(owner='t', pid=pid, until=None, note=note, **({'game': game} if game else {}))
    with open(slots.lock_path(i), 'w', encoding='utf-8') as f:
        json.dump(data, f)


def test_slot_one_keeps_the_old_name():
    # older tools (run_bench.ps1, the music probe, reslock) wait on bench.json: slot 1 must stay that file
    assert os.path.basename(slots.lock_path(1)) == 'bench.json'
    assert os.path.basename(slots.shots_dir(1)) == 'shots'
    assert slots.lock_path(2) != slots.lock_path(1) and slots.shots_dir(2) != slots.shots_dir(1)


def test_slots_fill_then_refuse(bench):
    assert slots.take('a') == 1
    assert slots.take('b') == 2
    assert slots.take('c') is None
    slots.release(1)
    assert slots.take('d') == 1


def test_a_full_bench_queues_till_a_slot_frees(bench, monkeypatch):
    assert slots.take('a') == 1 and slots.take('b') == 2
    naps = []
    monkeypatch.setattr(slots.time, 'sleep', lambda s: (naps.append(s), len(naps) == 2 and slots.release(1)))
    assert slots.take_waiting('c', wait=60, poll=5) == 1
    assert len(naps) == 2


def test_the_queue_gives_up_after_its_wait(bench, monkeypatch):
    assert slots.take('a') == 1 and slots.take('b') == 2
    clock = [0.0]
    monkeypatch.setattr(slots.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(slots.time, 'sleep', lambda s: clock.__setitem__(0, clock[0] + s))
    assert slots.take_waiting('c', wait=30, poll=5) is None
    assert clock[0] == 30


def test_the_users_game_is_not_waited_out(bench, monkeypatch):
    bench[100] = 'RA3_1.13.game'        # nobody's slot: the user playing
    monkeypatch.setattr(slots.time, 'sleep', lambda s: pytest.fail('waited on the user'))
    assert slots.take_waiting('a', wait=600) is None
    assert slots.holder(1) is None


def test_a_dead_holder_frees_its_slot(bench):
    lock(1, 999999)                     # not in the process list
    assert slots.holder(1) is None
    assert slots.take('a') == 1
    assert slots.holder(1)['pid'] == ME


def test_release_leaves_another_holder_alone(bench):
    bench[4242] = 'python.exe'
    lock(1, 4242)
    slots.release(1)
    assert slots.holder(1)['pid'] == 4242


def test_the_users_game_is_foreign(bench):
    bench[100] = 'RA3_1.13.game'        # a bench game, recorded in its slot
    bench[200] = 'RA3_1.13.game'        # nobody's: the user's
    lock(1, ME, game=100)
    assert slots.foreign_games() == {200}
    assert slots.busy('CampA4').startswith('RA3 is running')


def test_a_build_stages_only_for_its_own_mod(bench):
    bench[100] = 'RA3_1.13.game'
    lock(1, ME, note=r'C:\Users\x\Documents\Red Alert 3\Mods\CampA7\CampA7_1.0.skudef', game=100)
    assert slots.busy('CampA4') == ''
    assert 'CampA7' in slots.busy('CampA7')
    assert slots.busy('campa7')         # Windows names: case does not matter


def test_one_build_at_a_time(bench):
    import threading
    release = slots.build_lock('first', poll=0.05)
    got = []
    t = threading.Thread(target=lambda: got.append(slots.build_lock('second', poll=0.05)))
    t.start()
    t.join(0.3)
    assert not got                      # held: the second build waits
    release()
    t.join(2)
    assert got                          # released: the second one goes
    got[0]()
    assert not os.path.exists(os.path.join(slots.LOCKS, 'sdk-build.json'))


def test_a_dead_builder_frees_the_sdk(bench):
    with open(os.path.join(slots.LOCKS, 'sdk-build.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(owner='sdk build', pid=999999, until=None), f)
    import threading
    got = []
    t = threading.Thread(target=lambda: got.append(slots.build_lock('next', poll=0.05)), daemon=True)
    t.start()
    t.join(2)
    assert got                          # not waiting on a builder that is gone
    got[0]()


def test_a_worktree_finds_the_main_checkouts_locks(tmp_path):
    lab_dir = tmp_path / 'RA3Modding'
    main = lab_dir / 'RA3-CampaignLab'
    (main / '.git' / 'worktrees' / 'units').mkdir(parents=True)
    tree = main / '.claude' / 'worktrees' / 'units'
    tree.mkdir(parents=True)
    (tree / '.git').write_text(f'gitdir: {main / ".git" / "worktrees" / "units"}\n', encoding='utf-8')
    assert slots.lab(str(tree)) == str(lab_dir)
    assert slots.lab(str(main)) == str(lab_dir)        # the main checkout: its .git is a folder


def test_note_game_marks_the_game_ours(bench):
    i = slots.take('a')
    bench[300] = 'RA3_1.13.game'
    assert slots.foreign_games() == {300}
    slots.note_game(i, 300)
    assert slots.foreign_games() == set()
