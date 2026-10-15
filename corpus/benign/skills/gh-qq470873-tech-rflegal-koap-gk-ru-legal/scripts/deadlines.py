#!/usr/bin/env python3
"""Калькулятор процессуальных и материальных сроков по праву РФ.

Правила:
- Срок начинает течь со следующего дня после события (ст. 191 ГК, ч. 3 ст. 107 ГПК,
  ч. 2 ст. 113 АПК, ч. 1 ст. 4.8 КоАП).
- Срок в месяцах/годах истекает в соответствующее число последнего месяца;
  если такого числа нет — в последний день месяца (ст. 192 ГК).
- Если последний день нерабочий — переносится на ближайший рабочий
  (ст. 193 ГК, ст. 108 ГПК, ч. 4 ст. 114 АПК, ч. 3 ст. 4.8 КоАП).

Праздники — по ст. 112 ТК РФ. Переносы выходных по постановлениям Правительства
НЕ учитываются: при предупреждении сверяйте с производственным календарём.

Примеры:
  python deadlines.py --start 2026-03-15 --months 1
  python deadlines.py --start 2026-03-15 --days 10
  python deadlines.py --start 2023-05-10 --years 3 --list
  python deadlines.py --start 2026-12-20 --days 10 --off 2026-12-31   # с переносом
"""
import argparse
import calendar
import datetime as dt
import sys

HOLIDAYS_MD = {
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
    (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4),
}
RISKY_MONTHS = {1, 5, 6, 11, 12}  # где часто бывают переносы выходных

WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


EXTRA_OFF: set = set()   # доп. выходные из --off
EXTRA_WORK: set = set()  # рабочие субботы из --work


def is_nonworking(d: dt.date) -> bool:
    if d in EXTRA_WORK:
        return False
    if d in EXTRA_OFF:
        return True
    return d.weekday() >= 5 or (d.month, d.day) in HOLIDAYS_MD


def add_months(d: dt.date, months: int) -> dt.date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return dt.date(y, m, min(d.day, last))


def compute(start: dt.date, days=0, months=0, years=0):
    if days:
        raw_end = start + dt.timedelta(days=days)
    else:
        raw_end = add_months(start, months + 12 * years)
    end = raw_end
    skipped = []
    while is_nonworking(end):
        skipped.append(end)
        end += dt.timedelta(days=1)
    return raw_end, end, skipped


def fmt(d: dt.date) -> str:
    return f"{d:%d.%m.%Y} ({WEEKDAYS[d.weekday()]})"


def main(argv=None):
    p = argparse.ArgumentParser(description="Калькулятор сроков по праву РФ")
    p.add_argument("--start", required=True,
                   help="Дата события, с которым связано начало срока (ГГГГ-ММ-ДД)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--days", type=int, help="Срок в днях (календарных)")
    g.add_argument("--months", type=int, help="Срок в месяцах")
    g.add_argument("--years", type=int, help="Срок в годах")
    p.add_argument("--list", action="store_true", help="Показать пропущенные нерабочие дни")
    p.add_argument("--off", nargs="*", default=[],
                   help="Доп. нерабочие дни из производственного календаря (ГГГГ-ММ-ДД)")
    p.add_argument("--work", nargs="*", default=[],
                   help="Рабочие дни, перенесённые на выходные (ГГГГ-ММ-ДД)")
    a = p.parse_args(argv)
    EXTRA_OFF.update(dt.date.fromisoformat(x) for x in a.off)
    EXTRA_WORK.update(dt.date.fromisoformat(x) for x in a.work)

    try:
        start = dt.date.fromisoformat(a.start)
    except ValueError:
        sys.exit("Дата должна быть в формате ГГГГ-ММ-ДД")

    raw_end, end, skipped = compute(start, a.days or 0, a.months or 0, a.years or 0)
    unit = f"{a.days} дн." if a.days else (f"{a.months} мес." if a.months else f"{a.years} г.")

    print(f"Событие:            {fmt(start)}")
    print(f"Течение с:          {fmt(start + dt.timedelta(days=1))}")
    print(f"Срок:               {unit}")
    print(f"Формальный конец:   {fmt(raw_end)}")
    if skipped:
        print(f"ПОСЛЕДНИЙ ДЕНЬ:     {fmt(end)}  (перенесён с нерабочего дня)")
        if a.list:
            for d in skipped:
                print(f"   пропущен: {fmt(d)}")
    else:
        print(f"ПОСЛЕДНИЙ ДЕНЬ:     {fmt(end)}")
    print("Срок истекает в 24:00 последнего дня (ст. 194 ГК); при подаче в суд"
          " через организацию связи/онлайн — до 24:00 по месту подачи.")
    if (end.month in RISKY_MONTHS or raw_end.month in RISKY_MONTHS) and not (a.off or a.work):
        print("ВНИМАНИЕ: месяц с возможными переносами выходных — сверьте с"
              " производственным календарём на этот год.")


if __name__ == "__main__":
    main()
