"""YAML configuration loader for prompts and test scenarios."""
import os
import sys
import yaml
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def load_yaml(file_path: str) -> Dict[str, Any]:
    """Load YAML file and return configuration."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise ValueError("YAML file is empty")
        
        logger.info(f"✓ Loaded YAML configuration from {file_path}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"✗ YAML parsing error: {e}")
        raise
    except Exception as e:
        logger.error(f"✗ Error loading YAML file: {e}")
        raise


def validate_single_prompt_config(config: Dict[str, Any]) -> bool:
    """Validate single prompt configuration."""
    required_fields = ['prompt']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    return True


def validate_workflow_config(config: Dict[str, Any]) -> bool:
    """Validate workflow configuration.
    
    Supports two formats:
    1. Direct prompts list: prompts: [...]
    2. Screen-based workflows: workflow: {screen_name: [prompt1, prompt2, ...]}
    """
    # Check for screen-based workflow format
    if 'workflow' in config:
        if not isinstance(config['workflow'], dict):
            raise ValueError("'workflow' must be a dict")
        if len(config['workflow']) == 0:
            raise ValueError("'workflow' dict cannot be empty")
        return True
    
    # Check for direct prompts list format  
    required_fields = ['prompts']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field} or 'workflow'")
    
    if not isinstance(config['prompts'], list):
        raise ValueError("'prompts' must be a list")
    
    if len(config['prompts']) == 0:
        raise ValueError("'prompts' list cannot be empty")
    
    return True


def is_workflow(config: Dict[str, Any]) -> bool:
    """Check if config is a workflow (multiple prompts) or single prompt.
    
    Detects:
    1. Screen-based workflow: 'workflow' field present
    2. Prompts list workflow: 'prompts' field present (list)
    3. Single prompt: 'prompt' field present
    """
    if 'workflow' in config:
        return True
    if 'prompts' in config and isinstance(config.get('prompts'), list):
        return True
    return False


def get_platform(config: Dict[str, Any], default: str = "ios") -> str:
    """Extract platform from config."""
    return config.get('platform', default).lower()


def get_platform_from_config(config: Dict[str, Any], default: str = "ios") -> str:
    """Extract platform from config (supports nested structure)."""
    if 'platform' in config:
        return config['platform'].lower()
    
    if 'config' in config and isinstance(config['config'], dict):
        if 'platform' in config['config']:
            return config['config']['platform'].lower()
    
    return default


def get_device_config(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract device configuration."""
    if 'device' in config:
        return config['device']
    
    if 'config' in config and isinstance(config['config'], dict):
        if 'device' in config['config']:
            return config['config']['device']
    
    return None


def get_description(config: Dict[str, Any]) -> str:
    """Extract description from config."""
    return config.get('description', 'No description provided')


def get_tags(config: Dict[str, Any]) -> List[str]:
    """Extract tags from config."""
    tags = config.get('tags', [])
    if isinstance(tags, str):
        return [tags]
    return tags if isinstance(tags, list) else []


def get_timeout(config: Dict[str, Any], default: int = 30) -> int:
    """Extract timeout from config."""
    timeout = config.get('timeout', default)
    
    if 'config' in config and isinstance(config['config'], dict):
        timeout = config['config'].get('timeout', timeout)
    
    return int(timeout)


def get_stop_on_error(config: Dict[str, Any], default: bool = True) -> bool:
    """Extract stop_on_error setting from config."""
    stop = config.get('stop_on_error', default)
    
    if 'config' in config and isinstance(config['config'], dict):
        stop = config['config'].get('stop_on_error', stop)
    
    return bool(stop)


def print_config_summary(config: Dict[str, Any]) -> None:
    """Print a summary of the configuration."""
    logger.info("\n" + "="*60)
    logger.info("CONFIGURATION SUMMARY")
    logger.info("="*60)
    
    # Name
    if 'name' in config:
        logger.info(f"Name: {config['name']}")
    
    # Description
    if 'description' in config:
        logger.info(f"Description: {config['description']}")
    
    # Platform
    platform = get_platform_from_config(config)
    logger.info(f"Platform: {platform}")
    
    # Type
    if is_workflow(config):
        if 'workflow' in config:
            # Screen-based workflow
            num_screens = len(config['workflow'])
            total_prompts = sum(len(screen_prompts) if isinstance(screen_prompts, list) else 1 
                              for screen_prompts in config['workflow'].values())
            logger.info(f"Type: Screen-based Workflow ({num_screens} screens, {total_prompts} prompts)")
        else:
            # Direct prompts list
            logger.info(f"Type: Workflow ({len(config['prompts'])} steps)")
    else:
        logger.info("Type: Single Prompt")
    
    # Tags
    tags = get_tags(config)
    if tags:
        logger.info(f"Tags: {', '.join(tags)}")
    
    # Timeout
    timeout = get_timeout(config)
    logger.info(f"Timeout: {timeout}s")
    
    # Stop on error
    stop_on_error = get_stop_on_error(config)
    logger.info(f"Stop on error: {stop_on_error}")
    
    logger.info("="*60 + "\n")
