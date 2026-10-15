from main import generate_pokemon_names
def test_generate_pokemon_names():
    result = generate_pokemon_names()
    assert isinstance(result, list)
    assert len(result) == 6
    assert result[0] == "The main character's name is Pikachu."
    assert all("The main character's name is" in name for name in result)
