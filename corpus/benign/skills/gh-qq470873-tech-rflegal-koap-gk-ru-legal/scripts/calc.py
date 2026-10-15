#!/usr/bin/env python3
"""Расчёт процентов по ст. 395 ГК РФ и договорной неустойки.

Ставки ЦБ НЕ зашиты в скрипт намеренно: передавайте их сами (с cbr.ru),
чтобы расчёт не устарел.

Проценты по ст. 395 (ключевая ставка по периодам):
  python calc.py r395 --sum 500000 --from 2025-01-10 --to 2025-06-30 \
      --rates 2024-10-28:21 2025-06-09:20

  Каждая ставка — "дата_начала_действия:процент_годовых". Ставка действует
  до даты начала следующей. Первая ставка должна начинаться не позже --from.

Неустойка (процент в день или доля ставки):
  python calc.py penalty --sum 500000 --from 2025-01-10 --to 2025-06-30 --daily 0.1
  python calc.py penalty --sum 500000 --from 2025-01-10 --to 2025-06-30 --daily 0.1 --cap 10
      (--cap — ограничение неустойки в % от суммы, если оно есть в договоре)

Даты периода включительно. База года — фактическое число дней в году (365/366),
как принято в практике по ст. 395.
Вывод — таблица в Markdown, её можно вставлять в иск как расчёт.
"""
import argparse
import calendar
import datetime as dt
import sys

D = dt.date.fromisoformat


def days_in_year(y):
    return 366 if calendar.isleap(y) else 365


def split_by_year(a, b):
    """Разбивает период [a, b] по границам календарных лет."""
    cur = a
    while cur <= b:
        end = min(b, dt.date(cur.year, 12, 31))
        yield cur, end
        cur = end + dt.timedelta(days=1)


def r395(total, start, end, rates):
    rates = sorted(rates)
    if rates[0][0] > start:
        sys.exit("Первая ставка начинается позже начала периода — добавьте ставку на начало.")
    rows, acc = [], 0.0
    for i, (rs, rate) in enumerate(rates):
        re_ = rates[i + 1][0] - dt.timedelta(days=1) if i + 1 < len(rates) else end
        a, b = max(start, rs), min(end, re_)
        if a > b:
            continue
        for ya, yb in split_by_year(a, b):
            n = (yb - ya).days + 1
            s = total * rate / 100 * n / days_in_year(ya.year)
            acc += s
            rows.append((ya, yb, n, f"{rate:g}%", days_in_year(ya.year), s))
    return rows, acc


def penalty(total, start, end, daily, cap):
    n = (end - start).days + 1
    s = total * daily / 100 * n
    capped = False
    if cap is not None and s > total * cap / 100:
        s, capped = total * cap / 100, True
    return n, s, capped


def money(x):
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")


def main():
    p = argparse.ArgumentParser(description="Расчёт 395 ГК и неустойки")
    sub = p.add_subparsers(dest="mode", required=True)
    for name in ("r395", "penalty"):
        s = sub.add_parser(name)
        s.add_argument("--sum", type=float, required=True, help="Сумма долга")
        s.add_argument("--from", dest="start", required=True, help="Первый день просрочки ГГГГ-ММ-ДД")
        s.add_argument("--to", dest="end", required=True, help="Последний день периода ГГГГ-ММ-ДД")
    sub.choices["r395"].add_argument("--rates", nargs="+", required=True,
                                     help="дата:ставка, напр. 2024-10-28:21")
    sub.choices["penalty"].add_argument("--daily", type=float, required=True,
                                        help="Процент в день, напр. 0.1")
    sub.choices["penalty"].add_argument("--cap", type=float, help="Ограничение, % от суммы")
    a = p.parse_args()
    start, end = D(a.start), D(a.end)
    if end < start:
        sys.exit("Конец периода раньше начала.")

    if a.mode == "r395":
        rates = []
        for r in a.rates:
            d, v = r.split(":")
            rates.append((D(d), float(v.replace(",", "."))))
        rows, acc = r395(a.sum, start, end, rates)
        print(f"Расчёт процентов по ст. 395 ГК РФ на сумму {money(a.sum)} руб.\n")
        print("| Период | Дней | Ставка | Дней в году | Проценты, руб. |")
        print("|---|---|---|---|---|")
        for ya, yb, n, rate, diy, s in rows:
            print(f"| {ya:%d.%m.%Y} – {yb:%d.%m.%Y} | {n} | {rate} | {diy} | {money(s)} |")
        print(f"| **Итого** | {(end - start).days + 1} | | | **{money(acc)}** |")
        print("\nФормула: сумма × ставка × дни / дней в году. Ставки — ключевая ставка"
              " Банка России (указать источник: cbr.ru).")
    else:
        n, s, capped = penalty(a.sum, start, end, a.daily, a.cap)
        print(f"Расчёт неустойки на сумму {money(a.sum)} руб.\n")
        print("| Период | Дней | Ставка в день | Неустойка, руб. |")
        print("|---|---|---|---|")
        print(f"| {start:%d.%m.%Y} – {end:%d.%m.%Y} | {n} | {a.daily:g}% | {money(s)} |")
        if capped:
            print(f"\nПрименено договорное ограничение {a.cap:g}% от суммы.")
        print("\nФормула: сумма × ставка в день × дни. Проверить риск снижения по ст. 333 ГК РФ.")


if __name__ == "__main__":
    main()
