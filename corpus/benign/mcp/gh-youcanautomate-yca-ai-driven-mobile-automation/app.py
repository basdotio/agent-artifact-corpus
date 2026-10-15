"""Main application entry point with examples."""
import sys
import logging
from pathlib import Path
from typing import List
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
# Try multiple locations: script dir, cwd, then home
env_paths = [
    Path(__file__).parent / ".env",  # Script directory
    Path.cwd() / ".env",  # Current working directory
    Path.home() / ".env",  # Home directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        break
else:
    # Fallback: try find_dotenv
    dotenv_file = find_dotenv(raise_error_if_not_found=False)
    if dotenv_file:
        load_dotenv(dotenv_file, override=True)

from orchestrator import MobileAutomationOrchestrator
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_prompt(orchestrator: MobileAutomationOrchestrator, config: Config):
    """Simple example: Take a screenshot."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 1: Basic Screenshot")
    logger.info("="*60)
    
    result = orchestrator.execute_prompt(
        prompt="Take a screenshot of the current screen",
        device_info=config.get_device_info()
    )
    
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Actions executed: {len(result.get('actions_executed', []))}")
    return result


def example_login_workflow(orchestrator: MobileAutomationOrchestrator, config: Config):
    """Multi-step workflow: Login to an app."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 2: Login Workflow")
    logger.info("="*60)
    
    prompts = [
        "Take a screenshot to see the login screen",
        "Find the email input field and enter 'testuser@example.com'",
        "Find the password field and enter 'password123'",
        "Tap the login button",
        "Wait for the home screen to load and take a screenshot"
    ]
    
    result = orchestrator.execute_workflow(
        prompts=prompts,
        device_info=config.get_device_info()
    )
    
    logger.info(f"Workflow status: {result.get('status')}")
    logger.info(f"Steps completed: {result.get('steps_completed')}")
    return result


def example_navigation(orchestrator: MobileAutomationOrchestrator, config: Config):
    """Example: Navigate through app screens."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 3: App Navigation")
    logger.info("="*60)
    
    prompts = [
        "Take a screenshot of the home screen",
        "Find and tap the 'Profile' button in the navigation menu",
        "Scroll down to see all profile options",
        "Take a screenshot of the profile page"
    ]
    
    result = orchestrator.execute_workflow(
        prompts=prompts,
        device_info=config.get_device_info()
    )
    
    logger.info(f"Workflow status: {result.get('status')}")
    return result


def example_element_interaction(orchestrator: MobileAutomationOrchestrator, config: Config):
    """Example: Interact with form elements."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 4: Form Interaction")
    logger.info("="*60)
    
    prompts = [
        "Find the email input field using accessibility ID",
        "Type 'user@example.com' in the email field",
        "Find the password field",
        "Type 'securepassword' in the password field",
        "Find the submit button and tap it",
        "Take a screenshot to verify submission"
    ]
    
    result = orchestrator.execute_workflow(
        prompts=prompts,
        device_info=config.get_device_info()
    )
    
    logger.info(f"Workflow status: {result.get('status')}")
    logger.info(f"Steps completed: {result.get('steps_completed')}/{len(prompts)}")
    return result


def example_with_error_handling(orchestrator: MobileAutomationOrchestrator, config: Config):
    """Example: Handle errors gracefully."""
    logger.info("\n" + "="*60)
    logger.info("EXAMPLE 5: Error Handling")
    logger.info("="*60)
    
    prompts = [
        "Take a screenshot",
        "Find the login button",
        "Click the login button",
        "Wait for the next screen",
        "Take a screenshot"
    ]
    
    result = orchestrator.execute_workflow(
        prompts=prompts,
        device_info=config.get_device_info(),
        stop_on_error=False  # Continue even if there are errors
    )
    
    logger.info(f"Workflow status: {result.get('status')}")
    
    # Check for errors in any step
    for i, step_result in enumerate(result.get('results', [])):
        if step_result.get('status') != 'success':
            logger.warning(f"Step {i+1} failed: {step_result.get('error', 'Unknown error')}")
    
    return result


def example_custom_prompt(orchestrator: MobileAutomationOrchestrator, config: Config, prompt: str):
    """Execute a custom prompt."""
    logger.info("\n" + "="*60)
    logger.info(f"CUSTOM PROMPT: {prompt}")
    logger.info("="*60)
    
    result = orchestrator.execute_prompt(
        prompt=prompt,
        device_info=config.get_device_info()
    )
    
    logger.info(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        logger.info(f"Actions executed: {len(result.get('actions_executed', []))}")
    else:
        logger.error(f"Error: {result.get('error', 'Unknown error')}")
    
    return result


def main():
    """Main entry point."""
    logger.info("Mobile Automation Orchestrator - AI-Driven Testing")
    logger.info("=" * 60)
    
    # Check if AWS credentials are set
    import os
    if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
        logger.error("✗ AWS credentials not configured")
        logger.error("  Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        sys.exit(1)
    
    # Initialize config
    logger.info("Initializing configuration...")
    config = Config(platform="ios")  # Change to "android" for Android testing
    config.validate()
    logger.info(f"✓ Platform: {config.platform}")
    
    # Initialize orchestrator
    logger.info("Initializing orchestrator...")
    try:
        orchestrator = MobileAutomationOrchestrator(
            platform=config.platform,
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
        # Interactive menu
        examples = {
            "1": ("Basic Screenshot", lambda: example_basic_prompt(orchestrator, config)),
            "2": ("Login Workflow", lambda: example_login_workflow(orchestrator, config)),
            "3": ("App Navigation", lambda: example_navigation(orchestrator, config)),
            "4": ("Form Interaction", lambda: example_element_interaction(orchestrator, config)),
            "5": ("Error Handling", lambda: example_with_error_handling(orchestrator, config)),
            "6": ("Custom Prompt", None)
        }
        
        while True:
            logger.info("\n" + "="*60)
            logger.info("Available Examples:")
            for key, (name, _) in examples.items():
                logger.info(f"  {key}. {name}")
            logger.info("  0. Exit")
            logger.info("="*60)
            
            choice = input("\nSelect example (0-6): ").strip()
            
            if choice == "0":
                logger.info("Exiting...")
                break
            
            if choice == "6":
                prompt = input("Enter your prompt: ").strip()
                if prompt:
                    example_custom_prompt(orchestrator, config, prompt)
            elif choice in examples:
                name, func = examples[choice]
                if func:
                    try:
                        func()
                    except Exception as e:
                        logger.error(f"Example failed: {e}")
                else:
                    logger.info("This example requires custom input")
            else:
                logger.warning("Invalid choice")
    
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        logger.info("Cleaning up...")
        orchestrator.cleanup()
        logger.info("✓ Done")


if __name__ == "__main__":
    main()
