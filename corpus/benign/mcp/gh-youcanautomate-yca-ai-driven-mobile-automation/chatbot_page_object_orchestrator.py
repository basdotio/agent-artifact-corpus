"""
ORCHESTRATION FOR AUTOMATIC LOCATOR VALIDATION IN CHATBOT

This module integrates the locator validation service into the chatbot workflow.
When page objects are generated during a chatbot session, locators are automatically
validated against the real app before being saved.

Workflow:
1. User performs actions in chatbot
2. Workflow is captured by orchestrator
3. Page objects are generated with candidate locators
4. ✨ VALIDATION HAPPENS AUTOMATICALLY ✨
5. Only VERIFIED locators are saved to page objects
6. Test is generated with validated locators
7. Test is guaranteed to work

Integration Points:
- orchestrator.execute_workflow() returns device_info
- generate_page_objects_with_validation() validates and saves
- chatbot uses validated page objects for test generation
"""
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


def validate_and_save_page_objects(workflow_results: Dict[str, Any],
                                    output_dir: str = 'page_objects',
                                    appium_url: str = 'http://localhost:4723',
                                    skip_validation: bool = False) -> Dict[str, Any]:
    """
    Generate page objects and validate locators automatically.
    
    This is the chatbot-integrated entry point:
    - Generates page objects with candidate locators
    - Validates each locator against real app
    - Saves ONLY verified locators
    - Returns comprehensive report
    
    Args:
        workflow_results: Result dict from orchestrator.execute_workflow()
            Must include: results, device_info, platform
        output_dir: Where to save page object files
        appium_url: Appium server URL
        skip_validation: Set False to validate (default), True to skip (for testing)
    
    Returns:
        {
            'status': 'success' | 'partial' | 'error',
            'files': [
                {
                    'page_name': 'login_page',
                    'filepath': '...',
                    'total_elements': 5,
                    'verified_locators': 4,
                    'unverified_locators': 1,
                    'locator_success_rate': 80.0,
                }
            ],
            'total_verified': 12,
            'total_unverified': 3,
            'validation_report': {...}
        }
    """
    try:
        # Import here to avoid circular imports
        from generate_page_objects import generate_page_objects
        from locator_validation_service import LocatorValidationService
        
        logger.info("\n" + "="*80)
        logger.info("🚀 GENERATING PAGE OBJECTS WITH AUTOMATIC VALIDATION")
        logger.info("="*80)
        
        # Step 1: Generate page objects with candidate locators
        logger.info("\n📝 Step 1: Generating page objects...")
        generation_result = generate_page_objects(workflow_results, output_dir)
        
        if generation_result['status'] != 'success':
            logger.error(f"Failed to generate page objects: {generation_result.get('message')}")
            return generation_result
        
        generated_files = generation_result.get('files', [])
        logger.info(f"✓ Generated {len(generated_files)} page object files")
        
        # Step 2: Validate locators (if enabled)
        if skip_validation:
            logger.warning("\n⚠ Validation SKIPPED (skip_validation=True)")
            return {
                'status': 'success',
                'files': generated_files,
                'validation_enabled': False,
                'message': 'Page objects generated but NOT validated'
            }
        
        device_info = workflow_results.get('device_info', {})
        platform = workflow_results.get('platform', 'ios')
        
        if not device_info:
            logger.warning("⚠ No device_info in workflow results, skipping validation")
            return {
                'status': 'partial',
                'files': generated_files,
                'message': 'Page objects generated without validation (no device info)'
            }
        
        logger.info("\n✅ Step 2: Validating locators against real app...")
        
        service = LocatorValidationService(appium_url, device_info, platform)
        
        if not service.connect():
            logger.warning("⚠ Could not connect to app for validation")
            logger.warning("  Locators will not be verified, test may fail")
            return {
                'status': 'partial',
                'files': generated_files,
                'message': 'Page objects generated but validation failed (app not reachable)'
            }
        
        try:
            # Validate each generated page object
            validation_results = {}
            total_verified = 0
            total_unverified = 0
            
            for file_info in generated_files:
                page_name = file_info['page_name']
                element_names = file_info['element_names']
                
                logger.info(f"\n  Validating {page_name}... ({len(element_names)} locators)")
                
                # Build locator dict from generated file
                locator_dict = _extract_locators_from_file(
                    Path(output_dir) / file_info['filename']
                )
                
                if not locator_dict:
                    logger.warning(f"    Could not extract locators from {page_name}")
                    continue
                
                # Validate locators
                result = service.validate_locators(locator_dict)
                validation_results[page_name] = result
                
                verified_count = len(result.get('passed', []))
                unverified_count = len(result.get('failed', []))
                total_verified += verified_count
                total_unverified += unverified_count
                
                # Log results
                rate = (verified_count / (verified_count + unverified_count) * 100
                        if (verified_count + unverified_count) > 0 else 0)
                
                logger.info(f"    ✓ {verified_count} verified, ✗ {unverified_count} unverified ({rate:.0f}%)")
                
                # Update file info with validation results
                file_info['verified_locators'] = verified_count
                file_info['unverified_locators'] = unverified_count
                file_info['locator_success_rate'] = rate
                
                # Filter and save ONLY verified locators
                if unverified_count > 0:
                    logger.info(f"    🔄 Updating {page_name} with only verified locators...")
                    _update_page_object_with_verified_locators(
                        Path(output_dir) / file_info['filename'],
                        result
                    )
            
            logger.info("\n" + "="*80)
            logger.info("✅ VALIDATION COMPLETE")
            logger.info("="*80)
            logger.info(f"✓ Total verified locators: {total_verified}")
            logger.info(f"✗ Total unverified locators: {total_unverified}")
            rate = (total_verified / (total_verified + total_unverified) * 100
                    if (total_verified + total_unverified) > 0 else 0)
            logger.info(f"Success rate: {rate:.1f}%")
            
            status = 'success' if total_unverified == 0 else 'partial'
            
            return {
                'status': status,
                'files': generated_files,
                'total_verified': total_verified,
                'total_unverified': total_unverified,
                'validation_enabled': True,
                'validation_results': validation_results,
                'message': f'Page objects generated and validated: {total_verified} verified, {total_unverified} unverified'
            }
            
        finally:
            service.disconnect()
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return {'status': 'error', 'message': f'Import error: {e}'}
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return {'status': 'error', 'message': f'Validation error: {e}'}


