#!/usr/bin/env python3
"""Черновое обезличивание текста по шаблонам российских идентификаторов.

Использование:
  python anonymize.py input.txt > output.txt
  python anonymize.py input.txt --names "Иванов Иван Иванович=Истец" "ООО Ромашка=Ответчик"
Таблица замен печатается в stderr. ФИО автоматически не распознаются —
передавайте их через --names. Результат обязательно просмотреть глазами.
"""
import argparse
import re
import sys

PATTERNS = [
    ("EMAIL", r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    ("ТЕЛЕФОН", r"(?:\+7|\b8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}\b"),
    ("СНИЛС", r"\b\d{3}-\d{3}-\d{3}[\s-]\d{2}\b"),
    ("ПАСПОРТ", r"(?:серия\s*)?\b\d{2}\s?\d{2}\s*(?:№|N|номер)?\s*\d{6}\b"),
    ("СЧЁТ", r"\b\d{20}\b"),
    ("КАРТА", r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),
    ("ОГРН", r"\b\d{15}\b|\b\d{13}\b"),
    ("ИНН", r"\b\d{12}\b|\b\d{10}\b"),
]


def anonymize(text, names):
    mapping = {}
    for original, label in names:
        if original in text:
            text = text.replace(original, f"[{label}]")
            mapping[f"[{label}]"] = original
    for label, pat in PATTERNS:
        counter = 0

        def repl(m):
            nonlocal counter
            counter += 1
            tag = f"[{label} {counter}]"
            mapping[tag] = m.group(0)
            return tag

        text = re.sub(pat, repl, text, flags=re.IGNORECASE)
    return text, mapping


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("--names", nargs="*", default=[],
                   help='Пары "Оригинал=Метка"')
    a = p.parse_args()
    names = []
    for pair in a.names:
        if "=" not in pair:
            sys.exit(f"Неверная пара: {pair}")
        o, l = pair.split("=", 1)
        names.append((o.strip(), l.strip()))
    with open(a.input, encoding="utf-8") as f:
        text = f.read()
    out, mapping = anonymize(text, names)
    sys.stdout.write(out)
    print("\n--- Таблица замен (не передавать в ИИ) ---", file=sys.stderr)
    for k, v in mapping.items():
        print(f"{k}\t{v}", file=sys.stderr)


if __name__ == "__main__":
    main()
