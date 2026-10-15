"""
Сохранение токена МойСклад и проверка связи.

Запуск: двойной клик по authorize.bat  (или  .venv\\Scripts\\python authorize.py).
Токен хранится в файле moysklad_token.txt рядом с этим скриптом (файл в
.gitignore — в git не попадёт).

    python authorize.py            — Windows: откроет файл в Блокноте, вставь токен,
                                     сохрани и закрой. macOS/Linux: скрытый ввод.
    python authorize.py --console  — скрытый ввод в консоли (на любой ОС)
    python authorize.py --check    — только проверить уже сохранённый токен
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import server  # noqa: E402

HINT = (
    "# Вставь токен МойСклад на следующую строку (Ctrl+V), сохрани (Ctrl+S) и закрой Блокнот.\n"
    "# Где взять: МойСклад -> Настройки -> Токены -> «Создать токен».\n"
    "# Строки с # игнорируются. Этот файл — секрет: никому не пересылай.\n"
)


def check() -> bool:
    try:
        emp = server._request("GET", "context/employee")
    except server.AuthError as exc:
        print(f"\nОШИБКА: {exc}")
        return False
    except server.ApiError as exc:
        print(f"\nОШИБКА API МойСклад: {exc}")
        return False
    print(f"\nСвязь есть ✅  Пользователь токена: {emp.get('name')}")
    return True


def via_notepad() -> None:
    f = server.TOKEN_FILE
    if not server._read_token_file(f):
        f.write_text(HINT + "\n", encoding="utf-8")
    print("Открываю Блокнот с файлом", f.name)
    print("1) вставь токен на пустую строку под подсказками (Ctrl+V)")
    print("2) сохрани (Ctrl+S)")
    print("3) закрой Блокнот — проверка запустится сама.\n")
    subprocess.run(["notepad.exe", str(f)], check=False)  # ждёт закрытия Блокнота


def via_console() -> None:
    print("Вставь токен (правый клик или Ctrl+V) и нажми Enter.")
    print("Символы при вводе НЕ отображаются — так и задумано.\n")
    try:
        token = getpass.getpass("Токен: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nОтменено.")
        sys.exit(1)
    token = server._clean_token(token)
    if not token:
        print("Пустой ввод — ничего не сохранено.")
        sys.exit(1)
    server.TOKEN_FILE.write_text(token + "\n", encoding="utf-8")


def main() -> None:
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)

    print("Токен МойСклад")
    print("---------------")
    print("Где взять: МойСклад → Настройки → Токены → «Создать токен».")
    print("Права токена = права пользователя, для которого он создан.\n")
    if os.environ.get("MOYSKLAD_TOKEN", "").strip():
        print("ВНИМАНИЕ: задана переменная MOYSKLAD_TOKEN — она важнее файла.\n")

    if os.name == "nt" and "--console" not in sys.argv:
        via_notepad()
    else:
        via_console()

    token = server._clean_token(server._read_token_file())
    if not token:
        print("Токен в файле не найден — ничего не проверено. Запусти authorize ещё раз.")
        sys.exit(1)
    print(f"Токен сохранён в {server.TOKEN_FILE.name} (длина {len(token)} симв.).")
    if not check():
        print("Токен сохранён, но не работает. Проверь его и запусти authorize ещё раз.")
        sys.exit(1)
    print("\nГотово. Если Claude Code уже запущен с этим коннектором — перезапуск не нужен.")


if __name__ == "__main__":
    main()
