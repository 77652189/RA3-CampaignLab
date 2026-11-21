"""The skirmish AI's script actions on a small world (engine/script/act_player.py)."""
import engine.testing.small as simsmall


def test_consider_all_enemies_is_taken_and_leaves_the_ai_as_it_was():
    # bench A274 aiallflip (checks/engine_aiflip.readings.toml): the building enemies already follow the relations
    s = simsmall.small_world(model=False)
    s.act('SKIRMISH_AI_CONSIDER_ALL_ENEMIES_WHEN_BUILDING', ['Player_2'], None)
    assert not s.unknown and not s.ai_switches and not s.ai_priorities
