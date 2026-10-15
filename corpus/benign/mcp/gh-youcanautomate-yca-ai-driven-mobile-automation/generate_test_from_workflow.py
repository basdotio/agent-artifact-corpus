#!/usr/bin/env python3
"""Generate test script from workflow execution."""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

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

from mcp_client import MCPClient
from tools_test_generation import appium_generate_tests
from rich.console import Console
from rich.panel import Panel

console = Console()


def generate_test_from_workflow(test_name: str = None, actions: list = None):
    """Generate a test script from workflow actions."""
    
    if not test_name:
        test_name = f"Generated_Test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if not actions:
        console.print("[red]❌ Error: No actions provided[/red]")
        return None
    
    console.print()
    console.print(Panel(
        f"[bold cyan]📝 Generating Test Script[/bold cyan]\n\nTest Name: {test_name}\nActions: {len(actions)}",
        border_style="cyan",
        expand=False
    ))
    
    try:
        result = appium_generate_tests(test_name, actions)
        
        if result.get('status') == 'success':
            test_code = result.get('test_code')
            
            # Create tests directory if it doesn't exist
            tests_dir = 'generated_tests'
            if not os.path.exists(tests_dir):
                os.makedirs(tests_dir)
            
            # Save test file
            test_filename = f"{tests_dir}/test_{test_name.lower().replace(' ', '_')}.py"
            with open(test_filename, 'w') as f:
                f.write(test_code)
            
            console.print()
            console.print(Panel(
                f"[bold green]✓ Test Script Generated Successfully[/bold green]\n\n[cyan]File:[/cyan] {test_filename}\n[cyan]Lines:[/cyan] {len(test_code.splitlines())}\n[cyan]Actions:[/cyan] {len(actions)}",
                border_style="green",
                expand=False
            ))
            
            # Print preview
            console.print("\n[bold]Preview:[/bold]")
            console.print("[dim]" + "\n".join(test_code.splitlines()[:30]) + "[/dim]")
            if len(test_code.splitlines()) > 30:
                console.print("[dim]... (truncated) ...[/dim]")
            
            return test_filename
        else:
            console.print(f"[red]❌ Error: {result.get('message', 'Unknown error')}[/red]")
            return None
            
    except Exception as e:
        console.print(f"[red]❌ Exception: {e}[/red]")
        return None


def demo_test_generation():
    """Generate a sample test from demo actions."""
    
    # Sample actions from a typical workflow
    sample_actions = [
        {
            'type': 'screenshot',
            'tool': 'appium_screenshot',
            'elementUUID': None,
            'status': 'success'
        },
        {
            'type': 'find',
            'tool': 'appium_find_element',
            'strategy': 'xpath',
            'selector': '//XCUIElementTypeTextField[@value="Email"]',
            'elementUUID': '11000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'click',
            'tool': 'appium_click',
            'elementUUID': '11000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'setText',
            'tool': 'appium_set_value',
            'elementUUID': '11000000-0000-0000-459B-000000000000',
            'value': 'youcanautomate@gmail.com',
            'status': 'success'
        },
        {
            'type': 'find',
            'tool': 'appium_find_element',
            'strategy': 'xpath',
            'selector': '//XCUIElementTypeSecureTextField[@value="Password"]',
            'elementUUID': '22000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'click',
            'tool': 'appium_click',
            'elementUUID': '22000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'setText',
            'tool': 'appium_set_value',
            'elementUUID': '22000000-0000-0000-459B-000000000000',
            'value': 'Test123',
            'status': 'success'
        },
        {
            'type': 'find',
            'tool': 'appium_find_element',
            'strategy': 'xpath',
            'selector': '//XCUIElementTypeButton[@name="Sign In"]',
            'elementUUID': '33000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'click',
            'tool': 'appium_click',
            'elementUUID': '33000000-0000-0000-459B-000000000000',
            'status': 'success'
        },
        {
            'type': 'screenshot',
            'tool': 'appium_screenshot',
            'elementUUID': None,
            'status': 'success'
        }
    ]
    
    return generate_test_from_workflow("LoginWorkflow", sample_actions)


if __name__ == "__main__":
    console.print()
    console.print(Panel(
        "[bold cyan]🧪 Test Script Generator[/bold cyan]",
        border_style="cyan",
        expand=False
    ))
    
    if len(sys.argv) > 1:
        # Load actions from JSON file if provided
        json_file = sys.argv[1]
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            test_name = data.get('name', 'GeneratedTest')
            actions = data.get('actions', [])
            generate_test_from_workflow(test_name, actions)
        except FileNotFoundError:
            console.print(f"[red]❌ File not found: {json_file}[/red]")
        except json.JSONDecodeError:
            console.print(f"[red]❌ Invalid JSON file: {json_file}[/red]")
    else:
        # Run demo
        console.print("[yellow]ℹ️  Usage: python generate_test_from_workflow.py <actions.json>[/yellow]")
        console.print("[yellow]Running demo with sample actions...[/yellow]")
        demo_test_generation()
