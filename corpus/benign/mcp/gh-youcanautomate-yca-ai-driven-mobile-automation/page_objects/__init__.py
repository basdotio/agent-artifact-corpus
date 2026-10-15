"""Page Object Model package."""

from .login_page import LoginPage
from .home_page import HomePage
from .product_details_page import ProductDetailsPage

__all__ = ["login_page", "home_page", "product_details_page"]