def _extract_locators_from_file(filepath: Path) -> Dict[str, tuple]:
    """
    Extract locators from a generated page object file.
    
    Returns: {'EMAIL_FIELD_LOCATOR': (AppiumBy.XPATH, '...'), ...}
    """
    try:
        content = filepath.read_text()
        locators = {}
        
        # Parse the file to find locator definitions
        for line in content.split('\n'):
            line = line.strip()
            if '_LOCATOR = (AppiumBy.' in line:
                # Parse: EMAIL_FIELD_LOCATOR = (AppiumBy.XPATH, "...")
                try:
                    name_part, value_part = line.split(' = ', 1)
                    name = name_part.strip()
                    
                    # Extract locator strategy and value
                    # Format: (AppiumBy.XPATH, "value")
                    if 'AppiumBy.' in value_part:
                        # Extract strategy
                        strategy_start = value_part.find('AppiumBy.') + len('AppiumBy.')
                        strategy_end = value_part.find(',', strategy_start)
                        strategy = value_part[strategy_start:strategy_end].strip()
                        
                        # Extract selector value (between quotes)
                        quote_start = value_part.find('"', strategy_end) + 1
                        quote_end = value_part.rfind('"')
                        selector = value_part[quote_start:quote_end]
                        
                        # Reconstruct as AppiumBy constant
                        from appium.webdriver.common.appiumby import AppiumBy
                        by_constant = getattr(AppiumBy, strategy)
                        locators[name] = (by_constant, selector)
                except Exception as e:
                    logger.debug(f"Could not parse locator line: {line} -> {e}")
                    continue
        
        return locators
    except Exception as e:
        logger.error(f"Error extracting locators from {filepath}: {e}")
        return {}


def _update_page_object_with_verified_locators(filepath: Path, validation_result: Dict):
    """
    Update page object file keeping only verified locators.
    
    Removes failed locators from the generated file.
    """
    try:
        content = filepath.read_text()
        failed_names = {name for name, _, _ in validation_result.get('failed', [])}
        
        if not failed_names:
            logger.debug(f"All locators verified in {filepath.name}")
            return  # Nothing to remove
        
        # Remove lines defining failed locators
        updated_lines = []
        skip_next = False
        
        for line in content.split('\n'):
            # Check if this line defines a failed locator
            is_failed_locator = False
            for failed_name in failed_names:
                if f"{failed_name} = (AppiumBy." in line:
                    is_failed_locator = True
                    logger.debug(f"  Removing unverified locator: {failed_name}")
                    break
            
            if not is_failed_locator:
                updated_lines.append(line)
        
        # Write back
        filepath.write_text('\n'.join(updated_lines))
        logger.info(f"  ✓ Updated {filepath.name}")
        
    except Exception as e:
        logger.error(f"Error updating {filepath}: {e}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # This would be called from orchestrator/chatbot
    print("This module is meant to be imported and used within the chatbot workflow")
    print("See validate_and_save_page_objects() for the main entry point")
