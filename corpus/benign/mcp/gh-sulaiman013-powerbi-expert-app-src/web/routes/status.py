"""
Status Routes
=============
API endpoints for checking service status.
"""

from flask import Blueprint, jsonify

from ..services.state import app_state

status_bp = Blueprint('status', __name__)


@status_bp.route('/status')
def get_status():
    """Get the status of all services (Ollama, Power BI Desktop, Power BI Cloud)."""
    # Check Ollama
    ollama_ok = False
    try:
        import httpx
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2)
        ollama_ok = response.status_code == 200
    except Exception:
        pass

    # Check Power BI Desktop connection
    pbi_ok = app_state.is_desktop_connected

    # Check Power BI Service (cloud) connection
    pbi_cloud_ok = app_state.is_cloud_connected

    return jsonify({
        "ollama": ollama_ok,
        "powerbi": pbi_ok,
        "pbi_cloud": pbi_cloud_ok,
        "model": "powerbi-expert"
    })


@status_bp.route('/provider_status')
def provider_status():
    """Get current LLM provider status."""
    return jsonify({
        "provider": app_state.current_provider_type,
        "configured": app_state.is_llm_configured
    })
