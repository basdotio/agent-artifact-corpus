#!/usr/bin/env python3
"""
Garak LLM Vulnerability Scanner
Standalone script for scanning Ollama models with all vulnerability probes.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from typing import Optional
import requests
from src.utils import get_terminal_commands_output


class GarakScanner:
    """Scanner for running Garak vulnerability tests on LLM models."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.ollama_api_url = "http://localhost:11434/api/tags"

    def check_ollama_running(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(self.ollama_api_url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_ollama_models(self) -> list[str]:
        """Get list of available Ollama models."""
        try:
            response = requests.get(self.ollama_api_url)
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Ollama models: {e}")
            return []

    def create_ollama_config(self, model_name: str) -> str:
        """Create temporary config file for Ollama model."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ollama.json')

        with open(config_path, 'r') as f:
            config = json.load(f)

        config['rest']['RestGenerator']['req_template_json_object']['model'] = model_name

        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(config, temp_file)
        temp_file.close()

        return temp_file.name

    def run_scan(self, model_name: str, probes: Optional[str] = None,
                 parallel_attempts: int = 1, verbose: bool = True) -> str:
        """
        Run Garak vulnerability scan on specified model.

        Args:
            model_name: Name of the Ollama model to scan
            probes: Specific probes to run (None for all probes)
            parallel_attempts: Number of parallel attempts
            verbose: Enable verbose output

        Returns:
            str: Output from Garak scan
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_prefix = os.path.join(self.output_dir, f"scan_{model_name.replace(':', '_')}_{timestamp}")

        config_file = self.create_ollama_config(model_name)

        try:
            cmd = [
                'garak',
                '--model_type', 'rest',
                '--generator_option_file', config_file,
                '--report_prefix', report_prefix,
                '--generations', '1',
                '--config', 'fast',
                '--parallel_attempts', str(parallel_attempts)
            ]

            if probes:
                cmd.extend(['--probes', probes])

            if verbose:
                cmd.append('-v')

            print(f"\n{'='*60}")
            print(f"Starting Garak scan on model: {model_name}")
            print(f"Report prefix: {report_prefix}")
            print(f"Probes: {'all' if not probes else probes}")
            print(f"{'='*60}\n")

            result = get_terminal_commands_output(cmd)

            print(f"\n{'='*60}")
            print(f"Scan completed!")
            print(f"Report saved to: {report_prefix}.report.jsonl")
            print(f"{'='*60}\n")

            return result
        finally:
            if os.path.exists(config_file):
                os.unlink(config_file)


def main():
    """Main entry point for the scanner CLI."""
    parser = argparse.ArgumentParser(
        description="Garak LLM Vulnerability Scanner for Ollama models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a specific model with all probes
  python -m src.scan --model llama2

  # List available models
  python -m src.scan --list-models

  # Scan with specific probe
  python -m src.scan --model llama2 --probes encoding

  # Scan with custom output directory
  python -m src.scan --model llama2 --output-dir ./my_scans
        """
    )

    parser.add_argument(
        '--model',
        help='Name of the Ollama model to scan'
    )
    parser.add_argument(
        '--probes',
        help='Specific probes to run (default: all probes)',
        default=None
    )
    parser.add_argument(
        '--list-models',
        action='store_true',
        help='List available Ollama models'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Directory for scan reports (default: output)'
    )
    parser.add_argument(
        '--parallel-attempts',
        type=int,
        default=1,
        help='Number of parallel attempts (default: 1)'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Disable verbose output'
    )

    args = parser.parse_args()

    scanner = GarakScanner(output_dir=args.output_dir)

    # Check if Ollama is running
    if not scanner.check_ollama_running():
        print("ERROR: Ollama server is not running!")
        print("Please start Ollama with: ollama serve")
        sys.exit(1)

    # List models
    if args.list_models:
        models = scanner.get_ollama_models()
        if models:
            print("\nAvailable Ollama models:")
            for model in models:
                print(f"  - {model}")
        else:
            print("No Ollama models found.")
        sys.exit(0)

    # Scan model
    if not args.model:
        parser.error("--model is required (or use --list-models)")

    # Verify model exists
    models = scanner.get_ollama_models()
    if args.model not in models:
        print(f"ERROR: Model '{args.model}' not found.")
        print("\nAvailable models:")
        for model in models:
            print(f"  - {model}")
        sys.exit(1)

    # Run scan
    try:
        scanner.run_scan(
            model_name=args.model,
            probes=args.probes,
            parallel_attempts=args.parallel_attempts,
            verbose=not args.quiet
        )
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Scan failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
