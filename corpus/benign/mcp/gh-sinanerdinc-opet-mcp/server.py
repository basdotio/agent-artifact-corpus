from fastmcp import FastMCP
from utils import get_fuel_prices, get_json


mcp = FastMCP(name="Opet MCP")

@mcp.tool()
def get_provinces():
    """
    Returns the province of the cities.
    :return:
    """
    return get_json("provinces.json")

@mcp.tool()
def get_fuel_price(province_code: str):
    """
    Function to retrieve the fuel price for a specified province using its code.

    The function takes the province code as input and fetches the price using an
    external client. If any exception occurs during the process, it returns the
    error message within a dictionary.

    Args:
        province_code (str): Code of the province for which the fuel price
        needs to be retrieved.

    Returns:
        dict: A dictionary containing either the fuel price or an error message
        in case of an exception.
    """
    try:
        return get_fuel_prices(province_code)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()