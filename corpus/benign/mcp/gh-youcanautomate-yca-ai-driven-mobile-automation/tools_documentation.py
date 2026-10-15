"""Documentation tools: answer_appium."""
from typing import Any, Dict
from logger import info, error


def appium_answer_appium(question: str) -> Dict[str, Any]:
    """Answer questions about Appium."""
    
    # Simple knowledge base
    knowledge_base = {
        'locator strategies': 'Appium supports: xpath, id, name, class name, accessibility id, css selector, -android uiautomator, -ios predicate string, -ios class chain',
        'session creation': 'Use create_session tool with platform (ios/android), device name, and app path or bundle ID',
        'element interaction': 'Use appium_click, appium_set_value, appium_get_text, and other interaction tools',
        'screenshots': 'Use appium_screenshot for full page or appium_element_screenshot for specific element',
        'app management': 'Use appium_activate_app, appium_install_app, appium_terminate_app, etc.',
        'navigation': 'Use appium_scroll, appium_swipe, appium_scroll_to_element for navigation',
        'context switching': 'Use appium_get_contexts and appium_switch_context for web/native context',
        'test generation': 'Use appium_generate_tests to create test scripts from actions',
    }
    
    try:
        question_lower = question.lower()
        
        # Search for relevant answers
        answer = None
        for topic, response in knowledge_base.items():
            if any(word in question_lower for word in topic.split()):
                answer = response
                break
        
        if not answer:
            answer = 'I could not find information about your question. Please check the Appium documentation or ask about: locator strategies, session creation, element interaction, screenshots, app management, navigation, context switching, or test generation.'
        
        info(f"Answer provided for question: {question[:50]}...")
        return {
            'status': 'success',
            'question': question,
            'answer': answer,
            'message': 'Answer provided'
        }
    except Exception as e:
        error(f"Failed to answer question: {e}")
        return {
            'status': 'error',
            'message': f'Failed to answer question. Error: {str(e)}'
        }
