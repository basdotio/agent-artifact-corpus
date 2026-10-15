"""
Mobile App Testing Chatbot
- Explore app and generate page objects from YAML prompts
- Generate test scripts from page objects
- Run generated test scripts
"""
import os
import json
import logging
import subprocess
from typing import Dict, List, Any, Optional
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.logging import RichHandler
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, show_time=False, omit_repeated_times=True)]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# CRITICAL: Must happen before orchestrator import
import sys
if "pytest" not in sys.modules:  # Skip in test environments
    env_paths = [
        Path(__file__).parent / ".env",  # Script directory  
        Path.cwd() / ".env",  # Current working directory
        Path.home() / ".env",  # Home directory
        Path(__file__).parent.parent / ".env",  # Parent directory (for installed packages)
    ]
    
    loaded = False
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path, override=True)
            loaded = True
            # Print to stderr to avoid interfering with normal output
            sys.stderr.write(f"[chatbot] Loaded .env from: {env_path}\n")
            if os.getenv("BEDROCK_MODEL_ID"):
                sys.stderr.write(f"[chatbot] BEDROCK_MODEL_ID found\n")
            break
    
    if not loaded:
        # Fallback: try find_dotenv
        dotenv_file = find_dotenv(raise_error_if_not_found=False)
        if dotenv_file:
            load_dotenv(dotenv_file, override=True)
            sys.stderr.write(f"[chatbot] Loaded .env via find_dotenv: {dotenv_file}\n")


from config import Config
from orchestrator import MobileAutomationOrchestrator
from generate_page_objects import generate_page_objects
from chatbot_page_object_orchestrator import validate_and_save_page_objects
from generate_regression_test import generate_from_workflow


