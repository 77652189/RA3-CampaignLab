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
    assert s.ai_priorities['Player_2'] == [(None, 0), ('*', 20, ()), ('*', 20, ())] and not s.ai_switches


def test_set_all_fills_the_table_with_the_enemies_when_it_runs():
    # review uu #4 / vv: a player turned enemy before SET_ALL is in, one turned after is not, one turned back to
    # neutral after is still in -- whenever the brain reads the table (the model's contract: the call fills it)
    from types import SimpleNamespace as NS
    import engine.ai.core as simai
    s = simsmall.small_world(model=False)
    s.relations[('Player_2', 'Soviet_4')] = 'Enemy'
    s.act('SKIRMISH_AI_SET_ALL_ENEMY_PLAYERS_PRIORITIES', ['Player_2', 20], None)
    s.relations[('Player_2', 'Soviet_4')] = 'Neutral'
    s.relations[('Player_2', 'Soviet_1')] = 'Enemy'
    told = []
    b = NS(player='Player_2', ai=NS(tell=told.append), settings=NS(ai_switches={}, ai_priorities=s.ai_priorities),
           host=NS(mod={'player': NS(Command=lambda name, args: (name, args))}))
    simai.Brain.switches(b)
    assert told == [('enemy priorities', {'n': 20, 'enemies': ['Soviet_4']})]
