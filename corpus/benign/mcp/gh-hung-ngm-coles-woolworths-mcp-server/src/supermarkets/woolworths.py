from typing import Dict, Any, List, Optional
import re
import requests
import json

# Store information
STORE_NAME = "woolworths"
STORE_URL = "https://www.woolworths.com.au"
API_URL = "https://www.woolworths.com.au/apis/ui/Search/products"

def get_store_info() -> Dict[str, Any]:
    """
    Get information about the Woolworths store.
    
    Returns:
        Dict[str, Any]: Store information
    """
    return {
        "name": STORE_NAME,
        "url": STORE_URL,
        "api_url": API_URL
    }

def format_api_url(query: str) -> str:
    """
    Format the API URL for a query.
    
    Args:
        query (str): The search query
    
    Returns:
        str: The formatted API URL
    """
    # Replace spaces with plus signs
    formatted_query = query.replace(" ", "+")
    return f"{API_URL}?searchTerm={formatted_query}"

def search_products(query: str) -> Dict[str, Any]:
    """
    Search for products using the Woolworths API.
    
    Args:
        query (str): The search query
    
    Returns:
        Dict[str, Any]: The search results
    """
    try:
        # Format the API URL
        url = format_api_url(query)
        
        # Set up the headers
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Make the API request
        response = requests.get(url, headers=headers)
        
        # Check if the request was successful
        if response.status_code != 200:
            return {
                "status": "error",
                "message": f"API request failed with status code {response.status_code}",
                "response_text": response.text
            }
        
        # Parse the JSON response
        response_data = response.json()
        
        # Extract and format the products
        products = []
        # The outer "Products" key in response_data contains a list of product categories/groups.
        # Each category/group then has its own "Products" key containing a list of actual products.
        if "Products" in response_data and response_data["Products"]:
            for product_category in response_data.get("Products", []): # product_category is a dict
                actual_product_list = product_category.get("Products")
                
                if not isinstance(actual_product_list, list):
                    # Handle cases where product_category might be a product itself (e.g. direct search hit or promotion)
                    if isinstance(product_category, dict) and "Stockcode" in product_category and "Products" not in product_category:
                        actual_product_list = [product_category] # Treat the category as a single product list
                    else:
                        # If it's not a list and not a product-like dict, skip it.
                        # print(f"Skipping product_category due to unexpected structure: {product_category.get('Name')}")
                        continue

                for product in actual_product_list: # This 'product' is the actual product item
                    
                    # Extract product information
                    name = product.get("DisplayName", product.get("Name", ""))
                    
                    # Extract price information
                    price = product.get("Price")
                    if price is None:
                        price = product.get("InstorePrice") # Check InstorePrice as well
                    if price is None:
                        price = product.get("WasPrice") # Fallback to WasPrice
                    
                    # Extract unit information
                    unit = ""
                    package_size_str = product.get("PackageSize", "")
                    cup_string_str = product.get("CupString", "")
                    cup_measure_str = product.get("CupMeasure", "")
                    api_unit_field = product.get("Unit", "")

                    # Priority 1: PackageSize
                    if package_size_str and isinstance(package_size_str, str):
                        ps_lower = package_size_str.lower()
                        if "kg" in ps_lower: unit = "kg"
                        elif "g" in ps_lower and "kg" not in ps_lower: unit = "g"
                        elif "l" in ps_lower and "ml" not in ps_lower: unit = "L"
                        elif "ml" in ps_lower: unit = "ml"
                        elif "each" in ps_lower: unit = "each"
                        elif "pack" in ps_lower or "pk" in ps_lower: unit = "pack"
                    
                    # Priority 2: CupString
                    if not unit and cup_string_str and isinstance(cup_string_str, str):
                        cs_lower = cup_string_str.lower()
                        parts = cs_lower.split('/')
                        target_str_for_unit = parts[-1].strip() if len(parts) > 1 else cs_lower

                        if "kg" in target_str_for_unit: unit = "kg"
                        elif "g" in target_str_for_unit and "kg" not in target_str_for_unit: unit = "g"
                        elif "l" in target_str_for_unit and "ml" not in target_str_for_unit: unit = "L"
                        elif "ml" in target_str_for_unit: unit = "ml"
                        elif "each" in target_str_for_unit or "ea" in target_str_for_unit: unit = "each"
                        elif "pack" in target_str_for_unit or "pk" in target_str_for_unit: unit = "pack"

                    # Priority 3: CupMeasure
                    if not unit and cup_measure_str and isinstance(cup_measure_str, str):
                        cm_lower = cup_measure_str.lower()
                        if "kg" in cm_lower: unit = "kg"
                        elif "g" in cm_lower and "kg" not in cm_lower: unit = "g"
                        elif "l" in cm_lower and "ml" not in cm_lower: unit = "L"
                        elif "ml" in cm_lower: unit = "ml"
                        elif "each" in cm_lower: unit = "each"
                        elif "pack" in cm_lower or "pk" in cm_lower: unit = "pack"
                    
                    # Priority 4: API "Unit" field (often "Each")
                    if not unit and api_unit_field and isinstance(api_unit_field, str):
                        auf_lower = api_unit_field.lower()
                        if "each" == auf_lower: # Exact match for "each"
                            unit = "each"
                        # Can add other specific unit mappings from api_unit_field if needed
                
                    # Add the product to the list
                    products.append({
                        "name": name,
                        "price": float(price) if price is not None else None,
                        "unit": unit,
                        "store": STORE_NAME
                    })
        
        return {
            "status": "success",
            "query": query,
            "products": products,
            "product_count": len(products)
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

# Export the store
woolworths_store = {
    "name": STORE_NAME,
    "url": STORE_URL,
    "api_url": API_URL,
    "get_store_info": get_store_info,
    "format_api_url": format_api_url,
    "search_products": search_products,
    "parse_price": parse_price
}

if __name__ == "__main__":
    # Example search query
    query = "milk"
    
    # Get store info
    store_info = get_store_info()
    print(f"Store Info: {store_info}")
    
    # Search for products
    search_results = search_products(query)
    
    # Extract products from search results
    products = search_results.get("products", [])
    
    # Print results
    print(f"\nSearch Results for '{query}':")
    print(f"Found {len(products)} products")
    
    # Print each product
    for product in products:
        print(f"\nProduct: {product['name']}")
        print(f"Price: ${product['price']:.2f}" if product['price'] else "Price: N/A")
        print(f"Unit: {product['unit']}")
        print(f"Store: {product['store']}")