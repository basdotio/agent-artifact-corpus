"""Context tools: get_contexts, switch_context."""
from typing import Any, Dict, List
import session_store
from logger import info, error


def appium_get_contexts() -> Dict[str, Any]:
    """Get all available contexts."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        contexts = driver.contexts
        current_context = driver.current_context
        
        info(f"Retrieved contexts: {contexts}")
        return {
            'status': 'success',
            'contexts': contexts,
            'current_context': current_context,
            'message': f'Retrieved {len(contexts)} context(s)'
        }
    except Exception as e:
        error(f"Failed to get contexts: {e}")
        return {
            'status': 'error',
            'message': f'Failed to get contexts. Error: {str(e)}'
        }


def appium_switch_context(context_name: str) -> Dict[str, Any]:
    """Switch to a specific context."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.switch_to.context(context_name)
        current_context = driver.current_context
        
        info(f"Switched to context: {context_name}")
        return {
            'status': 'success',
            'context': context_name,
            'current_context': current_context,
            'message': f'Switched to context {context_name}'
        }
    except Exception as e:
        error(f"Failed to switch context: {e}")
        return {
            'status': 'error',
            'message': f'Failed to switch to context {context_name}. Error: {str(e)}'
        }
