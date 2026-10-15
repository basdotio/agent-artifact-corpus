"""Execute prompts from YAML configuration files."""
import sys
import os
import logging
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv, find_dotenv
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Configure logging BEFORE any other imports that might use logging
# Clear any existing handlers
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Set up Rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False, omit_repeated_times=True)]
)

# Load environment variables
# find_dotenv() searches from current dir upward, then home directory
dotenv_file = find_dotenv(raise_error_if_not_found=False)
if dotenv_file:
    load_dotenv(dotenv_file)
else:
    # Try home directory as fallback
    home_env = Path.home() / ".env"
    if home_env.exists():
        load_dotenv(home_env)

from orchestrator import MobileAutomationOrchestrator
from config import Config
from generate_regression_test import generate_from_workflow
from generate_page_objects import generate_page_objects
from yaml_loader import (
    load_yaml,
    is_workflow,
    get_platform_from_config,
    get_device_config,
    get_timeout,
    get_stop_on_error,
    print_config_summary,
    validate_single_prompt_config,
    validate_workflow_config
)

logger = logging.getLogger(__name__)
console = Console()


def execute_from_yaml(yaml_file: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file and execute prompts.
    
    YAML Structure (Single Prompt):
    ```yaml
    name: Test Name
    description: Brief description
    platform: ios  # or android
    prompt: "Your natural language prompt here"
    ```
    
    YAML Structure (Workflow):
    ```yaml
    name: Test Name
    description: Brief description
    platform: ios
    prompts:
      - "First step"
      - "Second step"
      - "Third step"
    ```
    """
    logger.info(f"Loading configuration from: {yaml_file}")
    
    # Check if AWS credentials are set
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.error("✗ AWS credentials not configured")
        logger.error("  Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        sys.exit(1)
    
    # Load YAML
    config_dict = load_yaml(yaml_file)
    
    # Print summary
    print_config_summary(config_dict)
    
    # Validate configuration
    if is_workflow(config_dict):
        validate_workflow_config(config_dict)
    else:
        validate_single_prompt_config(config_dict)
    
    # Extract configuration
    platform = get_platform_from_config(config_dict, "ios")
    device_config = get_device_config(config_dict)
    timeout = get_timeout(config_dict)
    stop_on_error = get_stop_on_error(config_dict)
    
    # Initialize config
    logger.info("Initializing configuration...")
    config = Config(platform=platform)
    config.validate()
    logger.info(f"✓ Platform: {config.platform}")
    
    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    try:
        orchestrator = MobileAutomationOrchestrator(
            platform=platform,
            bedrock_region=config.bedrock.region,
            debug=config.automation.debug
        )
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        raise SystemExit(1)
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        raise SystemExit(1)
    
    try:
        # Execute based on type
        if is_workflow(config_dict):
            logger.info("\n" + "="*60)
            logger.info("EXECUTING WORKFLOW")
            logger.info("="*60)
            
            # Handle both workflow formats:
            # Format 1: Screen-based workflow with 'workflow' key
            # Format 2: Direct prompts list with 'prompts' key
            
            if 'workflow' in config_dict:
                # Screen-based workflow format
                logger.info("Processing screen-based workflow...")
                workflow = config_dict['workflow']
                prompts = []
                screen_markers = {}
                prompt_index = 0
                
                for screen_name, screen_prompts in workflow.items():
                    logger.info(f"Processing screen: {screen_name}")
                    
                    # Add screen marker
                    prompts.append(f"[SCREEN: {screen_name}]")
                    screen_markers[prompt_index] = screen_name
                    prompt_index += 1
                    
                    # Add all prompts for this screen
                    if isinstance(screen_prompts, list):
                        for prompt in screen_prompts:
                            prompts.append(prompt)
                            screen_markers[prompt_index] = screen_name
                            prompt_index += 1
            else:
                # Direct prompts list format
                logger.info("Processing direct prompts list...")
                raw_prompts = config_dict['prompts']
                prompts = []
                screen_markers = {}
                current_screen = None
                
                for item in raw_prompts:
                    if isinstance(item, dict) and 'screen' in item:
                        # This is a screen marker
                        current_screen = item['screen']
                        # Convert to string prompt for orchestrator to process
                        prompts.append(f"[SCREEN: {current_screen}]")
                        screen_markers[len(prompts) - 1] = current_screen
                    elif isinstance(item, str):
                        prompts.append(item)
                        if current_screen:
                            screen_markers[len(prompts) - 1] = current_screen
            
            logger.info(f"Total steps: {len(prompts)} (after processing markers)")
            
            # Merge device config from YAML with environment config
            device_info = config.get_device_info()
            if device_config:
                device_info.update(device_config)
            
            result = orchestrator.execute_workflow(
                prompts=prompts,
                device_info=device_info,
                stop_on_error=stop_on_error
            )
            
            logger.info("\n" + "="*60)
            logger.info("WORKFLOW RESULTS")
            logger.info("="*60)
            logger.info(f"Status: {result.get('status')}")
            logger.info(f"Steps completed: {result.get('steps_completed', 0)}/{len(prompts)}")
            
            if result.get('results'):
                for i, step_result in enumerate(result['results'], 1):
                    status = step_result.get('status', 'unknown')
                    logger.info(f"  Step {i}: {status}")
                    if status != 'success':
                        logger.warning(f"    Error: {step_result.get('error', 'Unknown error')}")
            
            # AUTO-GENERATE REGRESSION TEST & PAGE OBJECTS FROM CAPTURED WORKFLOW
            if result.get('status') == 'success' and result.get('results'):
                logger.info("\n" + "="*60)
                logger.info("GENERATING PAGE OBJECT MODEL (POM) FIRST")
                logger.info("="*60)
                
                # FIRST: Generate page objects for proper organization
                pom_result = generate_page_objects(result, output_dir='page_objects')
                
                if pom_result.get('status') == 'success':
                    console.print(
                        Panel(
                            Text('✓ Page Objects Generated', style='bold green'),
                            title='[bold cyan]Page Object Model[/bold cyan]',
                            expand=False
                        )
                    )
                    logger.info(f"  Output dir: {pom_result['output_dir']}")
                    logger.info(f"  Pages created: {pom_result['page_count']}")
                    logger.info(f"  Total elements: {pom_result['total_elements']}")
                    logger.info("\n  Generated page objects:")
                    for file_info in pom_result['files']:
                        page_name = file_info['page_name'].replace('_', ' ').title()
                        logger.info(f"    • {page_name} ({file_info['elements']} elements)")
                        for elem_name in file_info['element_names'][:2]:
                            logger.info(f"      - {elem_name}")
                        if len(file_info['element_names']) > 2:
                            logger.info(f"      - ... and {len(file_info['element_names']) - 2} more")
                else:
                    logger.warning(f"  Failed to generate page objects: {pom_result.get('message')}")
                
                # SECOND: Generate test using page objects
                logger.info("\n" + "="*60)
                logger.info("GENERATING PYTEST TEST (USING PAGE OBJECTS)")
                logger.info("="*60)
                
                # Use workflow name as test name (convert to snake_case)
                workflow_name = config_dict.get('name', 'workflow').lower().replace(' ', '_').replace('-', '_')
                
                # Generate deterministic test from captured actions
                gen_result = generate_from_workflow(result, workflow_name, pom_result.get('files', []))
                
                if gen_result.get('status') == 'success':
                    console.print(
                        Panel(
                            Text('✓ Regression Test Generated', style='bold green'),
                            title='[bold cyan]Test Generation[/bold cyan]',
                            expand=False
                        )
                    )
                    logger.info(f"  File: {gen_result['filepath']}")
                    logger.info(f"  Lines: {gen_result['line_count']}")
                    logger.info(f"  Actions captured: {gen_result['action_count']}")
                    logger.info(f"  Uses page objects: YES ✓")
                    logger.info("\n  Test uses:")
                    for page_file in pom_result.get('files', []):
                        class_name = ''.join(word.capitalize() for word in page_file['page_name'].split('_'))
                        logger.info(f"    • {class_name} ({page_file['elements']} elements)")
                else:
                    logger.warning(f"  Failed to generate test: {gen_result.get('message')}")
        else:
            logger.info("\n" + "="*60)
            logger.info("EXECUTING SINGLE PROMPT")
            logger.info("="*60)
            
            prompt = config_dict['prompt']
            logger.info(f"Prompt: {prompt}")
            
            # Merge device config from YAML with environment config
            device_info = config.get_device_info()
            if device_config:
                device_info.update(device_config)
            
            result = orchestrator.execute_prompt(
                prompt=prompt,
                device_info=device_info
            )
            
            logger.info("\n" + "="*60)
            logger.info("PROMPT RESULTS")
            logger.info("="*60)
            logger.info(f"Status: {result.get('status')}")
            
            if result.get('status') == 'success':
                logger.info(f"Actions executed: {len(result.get('actions_executed', []))}")
                for i, action in enumerate(result.get('actions_executed', []), 1):
                    logger.info(f"  {i}. {action.get('tool', 'unknown')}")
            else:
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        logger.info("="*60)
        return result
    
    except Exception as e:
        logger.error(f"✗ Error during execution: {e}")
        return {'status': 'error', 'error': str(e)}
    
    finally:
        logger.info("\nCleaning up...")
        orchestrator.cleanup()
        logger.info("✓ Done")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        logger.error("Usage: python run_yaml.py <yaml_file>")
        logger.error("Example: python run_yaml.py prompts/login-test.yml")
        sys.exit(1)
    
    yaml_file = sys.argv[1]
    
    if not os.path.exists(yaml_file):
        logger.error(f"✗ File not found: {yaml_file}")
        sys.exit(1)
    
    result = execute_from_yaml(yaml_file)
    
    # Exit with appropriate code
    sys.exit(0 if result.get('status') == 'success' else 1)


if __name__ == "__main__":
    main()
