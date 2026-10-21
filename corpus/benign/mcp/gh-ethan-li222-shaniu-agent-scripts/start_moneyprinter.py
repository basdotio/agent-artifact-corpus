"""Launch the existing checkout with a caller-selected, compatible Python env."""
import argparse
import os
import subprocess
import socket
import json
from urllib.request import urlopen
from pathlib import Path
from project_paths import moneyprinter_project
from moneyprinter_runtime import configure_project


def existing_service(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            pass
    except ConnectionRefusedError:
        return False
    except OSError:
        return False
    try:
        with urlopen(f'http://127.0.0.1:{port}/openapi.json', timeout=3) as response:
            spec = json.loads(response.read(1_000_001))
        required = {'/api/v1/videos', '/api/v1/audio', '/api/v1/subtitle', '/api/v1/tasks/{task_id}'}
        if not required <= set(spec.get('paths', {})):
            raise ValueError()
    except Exception:
        raise RuntimeError(f'端口 {port} 已被其他程序占用，或现有服务没有响应。请检查占用进程；未终止任何进程。') from None
    print(f'MoneyPrinter API 已在运行：http://127.0.0.1:{port}，无需重复启动。', flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description='启动内置 MoneyPrinter API，也支持 --project 指向外部引擎')
    parser.add_argument('--project', type=Path, default=moneyprinter_project())
    parser.add_argument('--python', type=Path, default=Path(__file__).resolve().parents[1] / '.venv-moneyprinter/Scripts/python.exe', help='运行环境的 Python 路径；默认使用 Shaniu 独立环境')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    project, python = args.project.resolve(), args.python.resolve()
    if not python.is_file() or not (project / 'app/asgi.py').is_file():
        parser.error('请提供有效 Python 和 MoneyPrinterTurbo 引擎目录')
    if not 1 <= args.port <= 65535:
        parser.error('端口必须在 1–65535 之间')
    try:
        config_path = configure_project(project)
    except ValueError as error:
        parser.error(str(error))
    if not config_path.is_file():
        parser.error('外部引擎需要现有 config.toml；内置引擎会自动生成私有配置模板')
    try:
        if existing_service(args.port):
            return
    except RuntimeError as error:
        print(str(error), flush=True)
        raise SystemExit(1)
    env = os.environ.copy()
    # MoneyPrinter may explicitly reuse the conversation key when its own key
    # is blank. Preserve environment-only credentials as well as .env settings.
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # The checkout stays the working directory; its imports/config/resources still
    # resolve normally. An external ASGI entrypoint normalizes short task params.
    scripts = Path(__file__).resolve().parent
    env['PYTHONPATH'] = str(project) + os.pathsep + env.get('PYTHONPATH', '')
    raise SystemExit(subprocess.call([str(python), '-B', '-m', 'uvicorn', 'moneyprinter_host:app', '--app-dir', str(scripts), '--host', '127.0.0.1', '--port', str(args.port), '--log-level', 'warning'], cwd=project, env=env))


if __name__ == '__main__':
    main()
