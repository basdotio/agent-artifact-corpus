"""
Установщик МойСклад коннектора для Claude Code.

Что делает:
  1. Создаёт изолированное окружение .venv рядом с собой.
  2. Ставит зависимости из requirements.txt.
  3. Регистрирует MCP-сервер в ~/.claude.json (пути вычисляются от этой папки,
     поэтому работает где угодно — хоть на диске C, хоть в папке с пробелами).
  4. Проверяет наличие токена МойСклад и печатает следующие шаги.

Запуск: двойной клик по install.bat  (или  py setup.py).
Удаление регистрации:  py setup.py --uninstall
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # чтобы кириллица не ломалась в консоли
except Exception:  # noqa: BLE001
    pass

BASE = Path(__file__).resolve().parent
SERVER = BASE / "server.py"
REQUIREMENTS = BASE / "requirements.txt"
TOKEN_FILE = BASE / "moysklad_token.txt"
IS_WIN = os.name == "nt"
VENV = BASE / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
SERVER_NAME = "moysklad"
CONFIG = Path.home() / ".claude.json"


def line(msg: str = "") -> None:
    print(msg, flush=True)


def head(msg: str) -> None:
    line(f"\n=== {msg} ===")


def check_python() -> None:
    if sys.version_info < (3, 10):
        line(
            f"Нужен Python 3.10 или новее (у тебя {sys.version.split()[0]}).\n"
            "Скачай с https://www.python.org/downloads/ и запусти установку заново."
        )
        sys.exit(1)


def create_venv() -> None:
    head("Окружение (.venv)")
    if VENV_PY.exists():
        line("Уже создано — пропускаю.")
        return
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    line("Готово.")


def install_deps() -> None:
    head("Зависимости")
    subprocess.check_call(
        [str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip"],
        stdout=subprocess.DEVNULL,
    )
    subprocess.check_call(
        [str(VENV_PY), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    )
    line("Установлены.")


def verify_import() -> None:
    head("Проверка")
    subprocess.check_call([str(VENV_PY), "-c", "import server"], cwd=str(BASE))
    line("Сервер импортируется без ошибок.")


def _load_config() -> dict:
    if not CONFIG.exists():
        return {}
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        line(
            f"ВНИМАНИЕ: не удалось прочитать {CONFIG} ({exc}).\n"
            "Файл не тронут. Зарегистрируй сервер вручную (см. README, раздел "
            "«Ручная регистрация»)."
        )
        raise SystemExit(1) from exc


def _save_config(data: dict) -> None:
    if CONFIG.exists():
        shutil.copy2(CONFIG, CONFIG.parent / (CONFIG.name + ".bak"))
    tmp = CONFIG.parent / (CONFIG.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    json.loads(tmp.read_text(encoding="utf-8"))  # проверка валидности
    os.replace(tmp, CONFIG)


def register() -> None:
    head("Регистрация в Claude Code")
    data = _load_config()
    data.setdefault("mcpServers", {})
    data["mcpServers"][SERVER_NAME] = {
        "type": "stdio",
        "command": str(VENV_PY),
        "args": [str(SERVER)],
        "env": {},
    }
    _save_config(data)
    line(f"Сервер '{SERVER_NAME}' зарегистрирован (user scope, для всех проектов).")
    if (CONFIG.parent / (CONFIG.name + ".bak")).exists():
        line(f"Резервная копия конфига: {CONFIG.name}.bak")


def unregister() -> None:
    head("Удаление регистрации")
    if not CONFIG.exists():
        line("Конфиг не найден — нечего удалять.")
        return
    data = _load_config()
    if data.get("mcpServers", {}).pop(SERVER_NAME, None) is not None:
        _save_config(data)
        line(f"Сервер '{SERVER_NAME}' удалён из конфига.")
    else:
        line("Сервер не был зарегистрирован.")
    line("Папку с коннектором можно удалить вручную, если он больше не нужен.")
    line(f"Не забудь удалить и файл с токеном ({TOKEN_FILE.name}), если он там есть.")


def check_token() -> bool:
    head("Токен МойСклад")
    if os.environ.get("MOYSKLAD_TOKEN", "").strip():
        line("Токен задан в переменной окружения MOYSKLAD_TOKEN.")
        return True
    lines = (
        TOKEN_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if TOKEN_FILE.exists()
        else []
    )
    if any(s.strip() and not s.strip().startswith("#") for s in lines):
        line(f"Найден {TOKEN_FILE.name} — токен уже на месте. Отлично.")
        return True
    line("Токена пока НЕТ.")
    line("Создай его в МойСклад (Настройки → Токены) и запусти authorize.bat.")
    return False


def print_next_steps(has_token: bool) -> None:
    head("Что дальше")
    step = 1
    if not has_token:
        line(f"{step}. Создай токен в МойСклад: Настройки → Токены → «Создать токен».")
        step += 1
        line(f"{step}. Запусти authorize.bat: в Блокноте вставь токен, сохрани, закрой (в чат НЕ вставляй).")
        step += 1
    line(f"{step}. Полностью перезапусти Claude Code.")
    line(f"{step + 1}. Проверь: попроси Claude «проверь связь с МойСклад».")


def main() -> None:
    if "--uninstall" in sys.argv:
        unregister()
        return
    line("Установка МойСклад коннектора для Claude Code")
    line(f"Папка: {BASE}")
    if not SERVER.exists() or not REQUIREMENTS.exists():
        line("ОШИБКА: рядом нет server.py / requirements.txt. Запускай из папки коннектора.")
        sys.exit(1)
    check_python()
    create_venv()
    install_deps()
    verify_import()
    register()
    print_next_steps(check_token())
    line("\nГотово ✅")


if __name__ == "__main__":
    main()
