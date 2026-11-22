"""The skirmish AI's script actions on a small world (engine/script/act_player.py)."""
import engine.testing.small as simsmall


def test_consider_all_enemies_is_taken_and_leaves_the_ai_as_it_was():
    # bench A274 aiallflip (checks/engine_aiflip.readings.toml): the building enemies already follow the relations
    s = simsmall.small_world(model=False)
    s.act('SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING', ['Player_2'], None)
    for name in ('PLAYER_AI_CHANGEUNITBUILDER', 'PLAYER_AI_CHANGETEAMBUILDER', 'PLAYER_AI_CHANGE_ECONOMY_MANAGER'):
        s.act(name, ['Player_2', 0], None)          # bench A294 aichange (checks/engine_aichange.readings.toml)
    assert not s.unknown and not s.ai_switches and not s.ai_priorities


def test_the_enemy_priority_calls_are_one_table_in_script_order():
    # review 1122ss #2: CLEAR then SET_ALL in one frame ends at SET_ALL's n; a SET_ALL to the same n again counts
    s = simsmall.small_world(model=False)
    for name, args in [('SKIRMISH_AI_CLEAR_ALL_ENEMY_PLAYERS_PRIORITIES', ['Player_2']),
                       ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', ['Player_2', 20]),
                       ('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', ['Player_2', 20])]:
        s.act(name, args, None)
    assert s.ai_priorities['Player_2'] == [(None, 0), ('*', 20), ('*', 20)] and not s.ai_switches


def test_set_all_takes_a_player_turned_enemy_in_the_same_frame():
    # review 1122uu #4: the brain read SET_ALL before look() refreshed view.enemies, so the frame's new enemy was missed
    from types import SimpleNamespace as NS
    import engine.ai.core as simai
    told, rel = [], {'Player_1': True, 'Soviet_4': True}          # Soviet_4 turned back to enemy this frame
    world = NS(players={'a': 'Player_1', 'b': 'Soviet_4', 'c': 'Player_2'}, enemy=lambda a, b: rel.get(b, False))
    b = NS(player='Player_2', world=world, view=NS(enemies=frozenset({'Player_1'})), ai=NS(tell=told.append),
           settings=NS(ai_switches={}, ai_priorities={'Player_2': [('*', 20)]}),
           host=NS(mod={'player': NS(Command=lambda name, args: (name, args))}))
    b.foes = lambda: simai.Brain.foes(b)
    simai.Brain.switches(b)
    assert told == [('enemy priorities', {'n': 20, 'enemies': ['Player_1', 'Soviet_4']})]
