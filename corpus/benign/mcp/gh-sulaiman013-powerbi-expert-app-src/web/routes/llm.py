"""
LLM Routes
==========
API endpoints for configuring LLM providers (Ollama, Azure OpenAI, Azure Claude).
"""

import asyncio
import logging
from flask import Blueprint, jsonify, request

from src.llm.ollama_provider import create_ollama_provider
from src.llm.azure_provider import create_azure_provider
from src.llm.azure_claude_provider import create_azure_claude_provider
from ..services.state import app_state

logger = logging.getLogger("powerbi-v3-webui")
llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/configure_azure_claude', methods=['POST'])
def configure_azure_claude():
    """Configure Azure AI Foundry with Claude as the LLM provider."""
    try:
        data = request.json
        endpoint = data.get('endpoint', '').strip()
        api_key = data.get('api_key', '').strip()
        model = data.get('model', 'claude-3-haiku').strip()

        if not endpoint or not api_key:
            return jsonify({
                "success": False,
                "message": "Endpoint and API key are required"
            })

        # Create Azure Claude provider
        app_state.llm_provider = create_azure_claude_provider(
            endpoint=endpoint,
            api_key=api_key,
            model_name=model,
            temperature=0.1,
            max_tokens=2048,
            timeout=60
        )

        # Initialize
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(app_state.llm_provider.initialize())

        if success:
            app_state.current_provider_type = "azure-claude"
            return jsonify({
                "success": True,
                "message": f"Connected to Azure Claude ({model})"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to connect to Azure Claude. Check your credentials and endpoint."
            })

    except Exception as e:
        logger.error(f"Azure Claude config error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })


@llm_bp.route('/configure_azure', methods=['POST'])
def configure_azure():
    """Configure Azure OpenAI as the LLM provider."""
    try:
        data = request.json
        endpoint = data.get('endpoint', '').strip()
        api_key = data.get('api_key', '').strip()
        deployment = data.get('deployment', 'gpt-4o').strip()

        if not endpoint or not api_key:
            return jsonify({
                "success": False,
                "message": "Endpoint and API key are required"
            })

        # Create Azure OpenAI provider
        app_state.llm_provider = create_azure_provider(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=deployment,
            temperature=0.1,
            max_tokens=2048,
            timeout=60
        )

        # Initialize
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(app_state.llm_provider.initialize())

        if success:
            app_state.current_provider_type = "azure"
            return jsonify({
                "success": True,
                "message": f"Connected to Azure OpenAI ({deployment})"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to connect to Azure OpenAI. Check your credentials."
            })

    except Exception as e:
        logger.error(f"Azure config error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })


@llm_bp.route('/configure_ollama', methods=['POST'])
def configure_ollama():
    """Configure Ollama as the LLM provider."""
    try:
        data = request.json
        model = data.get('model', 'powerbi-expert').strip()

        # Create Ollama provider
        app_state.llm_provider = create_ollama_provider(
            endpoint="http://127.0.0.1:11434",
            model=model,
            temperature=0.1,
            max_tokens=2048,
            timeout=300
        )

        # Initialize
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(app_state.llm_provider.initialize())

        if success:
            app_state.current_provider_type = "ollama"
            return jsonify({
                "success": True,
                "message": f"Connected to Ollama ({model})"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Failed to connect to Ollama. Is it running?"
            })

    except Exception as e:
        logger.error(f"Ollama config error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })
