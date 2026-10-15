from fastmcp import FastMCP

mcp = FastMCP("Pokemon Name Generator 🚀")


def generate_pokemon_names() -> list[str]:
    """Generate the main Pokemon character names"""
    names = ["Pikachu", "Guilhem", "Vincent", "Aurelien", "Remi"]
    return [f"The main character's name is {name}." for name in names]


# give the list of main pokemon heros a name generator
@mcp.tool(name="name_main_pokemon", description="Generate names of the main Pokemon characters")
async def name_main_pokemon() -> list[str]:
    """Name the main pokemon characters"""
    return generate_pokemon_names()


if __name__ == "__main__":
    # Run the FastMCP application
    mcp.run(transport="stdio")
