import asyncio
from mcp.server.fastmcp import FastMCP

# Import from supermarkets package
from src.supermarkets import (
    coles_search_products,
    coles_extract_products,
    COLES_DEFAULT_STORE_ID,
    woolworths_search_products,
)

# Initialize FastMCP server
mcp = FastMCP("supermarket-mcp", host="localhost", port=7860)


@mcp.tool()
async def get_coles_products(query: str, store_id: str = COLES_DEFAULT_STORE_ID, limit: int = 10) -> str:
    """Search for products at Coles.

    Args:
        query: The product search query.
        store_id: The Coles store ID to search in.
        limit: Maximum number of products to return.
    """
    try:
        # The limit parameter in coles_search_products's signature is not used in its API call.
        # We will fetch all available (up to API's own limit) and then slice.
        # Also, the original coles_search_products signature includes a limit, but it's not used.
        # Forcing keyword arguments for clarity with asyncio.to_thread
        search_results = await asyncio.to_thread(
            coles_search_products,
            query=query,
            store_id=store_id
            # limit parameter is not passed here as the underlying coles_search_products doesn't use it in API call
        )

        if search_results.get("status") == "error":
            return f"Error fetching Coles products: {search_results.get('message', 'Unknown error')}\nResponse: {search_results.get('response_text', '')}"

        # extract_products is CPU-bound/quick, but run in thread for consistency with I/O
        products = await asyncio.to_thread(coles_extract_products, search_results)

        # Apply limit after extraction
        products = products[: min(limit, len(products))]

        if not products:
            return f"No products found at Coles for '{query}'."

        formatted_products = []
        for p in products:
            price_str = f"${p['price']:.2f}" if p['price'] is not None else "N/A"
            unit_str = p['unit'] if p['unit'] else "N/A" # Ensure unit is not None
            formatted_products.append(
                f"Name: {p['name']}\nPrice: {price_str}\nUnit: {unit_str}\nStore: {p['store']}"
            )
        return "\n---\n".join(formatted_products)
    except Exception as e:
        return f"An unexpected error occurred in get_coles_products: {str(e)}"


@mcp.tool()
async def get_woolworths_products(query: str, limit: int = 10) -> str:
    """Search for products at Woolworths.

    Args:
        query: The product search query.
        limit: Maximum number of products to return.
    """
    try:
        search_results = await asyncio.to_thread(woolworths_search_products, query=query)

        if search_results.get("status") == "error":
            return f"Error fetching Woolworths products: {search_results.get('message', 'Unknown error')}\nResponse: {search_results.get('response_text', '')}"

        products = search_results.get("products", [])

        # Apply limit after fetching
        products = products[: min(limit, len(products))]

        if not products:
            return f"No products found at Woolworths for '{query}'."

        formatted_products = []
        for p in products:
            price_str = f"${p['price']:.2f}" if p['price'] is not None else "N/A"
            unit_str = p['unit'] if p['unit'] else "N/A" # Ensure unit is not None
            formatted_products.append(
                f"Name: {p['name']}\nPrice: {price_str}\nUnit: {unit_str}\nStore: {p['store']}"
            )
        return "\n---\n".join(formatted_products)
    except Exception as e:
        return f"An unexpected error occurred in get_woolworths_products: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")