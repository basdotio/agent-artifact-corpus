from typing import Dict, Any, List
import re
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Store information
STORE_NAME = "coles"
STORE_URL = "https://www.coles.com.au"
API_URL = "https://www.coles.com.au/api/bff/products"

# Coles API key - provided by the user
# In a production environment, this should be stored securely, not hardcoded
API_KEY = os.getenv("COLES_API_KEY")

# Default store ID - provided in the example URL
DEFAULT_STORE_ID = "0584"

def get_store_info() -> Dict[str, Any]:
    """
    Get information about the Coles store.
    
    Returns:
        Dict[str, Any]: Store information
    """
    return {
        "name": STORE_NAME,
        "url": STORE_URL,
        "api_url": API_URL,
        "api_key": API_KEY,
        "default_store_id": DEFAULT_STORE_ID
    }

def search_products(query: str, store_id: str = DEFAULT_STORE_ID, limit: int = 10) -> Dict[str, Any]:
    """
    Search for products using the Coles API.
    
    Args:
        query (str): The search query
        store_id (str, optional): The store ID to search in. Defaults to DEFAULT_STORE_ID.
        limit (int, optional): The maximum number of results to return. Defaults to 10.
    
    Returns:
        Dict[str, Any]: The search results
    """
    try:
        # Use the exact URL format provided by the user
        search_url = f"{API_URL}/search"
        
        # Set up the API request parameters for search using the exact format provided
        search_params = {
            "storeId": store_id,
            "searchTerm": query,
            "start": "0",
            "sortBy": "salesDescending",
            "excludeAds": "true",
            "authenticated": "false",
            "subscription-key": API_KEY
        }
        
        # Set up the headers
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Make the API request
        response = requests.get(search_url, params=search_params, headers=headers)
        
        # Check if the request was successful
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"API request failed with status code {response.status_code}",
                "response_text": response.text
            }
        
        # Parse the JSON response
        response_data = response.json()
        
        return {
            "status": "success",
            "query": query,
            "store_id": store_id,
            "response_data": response_data
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def parse_price(price_text: str) -> float:
    """
    Parse a price string into a float.
    
    Args:
        price_text (str): The price text (e.g., "$2.50")
    
    Returns:
        float: The parsed price
    """
    # Extract the price using regex
    price_match = re.search(r'(\d+\.\d+)', price_text)
    if price_match:
        return float(price_match.group(1))
    return None

def extract_products(search_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract product information from search results.
    
    Args:
        search_results (Dict[str, Any]): The search results from the Coles API
    
    Returns:
        List[Dict[str, Any]]: The extracted product information
    """
    products = []
    
    if search_results["status"] != "success":
        return products
    
    response_data = search_results["response_data"]
    
    # Check if the response contains products
    if "results" in response_data and response_data["results"]:
        api_products = response_data["results"]
        
        # Process the products
        for product in api_products:
            try:
                # Extract product information
                name = product.get("name", "")
                
                # Extract price information
                pricing = product.get("pricing", {})
                now_price = pricing.get("now", None)
                was_price = pricing.get("was", None)
                
                # Use the current price if available, otherwise use the regular price
                price = now_price if now_price is not None else was_price
                
                # Extract unit information - check multiple fields
                unit = ""
                
                # Check package_size field
                package_size = product.get("packageSize", "")
                
                # Check quantity field
                quantity = product.get("quantity", "")
                
                # Check size field
                size = product.get("size", "")
                
                # Check description field for unit information
                description = product.get("description", "")
                
                # Try to extract unit information from available fields
                unit_fields = [package_size, quantity, size, description]
                for field in unit_fields:
                    if not field:
                        continue
                    
                    field = field.lower()
                    if "kg" in field:
                        unit = "kg"
                        break
                    elif "g" in field and not "mg" in field:
                        unit = "g"
                        break
                    elif "l" in field and not "ml" in field:
                        unit = "L"
                        break
                    elif "ml" in field:
                        unit = "ml"
                        break
                    elif "each" in field:
                        unit = "each"
                        break
                    elif "pack" in field:
                        unit = "pack"
                        break
                
                products.append({
                    "name": name,
                    "price": float(price) if price is not None else None,
                    "unit": unit,
                    "store": STORE_NAME
                })
            except Exception as e:
                continue
    
    return products

# Export the store
coles_store = {
    "name": STORE_NAME,
    "url": STORE_URL,
    "api_url": API_URL,
    "api_key": API_KEY,
    "default_store_id": DEFAULT_STORE_ID,
    "get_store_info": get_store_info,
    "search_products": search_products,
    "parse_price": parse_price,
    "extract_products": extract_products
}

if __name__ == "__main__":
    # Example search query
    query = "juice"
    
    # Get store info
    store_info = get_store_info()
    print(f"Store Info: {store_info}")
    
    # Search for products
    search_results = search_products(query)
    
    # Extract products from search results
    products = extract_products(search_results)
    
    # Print results
    print(f"\nSearch Results for '{query}':")
    print(f"Found {len(products)} products")
    
    # Print each product
    for product in products:
        print(f"\nProduct: {product['name']}")
        print(f"Price: ${product['price']:.2f}" if product['price'] else "Price: N/A")
        print(f"Unit: {product['unit']}")
        print(f"Store: {product['store']}")