class MobileAppTestingChatbot:
    """Chatbot for YAML-driven app testing and page object generation."""
    
    def __init__(self):
        """Initialize chatbot."""
        self.console = Console()
        self.config = Config()
        self.orchestrator = None
        self.workflow_results = None
        self.prompts_file = None
        self.platform_version = None
        self.generated_page_objects_dir = "page_objects"
        self.generated_tests_dir = "generated_tests"
        self.page_object_files = None  # Store metadata from page generation
        
    def welcome(self):
        """Display welcome message."""
        self.console.print(Panel(
            "[bold cyan]📱 Mobile App Testing Chatbot[/bold cyan]\n"
            "[yellow]YAML-Driven Workflow[/yellow]\n\n"
            "[cyan]Option 1:[/cyan] Explore app & generate page objects\n"
            "[cyan]Option 2:[/cyan] Generate test scripts\n"
            "[cyan]Option 3:[/cyan] Run generated tests",
            expand=False
        ))
        
    def setup_app_connection(self) -> bool:
        """Setup connection to app."""
        self.console.print("\n[bold]🔧 Setting up app connection...[/bold]")
        
        # Get platform
        platform = Prompt.ask(
            "[cyan]Select platform[/cyan]",
            choices=["ios", "android"],
            default="ios"
        )
        
        # Get platform version
        if platform == "ios":
            platform_version = Prompt.ask(
                "[cyan]iOS version[/cyan]",
                default="18.0"
            )
            device_name = Prompt.ask("[cyan]Device name[/cyan]", default="iPhone 16")
            bundle_id = Prompt.ask("[cyan]Bundle ID[/cyan]", default="com.example.ecommerce")
        else:
            platform_version = Prompt.ask(
                "[cyan]Android version[/cyan]",
                default="13.0"
            )
            device_name = Prompt.ask("[cyan]Device name/ID[/cyan]", default="emulator-5554")
            bundle_id = Prompt.ask("[cyan]App package[/cyan]", default="com.example.ecommerce")
        
        # Update config with user input
        self.config = Config(platform=platform)
        if platform == "ios":
            self.config.appium.device_name = device_name
            self.config.appium.bundle_id = bundle_id
        else:
            self.config.appium.device_id = device_name
            self.config.appium.app_package = bundle_id
        
        # Store platform version for capabilities
        self.platform_version = platform_version
        
        # Initialize orchestrator (without config parameter)
        try:
            self.orchestrator = MobileAutomationOrchestrator(
                platform=platform,
                bedrock_region=self.config.bedrock.region,
                debug=self.config.automation.debug
            )
            self.console.print("[green]✓ App connection established[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]✗ Failed to connect: {e}[/red]")
            return False
    
    def get_prompts_file(self) -> str:
        """Get YAML file path from user."""
        self.console.print("\n[bold]📁 Select Prompts YAML File[/bold]")
        
        # List available YAML files
        prompts_dir = Path("prompts")
        yaml_files = list(prompts_dir.glob("*.yml")) + list(prompts_dir.glob("*.yaml"))
        
        if not yaml_files:
            self.console.print("[red]✗ No YAML files found in prompts/ directory[/red]")
            return None
        
        self.console.print(f"\n[yellow]Available YAML files:[/yellow]")
        for idx, file in enumerate(yaml_files, 1):
            self.console.print(f"  {idx}. {file.name}")
        
        choice = Prompt.ask("[cyan]Select file[/cyan]", choices=[str(i) for i in range(1, len(yaml_files) + 1)])
        selected_file = yaml_files[int(choice) - 1]
        self.console.print(f"[green]✓ Selected: {selected_file}[/green]")
        return str(selected_file)
    
    def load_yaml_workflow(self, file_path: str) -> Optional[List[str]]:
        """Load prompts from YAML file with screen markers embedded."""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            # Extract prompts list
            if isinstance(data, dict):
                if 'prompts' in data:
                    # Simple list format: prompts: [...]
                    return data['prompts']
                elif 'workflow' in data:
                    # Workflow format can be:
                    # 1. workflow: {screen1: [prompts], screen2: [prompts]}
                    # 2. workflow: [{prompt: ...}, {prompt: ...}]
                    workflow = data['workflow']
                    
                    if isinstance(workflow, dict):
                        # Dict format: screen-based workflow
                        # Inject screen markers into prompts for page object generation
                        prompts = []
                        for screen_name, screen_prompts in workflow.items():
                            # Add screen marker as display marker (will be skipped during execution)
                            prompts.append(f"📍 [SCREEN: {screen_name}]")
                            
                            if isinstance(screen_prompts, list):
                                # Convert screen name to clean format
                                # "LoginScreen" -> "login screen"
                                # "ProductDetailsScreen" -> "product details screen"
                                clean_screen = self._convert_to_screen_label(screen_name)
                                
                                # Inject "screen: xxx" into first prompt of each screen
                                for i, prompt in enumerate(screen_prompts):
                                    if i == 0:
                                        # Prepend screen marker to first prompt for detection
                                        enhanced_prompt = f"[screen: {clean_screen}] {prompt}"
                                        prompts.append(enhanced_prompt)
                                    else:
                                        prompts.append(prompt)
                        return prompts if prompts else None
                    elif isinstance(workflow, list):
                        # List format: extract prompts from dicts or strings
                        prompts = []
                        for item in workflow:
                            if isinstance(item, dict) and 'prompt' in item:
                                prompts.append(item['prompt'])
                            elif isinstance(item, str):
                                prompts.append(item)
                        return prompts if prompts else None
            elif isinstance(data, list):
                return data
            
            return None
        except Exception as e:
            self.console.print(f"[red]✗ Failed to load YAML: {e}[/red]")
            return None
    
    def _convert_to_screen_label(self, screen_name: str) -> str:
        """Convert CamelCase screen names to lowercase labels.
        
        Examples:
        - "LoginScreen" -> "login screen"
        - "HomeScreen" -> "home screen"
        - "ProductDetailsScreen" -> "product details screen"
        """
        import re
        # Insert space before uppercase letters
        label = re.sub(r'([a-z])([A-Z])', r'\1 \2', screen_name)
        # Remove 'Screen' suffix if present
        if label.endswith(' Screen') or label.endswith('Screen'):
            label = label.replace(' Screen', '').replace('Screen', '')
        return label.lower().strip()
    
    def option_explore(self) -> bool:
        """Option 1: Explore app and generate page objects."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]OPTION 1: EXPLORE & GENERATE PAGE OBJECTS[/bold cyan]")
        self.console.print("="*60)
        
        # Get YAML file
        yaml_file = self.get_prompts_file()
        if not yaml_file:
            return False
        
        self.prompts_file = yaml_file
        
        # Load prompts
        prompts = self.load_yaml_workflow(yaml_file)
        if not prompts:
            self.console.print("[red]✗ No prompts found in YAML file[/red]")
            return False
        
        self.console.print(f"\n[yellow]Loaded {len(prompts)} prompts[/yellow]")
        
        # Initialize workflow results
        self.workflow_results = {'results': []}
        
        # Execute each prompt
        for idx, prompt in enumerate(prompts, 1):
            # Skip screen display markers
            if prompt.startswith('📍 [SCREEN:'):
                self.console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
                continue
            
            # Extract the actual prompt text for display (removing [screen: xxx] prefix if present)
            display_prompt = prompt
            if prompt.startswith('[screen:'):
                # Extract the part after the screen marker for display
                parts = prompt.split(']', 1)
                if len(parts) > 1:
                    display_prompt = parts[1].strip()
                    # Extract screen name for tracking
                    screen_marker = parts[0][1:]  # Remove leading '['
            
            self.console.print(f"\n[cyan]Prompt #{idx}:[/cyan] {display_prompt[:80]}{'...' if len(display_prompt) > 80 else ''}")
            
            try:
                # Build device info
                device_info = self._build_device_info()
                
                # Execute prompt (send with screen marker for page object generation)
                result = self.orchestrator.execute_prompt(
                    prompt=prompt,  # Keep original prompt with screen marker
                    device_info=device_info,
                    execution_history=self.workflow_results['results']
                )
                
                self.workflow_results['results'].append(result)
                actions_count = len(result.get('actions_executed', []))
                self.console.print(f"[green]✓ Step completed ({actions_count} actions)[/green]")
                
            except Exception as e:
                self.console.print(f"[red]✗ Error: {str(e)}[/red]")
        
        # Generate page objects with automatic validation
        self.console.print("\n[bold]📄 Generating Page Objects with Automatic Validation...[/bold]")
        try:
            stats = validate_and_save_page_objects(
                self.workflow_results,
                output_dir=self.generated_page_objects_dir,
                appium_url=self.config.automation.appium_url,
                skip_validation=False  # Enable automatic validation
            )
            
            if stats.get('status') == 'error':
                self.console.print(f"[red]✗ {stats.get('message', 'Unknown error')}[/red]")
                return False
            
            # Store page object metadata for later use in test generation
            self.page_object_files = stats.get('files', [])
            
            self.console.print(f"[green]✓ Generated {len(self.page_object_files)} page objects[/green]")
            
            if stats.get('validation_enabled'):
                verified = stats.get('total_verified', 0)
                unverified = stats.get('total_unverified', 0)
                self.console.print(f"[green]✓ Verified {verified} locators[/green]")
                if unverified > 0:
                    self.console.print(f"[yellow]⚠ {unverified} unverified locators removed[/yellow]")
            
            return stats.get('status') != 'error'
            
        except Exception as e:
            self.console.print(f"[red]✗ Failed to generate page objects: {e}[/red]")
            return False
    
    def option_generate_tests(self) -> bool:
        """Option 2: Execute workflow & generate tests with page objects."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]OPTION 2: EXECUTE & GENERATE TEST SCRIPTS[/bold cyan]")
        self.console.print("="*60)
        
        # Select YAML file
        yaml_file = self.get_prompts_file()
        if not yaml_file:
            return False
        
        # Execute prompts from YAML to capture real workflow
        if not self._execute_workflow_for_tests(yaml_file):
            return False
        
        # Generate page objects from workflow
        if not self._generate_page_objects_for_tests():
            return False
        
        # Generate tests using page objects
        if not self._generate_regression_test_from_workflow():
            return False
        
        return True
    
    def _execute_workflow_for_tests(self, yaml_file: str) -> bool:
        """Execute workflow prompts on app to capture real actions."""
        self.console.print("\n[bold]🚀 Executing workflow on app...[/bold]")
        
        try:
            # Load prompts
            prompts = self.load_yaml_workflow(yaml_file)
            if not prompts:
                self.console.print("[red]✗ No prompts found in YAML file[/red]")
                return False
            
            self.console.print(f"[yellow]Loaded {len(prompts)} prompts[/yellow]")
            
            # Initialize workflow results
            self.workflow_results = {'results': []}
            self.prompts_file = yaml_file
            
            # Execute each prompt
            for idx, prompt in enumerate(prompts, 1):
                # Skip screen display markers
                if prompt.startswith('📍 [SCREEN:'):
                    self.console.print(f"\n[bold cyan]{prompt}[/bold cyan]")
                    continue
                
                # Extract display prompt
                display_prompt = prompt
                if prompt.startswith('[screen:'):
                    parts = prompt.split(']', 1)
                    if len(parts) > 1:
                        display_prompt = parts[1].strip()
                
                self.console.print(f"\n[cyan]Prompt #{idx}:[/cyan] {display_prompt[:80]}{'...' if len(display_prompt) > 80 else ''}")
                
                try:
                    # Build device info
                    device_info = self._build_device_info()
                    
                    # Execute prompt
                    result = self.orchestrator.execute_prompt(
                        prompt=prompt,
                        device_info=device_info,
                        execution_history=self.workflow_results['results']
                    )
                    
                    self.workflow_results['results'].append(result)
                    actions_count = len(result.get('actions_executed', []))
                    
                    # Show action details
                    self.console.print(f"[green]✓ Step completed ({actions_count} actions)[/green]")
                    
                    # Display each action briefly
                    if actions_count > 0:
                        for action in result.get('actions_executed', []):
                            tool = action.get('tool', 'unknown')
                            action_result = action.get('result', {})
                            status = action_result.get('status', 'unknown')
                            
                            status_icon = "✓" if status == "success" else "✗"
                            status_color = "green" if status == "success" else "red"
                            
                            # Format action display
                            if tool == 'appium_set_value':
                                text = action_result.get('text', '')[:20]
                                self.console.print(f"  {status_icon} [{status_color}]{tool}[/{status_color}] input: '{text}'")
                            elif tool == 'appium_click':
                                self.console.print(f"  {status_icon} [{status_color}]{tool}[/{status_color}]")
                            elif tool == 'appium_find_element':
                                strategy = action_result.get('strategy', 'unknown')
                                self.console.print(f"  {status_icon} [{status_color}]{tool}[/{status_color}] {strategy}")
                            else:
                                self.console.print(f"  {status_icon} [{status_color}]{tool}[/{status_color}]")
                    
                except Exception as e:
                    self.console.print(f"[red]✗ Error: {str(e)}[/red]")
            
            self.console.print(f"\n[green]✓ Workflow execution complete: {len(self.workflow_results['results'])} steps[/green]")
            
            # Display detailed execution summary
            self._display_workflow_execution_summary()
            
            return True
            
        except Exception as e:
            self.console.print(f"[red]✗ Failed to execute workflow: {e}[/red]")
            return False
    
    def _display_workflow_execution_summary(self) -> None:
        """Display summary of captured actions from workflow execution."""
        if not self.workflow_results or not self.workflow_results.get('results'):
            return
        
        # Aggregate statistics
        total_steps = len(self.workflow_results['results'])
        total_actions = 0
        actions_by_type = {}
        failed_actions = 0
        
        for step_result in self.workflow_results['results']:
            actions = step_result.get('actions_executed', [])
            total_actions += len(actions)
            
            for action in actions:
                tool = action.get('tool', 'unknown')
                action_result = action.get('result', {})
                status = action_result.get('status', 'unknown')
                
                key = f"{tool}:{status}"
                actions_by_type[key] = actions_by_type.get(key, 0) + 1
                
                if status != 'success':
                    failed_actions += 1
        
        # Display summary
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]WORKFLOW EXECUTION SUMMARY[/bold cyan]")
        self.console.print("="*60)
        self.console.print(f"[yellow]Prompts executed:[/yellow] {total_steps}")
        self.console.print(f"[yellow]Total actions captured:[/yellow] {total_actions}")
        
        if total_actions > 0:
            self.console.print("\n[bold]Actions breakdown:[/bold]")
            for key, count in sorted(actions_by_type.items()):
                tool, status = key.split(':')
                status_icon = "✓" if status == "success" else "✗"
                self.console.print(f"  {status_icon} {tool} ({status}): {count}")
        
        if failed_actions > 0:
            self.console.print(f"\n[yellow]⚠ {failed_actions} actions failed - check logs for details[/yellow]")
        
        self.console.print("="*60)
    
    def _generate_page_objects_for_tests(self) -> bool:
        """Generate page objects from captured workflow with automatic validation."""
        self.console.print("\n[bold]📄 Generating Page Objects with Automatic Validation...[/bold]")
        
        try:
            # Use validation-enabled version that automatically validates locators
            stats = validate_and_save_page_objects(
                self.workflow_results,
                output_dir=self.generated_page_objects_dir,
                appium_url=self.config.automation.appium_url,
                skip_validation=False  # Enable automatic validation
            )
            
            if stats.get('status') == 'error':
                self.console.print(f"[red]✗ {stats.get('message', 'Unknown error')}[/red]")
                return False
            
            # Store page object metadata for test generation
            self.page_object_files = stats.get('files', [])
            
            # Display results
            page_count = len(self.page_object_files)
            self.console.print(f"[green]✓ Generated {page_count} page objects[/green]")
            
            if stats.get('validation_enabled'):
                total_elements = sum(f.get('total_elements', 0) for f in self.page_object_files)
                verified = stats.get('total_verified', 0)
                unverified = stats.get('total_unverified', 0)
                
                self.console.print(f"[green]✓ Captured {total_elements} elements[/green]")
                self.console.print(f"[green]✓ Verified {verified} locators[/green]")
                
                if unverified > 0:
                    self.console.print(f"[yellow]⚠ {unverified} unverified locators were removed[/yellow]")
                    self.console.print("[dim]  (These locators did not match real app elements)[/dim]")
            else:
                total_elements = sum(f.get('elements', 0) for f in self.page_object_files)
                self.console.print(f"[yellow]⚠ Captured {total_elements} elements (validation disabled)[/yellow]")
            
            return stats.get('status') != 'error'
            
        except Exception as e:
            self.console.print(f"[red]✗ Failed to generate page objects: {e}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return False
    
    def _generate_regression_test_from_workflow(self) -> bool:
        """Generate regression test from captured workflow using page objects."""
        self.console.print("\n[bold]📝 Generating test script...[/bold]")
        
        try:
            # Extract action flow to show what will be in test
            from generate_regression_test import extract_action_flow
            action_flow = extract_action_flow(self.workflow_results)
            
            # Display detailed action breakdown
            self.console.print(f"[cyan]Extracted {len(action_flow)} test actions:[/cyan]")
            if action_flow:
                for i, action in enumerate(action_flow, 1):
                    action_type = action.get('action', 'unknown').upper()
                    description = action.get('step_description', 'No description')
                    selector = action.get('selector', '')[:40]
                    text = action.get('text', '')
                    
                    # Format output based on action type
                    if action_type == 'SET_VALUE':
                        self.console.print(f"  {i}. [{action_type}] {description} = '{text}'")
                    else:
                        self.console.print(f"  {i}. [{action_type}] {description}")
            else:
                self.console.print("[yellow]  ⚠ No actions extracted. Check if prompts executed successfully.[/yellow]")
            
            page_object_files = self.page_object_files
            
            if page_object_files:
                self.console.print(f"[cyan]Using {len(page_object_files)} page object(s)[/cyan]")
            
            # Generate test with descriptive name
            test_name = "workflow_test"
            if self.prompts_file:
                test_name = Path(self.prompts_file).stem
            
            stats = generate_from_workflow(
                workflow_results=self.workflow_results,
                test_name=test_name,
                page_object_files=page_object_files,
                output_dir=self.generated_tests_dir
            )
            
            if stats.get('status') == 'error':
                self.console.print(f"[red]✗ {stats.get('message', 'Unknown error')}[/red]")
                return False
            
            test_file = stats.get('test_file', stats.get('filename', 'Unknown'))
            self.console.print(f"[green]✓ Test script generated: {test_file}[/green]")
            self.console.print(f"[green]✓ {stats.get('test_count', stats.get('action_count', 0))} test cases created[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]✗ Failed to generate test: {e}[/red]")
            return False
    
    def option_run_tests(self) -> bool:
        """Option 3: Run generated test scripts."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]OPTION 3: RUN TEST SCRIPTS[/bold cyan]")
        self.console.print("="*60)
        
        # Find generated test files
        tests_dir = Path(self.generated_tests_dir)
        if not tests_dir.exists():
            self.console.print(f"[red]✗ Tests directory not found: {self.generated_tests_dir}[/red]")
            return False
        
        test_files = list(tests_dir.glob("test_*.py"))
        if not test_files:
            self.console.print("[red]✗ No test files found[/red]")
            return False
        
        self.console.print(f"\n[yellow]Available tests:[/yellow]")
        for idx, file in enumerate(test_files, 1):
            self.console.print(f"  {idx}. {file.name}")
        
        choice = Prompt.ask("[cyan]Select test to run[/cyan]", choices=[str(i) for i in range(1, len(test_files) + 1)])
        selected_test = test_files[int(choice) - 1]
        
        self.console.print(f"\n[bold]Running: {selected_test.name}[/bold]")
        
        try:
            # Run pytest on the selected test
            result = subprocess.run(
                ["python", "-m", "pytest", str(selected_test), "-v"],
                capture_output=True,
                text=True
            )
            
            self.console.print(result.stdout)
            if result.stderr:
                self.console.print(f"[yellow]{result.stderr}[/yellow]")
            
            if result.returncode == 0:
                self.console.print(f"[green]✓ Tests passed[/green]")
                return True
            else:
                self.console.print(f"[yellow]⚠ Tests completed with issues[/yellow]")
                return False
                
        except Exception as e:
            self.console.print(f"[red]✗ Failed to run tests: {e}[/red]")
            return False
    
    def _build_device_info(self) -> Dict[str, Any]:
        """Build device info from config."""
        if self.config.platform == "ios":
            return {
                "device_name": self.config.appium.device_name,
                "bundle_id": self.config.appium.bundle_id,
                "platform_version": self.platform_version
            }
        else:
            return {
                "device_id": self.config.appium.device_id,
                "app_package": self.config.appium.app_package,
                "app_activity": self.config.appium.app_activity,
                "platform_version": self.platform_version
            }
    
    def show_summary(self):
        """Show execution summary."""
        self.console.print("\n" + "="*60)
        self.console.print("[bold cyan]📊 SUMMARY[/bold cyan]")
        self.console.print("="*60)
        
        if self.workflow_results and self.workflow_results.get('results'):
            steps = len(self.workflow_results['results'])
            self.console.print(f"[green]✓ Workflow Steps:[/green] {steps}")
        
        if Path(self.generated_page_objects_dir).exists():
            page_files = list(Path(self.generated_page_objects_dir).glob("*.py"))
            if page_files:
                self.console.print(f"[green]✓ Page Objects:[/green] {len(page_files)} files")
        
        if Path(self.generated_tests_dir).exists():
            test_files = list(Path(self.generated_tests_dir).glob("test_*.py"))
            if test_files:
                self.console.print(f"[green]✓ Test Scripts:[/green] {len(test_files)} files")
    
    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
    
    def run(self):
        """Main chatbot loop."""
        self.welcome()
        
        # Setup
        if not self.setup_app_connection():
            return
        
        # Main menu
        while True:
            self.console.print("\n[bold cyan]═══ MAIN MENU ═══[/bold cyan]")
            self.console.print("  [cyan]1[/cyan] - Explore & Generate Page Objects")
            self.console.print("  [cyan]2[/cyan] - Generate Test Scripts")
            self.console.print("  [cyan]3[/cyan] - Run Tests")
            self.console.print("  [cyan]4[/cyan] - Exit")
            
            choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3", "4"])
            
            if choice == "1":
                if self.option_explore():
                    self.console.print("[green]✓ Page objects generated successfully[/green]")
            elif choice == "2":
                if self.option_generate_tests():
                    self.console.print("[green]✓ Test scripts generated successfully[/green]")
            elif choice == "3":
                if self.option_run_tests():
                    self.console.print("[green]✓ Tests executed successfully[/green]")
            elif choice == "4":
                self.console.print("[yellow]Goodbye![/yellow]")
                self.show_summary()
                self.cleanup()
                break


def main():
    """Run chatbot."""
    chatbot = MobileAppTestingChatbot()
    try:
        chatbot.run()
    except KeyboardInterrupt:
        chatbot.console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        chatbot.cleanup()
    except Exception as e:
        logger.error(f"Chatbot error: {e}", exc_info=True)
        chatbot.cleanup()


if __name__ == "__main__":
    main()
