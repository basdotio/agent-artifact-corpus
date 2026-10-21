"""Тесты v4: провенанс (E), подача (F), лента (G), источник и черновик в блоке A, страты бюджетов C.

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


def v4(result, source=None, draft=None, material=None, mode="rewrite", profile="core", genre="post", feed=None,
       assemble=False, source_kind=None):
    return check.run(result, source, mode, profile, genre, draft_text=draft, material_text=material, feed=feed,
                     assemble=assemble, source_kind=source_kind)


def find(rep, code, severities=("hard", "soft", "note")):
    return [f for f in rep.findings if f.code == code and f.severity in severities]


def sev(rep, code):
    fs = find(rep, code)
    return fs[0].severity if fs else None


# =============================================================================== A: источник и черновик
BRIEF = ("Кофейня на Ленина открылась 3 марта.\n"
         "Хозяйка — Анна Смирнова.\n"
         "Капучино стоит 180 рублей.\n"
         "Автор советует брать круассаны.")
DRAFT = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. "
         "Автор советует брать круассаны. В первый день пришли 250 гостей, и бариста Олег не успевал варить кофе. "
         "Это настоящий праздник для всего района!")


def test_a_draft_number_not_in_source_removed_is_cleanup_not_loss():
    res = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. "
           "Автор советует брать круассаны.")
    rep = v4(res, BRIEF, DRAFT)
    assert not [f for f in rep.findings if f.code in ("A1", "A3") and f.severity == "hard"], [
        (f.code, f.message) for f in rep.findings if f.block == "A"]
    cleaned = " ".join(rep.provenance["cleaned"])
    assert "250" in cleaned
    assert find(rep, "E7")


def test_a_source_number_lost_is_hard():
    res = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит недорого. "
           "Автор советует брать круассаны.")
    rep = v4(res, BRIEF, DRAFT)
    lost = [f for f in rep.findings if f.code == "A1" and f.title == "Числа: потеряны"]
    assert lost and "180" in lost[0].message


def test_a_number_restored_from_source_is_not_new():
    draft = "Кофейня на Ленина открылась весной. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей."
    res = "Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей."
    rep = v4(res, BRIEF, draft)
    assert not [f for f in rep.findings if f.code == "A1" and f.title == "Числа: новые"]


def test_a_old_call_unchanged():
    """Старый вызов --source черновик: потеря числа черновика — по-прежнему A1."""
    res = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. "
           "Автор советует брать круассаны. В первый день пришло много гостей.")
    rep = check.run(res, DRAFT, "rewrite", "core", "post")
    assert [f for f in rep.findings if f.code == "A1" and f.title == "Числа: потеряны"]
    assert not rep.provenance["distinct"]


@needs_morph
def test_a_draft_name_not_in_source_removed_is_cleanup():
    res = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. "
           "Автор советует брать круассаны. В первый день пришли 250 гостей.")
    rep = v4(res, BRIEF, DRAFT)
    assert not [f for f in rep.findings if f.code == "A3" and f.severity == "hard"]
    assert any("Олег" in w for w in rep.provenance["cleaned"])


def test_a_length_lower_bound_70_when_m_cut():
    brief = ("Мы переехали в новый офис на Садовой. Он больше старого в два раза. Переговорных теперь три. "
             "Кухня общая с соседями по этажу. Парковка платная, но рядом метро.")
    draft = brief + " Это настоящий праздник для всей нашей дружной команды!"
    res = brief                                       # 30 слов из 38 = 79%: между 70% и 85%
    rep = v4(res, brief, draft)
    assert rep.provenance["m_cut"]
    assert not find(rep, "A9")
    # v5: старый вызов (--source черновик) — rewrite без источника. Фраза с содержанием («праздник для команды»)
    # — «А?», её снятие — E8, а предел сокращения 10% считается без рамки модели: граница 90%
    rep_old = check.run(res, draft, "rewrite", "core", "post")
    assert rep_old.provenance["no_source"]
    assert "90–115% (без источника)" in find(rep_old, "A9")[0].title
    assert [f for f in find(rep_old, "E8") if f.severity == "hard"]
    # а снятая пустая формула — рамка модели: в предел не идёт, но перечисляется в заметке (E7)
    draft2 = brief + " Подписывайтесь на канал и делитесь постом с друзьями!"
    rep2 = check.run(res, draft2, "rewrite", "core", "post")
    assert not find(rep2, "A9") and not find(rep2, "E8")
    assert any("Подписывайтесь" in x for x in rep2.provenance["removed_m"])


def test_a_length_hard_below_85_without_m_cut():
    src = ("Мы переехали в новый офис на Садовой. Он больше старого в два раза. Переговорных теперь три. "
           "Кухня общая с соседями по этажу. Парковка платная, но рядом метро.")
    res = "Мы переехали в новый офис на Садовой. Он больше старого в два раза."
    rep = check.run(res, src, "edit", "core", "post")
    a9 = find(rep, "A9")
    assert a9 and a9[0].title == "Длина вне 85–115%"          # заголовок как в v3 (edit и rewrite с источником)
    rep = check.run(res, src, "rewrite", "core", "post")      # v5: rewrite без источника — граница 90%
    a9 = find(rep, "A9")
    assert a9 and a9[0].title == "Длина вне 90–115% (без источника)"


# =============================================================================== E: провенанс
def test_e1_last_sentence_m_flagged_with_source():
    res = DRAFT
    rep = v4(res, BRIEF, DRAFT)
    e1 = find(rep, "E1")
    assert e1 and "праздник" in e1[0].frags[0].text
    assert e1[0].severity == check.detector_sev("E1_last_m", True)
    assert rep.provenance["last_m"]


def test_e1_not_flagged_when_last_sentence_backed():
    res = ("Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. Кофейня на Ленина открылась 3 марта, "
           "и автор советует брать круассаны.")
    rep = v4(res, BRIEF, DRAFT)
    assert not find(rep, "E1")


def test_e2_number_from_draft_not_in_source_is_hard():
    rep = v4(DRAFT, BRIEF, DRAFT)
    e2 = [f for f in find(rep, "E2") if f.title.startswith("Числа")]
    assert e2 and e2[0].severity == "hard" and "250" in e2[0].message


def test_e2_small_word_number_is_derived_count():
    brief = "Офисы фонда — в Люксембурге, Лондоне и Берлине."
    draft = "У фонда три офиса: в Люксембурге, Лондоне и Берлине."
    rep = v4(draft, brief, draft)
    assert not [f for f in find(rep, "E2") if f.title.startswith("Числа")]


@needs_morph
def test_e2_invented_name_kept_but_abbreviation_is_not():
    rep = v4(DRAFT + " Отдел HR доволен.", BRIEF, DRAFT + " Отдел HR доволен.")
    names = [f for f in find(rep, "E2") if f.title.startswith("Имена")]
    assert names and "Олег" in names[0].message
    assert "HR" not in names[0].message
    # имена — мягкий флаг: точность 0,14 / 0,33 на TEST / DEV (e2_eval.json), числа — жёсткий (1,0 / 1,0)
    assert names[0].severity == check.detector_sev("E2_names", True) == "soft"
    assert check.detector_sev("E2_numbers", True) == "hard"


def test_e2_glued_digits_and_digit_one_are_not_new_numbers():
    brief = "LinkedIn остаётся сильным инструментом продвижения."
    draft = "LinkedIn остаётся сильным инструментом для B2B-продвижения: 1 пост в неделю уже даёт заявки."
    rep = v4(draft, brief, draft)
    assert not [f for f in find(rep, "E2") if f.title.startswith("Числа")]
    assert "2" not in check.numbers_in(tk.Doc("Рынок B2B и P2P-переводы."))


def test_e2_time_with_dot_matches_colon():
    brief = "Автор работает с 5:00 до 22:00 и засыпает к 22:50."
    draft = "Я вкалываю с 5 утра до 22.00 вечера, засыпаю до 22.50."
    rep = v4(draft, brief, draft)
    assert not [f for f in find(rep, "E2") if f.title.startswith("Числа")]
    nums = check.numbers_in(tk.Doc(draft))
    assert {"5:00", "22:00", "22:50"} <= set(nums)
    assert "15.3" in check.numbers_in(tk.Doc("Курс вырос до 15.30 рублей."))       # дробь с единицей — не время


@needs_morph
def test_e2_names_first_word_shout_and_part_of_known_name_not_flagged():
    brief = "Автор посмотрел фильм «Обряд» с Хопкинсом и просит совета, что ещё посмотреть."
    draft = ("Посмотрела «Обряд» с Энтони Хопкинсом. Постебалась над собой: боялась зря. "
             "ПОМОГИТЕЕЕ выбрать следующий фильм!")
    rep = v4(draft, brief, draft)
    names = [f for f in find(rep, "E2") if f.title.startswith("Имена")]
    assert not names, names[0].message if names else ""
    invented = draft + " Его советовал Михаил Айзенберг."
    names = [f for f in find(v4(invented, brief, invented), "E2") if f.title.startswith("Имена")]
    assert names and "Айзенберг" in names[0].message


def test_e2_latin_name_written_together_in_source():
    brief = "По опросу StackOverflow фреймворк самый востребованный."
    draft = "По опросу Stack Overflow 2021 года это самый востребованный фреймворк."
    rep = v4(draft, brief, draft)
    names = [f for f in find(rep, "E2") if f.title.startswith("Имена")]
    assert not names


@needs_morph
def test_e3_evaluative_word_not_in_source():
    brief = "Студия показала вертолёт «Скаут» на выставке."
    draft = "Студия показала инновационный вертолёт «Скаут» на выставке."
    rep = v4(draft, brief, draft)
    e3 = find(rep, "E3")
    assert e3 and "инновационный" in e3[0].message
    assert e3[0].severity == check.detector_sev("E3_eval", True)
    brief2 = "Студия показала инновационный вертолёт «Скаут» на выставке."
    assert not find(v4(draft, brief2, draft), "E3")


@needs_morph
def test_e4_author_phrase_without_material_is_hard():
    material = "Сходил в новую кофейню на Ленина. Капучино за 180, круассаны свежие, беру их каждый раз."
    res = ("Сходил в новую кофейню на Ленина. Капучино за 180, круассаны свежие. "
           "Я считаю, что это лучшее место для встреч с друзьями.")
    rep = v4(res, None, None, material, mode="write", assemble=True)
    e4 = find(rep, "E4")
    assert e4 and e4[0].severity == "hard" and "лучшее место" in e4[0].frags[0].text
    ok = "Сходил в новую кофейню на Ленина. Капучино за 180, круассаны свежие, беру их каждый раз."
    assert not find(v4(ok, None, None, material, mode="write", assemble=True), "E4")


def test_e5_assemble_bigram_share_warning():
    material = ("Вчера тестировал новую нейросеть для презентаций. Слайды собрала за минуту, но шрифты кривые. "
                "Для черновика годится, для клиента нет.")
    far = ("Современные технологии стремительно меняют подход к созданию презентаций и деловых материалов. "
           "Инструменты нового поколения экономят ресурсы команды и повышают качество визуала.")
    rep = v4(far, None, None, material, mode="write", assemble=True)
    e5 = find(rep, "E5")
    assert any("мало слов автора" in f.title for f in e5)
    near = "Вчера тестировал новую нейросеть для презентаций. Слайды собрала за минуту, но шрифты кривые."
    rep2 = v4(near, None, None, material, mode="write", assemble=True)
    assert not [f for f in find(rep2, "E5") if "мало слов" in f.title]
    assert rep2.provenance["assemble_bigrams"] >= 0.5


def test_e6_timid_edit_warning():
    draft = ("Хотите узнать, как пройти собеседование? Вы узнаете: какие вопросы задают, как готовиться. "
             "Переходите по ссылке и читайте гайд!")
    rep = v4(draft, None, draft)
    e6 = find(rep, "E6")
    assert e6 and e6[0].severity == "soft"
    assert rep.stats["change_share"] == 0
    changed = "В статье — какие вопросы задают на собеседовании и как к нему готовиться. Гайд по ссылке."
    assert not find(v4(changed, None, draft), "E6")


def test_changed_words_matches_round2_metric():
    a = "Кофейня открылась вчера, и гостей было много."
    b = "Кофейня открылась вчера. Гостей было очень много."
    assert check.changed_words(a, b) == 2
    assert check.change_share(a, a) == 0


def test_e7_cleaned_m_is_note_not_counted():
    res = ("Кофейня на Ленина открылась 3 марта. Хозяйка — Анна Смирнова. Капучино стоит 180 рублей. "
           "Автор советует брать круассаны.")
    e7 = find(v4(res, BRIEF, DRAFT), "E7")
    assert e7 and e7[0].severity == "note" and not e7[0].counted


def test_e1_dictation_source_ending_is_author():
    """Источник-диктовка: концовка из слов автора — А, не М; F1 по ней не срабатывает."""
    dictation = "Короче, попробовали новый тариф, отток упал. Спасибо всем, кто писал отзывы, правда помогло."
    res = "Попробовали новый тариф, отток упал. Спасибо всем, кто писал отзывы, правда помогло."
    rep = v4(res, dictation, None, mode="write", source_kind="dictation")
    assert rep.provenance["authored"]
    assert not find(rep, "E1") and not find(rep, "F1")


# =============================================================================== F: подача
@pytest.mark.parametrize("ending,kind", [("Спасибо, что дочитали!", "благодарность"),
                                         ("Желаю всем хороших выходных.", "пожелание"),
                                         ("А вы бы как поступили?", "вопрос читателю"),
                                         ("Таким образом, перемены пошли на пользу.", "итог")])
def test_f1_ending_kinds(ending, kind):
    text = "Мы провели три встречи с клиентами и поменяли тариф. Отток упал. " + ending
    f1 = find(check.run(text, None, "rewrite", "core", "post"), "F1")
    assert f1 and kind in f1[0].message


def test_f1_ending_moral_flagged_soft_without_source():
    text = ("Мы провели три встречи с клиентами и поменяли тариф. Отток упал. "
            "Главное — никогда не бояться перемен и всегда двигаться дальше.")
    rep = check.run(text, None, "rewrite", "core", "post")
    f1 = find(rep, "F1")
    assert f1 and f1[0].severity == check.detector_sev("F1_ending", False)


def test_f1_ending_with_number_not_flagged():
    text = "Мы провели три встречи с клиентами и поменяли тариф. Все подробности — на встрече 12 мая в 19:00."
    rep = check.run(text, None, "rewrite", "core", "post")
    assert not find(rep, "F1")


def test_f1_suppressed_when_ending_backed_by_source():
    brief = "Автор благодарит подписчиков за отклики на пост про ролевые модели и истории успеха."
    draft = "Пару дней назад говорили о ролевых моделях. Спасибо подписчикам за отклики и истории!"
    rep = v4(draft, brief, draft)
    assert not find(rep, "F1")


def test_f2_announcement_connectives():
    text = "Цены выросли на десять процентов. Важнее другое: поставки сорвались. Дальше — интереснее."
    f2 = find(check.run(text, None, "rewrite", "core", "post"), "F2")
    assert f2 and f2[0].severity == "soft" and len(f2[0].frags) == 2
    plain = "Итак, цены выросли на десять процентов. Поставки сорвались."
    assert not find(check.run(plain, None, "rewrite", "core", "post"), "F2")


@needs_morph
def test_f3_extra_explanation():
    text = ("Сервис хранит переписку только на устройстве пользователя. "
            "То есть переписка пользователя хранится только на его устройстве.")
    f3 = find(check.run(text, None, "rewrite", "core", "post"), "F3")
    assert f3 and f3[0].severity == "soft"
    new_fact = ("Сервис хранит переписку только на устройстве пользователя. "
                "То есть при потере телефона восстановить её нельзя.")
    assert not find(check.run(new_fact, None, "rewrite", "core", "post"), "F3")


PROMO = ("🔍 Хотите узнать, какие бывают собеседования в IT? 🌐\n\n"
         "В новой статье разобрали шесть видов интервью. Вы узнаете:\n\n"
         "- какие вопросы задают;\n- как готовиться к каждому этапу.\n\n"
         "Переходите по ссылке и читайте гайд!")


def test_f4_promo_frame_hard_by_measured_precision():
    f4 = find(check.run(PROMO, None, "rewrite", "gigachat", "post"), "F4")
    assert f4 and f4[0].severity == check.detector_sev("F4_promo", False)
    assert check.detector_sev("F4_promo", False) == "hard"           # точность 1,0 на TEST и DEV (REVIEW v4)
    assert "вопрос в зачине" in f4[0].message and "призыв" in f4[0].message


def test_f4_single_part_and_instruction_steps_not_promo():
    one = "Новая статья про собеседования в IT. Переходите по ссылке."
    assert not find(check.run(one, None, "rewrite", "gigachat", "post"), "F4")
    steps = ("Отключаем сбор геоданных на iPhone.\n\n"
             "🔹 Шаг 1: откройте «Настройки».\n\n🔹 Шаг 2: перейдите в «Службы геолокации».\n\n"
             "🔹 Шаг 3: выключите «Важные геопозиции».\n\nГотово.")
    assert not find(check.run(steps, None, "rewrite", "gigachat", "post"), "F4")


def test_f4_parts_from_author_text_not_counted_in_edit():
    rep = check.run(PROMO, PROMO, "edit", "gigachat", "post")
    assert not find(rep, "F4")


@pytest.mark.parametrize("ph", ["[уточнить: ссылка на статью]", "[ссылка]", "[имя автора]",
                                "[Читайте здесь →](ссылка-на-статью)"])
def test_f5_placeholders_hard_and_not_double_counted_in_c(ph):
    text = f"Гайд по собеседованиям вышел. Читать: {ph}"
    rep = check.run(text, None, "rewrite", "core", "post")
    assert sev(rep, "F5") == "hard"
    assert not [f for f in rep.findings if f.code == "CORE-15"]


def test_f5_ordinary_brackets_are_not_placeholders():
    text = "Об этом писали в отчёте [1]. Подробнее в разделе [Методика]."
    assert not find(check.run(text, None, "rewrite", "core", "post"), "F5")


def test_f6_subheadings_in_post():
    text = ("Мы запустили бота для соседей.\n\n## Как работает\n\nВводите адрес дома и смотрите профили соседей "
            "в радиусе полутора километров.\n\n**Сколько стоит**\n\nБот бесплатный, рекламы в нём нет, "
            "и платить ничего не нужно.")
    f6 = [f for f in find(check.run(text, None, "rewrite", "core", "post"), "F6") if "Подзаголовки" in f.title]
    assert f6 and "2" in f6[0].message
    assert not [f for f in find(check.run(text, None, "rewrite", "core", "guide"), "F6")]


def test_f6_title_line_in_post():
    text = "Как повысить пользу стендапов\n\nОбычно я советую их отменить. Но есть мягкий вариант: перевести общение в чат."
    f6 = [f for f in find(check.run(text, None, "rewrite", "core", "post"), "F6") if "Строка-заголовок" in f.title]
    assert f6


def test_f7_templates_gigachat_only_and_not_from_author():
    text = "Салават сдал экзамен со второй попытки. Это вдохновляющий пример: стремитесь к новым высотам."
    f7 = find(check.run(text, None, "rewrite", "gigachat", "post"), "F7")
    assert f7 and "вдохновляющий пример" in f7[0].message
    assert not find(check.run(text, None, "rewrite", "claude", "post"), "F7")
    assert not find(check.run(text, text, "edit", "gigachat", "post"), "F7")


# =============================================================================== G: лента
FEED_Q = [("2026-10-01", "Пост про модели. А вы что думаете?"), ("2026-10-02", "Пост про скиллы. А вы пробовали?")]


def test_g1_third_question_ending_in_a_row():
    rep = check.run("Пост про харнесс. Какой выберете вы?", None, "write", "claude", "post", feed=FEED_Q)
    g1 = find(rep, "G1")
    assert g1 and g1[0].severity == "soft" and "вопрос" in g1[0].message
    assert rep.feed["ending"] == "вопрос"


def test_g1_fact_ending_not_flagged():
    rep = check.run("Пост про харнесс. Код лежит на GitHub с 4 октября.", None, "write", "claude", "post",
                    feed=FEED_Q)
    assert not find(rep, "G1")
    assert find(rep, "G0")


def test_g2_third_same_opening_is_note():
    feed = [("2026-10-01", "Друзья, у нас новость. Текст."), ("2026-10-02", "Друзья, снова новость. Текст.")]
    rep = check.run("Друзья, ещё одна новость. Текст про харнесс.", None, "write", "claude", "post", feed=feed)
    g2 = find(rep, "G2")
    assert g2 and g2[0].severity == "note" and "обращение" in g2[0].message
    assert rep.passed or rep.hard == 0


def test_g1_needs_three_in_a_row():
    feed = [("2026-10-01", "Пост про модели. А вы что думаете?"), ("2026-10-02", "Пост про скиллы. Код на GitHub.")]
    rep = check.run("Пост про харнесс. Какой выберете вы?", None, "write", "claude", "post", feed=feed)
    assert not find(rep, "G1")


def test_g_types():
    assert check.ending_type(tk.Doc("Текст. Спасибо всем, кто пришёл!")) == "благодарность"
    assert check.ending_type(tk.Doc("Текст. Подписывайтесь на канал.")) == "призыв"
    assert check.ending_type(tk.Doc("Текст. Подробности: https://example.com")) == "ссылка"
    assert check.opening_type(tk.Doc("Друзья, у нас новость. Текст.")) == "обращение"
    assert check.opening_type(tk.Doc("Хотите узнать, как это работает? Текст.")) == "вопрос"
    assert check.opening_type(tk.Doc("Сегодня хочу поделиться находкой. Текст.")) == "анонс"


def test_read_feed_folder_of_post_dirs(tmp_path):
    for name, text in (("2026-10-02-b", "Второй. А вы?"), ("2026-10-01-a", "Первый. А вы?"),
                       ("2026-10-03-c", "Третий. Факт.")):
        d = tmp_path / name
        d.mkdir()
        (d / "post.txt").write_text(text, encoding="utf-8")
    feed = check.read_feed(str(tmp_path), 2)
    assert [n for n, _ in feed] == ["2026-10-02-b", "2026-10-03-c"]


# =============================================================================== C: страты и «!»
def test_c_strata_hard_final_formula_gigachat():
    text = ("Компания открыла склад в Казани и наняла сорок человек. Склад обслуживает три региона. "
            "Таким образом, доставка ускорится.")
    rep = check.run(text, None, "rewrite", "gigachat", "news")
    f = [x for x in rep.findings if x.code == "GIGA-02"]
    assert f and f[0].severity == "hard"
    assert check.stratum({"key": "final_formula"}, "gigachat", "news")["severity"] == "hard"


def test_c_soft_only_markers_never_hard():
    for key, profs in check.BUDGETS["strata"].items():
        for p, st in profs.items():
            if st["soft_only"]:
                assert st["severity"] != "hard", (key, p)


def test_c_excl_bound_to_source_any_profile():
    brief = "Кофейня открылась на Ленина. Капучино стоит 180 рублей."
    draft = "Кофейня открылась на Ленина! Капучино стоит 180 рублей."
    rep = v4(draft, brief, draft, profile="claude")
    f = [x for x in rep.findings if x.code == "YA-04"]
    assert f and "0: в источнике" in f[0].message
    brief2 = brief + " Ура!"
    assert not [x for x in v4(draft, brief2, draft, profile="claude").findings if x.code == "YA-04"]


def test_c_dash_override_gigachat_short_post():
    text = ("Кофейня на Ленина — новая. Капучино — 180 рублей, круассаны — свежие. Хозяйка — Анна. "
            "Открыто с восьми утра до десяти вечера, без выходных и перерывов на обед.")
    rep = check.run(text, None, "rewrite", "gigachat", "post")
    f = [x for x in rep.findings if x.code == "DASH-03"]
    assert f and f[0].severity == "soft" and "GigaChat в посте до 120 слов" in f[0].message
    assert not [x for x in check.run(text, None, "rewrite", "gigachat", "guide").findings if x.code == "DASH-03"]


# =============================================================================== CLI
def _cli(args, env=None):
    return subprocess.run([sys.executable, str(SCRIPTS / "check.py")] + args, capture_output=True, text=True,
                          encoding="utf-8", env=env)


def test_cli_v4_all_inputs_and_json(tmp_path):
    (tmp_path / "brief.txt").write_text(BRIEF, encoding="utf-8")
    (tmp_path / "draft.txt").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "out.txt").write_text(DRAFT + " Меню: [ссылка]", encoding="utf-8")
    (tmp_path / "mat.txt").write_text("Кофейня на Ленина, капучино за 180. Круассаны бери обязательно.",
                                      encoding="utf-8")
    feed = tmp_path / "feed"
    feed.mkdir()
    (feed / "a.txt").write_text("Первый пост. А вы?", encoding="utf-8")
    p = _cli(["--source", str(tmp_path / "brief.txt"), "--draft", str(tmp_path / "draft.txt"),
              "--material", str(tmp_path / "mat.txt"), "--feed", str(feed), "--result", str(tmp_path / "out.txt"),
              "--profile", "gigachat", "--json"])
    assert p.returncode == 1, p.stderr
    d = json.loads(p.stdout)
    assert d["provenance"]["distinct"] and d["provenance"]["last_m"]
    assert {f["block"] for f in d["findings"]} >= {"E", "F", "G"}
    t = _cli(["--source", str(tmp_path / "brief.txt"), "--draft", str(tmp_path / "draft.txt"),
              "--result", str(tmp_path / "out.txt")])
    assert "E. Провенанс" in t.stdout and "F. Подача" in t.stdout and "Черновик:" in t.stdout


def test_cli_assemble_sets_write_mode(tmp_path):
    (tmp_path / "mat.txt").write_text("Вчера тестировал нейросеть для слайдов. Шрифты кривые.", encoding="utf-8")
    (tmp_path / "out.txt").write_text("Вчера тестировал нейросеть для слайдов. Шрифты кривые.", encoding="utf-8")
    p = _cli(["--source", str(tmp_path / "mat.txt"), "--material", str(tmp_path / "mat.txt"),
              "--result", str(tmp_path / "out.txt"), "--assemble", "--json"])
    d = json.loads(p.stdout)
    assert d["mode"] == "write" and d["provenance"]["assemble_bigrams"] == 1.0


def test_cli_v4_fallback_without_libraries(tmp_path):
    (tmp_path / "brief.txt").write_text(BRIEF, encoding="utf-8")
    (tmp_path / "draft.txt").write_text(DRAFT, encoding="utf-8")
    (tmp_path / "out.txt").write_text(PROMO + " [ссылка]", encoding="utf-8")
    env = dict(os.environ, POCHERK_NO_MORPH="1", POCHERK_NO_RAZDEL="1", PYTHONIOENCODING="utf-8")
    p = _cli(["--source", str(tmp_path / "brief.txt"), "--draft", str(tmp_path / "draft.txt"),
              "--result", str(tmp_path / "out.txt"), "--profile", "gigachat", "--json"], env=env)
    assert p.returncode == 1, p.stderr
    d = json.loads(p.stdout)
    codes = {f["code"] for f in d["findings"]}
    assert {"F4", "F5"} <= codes


# =============================================================================== вердикт
def test_soft_e_f_g_are_hints_not_counted():
    """SKILL v4: мягкие E и F — подсказки; в счёт мягких (допустимо одно) идут только C и D."""
    text = ("Мы запустили бота для соседей.\n\n## Как работает\n\nВводите адрес дома и смотрите профили соседей "
            "в радиусе полутора километров.\n\n## Сколько стоит\n\nБот бесплатный, рекламы в нём нет. "
            "Главное — всегда помогать друг другу.")
    rep = check.run(text, None, "rewrite", "core", "post", feed=FEED_Q)
    efg = [f for f in rep.findings if f.block in "EFG" and f.severity == "soft"]
    assert {f.code for f in efg} >= {"F1", "F6"}
    assert not any(f.counted for f in efg)
    assert rep.soft == sum(1 for f in rep.findings if f.block in "CD" and f.severity == "soft" and f.counted)
    out = check.render(rep)
    assert "мягких (подсказки, не в счёт)" in out


def test_hard_f_still_fails():
    rep = check.run(PROMO, None, "rewrite", "gigachat", "post")
    assert rep.hard >= 1 and not rep.passed
