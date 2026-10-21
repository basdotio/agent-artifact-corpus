"""Тесты самопроверки pocherk: блоки A–D, запасной режим, CLI.

Запуск: python -m pytest .claude/skills/pocherk/scripts/tests -q
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check  # noqa: E402
import textkit as tk  # noqa: E402

MORPH = tk.has_morph()
needs_morph = pytest.mark.skipif(not MORPH, reason="нужен pymorphy3")


def run(result, source=None, mode="edit", profile="core", genre="post"):
    return check.run(result, source, mode, profile, genre)


def codes(rep, block, severities=("hard", "soft"), counted_only=True):
    return [f.code for f in rep.findings if f.block == block and f.severity in severities
            and (f.counted or not counted_only)]


def titles(rep, block):
    return [f.title for f in rep.findings if f.block == block and f.severity in ("hard", "soft")]


# =============================================================================== A: факт-замок
BASE = ("Сбер открыл офис в Казани 12 марта. На открытие пришли 40 человек, "
        "а гостей угощали кофе. Платить за парковку надо до 10-го числа, а не в конце месяца. "
        "Мы выполняли эту задачу вручную. Я жду ответа от поддержки.")


def test_identity_is_clean():
    rep = run(BASE, BASE)
    assert codes(rep, "A") == [] and codes(rep, "B") == []
    assert rep.passed


def test_number_lost_and_new_flagged():
    res = BASE.replace("40 человек", "45 человек")
    rep = run(res, BASE)
    a1 = [f for f in rep.findings if f.code == "A1"]
    assert any("«40»" in f.message for f in a1)          # потеряно
    assert any("«45»" in f.message for f in a1)          # новое


def test_number_word_equals_digit():
    src = "Есть два пути, и оба рабочие. Первый занимает 3 часа, второй быстрее."
    res = "Есть 2 пути, и оба рабочие. Первый занимает три часа, второй быстрее."
    assert "A1" not in codes(run(res, src), "A")


def test_month_change_flagged():
    rep = run(BASE.replace("12 марта", "12 апреля"), BASE)
    assert "A2" in codes(rep, "A")


@needs_morph
def test_name_lost_flagged_case_change_not():
    rep = run(BASE.replace("Сбер открыл", "Банк открыл"), BASE)
    assert "A3" in codes(rep, "A")
    src = "Мы долго жили в Казани и часто вспоминаем этот город."
    ok = "Казань — город, где мы долго жили и который часто вспоминаем."
    assert "A3" not in codes(run(ok, src, mode="rewrite"), "A")


def test_new_name_flagged():
    src = "Мы запустили бота за неделю и сразу получили первые заявки."
    res = "Мы запустили бота на Python за неделю и сразу получили первые заявки."
    rep = run(res, src)
    assert any(f.code == "A3" and "Python" in f.message for f in rep.findings)


def test_negation_flip_flagged():
    src = "Кнопка не работает после обновления, и это раздражает пользователей."
    res = "Кнопка работает после обновления, и это раздражает пользователей."
    assert "A4" in codes(run(res, src), "A")


def test_negation_kept_with_bez_not_flagged():
    src = "Ну ок, нет проблем, сделаем завтра утром."
    res = "Ну ок, без проблем, сделаем завтра утром."
    assert "A4" not in codes(run(res, src), "A")


def test_modality_nado_to_mozhno_flagged():
    src = "Платить за парковку надо строго до 10-го числа каждого месяца."
    res = "Платить за парковку можно до 10-го числа каждого месяца."
    rep = run(res, src)
    a5 = [f.title for f in rep.findings if f.code == "A5"]
    assert any("потеряна" in t for t in a5) and any("добавлена" in t for t in a5)


def test_modality_same_class_not_flagged_in_a():
    src = "Платить за парковку надо строго до 10-го числа каждого месяца."
    res = "Платить за парковку нужно строго до 10-го числа каждого месяца."
    rep = run(res, src)
    assert "A5" not in codes(rep, "A")
    assert "Пропали «надо / необходимо / должен»" in titles(rep, "B")     # но след правки в B


@needs_morph
def test_aspect_change_flagged():
    src = "Мы выполняли эту задачу вручную каждый вечер после смены."
    res = "Мы выполнили эту задачу вручную каждый вечер после смены."
    rep = run(res, src)
    assert any(f.code == "A6" and "вид" in f.message for f in rep.findings)


@needs_morph
def test_tense_change_flagged():
    src = "Я жду ответа от поддержки уже третий день подряд."
    res = "Я ждал ответа от поддержки уже третий день подряд."
    assert any(f.code == "A6" and "время" in f.message for f in run(res, src).findings)


@needs_morph
def test_same_verbs_no_aspect_flag():
    src = "Мы выполняли эту задачу вручную, потому что так было надёжнее."
    res = "Эту задачу мы выполняли вручную, потому что так было надёжнее."
    assert "A6" not in codes(run(res, src), "A")


def test_list_count_change_flagged():
    src = "Что взять в поход:\n- палатку\n- спальник\n- горелку\n- аптечку\n\nОстальное купим на месте."
    res = "Что взять в поход:\n- палатку\n- спальник\n- горелку\n\nОстальное купим на месте."
    rep = run(res, src)
    assert "A7" in codes(rep, "A")
    assert any("было 4, стало 3" in f.message for f in rep.findings if f.code == "A7")


def test_inline_list_item_lost_flagged():
    src = "Каждый день собираю отчёт за смену, протокол совещания, акт, сводку для руководства."
    res = "Каждый день собираю отчёт за смену, протокол совещания, сводку для руководства."
    rep = run(res, src)
    assert any(f.code == "A7" and "акт" in f.message for f in rep.findings)


def test_list_reformatted_not_flagged():
    src = "Что взять в поход:\n- палатку\n- спальник\n- горелку\n\nОстальное купим на месте."
    res = "В поход возьмём палатку, спальник и горелку.\n\nОстальное купим на месте."
    assert "A7" not in codes(run(res, src, mode="rewrite"), "A")


def test_inline_list_with_long_last_pair_flagged():
    # последний кусок «зарядку телефона и стабильность интернета» длиннее 4 слов, но это два пункта
    src = "Перед эфиром проверяю четыре вещи: звук, свет, зарядку телефона и стабильность интернета."
    res = "Перед эфиром проверяю четыре вещи: звук, свет и стабильность интернета."
    assert any(f.code == "A7" and "зарядку" in f.message for f in run(res, src).findings)


@needs_morph
def test_clause_chunks_are_not_a_list():
    for t in ("По его мнению, лучше сосредоточиться на цифрах, чем заниматься глупыми концепциями.",
              "И это очень плохо, и не понятно, в чём дело.",
              "Более того, мы не правы, когда, говоря об ответственности, разделяем людей.",
              "Насколько мне известно, во всех каталогах, признаваемых сообществом, наименование звёзд "
              "следует строгой процедуре."):
        assert check.inline_lists(tk.Doc(t)) == [], t
    assert check.inline_lists(tk.Doc("Мы купили хлеб, молоко и сыр."))


def test_weekday_wednesday_tracked_environment_not():
    src = "Следующий эфир будет в среду в семь вечера, а ссылку пришлю за час до начала."
    res = "Следующий эфир будет в семь вечера, а ссылку пришлю за час до начала."
    assert "A2" in codes(run(res, src), "A")
    src2 = "Отходы попадают в окружающую среду, и это видно по анализам воды из реки."
    res2 = "Отходы попадают в природу, и это видно по анализам воды из реки."
    assert "A2" not in codes(run(res2, src2), "A")
    src3 = "Код попадает в среду разработки, и это видно по логам сборки на сервере."
    res3 = "Код попадает в IDE, и это видно по логам сборки на сервере."
    assert "A2" not in codes(run(res3, src3), "A")
    for t in ("В среде маркетинга я всех называю по имени.", "Запустить игру в среде виртуальной машины."):
        assert check._date_words(tk.Doc(t)) == {}, t
    for t in ("Эфир в среду вечером.", "Созвоны по средам.", "В эту среду выходной."):
        assert "сред" in check._date_words(tk.Doc(t)), t


def test_repeated_number_lost_flagged():
    src = "Купили 2 лицензии для отдела продаж и 2 для поддержки, остальным хватает бесплатного тарифа."
    res = "Купили 2 лицензии для отдела продаж и для поддержки, а остальным хватает бесплатного тарифа."
    assert any(f.title == "Числа: встречаются реже" for f in run(res, src).findings)


def test_approximation_lost_flagged_and_same_class_kept():
    src = "За месяц пришло почти 300 новых подписчиков, а охват вырос почти на 2% за ту же неделю."
    res = "За месяц пришло 300 новых подписчиков, а охват вырос почти на 2% за ту же неделю."
    assert any(f.code == "A1" and "оговорка" in f.title for f in run(res, src).findings)
    src2 = "Видеокарта минимум на 1 ГБ, накопитель не менее 256 ГБ, прибавка >800 руб."
    res2 = "Видеокарта минимум 1 ГБ, накопитель минимум 256 ГБ, прибавка свыше 800 руб."
    assert not any("оговорка" in f.title for f in run(res2, src2).findings)


def test_unit_change_flagged():
    src = "Вся связка обходится примерно в 900 рублей в месяц, и это дешевле фрилансера."
    res = "Вся связка обходится примерно в 900 долларов в месяц, и это дешевле фрилансера."
    assert any(f.title == "Числа: другая единица" for f in run(res, src).findings)
    same = "Вся связка обходится примерно в 900 ₽ в месяц, и это дешевле фрилансера."
    assert not any(f.title == "Числа: другая единица" for f in run(same, src).findings)


def test_negation_added_flagged():
    src = "Бот отвечает на вопросы о доставке и сроках возврата уже несколько дней."
    res = "Бот не отвечает на вопросы о доставке и сроках возврата уже несколько дней."
    assert "A4" in codes(run(res, src), "A")


@needs_morph
def test_negation_moves_and_not_only_not_flagged():
    pairs = [("Рынок, который раньше не считался модным, резко вырос за год.",
              "Рынок, который раньше считался немодным, резко вырос за год."),
             ("Бот отвечает на вопросы о доставке и передаёт заявки менеджеру.",
              "Бот не только отвечает на вопросы о доставке, но и передаёт заявки менеджеру.")]
    for a, b in pairs:
        assert "A4" not in codes(run(b, a), "A") and "A4" not in codes(run(a, b), "A"), (a, b)


def test_negation_does_not_leak_across_comma_when_joined():
    # склейка «…нет. Единственное…» → «…нет, и единственное…» — не переворот
    src = ("Возрастного порога для изучения языка нет. Единственное, что нужно человеку любого возраста, — это "
           "мотивация. Остальное приложится.")
    res = ("Возрастного порога для изучения языка нет, и единственное, что нужно человеку любого возраста, — это "
           "мотивация. Остальное приложится.")
    assert codes(run(res, src), "A") == []


def test_a_ne_boundary_lost_flagged():
    src = "Учиться надо через практику, а не через лекции, и это видно по результатам."
    res = "Учиться надо через практику, и это видно по результатам."
    assert "A8" in codes(run(res, src), "A")


def test_length_out_of_range_flagged():
    src = " ".join(["Мы долго выбирали площадку для встречи и в итоге остановились на старом цеху."] * 4)
    res = "Мы выбрали старый цех."
    rep = run(res, src)
    assert "A9" in codes(rep, "A")
    # A10 (знаменательные слова < 75%) — подсказка, а не нарушение (DEV-замер, P8)
    a10 = [f for f in rep.findings if f.code == "A10"]
    assert a10 and all(f.severity == "note" and not f.counted for f in a10)
    assert "A10" not in codes(rep, "A")


def test_yo_e_equivalent_for_fact_lock():
    src = "Ещё раз проверили её отчёт и нашли ошибку в расчёте."
    res = "Еще раз проверили ее отчет и нашли ошибку в расчете."
    rep = run(res, src)
    assert codes(rep, "A") == []


def test_write_mode_checks_only_new_facts():
    brief = "Новость: OpenAI выпустила модель, цена 20 долларов в месяц."
    post = "OpenAI выпустила новую модель. Подписка стоит 20 долларов в месяц, а у Google — 25."
    rep = run(post, brief, mode="write")
    a = [f for f in rep.findings if f.block == "A"]
    assert any(f.code == "A1" and "«25»" in f.message for f in a)
    assert any(f.code == "A3" and "Google" in f.message for f in a)
    assert not any(f.block == "B" for f in rep.findings)


# =============================================================================== B: след правки
def test_hyphen_dash_converted_flagged():
    src = "Есть два пути - и оба рабочие, хотя первый дольше второго."
    res = "Есть два пути — и оба рабочие, хотя первый дольше второго."
    assert "B1" in codes(run(res, src), "B")
    assert "B1" not in codes(run(src, src), "B")


def test_quotes_converted_flagged():
    src = 'Он назвал это "магией" и ушёл, не дождавшись ответа.'
    res = "Он назвал это «магией» и ушёл, не дождавшись ответа."
    assert "B2" in codes(run(res, src), "B")


def test_yo_introduced_flagged_and_kept_not():
    src = "Еще раз проверили ее отчет, нашли ошибку в расчете и отправили его назад автору на доработку."
    res = "Ещё раз проверили её отчёт, нашли ошибку в расчёте и отправили его назад автору на доработку."
    assert "B3" in codes(run(res, src), "B")
    assert "B3" not in codes(run(res, res), "B")


def test_colons_grew_flagged_one_extra_allowed():
    src = ("Мы долго думали, как назвать продукт, и решили взять простое слово. "
           "Причина в том, что длинные названия никто не запоминает.")
    one = src.replace("и решили взять простое слово.", "и решили так: взять простое слово.")
    three = ("Мы долго думали над названием: какое выбрать. Решение простое: короткое слово. "
             "Причина такая: длинные названия никто не запоминает.")
    assert "Двоеточий больше, чем в исходнике (+1 на 300 слов)" not in titles(run(one, src), "B")
    assert "Двоеточий больше, чем в исходнике (+1 на 300 слов)" in titles(run(three, src, mode="rewrite"), "B")


def test_single_reveal_colon_flagged_without_slack():
    src = "Охваты упали почти вдвое, когда мы перестали публиковать по утрам. Вернули утренние посты."
    res = "Охваты упали почти вдвое по одной причине: мы перестали публиковать по утрам. Вернули утренние посты."
    assert "Новые двоеточия-раскрытия («Причина проста: …»)" in titles(run(res, src), "B")
    # ярлык стал раскрытием — новых «:» нет
    src2 = "Итог: всё заработало после обновления, и клиенты довольны."
    res2 = "Итог такой: всё заработало после обновления, и клиенты довольны."
    assert "Новые двоеточия-раскрытия («Причина проста: …»)" not in titles(run(res2, src2), "B")


def test_persona_and_honesty_variants_flagged():
    src = "Сервис удобный, но для небольших команд дорогой, и бесплатного тарифа хватает только на пробу."
    for res in ("Сервис удобный, но для небольших команд, мне кажется, дорогой, и бесплатного тарифа хватает только на пробу.",
                "Я думаю, сервис удобный, но для небольших команд дорогой, и бесплатного тарифа хватает только на пробу."):
        assert "Новые «по-моему / мне кажется / я считаю / я уверен»" in titles(run(res, src), "B"), res
    for res in ("Честно скажу, сервис удобный, но для небольших команд дорогой, и бесплатного тарифа хватает только на пробу.",
                "Сервис удобный, но, честно, для небольших команд дорогой, и бесплатного тарифа хватает только на пробу."):
        assert "Новое «честно»" in titles(run(res, src), "B"), res
    plain = "Сервис удобный и честно показывает цену, но для команд дорогой, и бесплатного тарифа хватает только на пробу."
    assert "Новое «честно»" not in titles(run(plain, src), "B")


def test_colon_inside_quotes_not_counted():
    s = tk.Doc("Подробнее в книге «Фактор доверия: наука о командах» и в статье «Советы: как начать».").sents[0]
    assert check.colon_kinds(s) == []
    s2 = tk.Doc("Попросите подписчиков выбрать: «Пишите в комментариях: 1 или 2».").sents[0]
    assert [k for k, _ in check.colon_kinds(s2)] == ["speech"]


def test_new_dash_turn_flagged():
    src = "Запустили один проект, отчитались и считают, что всё получилось."
    res = "Запустили один проект, отчитались — и считают, что всё получилось."
    assert "Новые тире-повороты «— и / — а / — но»" in titles(run(res, src), "B")


def test_particles_lost_flagged():
    src = "Это же очевидно, ведь мы уже пробовали. Ну и ладно, вот так бывает."
    res = "Это очевидно: мы уже пробовали. Так бывает."
    assert "Пропали частицы («же, ведь, вот, ну, -то»)" in titles(run(res, src), "B")


def test_kto_to_is_not_particle():
    s = tk.Doc("Кто-то пришёл, что-то сказал и как-то странно посмотрел. Тот же человек.").sents
    assert tk.particles(s[0]) == [] and tk.particles(s[1]) == []
    assert tk.particles(tk.Doc("Он-то знал, наконец-то пришёл.").sents[0]) == ["он-то", "наконец-то"]
    src = "Кто-то пришёл и что-то сказал про отчёт."
    res = "Кто-то пришёл и сказал про отчёт."
    assert "Пропали частицы («же, ведь, вот, ну, -то»)" not in titles(run(res, src), "B")


def test_long_sentences_lost_flagged():
    long_s = ("Такой формат, хоть и использовался у нас ранее для курсов по иностранным языкам и ридинг-групп, "
              "был необычным для нашей площадки, потому что лекции до этого были в основном разовыми трансляциями.")
    res = ("Такой формат у нас уже был: курсы иностранных языков и ридинг-группы. Но для площадки он необычный. "
           "Лекции до этого были в основном разовыми трансляциями.")
    assert "Длинных фраз (> 25 слов) стало меньше 70% исходника" in titles(run(res, long_s), "B")


def test_brackets_and_rhetorical_question_and_ty_lost_flagged():
    src = ("Если ты собираешь отчёт руками (а таких много), этот пост для тебя. Зачем тратить час? "
           "Нейросеть сделает это за минуту.")
    res = "Если вы собираете отчёт руками, этот пост для вас. Нейросеть сделает это за минуту, и час не нужен."
    t = titles(run(res, src), "B")
    assert "Скобок стало меньше 80% исходника" in t
    assert "Пропали риторические вопросы" in t
    assert "Пропало обращение на «ты»" in t


def test_persona_and_honesty_added_flagged():
    src = "Сервис удобный, но дорогой для небольших команд и фрилансеров."
    res = "Честно говоря, сервис удобный, но, по-моему, дорогой для небольших команд и фрилансеров."
    t = titles(run(res, src), "B")
    assert "Новое «честно»" in t and "Новые «по-моему / мне кажется / я считаю / я уверен»" in t


# =============================================================================== C: бюджеты
def test_colon_reveals_over_budget_in_post():
    txt = ("Лечится это так: перед форком нужно закрыть все подключения. "
           "Почему это работает, объясню отдельно, а пока результат тестов хороший: ошибки пропали. "
           "Дальше мы проверили нагрузку и увидели важное: база держит в два раза больше.")
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert "CORE-04" in codes(rep, "C")


def test_service_label_and_smiley_not_counted():
    txt = "Цена: 500 рублей. Платформы: веб, Windows, macOS. Приходите, будет весело :)"
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert "CORE-03" not in codes(rep, "C") and "CORE-04" not in codes(rep, "C")
    kinds = [k for s in tk.Doc(txt).sents for k, _ in check.colon_kinds(s)]
    assert "label" not in kinds and "reveal" not in kinds


def test_label_counted():
    txt = ("Мой совет: заранее решите, что показывать. Сразу оговорюсь: я не специалист. "
           "Удобный приём: сложите носки в мешок.")
    rep = run(txt, mode="rewrite", profile="core", genre="post")
    assert "CORE-03" in codes(rep, "C")


@needs_morph
def test_grammatical_dash_not_flagged():
    txt = ("Москва — столица России. Задача — успеть до вечера. Латте — 450 тенге. "
           "Успех — это привычка, а не талант. Работаем с 9–18 по будням.")
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert not {"DASH-01", "DASH-02"} & set(codes(rep, "C"))
    for s in tk.Doc(txt).sents:
        assert tk.dash_tail_hits(s) == []
    classes = [c for s in tk.Doc(txt).sents for c in tk.classify_dash_sentence(s.norm)]
    assert "turn" not in classes and "apposition" not in classes


@needs_morph
def test_dash_tail_flagged():
    s = tk.Doc("Есть и другая сторона дела — популярность.").sents[0]
    assert tk.dash_tail_hits(s)


def test_dash_turns_over_budget():
    txt = ("Запустили проект — и считают, что всё получилось. Отчитались — а потом забыли. "
           "Команда устала — но продолжает работать.")
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert "DASH-01" in codes(rep, "C")
    assert "DASH-01" not in codes(run(txt, mode="rewrite", profile="gigachat", genre="post"), "C")


def test_honesty_flagged():
    rep = run("Честно говоря, я не ожидал такого результата от новой модели.", mode="rewrite", profile="core")
    assert "CORE-05" in codes(rep, "C")


def test_profiles_are_separate():
    txt = ("Однако модель ошибается. Однако это не страшно. Однако стоит проверить результат. "
           "Модель считает быстро и без сбоев.")
    assert "GIGA-01" in codes(run(txt, mode="rewrite", profile="gigachat"), "C")
    assert "GIGA-01" not in codes(run(txt, mode="rewrite", profile="claude"), "C")
    hello = "Привет, друзья! Сегодня хочу поделиться новостью о модели."
    assert "YA-01" in codes(run(hello, mode="rewrite", profile="yandex"), "C")
    assert "YA-01" not in codes(run(hello, mode="rewrite", profile="claude"), "C")


def test_markdown_in_post_flagged():
    txt = "## Новая модель\n\n**Главное:** она быстрее старой и дешевле в два раза."
    assert "CORE-16" in codes(run(txt, mode="rewrite", profile="core", genre="post"), "C")


@needs_morph
def test_one_marker_counts_once():
    txt = ("Лечится это так: перед форком нужно закрыть подключения. Результат хороший: ошибки пропали. "
           "Видим важное: база держит нагрузку. Вывод очевиден: работает.")
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    core04 = [f for f in rep.findings if f.code == "CORE-04" and f.severity == "soft"]
    assert len(core04) >= 2 and sum(f.counted for f in core04) == 1


def test_edit_mode_budget_relative_to_source():
    src = ("Причина проста: никто не читал инструкцию. Решение такое: читать инструкцию. "
           "Итог понятный: всё заработало.")
    rep = run(src, src, mode="edit", profile="claude", genre="post")
    assert codes(rep, "C") == []
    assert any(f.code == "CORE-04" and f.severity == "note" for f in rep.findings)


# =============================================================================== D: ритм
SHORT = "Мы запустили бота в понедельник утром. Он отвечает клиентам за пару секунд."
LONG_S = ("Когда мы впервые запустили этого бота в рабочем чате поддержки, никто из команды не верил, "
          "что он справится хотя бы с половиной типовых вопросов клиентов без помощи живых операторов.")


def _metronome(n=16):
    return " ".join([SHORT] * (n // 2))


def test_no_long_sentences_flagged():
    txt = _metronome(26)
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert rep.stats["words"] >= 150
    assert "Нет длинных фраз" in titles(rep, "D")
    assert sum(f.counted for f in rep.findings if f.block == "D" and f.severity == "soft") == 1


def test_long_sentences_present_not_flagged():
    txt = _metronome(20) + " " + LONG_S + " " + LONG_S
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert rep.stats["words"] >= 150 and rep.stats["long_sentences"] == 2
    assert "Нет длинных фраз" not in titles(rep, "D")


def test_uniform_long_sentences_cv_flagged():
    txt = " ".join([LONG_S] * 9)
    rep = run(txt, mode="rewrite", profile="claude", genre="post")
    assert "Фразы одной длины (метроном)" in titles(rep, "D")
    assert "Нет длинных фраз" not in titles(rep, "D")


def test_short_text_no_rhythm_rules():
    rep = run(_metronome(6), mode="rewrite", profile="claude", genre="post")
    assert [f for f in rep.findings if f.block == "D" and f.severity == "soft"] == []


def test_edit_mode_rhythm_same_as_source_not_counted():
    txt = _metronome(26)
    rep = run(txt, txt, mode="edit", profile="claude", genre="post")
    assert not any(f.block == "D" and f.counted and f.severity == "soft" for f in rep.findings)


# =============================================================================== DEV-замер v1: P1 рамки и источники
def a11(rep):
    return [f for f in rep.findings if f.code == "A11" and f.severity == "hard"]


def test_opinion_frame_removed_flagged():
    # tg_wayback-299 и opinion-303 из DEV-замера: рамку сняли, мнение стало фактом
    src = "Стартап закрылся. И, как мне кажется, дело здесь скорее в общественном мнении, чем в политике."
    res = "Стартап закрылся, и дело здесь скорее в общественном мнении, чем в политике."
    f = a11(run(res, src, mode="rewrite"))
    assert f and f[0].title == "Рамка мнения пропала" and "мне кажется" in f[0].message
    src2 = "Я девять лет работала репетитором. И я уверена: разговорному уровню можно научить за полгода."
    res2 = "Я девять лет работала репетитором. Разговорному уровню можно научить за полгода."
    assert a11(run(res2, src2, mode="rewrite"))


def test_source_removed_flagged():
    # opinion-62 (DEV): «По моему опыту» снято — опыт стал общим правилом; habr_news-22 (контроль): «по их мнению»
    src = "По моему опыту, переходов на сайт отсюда может быть больше, чем со всех остальных соцсетей."
    res = "Переходов на сайт отсюда может быть больше, чем со всех остальных соцсетей."
    f = a11(run(res, src))
    assert f and f[0].title == "Источник или опыт пропал"
    src2 = "Акционеры недовольны. По их мнению, это даёт ему практически неограниченную власть."
    res2 = "Акционеры недовольны. Из-за этого власть у него практически неограниченная."
    assert a11(run(res2, src2, mode="rewrite"))


def test_frame_reshaped_not_flagged():
    pairs = [
        ("Можно спорить, но я уверен: решающим фактором стало происхождение стартапа.",
         "Можно спорить, но я уверен, что решающим фактором стало происхождение стартапа."),
        ("Мне кажется, сервис для небольших команд дорогой.", "По-моему, сервис для небольших команд дорогой."),
        ("Мне казалось, что вот-вот я во всём разберусь.", "Казалось, ещё чуть-чуть, и я во всём разберусь."),
        ("Акционеры недовольны. По их мнению, это даёт ему неограниченную власть.",
         "Акционеры недовольны. Они считают, что это даёт ему неограниченную власть."),
        ("Как пишет Forbes, компания потеряла треть выручки за квартал.",
         "Forbes пишет, что компания потеряла треть выручки за квартал."),
        # вторую рамку у той же мысли снимать можно
        ("По-моему, я думаю, это ошибка разработчиков и тестировщиков.",
         "По-моему, это ошибка разработчиков и тестировщиков."),
    ]
    for src, res in pairs:
        assert not a11(run(res, src, mode="rewrite")), (src, res)


def test_frame_kept_when_alignment_ties():
    # склейка соседних фраз не должна уводить окно к похожей фразе без рамки
    src = ("Что ты считаешь успехом, спросил он. Я задумалась. Что я считаю успехом? "
           "Наверное, свободу выбирать задачи.")
    res = ("Что ты считаешь успехом, спросил он. Я задумалась, и что я считаю успехом? "
           "Наверное, свободу выбирать задачи.")
    assert not a11(run(res, src))


def test_evidential_is_not_persona():
    # «по моему опыту» — источник: в B не «новая рамка мнения», а «новый источник»; в CORE-06 не считается
    src = "Переходов на сайт отсюда больше, чем со всех остальных соцсетей вместе взятых."
    res = "По моему опыту, переходов на сайт отсюда больше, чем со всех остальных соцсетей вместе взятых."
    t = titles(run(res, src), "B")
    assert "Новые источники и опыт («по моему опыту», «по их данным»)" in t
    assert "Новые «по-моему / мне кажется / я считаю / я уверен»" not in t
    persona = next(c for c in check.BUDGETS["counters"] if c["key"] == "persona")
    assert not check.rx(persona["regex"]).search("по моему опыту, так быстрее")
    assert not check.rx(check.PERSONA_RX).search("по моему опыту, так быстрее")


def test_inserted_source_flagged_and_reshaped_source_not():
    src = "Посты с вопросом в конце получают меньше показов, чем раньше."
    res = "По их данным, посты с вопросом в конце получают меньше показов, чем раньше."
    assert "Новые источники и опыт («по моему опыту», «по их данным»)" in titles(run(res, src), "B")
    src2 = "Уверен, что через год список подобных мелочей подрастёт. Тенденция уже наметилась."
    res2 = "Тенденция уже наметилась, и уверен, что через год список подобных мелочей подрастёт."
    assert "Новые источники и опыт («по моему опыту», «по их данным»)" not in titles(run(res2, src2), "B")
    # источник был в мягкой форме: «Аналитик сказал, что…» → «По словам аналитика…» — не новый
    src3 = "Аналитик сказал, что для кредиторов такая форма санации невыгодна."
    res3 = "По словам аналитика, для кредиторов такая форма санации невыгодна."
    assert "Новые источники и опыт («по моему опыту», «по их данным»)" not in titles(run(res3, src3), "B")
    # и обратно: «По мнению главы правительства, X» → «Медведев подчеркнул, что X» — источник на месте
    src4 = "По мнению главы правительства, санкции не вопрос жизни и смерти для экономики."
    res4 = "Медведев подчеркнул, что санкции не вопрос жизни и смерти для экономики."
    assert not a11(run(res4, src4, mode="rewrite"))


_FRAMES_POST = ("Сервис удобный, по-моему, для небольших команд. Я считаю, что тариф дороговат.\n\n"
                "Поддержка отвечает быстро. Документация понятная.\n\n"
                "Интеграций хватает. Обновления выходят часто.")


def test_core06_counts_per_paragraph():
    rep = run(_FRAMES_POST, mode="rewrite", profile="claude", genre="post")
    assert "CORE-06" in codes(rep, "C")                   # две рамки в одном абзаце
    spread = ("Сервис удобный, по-моему, для небольших команд. Тариф дороговат.\n\n"
              "Поддержка отвечает быстро. Я считаю, что документация понятная.\n\n"
              "Интеграций хватает. Обновления выходят часто.")
    assert "CORE-06" not in codes(run(spread, mode="rewrite", profile="claude", genre="post"), "C")


def test_core06_not_capped_in_opinion_or_first_person():
    rep = run(_FRAMES_POST, mode="rewrite", profile="claude", genre="opinion")
    assert "CORE-06" not in codes(rep, "C")
    assert any(f.code == "CORE-06" and f.severity == "note" and "колонка" in f.message for f in rep.findings)
    first = ("Я пользуюсь сервисом полгода, мне его посоветовал коллега. " + _FRAMES_POST
             + "\n\nМой отчёт я собираю там же, и мне это удобно.")
    rep2 = run(first, mode="rewrite", profile="claude", genre="post")
    assert check.is_first_person(tk.Doc(first)) and not check.is_first_person(tk.Doc(_FRAMES_POST))
    assert "CORE-06" not in codes(rep2, "C")
    assert any(f.code == "CORE-06" and "первого лица" in f.message for f in rep2.findings)


# =============================================================================== P2: возможность
def test_possibility_to_indicative_flagged():
    # opinion-403 (DEV): «позволяет достичь» → «добивается», «позволит сократить» → «сократит»
    for src, res in (("Она позволяет достичь тех же результатов всего за 1–2 месяца занятий.",
                      "С ней человек за 1–2 месяца занятий добивается тех же результатов."),
                     ("Такая технология позволит существенно сократить число больничных.",
                      "Такая технология сильно сократит число больничных."),
                     ("Нейросеть может помочь с первым черновиком поста.",
                      "Нейросеть помогает с первым черновиком поста.")):
        rep = run(res, src, mode="rewrite")
        f = [x for x in rep.findings if x.code == "A5" and "возможност" in x.title]
        assert f and "потеряна" in f[0].title, (src, res)
        assert f[0].frags and f[0].frags[0].where == "исходник"


def test_possibility_reshaped_not_flagged():
    for src, res in (("Такая технология позволит сократить число больничных.",
                      "Такая технология может сократить число больничных."),
                     ("Такая технология позволит сократить число больничных.",
                      "Такая технология поможет сократить число больничных."),
                     ("Она позволяет достичь тех же результатов за месяц.",
                      "С ней можно добиться тех же результатов за месяц."),
                     ("Это можно сделать за вечер без программиста.",
                      "Это может сделать за вечер любой, без программиста.")):
        assert "A5" not in codes(run(res, src, mode="rewrite"), "A"), (src, res)


# =============================================================================== P3: склейки
def test_new_comma_and_beyond_slack_flagged():
    src = "Мы запустили бота. Он отвечает за секунды. Клиенты довольны. Менеджеры отдыхают."
    one = "Мы запустили бота, и он отвечает за секунды. Клиенты довольны. Менеджеры отдыхают."
    two = "Мы запустили бота, и он отвечает за секунды. Клиенты довольны, а менеджеры отдыхают."
    title = "Новые «, и» / «, а» (больше +1 на 200 слов)"
    assert title not in titles(run(one, src), "B")
    assert title in titles(run(two, src), "B")


@needs_morph
def test_comma_splice_flagged():
    title = "Новая склейка через запятую (две самостоятельные фразы)"
    for src, res in (
            ("Люди не отрабатывают это в речи. Вот дети и ищут готовые ответы.",
             "Люди не отрабатывают это в речи, вот дети и ищут готовые ответы."),
            ("Кто-то может получить повторное сообщение. Будьте к этому готовы.",
             "Кто-то может получить повторное сообщение, будьте к этому готовы."),
            ("Разговоры тут серьёзнее, чем на других площадках. Котиков меньше, а дела больше.",
             "Разговоры тут серьёзнее, чем на других площадках, котиков меньше, а дела больше.")):
        assert title in titles(run(res, src), "B"), res


@needs_morph
def test_comma_splice_from_colon_list_not_new():
    # tg_wayback-370 (DEV): запятая была в перечне после двоеточия; двоеточие стало точкой — склейка не новая
    src = "Сюжет один и тот же: что-то идёт не так, поддержка удивляется проблеме и ничего не делает."
    res = "Сюжет один и тот же. Что-то идёт не так, поддержка удивляется проблеме и ничего не делает."
    assert "Новая склейка через запятую (две самостоятельные фразы)" not in titles(run(res, src, mode="rewrite"), "B")


@needs_morph
def test_comma_splice_not_flagged_on_subordinate_or_homogeneous():
    for t in ("Когда он пришёл домой, мама готовила ужин.",
              "Он открыл дверь, вошёл в комнату и сел.",
              "Я думаю, это правильно.",
              "Откройте настройки, нажмите кнопку «Сохранить».",
              "Можно сдать позже, и скорее всего, его можно сдать после собеседования.",
              "На карте хранятся ваши деньги, и если преступники доберутся до них, вы лишитесь средств.",
              "Проверяете, укладывается ли сотрудник в срок.",
              "Он добивается того же, чего обычные клиенты достигают за годы.",
              "А когда жена начинает ворчать, я ищу небольшие компании.",
              "Получается, фактически индексация составила чуть больше двух процентов.",
              "Процесс занял считанные дни: бот был сделан легко, база освоилась быстро.",
              "Долго размышлял над этой темой и уверен, она окажется полезной.",
              "Теперь текст звучит яснее, четче и структурирован по пунктам.",
              "Хотя финальная версия, скорее всего, будет другой, хакеры уже изучают сборку.",
              "Это поможет оценить, насколько верно вы расставляете приоритеты.",
              "Переходите по ссылке, изучайте предложение, получайте доступ."):
        assert tk.comma_splices(tk.Doc(t).sents[0]) == [], t


@needs_morph
def test_conjunction_chain_flagged():
    src = ("Я был то посредником, то исполнителем. Мне казалось, что вот-вот я во всём разберусь. "
           "Сейчас понимаю, что просто распылялся и занимался всем сразу.")
    res = ("Я был то посредником, то исполнителем, и мне казалось, что вот-вот я во всём разберусь, а сейчас "
           "понимаю, что просто распылялся и занимался всем сразу.")
    assert "Новая цепочка: больше двух сочинительных союзов во фразе" in titles(run(res, src, mode="rewrite"), "B")
    count = lambda t: tk.coord_conj_count(tk.Doc(t).sents[0])  # noqa: E731
    assert count("Проверяю звук, свет и интернет, а потом включаю запись.") == 1     # однородные члены не в счёт
    assert count("Работает по принятому порядку, а не по собственному.") == 0         # «а не» — граница охвата
    assert count("Вот и сегодня зашёл в магазин.") == 0                               # «вот и» — частица
    assert count("Ребёнок зажат и внешне, и внутренне.") == 0                          # «и X, и Y»
    assert count("Он пришёл, и мы поговорили, а потом он ушёл и не вернулся.") == 3


# =============================================================================== P4: новые маркеры замены двоеточия
def test_new_potomu_chto_beyond_slack_flagged():
    src = "Метод щадящий: прогресс виден сразу. Курс короткий: всего месяц. Цена низкая: бюджетный тариф."
    one = "Метод щадящий, потому что прогресс виден сразу. Курс короткий: всего месяц. Цена низкая: бюджетный тариф."
    three = ("Метод щадящий, потому что прогресс виден сразу. Курс короткий, потому что длится месяц. "
             "Цена низкая, потому что тариф бюджетный.")
    title = "Новые «потому что» (больше +1 на 300 слов)"
    assert title not in titles(run(one, src), "B")
    assert title in titles(run(three, src, mode="rewrite"), "B")


def test_new_v_tom_chto_more_than_one_flagged():
    src = "Суть простая: публикуем каждый день. Идея такая: никаких выходных для контент-плана."
    one = "Суть в том, что публикуем каждый день. Идея такая: никаких выходных для контент-плана."
    two = "Суть в том, что публикуем каждый день. Идея в том, чтобы контент-план не знал выходных."
    title = "Новые «X в том, что / чтобы» (больше одного)"
    assert title not in titles(run(one, src), "B")
    assert title in titles(run(two, src, mode="rewrite"), "B")


def test_new_vo_pervyh_and_ponyal_chto_flagged():
    src = "Почему ушли с таргета. Первое: заявки дорожают каждый месяц. Второе: половина из них боты."
    res = "Почему ушли с таргета. Во-первых, заявки дорожают каждый месяц. Во-вторых, половина из них боты."
    assert "Новые «во-первых / во-вторых»" in titles(run(res, src), "B")
    # SKILL v3: новых «уверен / понял / сказали / признаюсь, что» — не больше одного на текст
    title = "Новые «уверен / понял / сказали / признаюсь, что» (больше одного)"
    src2 = "Тогда я понял простую вещь: надо работать каждый день. Мне прямо сказали: без графика ничего не выйдет."
    one = "Тогда я понял, что надо работать каждый день. Мне прямо сказали: без графика ничего не выйдет."
    two = "Тогда я понял, что надо работать каждый день. Мне прямо сказали, что без графика ничего не выйдет."
    assert title not in titles(run(one, src2), "B")
    assert title in titles(run(two, src2), "B")
    # рекомендованная замена «Я уверен: X» → «Я уверен, что X» — не след правки, даже две
    src3 = "И я уверен: так будет лучше для всех. Мы уверены: участники это оценят."
    res3 = "И я уверен, что так будет лучше для всех. Мы уверены, что участники это оценят."
    assert title not in titles(run(res3, src3), "B")


# =============================================================================== P7: markdown
def test_markdown_stripped_before_b():
    # pikabu-26 (DEV): снятые ** у заголовка давали ложное «Новые вопросы»
    src = "**Не взяли на работу из-за веса. Что делать?**\n\nВ армию тоже не взяли из-за лишнего веса."
    res = "Не взяли на работу из-за веса. Что делать?\n\nВ армию тоже не взяли из-за лишнего веса."
    assert codes(run(res, src, mode="rewrite"), "B") == []
    # новая разметка по-прежнему след правки
    assert "Новая разметка, пункты, «Шаг N»" in titles(run(src, res, mode="rewrite"), "B")
    assert tk.strip_markdown("## Заголовок\n\n**Жирный** и *курсив*, `код`, [ссылка](https://x.ru)") == \
        "Заголовок\n\nЖирный и курсив, код, ссылка"


# =============================================================================== P8: калибровка A
def test_numbers_as_words_and_times():
    # opinion-281 (контроль DEV): время цифрами и словами — одно и то же
    src = "Теперь я работаю каждый день с 5:00 до 22:00 и засыпаю к 22:50."
    res = "Теперь работаю каждый день с пяти утра до десяти вечера, а засыпаю без десяти одиннадцать."
    assert "A1" not in codes(run(res, src, mode="rewrite"), "A")
    changed = "Теперь работаю каждый день с пяти утра до девяти вечера, а засыпаю без десяти одиннадцать."
    a1 = [f for f in run(changed, src, mode="rewrite").findings if f.code == "A1"]
    assert any("22:00" in f.message for f in a1) and any("21:00" in f.message for f in a1)
    # «десятилетняя» = 10, «полчаса» = «30 минут»
    for s, r in (("У меня есть десятилетняя племянница, она учит английский.",
                  "У меня есть племянница, ей десять, она учит английский."),
                 ("На настройку уходит полчаса, потом всё работает само.",
                  "На настройку уходит 30 минут, потом всё работает само.")):
        assert "A1" not in codes(run(r, s, mode="rewrite"), "A"), (s, r)


def test_number_word_compounds():
    vals = lambda t: set(check.numbers_in(tk.Doc(t)))  # noqa: E731
    assert "125" in vals("Пришло сто двадцать пять человек.")
    assert "2024" in vals("Это было в две тысячи двадцать четвёртом году, точнее в две тысячи двадцать четыре.")
    v = vals("Он пришёл без десяти одиннадцать.")
    assert "21" not in v and "~10:50" in v
    assert not any(":" in x for x in vals("Мы управились за 3 дня и две ночи."))   # сутки, а не время


def test_bound_comparative_is_not_negation():
    # yandex_q-87 (контроль DEV): «от F50» → «не ниже F50» — граница, а не перевёрнутое отрицание
    src = "Для наружных работ рекомендуют марки от F50."
    res = "Для наружных работ советуют брать не ниже F50."
    assert "A4" not in codes(run(res, src, mode="rewrite"), "A")
    assert "A4" not in codes(run("Оплатить нужно не позже 10-го числа.", "Оплатить нужно до 10-го числа."), "A")
    # без числа это обычное отрицание
    assert "A4" in codes(run("Новая версия лучше старой.", "Новая версия не лучше старой."), "A")


# =============================================================================== v3: блок B по DEV-замеру v2
LABEL_SENT = "Ярлык стал отдельной фразой («Суть простая.», «Сцена знакомая.»)"
MEAN_DROP = "Средняя фраза стала короче исходника (больше чем на 10%)"
TAK_CHTO = "Новые «так что» (больше +1 на 300 слов)"
GLUED = "Рамка мнения или источник приклеены через союз («…, и, как мне кажется, …»)"
NEW_DASH = "Новое тире на месте двоеточия или оборота"


@needs_morph
def test_label_turned_into_sentence_flagged():
    # tg_wayback-197 и opinion-303 (DEV v2): «Суть простая: X» → «Суть простая. X»
    src = ("Есть способ закрыть кредиты быстрее. Суть простая: первым гасится кредит с самой высокой ставкой. "
           "Сцена знакомая: отель, бассейн, девочка зовёт играть.")
    res = ("Есть способ закрыть кредиты быстрее. Суть простая. Первым гасится кредит с самой высокой ставкой. "
           "Сцена знакомая. Отель, бассейн, девочка зовёт играть.")
    rep = run(res, src, mode="rewrite")
    f = [x for x in rep.findings if x.title == LABEL_SENT]
    assert f and f[0].severity == "hard" and "в результате 2" in f[0].message
    # ярлык снят, раскрытие осталось — правильная замена
    ok = ("Есть способ закрыть кредиты быстрее. Первым гасится кредит с самой высокой ставкой. "
          "Отель, бассейн, девочка зовёт играть.")
    assert LABEL_SENT not in titles(run(ok, src, mode="rewrite"), "B")
    # такая же фраза уже была в исходнике — не новая
    assert LABEL_SENT not in titles(run(res, res, mode="rewrite"), "B")


@needs_morph
def test_label_sentence_detector_bounds():
    yes = ["Суть простая. Первым гасится кредит.", "Метод щадящий для психики. Прогресс виден сразу.",
           "Причина проста. Никто не читал инструкцию.", "Ответ простой. Надо работать каждый день."]
    no = ["Регулярность важнее идеального текста. Пост каждый день лучше.",     # сравнение — сказуемое
          "Сильная химия не нужна. Хватит тёплой воды.",                       # отрицание и «нужна»
          "Разговор не сложился. Племянница молчала.",                          # глагол
          "Первая часть. Тут всё просто.",                                      # порядковое
          "Моя история. Я пришёл в компанию весной.",                           # местоименное
          "Суть простая.\n\nПервым гасится кредит.",                            # раскрытие в другом абзаце
          "Итог хороший.",                                                      # раскрытия нет
          # правки моделей dev: обёртка, указатель, название-словосочетание, реплика в кавычках
          "Вот отредактированный вариант. Текст ниже.", "Значит, последний день. Завтра выходим.",
          "Магнитная лента для ножей. Крепится на стену.", "Бюджет на конкретный канал. Считаем отдельно.",
          "«Дерьмо дикое. Не берите."]
    for t in yes:
        assert tk.label_sentence(tk.Doc(t), 0), t
    for t in no:
        assert not tk.label_sentence(tk.Doc(t), 0), t


def test_mean_sentence_drop_hard_in_rewrite_soft_in_edit():
    src = ("Мы перевели рассылку на нейросеть в прошлом месяце, когда выпуски стали занимать весь вечер. "
           "Теперь выпуск собирается за час, а большая часть времени уходит на проверку фактов и ссылок. "
           "Подписчики разницы пока не заметили, хотя отписок за месяц стало чуть меньше.")
    split = ("Мы перевели рассылку на нейросеть в прошлом месяце. Выпуски стали занимать весь вечер. "
             "Теперь выпуск собирается за час. Большая часть времени уходит на проверку фактов и ссылок. "
             "Подписчики разницы пока не заметили, хотя отписок за месяц стало чуть меньше.")
    hard = [f for f in run(split, src, mode="rewrite").findings if f.title == MEAN_DROP]
    assert hard and hard[0].severity == "hard"
    assert hard[0].frags and hard[0].frags[0].where == "исходник"         # показана поделённая фраза
    soft = [f for f in run(split, src, mode="edit").findings if f.title == MEAN_DROP]
    assert soft and soft[0].severity == "soft" and soft[0].counted
    # склейка (средняя длиннее) и удалённый хвост-обёртка не в счёт
    joined = src.replace("весь вечер. Теперь", "весь вечер, и теперь")
    assert MEAN_DROP not in titles(run(joined, src, mode="rewrite"), "B")
    wrapped = src + "\n\nЕсли хотите, могу сократить пост, добавить хэштеги или адаптировать его под другой формат публикации."
    assert MEAN_DROP not in titles(run(src, wrapped, mode="rewrite"), "B")
    # короткий текст (меньше 3 фраз или 40 слов) не проверяется
    assert check.mean_drop(tk.Doc("Первая фраза довольно длинная, в ней девять слов всего. Вторая тоже."),
                           tk.Doc("Первая фраза довольно длинная. В ней девять слов всего. Вторая тоже.")) is None


def test_new_tak_chto_beyond_slack_flagged():
    src = ("Наушники быстро пачкаются: сера и пыль забивают сетку. Мыть их под краном нельзя: внутри электроника. "
           "Посудомойка тоже не вариант: корпус не выдержит температуры.")
    one = src.replace("Мыть их под краном нельзя: внутри электроника.", "Внутри электроника, так что мыть их под краном нельзя.")
    two = one.replace("Посудомойка тоже не вариант: корпус не выдержит температуры.",
                      "Корпус не выдержит температуры, так что посудомойка тоже не вариант.")
    assert TAK_CHTO not in titles(run(one, src), "B")
    assert TAK_CHTO in titles(run(two, src), "B")
    # «так, что» (образ действия) — не связка
    assert not check.rx(r"\bтак что\b").search("сделал так, что все довольны")


def test_frame_glued_flagged():
    # tg_wayback-299 и opinion-62 (DEV v2): рамку приклеили к предыдущей фразе
    for src, res in (
            ("Многие держатся подальше от всего, что связано с Россией. Как мне кажется, дело в общественном мнении.",
             "Многие держатся подальше от всего, что связано с Россией, и, как мне кажется, дело в общественном мнении."),
            ("LinkedIn для вас обязателен. По моему опыту, переходов на сайт отсюда больше.",
             "LinkedIn для вас обязателен, и, по моему опыту, переходов на сайт отсюда больше."),
            ("Тенденция уже наметилась. Уверен, что через год список подрастёт.",
             "Тенденция уже наметилась, и уверен, что через год список подрастёт.")):
        assert GLUED in titles(run(res, src, mode="rewrite"), "B"), res
    # рамка осталась отдельной фразой; та же склейка была в исходнике
    src = "Многие держатся подальше от всего, что связано с Россией. Как мне кажется, дело в общественном мнении."
    assert GLUED not in titles(run(src.replace("подальше от", "в стороне от"), src), "B")
    glued = "Можно спорить, но я уверен: решающим стало происхождение стартапа."
    assert GLUED not in titles(run(glued.replace("уверен:", "уверен, что"), glued), "B")


@needs_morph
def test_new_dash_in_place_of_colon_or_turn_flagged():
    for src, res in (
            # opinion-403 (DEV v2): «заключается в создании» → «— создать»
            ("Моя идея заключается в создании капсулы, которую можно вживить под кожу.",
             "Моя идея — создать капсулу, которую можно вживить под кожу."),
            ("Причина проста: никто не читал инструкцию до конца.",
             "Причина проста — никто не читал инструкцию до конца."),
            ("Он ушёл из офиса, хлопнув дверью на прощание.",
             "Он ушёл из офиса — хлопнул дверью на прощание.")):
        assert NEW_DASH in titles(run(res, src, mode="rewrite"), "B"), res
    for src, res in (
            # минус после двоеточия (yandex_q-87, v1): не тире на месте двоеточия
            ("Используют тот же интервал или изменённый: −50 и +20 °C.",
             "Используют тот же интервал или изменённый: −50 и +20 °C, без исключений."),
            # тире было и в исходнике
            ("Моя идея — создать капсулу, которую можно вживить под кожу.",
             "Моя идея — создать капсулу, которую можно вживить пациенту под кожу."),
            # «является» → «—»: грамматическое тире, для этого правила не оборот
            ("Москва является столицей России и крупнейшим городом страны.",
             "Москва — столица России и крупнейший город страны."),
            # тире не прибавилось: сняли причастный оборот перед уже стоявшим тире
            ("Задача, стоящая перед командой, — успеть до вечера все отчёты.",
             "Задача — успеть до вечера все отчёты, которые стоят перед командой.")):
        assert NEW_DASH not in titles(run(res, src, mode="rewrite"), "B"), res


# =============================================================================== v3: P8 — ложные тревоги
def test_line_numbering_is_not_a_number_or_new_markup():
    # tg_wayback-299 (DEV v2): рубрики «Первое. … Четвёртое.» → «1. … 4.» — не новые числа и не новая разметка
    src = ("Дальше всё пошло плохо по нескольким причинам.\n\nПервое. Основатели упустили момент для раунда.\n\n"
           "Второе. Они не рассчитали расходы.\n\nТретье. Конкуренты привлекли крупные суммы.")
    res = ("Дальше всё пошло плохо по нескольким причинам.\n\n1. Основатели упустили момент для раунда.\n"
           "2. Они не рассчитали расходы.\n3. Конкуренты привлекли крупные суммы.")
    rep = run(res, src, mode="rewrite")
    assert "A1" not in codes(rep, "A")
    assert "Новая разметка, пункты, «Шаг N»" not in titles(rep, "B")
    # эмодзи-цифры → «1. 2.» тоже
    src2 = "Программа:\n\n1️⃣ История и польза профессии.\n2️⃣ Компетенции и рост в работе."
    res2 = "Программа:\n\n1. История и польза профессии.\n2. Компетенции и рост в работе."
    assert "A1" not in codes(run(res2, src2, mode="rewrite"), "A")
    # число в начале строки, но не нумерация, — по-прежнему число
    assert "12" in check.numbers_in(tk.Doc("12 человек пришли на встречу."))
    assert "2" in check.numbers_in(tk.Doc("Купили 2 лицензии.\n3) Ещё одну."))
    assert "3" not in check.numbers_in(tk.Doc("Купили 2 лицензии.\n3) Ещё одну."))
    # нумерация без рубрик в исходнике — новая разметка
    plain = src.replace("Первое. ", "").replace("Второе. ", "").replace("Третье. ", "")
    assert "Новая разметка, пункты, «Шаг N»" in titles(run(res, plain, mode="rewrite"), "B")


def test_list_count_compared_by_content_not_order():
    # новый нумерованный список (из рубрик) не сравнивается с маркированным списком исходника
    src = ("Что взять в поход:\n- палатку\n- спальник\n- горелку\n\nПервое. Проверьте прогноз погоды.\n\n"
           "Второе. Скажите близким маршрут.")
    res = ("В поход возьмём палатку, спальник и горелку.\n\n1. Проверьте прогноз погоды.\n"
           "2. Скажите близким маршрут.")
    assert "Перечень: другое число пунктов" not in titles(run(res, src, mode="rewrite"), "A")
    # а тот же список с пропавшим пунктом — по-прежнему находка
    lost = src.replace("- горелку\n", "")
    assert "Перечень: другое число пунктов" in titles(run(lost, src), "A")


def test_md_headers_stripped_before_one_sentence_paragraphs():
    # habr_news-22, opinion-403 (DEV v2): снятый «## Подзаголовок» — не потерянный однофразный абзац
    src = ("Акционеры предложили лишить основателя поста. Голосование пройдёт в мае.\n\n## Позиция компании\n\n"
           "В компании предложение раскритиковали. Там считают, что всё работает.\n\n"
           "**Что дальше**\n\nСовет соберётся через месяц. Решение объявят сразу.")
    res = ("Акционеры предложили лишить основателя поста. Голосование пройдёт в мае.\n\n"
           "В компании предложение раскритиковали. Там считают, что всё работает.\n\n"
           "Совет соберётся через месяц. Решение объявят сразу.")
    t = titles(run(res, src, mode="rewrite"), "B")
    assert "Однофразных абзацев стало меньше" not in t
    # заголовок оставлен строкой без разметки — тоже не новый однофразный абзац и не новая фраза
    kept = res.replace("Голосование пройдёт в мае.\n\n", "Голосование пройдёт в мае.\n\nПозиция компании\n\n")
    assert "Однофразных абзацев стало меньше" not in titles(run(kept, src, mode="rewrite"), "B")
    assert tk.md_header_texts("🚀 **Кейс агентства: продвижение**\n\nТекст.") == {"🚀 кейс агентства: продвижение"}
    # настоящий однофразный абзац автора по-прежнему сверяется
    src2 = "Мы долго выбирали площадку.\n\nВыбрали старый цех.\n\nТам светло и просторно. Есть парковка."
    res2 = "Мы долго выбирали площадку и выбрали старый цех.\n\nТам светло и просторно. Есть парковка."
    assert "Однофразных абзацев стало меньше" in titles(run(res2, src2), "B")


@needs_morph
def test_yo_normalised_to_majority_allowed_minority_not():
    # opinion-134 (DEV v2): «её» при «нашел», «еще», «шел» — убрать «ё» можно
    src = "Нашел флешку, вставил её в плеер. Еще раз обновился. Шел уже второй час ночи."
    res = "Нашел флешку, вставил ее в плеер. Еще раз обновился. Шел уже второй час ночи."
    assert "B3" not in codes(run(res, src, mode="rewrite"), "B")
    # ё в меньшинстве: расставить её везде — против конвенции автора
    all_yo = "Нашёл флешку, вставил её в плеер. Ещё раз обновился. Шёл уже второй час ночи."
    assert any(f.code == "B3" and "против конвенции" in f.title for f in run(all_yo, src, mode="rewrite").findings)
    # ё в большинстве: убрать — нельзя, расставить в остальных словах — можно
    src2 = "Нашёл флешку, вставил её в плеер. Ещё раз обновился. Шел уже второй час ночи."
    assert "B3" in codes(run(res, src2, mode="rewrite"), "B")
    assert "B3" not in codes(run(all_yo, src2, mode="rewrite"), "B")


# =============================================================================== v3: P9 — точность блока A
@needs_morph
def test_name_lost_hard_only_in_aligned_sentence():
    # фраза уцелела, имя пропало — нарушение
    src = "Сбер открыл офис в Казани 12 марта. На открытие пришли 40 человек, гостей угощали кофе."
    rep = run(src.replace("Сбер открыл", "Банк открыл"), src)
    assert any(f.code == "A3" and f.severity == "hard" and "Сбер" in f.message for f in rep.findings)
    # та же фраза с синонимом вместо имени — пара есть, имя пропало: нарушение
    src2 = ("Мы тестировали Midjourney для обложек две недели. Картинки красивые, но долго. "
            "Команда решила вернуться к шаблонам.")
    syn = src2.replace("тестировали Midjourney", "тестировали нейросеть")
    assert any(f.code == "A3" and f.severity == "hard" for f in run(syn, src2).findings)
    # фраза переписана целиком (пары по леммам нет) — подсказка «сверь глазами», в счёт не идёт
    res2 = "Картинки для обложек нейросеть рисует красивые, но долго. Команда решила вернуться к шаблонам."
    rep2 = run(res2, src2, mode="rewrite")
    a3 = [f for f in rep2.findings if f.code == "A3"]
    assert a3 and all(f.severity == "note" and not f.counted for f in a3)
    assert "A3" not in codes(rep2, "A")


def test_capitalised_word_after_numbering_markup_or_emoji_is_not_a_name():
    # lifehacker-60, tg_wayback-229, opinion-62 (контроль DEV): «3. **Приготовьте…**», «2️⃣ **Компетенции…**»
    for t in ("3. **Приготовьте мыльный раствор.** Хватит тёплой воды.", "2️⃣ **Компетенции и рост**: мой путь.",
              "- **Ускоренные.** Используют тот же интервал.", "психолог пожмёт плечами 🙂 Суть простая: первым",
              "**Аватар.** При второй блокировке удаляют аватар."):
        names = [x for _, x, _ in check.name_candidates(tk.Doc(t))]
        assert not {"Приготовьте", "Компетенции", "Используют", "Суть", "При", "Хватит"} & set(names), (t, names)
    assert [x for _, x, _ in check.name_candidates(tk.Doc("Вчера мы встретили Сбер на выставке."))] == ["Сбер"]


@needs_morph
def test_aspect_change_hard_only_in_aligned_sentence():
    src = "Мы выполняли эту задачу вручную каждый вечер после смены."
    rep = run("Мы выполнили эту задачу вручную каждый вечер после смены.", src)
    assert any(f.code == "A6" and f.severity == "hard" for f in rep.findings)
    # «который настроит» → «чтобы настроил»: сослагательное, а не прошедшее (pikabu-177, контроль DEV)
    src2 = "Или стоит найти нормального специалиста, который всё настроит и разведёт провода как надо?"
    res2 = "Или стоит искать нормального мастера, чтобы всё настроил и развёл провода как надо?"
    assert not any(f.code == "A6" and "время" in f.message for f in run(res2, src2, mode="rewrite").findings)
    # вид поменялся у глагола в соседней, а не в парной фразе — подсказка
    src3 = ("Мы выполняли отчёты для отдела продаж каждую неделю. Клиенты ждали их по понедельникам. "
            "Потом всё изменилось.")
    res3 = ("Отчёты для отдела продаж готовили каждую неделю. Клиенты выполнили свою часть и ждали их "
            "по понедельникам. Потом всё изменилось.")
    a6 = [f for f in run(res3, src3, mode="rewrite").findings if f.code == "A6"]
    assert all(f.severity == "note" and not f.counted for f in a6)


def test_quote_lock():
    # pikabu-26 (контроль DEV): изменённая цитата не ловилась ничем
    src = "Мне прямо сказали: магазин не устраивают сотрудники «солидного веса». Обидно, но спорить не стал."
    bad = "Мне прямо сказали: магазин не устраивают сотрудники «солидной комплекции». Обидно, но спорить не стал."
    rep = run(bad, src, mode="rewrite")
    f = [x for x in rep.findings if x.code == "A12"]
    assert f and f[0].severity == "hard" and "солидного веса" in f[0].message
    # дословно, но другие кавычки, регистр и «ё» — не A12 (кавычки сверяет B2)
    same = src.replace("«солидного веса»", '"Солидного веса"')
    assert "A12" not in codes(run(same, src), "A")
    # короткое название без глагола можно склонять: «Истребитель проблем» → «Истребителя проблем»
    src2 = "Один из моих проектов — система «Истребитель проблем». Она помогает за месяц."
    res2 = "Среди моих проектов есть «Истребитель проблем». Он помогает за месяц."
    assert "A12" not in codes(run(res2, src2, mode="rewrite"), "A")
    # речь в кавычках склонять нельзя: «я не приду» → «я не пришёл»
    src3 = "Он написал: «я не приду на встречу». Мы перенесли её на пятницу."
    res3 = "Он написал: «я не пришёл на встречу». Мы перенесли её на пятницу."
    assert "A12" in codes(run(res3, src3), "A")
    # обёртка ответа в кавычках на весь текст — не цитата
    wrapped = "Вот пост:\n\n«Мы запустили бота в понедельник. Он отвечает клиентам за секунды.»"
    assert "A12" not in codes(run("Бот работает с понедельника и отвечает клиентам за секунды.", wrapped,
                                  mode="rewrite"), "A")
    assert check.quotes_in('Он сказал "привет" и «пока», а потом „ещё“.') == ["привет", "пока", "ещё"]


# =============================================================================== итог и CLI
def test_exit_code_rule():
    ai_like = (_metronome(26) + "\n\nПричина проста: всё работает. Вывод такой: внедряем. Итог понятный: довольны. "
               "Честно говоря, по-моему, это успех.")
    rep = run(ai_like, mode="rewrite", profile="claude", genre="post")
    assert not rep.passed
    human = "Вчера сходили в кино, фильм так себе, но попкорн был отличный."
    assert run(human, mode="rewrite", profile="claude", genre="post").passed


def test_cli_json_and_exit_codes(tmp_path):
    src = tmp_path / "src.txt"
    out = tmp_path / "out.txt"
    src.write_text("Платить надо строго до 10-го числа.", encoding="utf-8")
    out.write_text("Платить можно до 10-го числа.", encoding="utf-8")
    code = subprocess.run([sys.executable, str(SCRIPTS / "check.py"), "--source", str(src), "--result", str(out),
                           "--mode", "edit", "--json"], capture_output=True)
    assert code.returncode == 1
    data = json.loads(code.stdout.decode("utf-8"))
    assert data["passed"] is False and data["hard"] >= 1
    same = subprocess.run([sys.executable, str(SCRIPTS / "check.py"), "--source", str(src), "--result", str(src),
                           "--mode", "edit"], capture_output=True)
    assert same.returncode == 0
    assert "ПРОЙДЕНО" in same.stdout.decode("utf-8")


def test_fallback_without_morph_and_razdel(tmp_path):
    src = tmp_path / "src.txt"
    out = tmp_path / "out.txt"
    src.write_text("Мы выполняли задачу вручную. Платить надо до 10-го числа, а не в конце месяца.", encoding="utf-8")
    out.write_text("Мы выполнили задачу вручную. Платить можно в конце месяца.", encoding="utf-8")
    env = dict(os.environ, POCHERK_NO_MORPH="1", POCHERK_NO_RAZDEL="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPTS / "check.py"), "--source", str(src), "--result", str(out),
                        "--mode", "edit", "--profile", "gigachat", "--json"], capture_output=True, env=env)
    assert p.returncode == 1
    data = json.loads(p.stdout.decode("utf-8"))
    assert any("pymorphy3" in w for w in data["warnings"]) and any("razdel" in w for w in data["warnings"])
    found = {f["code"] for f in data["findings"]}
    assert {"A1", "A5", "A8"} <= found or {"A5", "A8"} <= found
    assert "A6" not in found                                    # вид глагола без морфологии не проверяется


def test_budgets_json_matches_markers():
    build_budgets = pytest.importorskip("build_budgets", reason="сборка бюджетов из корпуса в публичную версию не входит")
    markers = build_budgets.DEFAULT_MARKERS
    if not markers.exists():
        pytest.skip("markers.json исследования недоступен")
    fresh = build_budgets.build(markers)
    stored = json.loads((SCRIPTS / "budgets.json").read_text(encoding="utf-8"))
    assert fresh["counters"] == stored["counters"]
    assert fresh["rhythm"] == stored["rhythm"]
