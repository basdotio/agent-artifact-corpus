"""
Export necessary functions from supermarket modules to enable cleaner imports.
"""

# Export from coles.py
from .coles import (
    search_products as coles_search_products,
    extract_products as coles_extract_products,
    DEFAULT_STORE_ID as COLES_DEFAULT_STORE_ID,
)

# Export from woolworths.py
from .woolworths import (
    search_products as woolworths_search_products,
)

__all__ = [
    "coles_search_products",
    "coles_extract_products", 
    "COLES_DEFAULT_STORE_ID",
    "woolworths_search_products",
] 