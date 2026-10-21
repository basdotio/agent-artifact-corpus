"""Create the bundled engine's private configuration from its public template."""
import argparse
import json
from pathlib import Path
from project_paths import moneyprinter_project
from moneyprinter_runtime import configure_project


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=moneyprinter_project())
    args = parser.parse_args()
    if not (args.project / 'app/asgi.py').is_file():
        parser.error('MoneyPrinter API source is missing')
    path = configure_project(args.project)
    if not path.is_file():
        parser.error('External engines need their own existing config.toml')
    print(json.dumps(dict(config=str(path), credentials_printed=False,
                         next_step='Fill stock API keys in this private config, and LLM credentials in Shaniu .env'), indent=2))


if __name__ == '__main__':
    main()
