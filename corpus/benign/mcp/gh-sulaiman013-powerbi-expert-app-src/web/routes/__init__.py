"""
Routes Package
==============
Flask blueprints for the Power BI MCP Server web application.
"""

from flask import Flask

from .status import status_bp
from .desktop import desktop_bp
from .cloud import cloud_bp
from .llm import llm_bp
from .chat import chat_bp
from .pbip import pbip_bp


def register_blueprints(app: Flask) -> None:
    """
    Register all blueprints with the Flask application.

    Args:
        app: The Flask application instance
    """
    app.register_blueprint(status_bp, url_prefix='/api')
    app.register_blueprint(desktop_bp, url_prefix='/api')
    app.register_blueprint(cloud_bp, url_prefix='/api')
    app.register_blueprint(llm_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(pbip_bp, url_prefix='/api')


__all__ = [
    'register_blueprints',
    'status_bp',
    'desktop_bp',
    'cloud_bp',
    'llm_bp',
    'chat_bp',
    'pbip_bp'
]
