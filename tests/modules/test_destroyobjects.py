"""DestroyObjectsUpdate only models the stock civilian filter."""
from engine.testing.small import small_world


def test_custom_relationship_is_logged_without_removing_the_civilian():
    s = small_world(model=False)
    s.own['CNVFilteredEffect'] = '''<GameObject id="CNVFilteredEffect">
        <Behaviors><DestroyObjectsUpdate id="ModuleTag_Destroy" Radius="500">
            <ObjectFilter Rule="NONE" Include="CIVILIAN_UNIT" Relationship="ENEMIES" />
        </DestroyObjectsUpdate></Behaviors>
    </GameObject>'''
    s.add('civilian', 'CivilianFemale1', 'Player_1', 450, 300)
    s.add('effect', 'CNVFilteredEffect', 'Player_1', 300, 300)
    s.advance(3)
    assert s.bodies['civilian'].alive
    assert ('DestroyObjectsUpdate', 'CNVFilteredEffect') in s.world.gaps
