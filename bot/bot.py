"""
Telegram-бот Ольги Чайки — контекстная версия.

Контекстные механики:
- Переменные: problem, duration, goal, contact, name
- Эхо-цепочка: каждый ответ отражается в заголовке следующего вопроса
- Персональный результат: собирается из трёх переменных контекста
- Уведомление специалисту: полная картина запроса

Конверсионные механики:
- Микро-коммиты: каждый шаг — маленькое «да», ведущее к записи
- Социальное доказательство: вплетено в текст, не отдельным блоком
- Фрейминг CTA: «Получить бесплатную консультацию» вместо «Записаться»
- Снятие страха: цена, формат и время отклика названы явно

Стек: Python 3.10+, aiogram 3.x, MemoryStorage.
"""

import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SPECIALIST_CHAT_ID = int(os.getenv("SPECIALIST_CHAT_ID", "0"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

router = Router()


# ---------------------------------------------------------------------------
# Состояния FSM
# ---------------------------------------------------------------------------

class Survey(StatesGroup):
    q_problem  = State()   # что беспокоит        → сохраняется в: problem
    q_duration = State()   # как давно             → сохраняется в: duration
    q_goal     = State()   # чего хотите достичь  → сохраняется в: goal
    q_contact  = State()   # способ связи          → сохраняется в: contact (q2)
    contact_ph = State()   # номер телефона
    question   = State()   # вопрос специалисту


# ---------------------------------------------------------------------------
# Данные: варианты ответов и эхо-реакции
# ---------------------------------------------------------------------------

# Q1: Проблема (problem)
PROBLEM_OPTIONS = {
    "stress":  "Стресс и нарушение сна",
    "pain":    "Боли в спине или шее",
    "fatigue": "Усталость и нехватка сил",
    "general": "Хочу подобрать метод",
}

# Эхо на problem → встраивается в заголовок вопроса про duration.
# «Услышали» — человек продолжает разговор.
PROBLEM_ECHO = {
    "stress":  "Стресс и нарушение сна — с этим работаем чаще всего.",
    "pain":    "Боли в спине и шее — это хорошо поддаётся работе.",
    "fatigue": "Усталость и нехватка сил — понятный и частый запрос.",
    "general": "Хорошо — подберём вместе на консультации.",
}

# Q2: Давность (duration)
DURATION_OPTIONS = {
    "less_month":  "Меньше месяца",
    "few_months":  "Несколько месяцев",
    "long_time":   "Больше года",
    "chronic":     "Давно, привык(ла)",
}

# Эхо на duration → встраивается в заголовок вопроса про goal.
DURATION_ECHO = {
    "less_month":  "Совсем недавно — хорошо, что обратились сразу.",
    "few_months":  "Несколько месяцев — уже достаточно, чтобы разобраться.",
    "long_time":   "Давно — тем важнее выбрать подходящий метод.",
    "chronic":     "Давно и привычно — с этим тоже работаем, мягко и без спешки.",
}

# Q3: Цель (goal)
GOAL_OPTIONS = {
    "fast":       "Снять симптом как можно скорее",
    "gradual":    "Восстановиться постепенно",
    "understand": "Понять причину и подобрать метод",
}

# Эхо на goal → встраивается в заголовок вопроса про контакт.
GOAL_ECHO = {
    "fast":       "Понятно — важна быстрая помощь.",
    "gradual":    "Постепенное восстановление — правильный подход.",
    "understand": "Разобраться в причине — хорошая стратегия.",
}

# problem → рекомендованные методы + базовый контекст
RECOMMENDATIONS = {
    "stress": {
        "methods": ("аурикулотерапию", "Су-Джок"),
        "context": (
            "Эти методы мягко влияют на нервную систему "
            "и помогают снять накопленное напряжение."
        ),
    },
    "pain": {
        "methods": ("баночный массаж", "Су-Джок"),
        "context": (
            "Работают с мышечным напряжением, улучшают "
            "кровоток и снимают зажатость в теле."
        ),
    },
    "fatigue": {
        "methods": ("гирудотерапию", "баночный массаж"),
        "context": (
            "Поддерживают кровообращение и обменные процессы — "
            "помогают восстановить тонус и силы."
        ),
    },
    "general": {
        "methods": ("индивидуальный подбор на консультации",),
        "context": (
            "Ольга подберёт подходящий метод "
            "после короткой беседы о вашем состоянии."
        ),
    },
}

# Дополнительный контекст на основе duration
DURATION_CONTEXT = {
    "less_month": "Вы обратились вовремя — на начальном этапе работа идёт легче.",
    "few_months": "",  # нейтральная давность — дополнительный контекст не нужен
    "long_time":  "Даже с давним состоянием — работаем мягко, результат приходит постепенно.",
    "chronic":    "Хронические состояния требуют регулярности — Ольга составит подходящий план.",
}

# Дополнительный контекст на основе goal
GOAL_CONTEXT = {
    "fast":       "Для быстрого результата подберём наиболее подходящий метод.",
    "gradual":    "Постепенный подход — самый устойчивый результат.",
    "understand": "На консультации разберём причину и выберем метод именно под вас.",
}

METHOD_TEXTS = {
    "hirudotherapy": (
        "<b>Гирудотерапия</b>\n\n"
        "Метод с применением медицинских пиявок.\n\n"
        "Природные вещества их слюны мягко влияют на кровообращение "
        "и обменные процессы. Применяют при усталости, нарушениях сна, "
        "ощущении тяжести в теле.\n\n"
        "<i>Первая консультация — бесплатно.</i>"
    ),
    "cupping": (
        "<b>Баночный массаж</b>\n\n"
        "Вакуумное воздействие на мышцы и ткани.\n\n"
        "Помогает снять зажатость в спине и шее, улучшить кровоток "
        "и расслабиться. Особенно подходит тем, кто много сидит "
        "или чувствует хроническое напряжение.\n\n"
        "<i>Первая консультация — бесплатно.</i>"
    ),
    "sujok": (
        "<b>Су-Джок</b>\n\n"
        "Воздействие на точки кистей и стоп.\n\n"
        "В восточной медицине кисть руки — проекция всего тела. "
        "Мягкий метод, подходит широкому кругу людей.\n\n"
        "<i>Первая консультация — бесплатно.</i>"
    ),
    "auriculotherapy": (
        "<b>Аурикулотерапия</b>\n\n"
        "Воздействие на активные точки ушной раковины.\n\n"
        "Применяют при стрессе, нарушениях сна и хроническом "
        "напряжении. Деликатная процедура без специальной подготовки.\n\n"
        "<i>Первая консультация — бесплатно.</i>"
    ),
}

METHOD_NAMES = {
    "hirudotherapy":   "Гирудотерапия",
    "cupping":         "Баночный массаж",
    "sujok":           "Су-Джок",
    "auriculotherapy": "Аурикулотерапия",
}


# ---------------------------------------------------------------------------
# Построение текстов
# ---------------------------------------------------------------------------

def get_display_name(user) -> str:
    if user.first_name:
        return user.first_name
    if user.username:
        return f"@{user.username}"
    return "Пользователь"


def build_duration_question(problem_key: str) -> str:
    """
    Вопрос про давность.
    Заголовок = эхо на problem → пользователь слышит своё слово → доверие.

    Пример:
      problem = "stress"
      → "Стресс и нарушение сна — с этим работаем чаще всего.
         Как давно это беспокоит?"
    """
    echo = PROBLEM_ECHO.get(problem_key, "Понял.")
    return f"{echo}\n\nКак давно это беспокоит?"


def build_goal_question(duration_key: str) -> str:
    """
    Вопрос про цель.
    Заголовок = эхо на duration.

    Пример:
      duration = "few_months"
      → "Несколько месяцев — уже достаточно, чтобы разобраться.
         Чего вы хотите достичь в первую очередь?"
    """
    echo = DURATION_ECHO.get(duration_key, "Понял.")
    return f"{echo}\n\nЧего вы хотите достичь в первую очередь?"


def build_contact_question(goal_key: str) -> str:
    """
    Вопрос про способ связи.
    Заголовок = эхо на goal.

    Пример:
      goal = "understand"
      → "Разобраться в причине — хорошая стратегия.
         Как Ольге удобнее передать вам результат?"
    """
    echo = GOAL_ECHO.get(goal_key, "Хорошо.")
    return f"{echo}\n\nКак Ольге удобнее передать вам результат подбора?"


def build_result_text(data: dict, name: str) -> str:
    """
    Персональный результат на основе трёх переменных: problem, duration, goal.

    Пример итогового текста:
      "Анна, вот что подходит вашему запросу:

      • аурикулотерапию
      • Су-Джок

      Эти методы мягко влияют на нервную систему и помогают снять накопленное напряжение.

      Разобраться в причине — хорошая стратегия. На консультации разберём причину
      и выберем метод именно под вас.

      Ольга работает с такими запросами регулярно и подберёт конкретный вариант
      на первой беседе.

      Первая консультация — бесплатно."
    """
    problem  = data.get("problem", "general")
    duration = data.get("duration", "")
    goal     = data.get("goal", "")

    rec = RECOMMENDATIONS.get(problem, RECOMMENDATIONS["general"])
    methods  = rec["methods"]
    context  = rec["context"]

    if len(methods) == 1:
        bullets = f"• {methods[0]}"
    else:
        bullets = "\n".join(f"• {m}" for m in methods)

    # Собираем дополнительные блоки только если они несут смысл
    duration_note = DURATION_CONTEXT.get(duration, "")
    goal_note     = GOAL_CONTEXT.get(goal, "")

    parts = [f"{name}, вот что подходит вашему запросу:\n\n{bullets}\n\n{context}"]

    if duration_note:
        parts.append(duration_note)

    if goal_note:
        parts.append(goal_note)

    parts.append(
        "Ольга работает с такими запросами регулярно "
        "и подберёт конкретный вариант на первой беседе.\n\n"
        "<i>Первая консультация — бесплатно.</i>"
    )

    return "\n\n".join(parts)


def build_specialist_notification(data: dict, user) -> str:
    """
    Уведомление специалисту — полная картина запроса.
    Ольга сразу видит: кто, с чем, как давно, чего хочет, как ответить.

    Пример:
      Новая заявка

      Имя: Анна
      Telegram: @anna_example
      Контакт: @anna_example

      Запрос: Стресс и нарушение сна
      Давность: Несколько месяцев
      Цель: Понять причину и подобрать метод
      Способ связи: Telegram
      Рекомендованные методы: аурикулотерапию, Су-Джок

      Дата: 07.03.2026 14:30
    """
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    problem_text  = PROBLEM_OPTIONS.get(data.get("problem", ""), "—")
    duration_text = DURATION_OPTIONS.get(data.get("duration", ""), "—")
    goal_text     = GOAL_OPTIONS.get(data.get("goal", ""), "—")
    q2_text       = "Telegram" if data.get("q2") == "tg" else "Телефон"
    contact       = data.get("contact", "—")
    username      = f"@{user.username}" if user.username else "нет username"

    rec = RECOMMENDATIONS.get(data.get("problem", ""), RECOMMENDATIONS["general"])
    methods_str = ", ".join(rec["methods"])

    return (
        "Новая заявка\n\n"
        f"Имя: {get_display_name(user)}\n"
        f"Telegram: {username}\n"
        f"Контакт: {contact}\n\n"
        f"Запрос: {problem_text}\n"
        f"Давность: {duration_text}\n"
        f"Цель: {goal_text}\n"
        f"Способ связи: {q2_text}\n"
        f"Рекомендованные методы: {methods_str}\n\n"
        f"Дата: {now}"
    )


def build_question_notification(user, question: str) -> str:
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    username = f"@{user.username}" if user.username else "нет username"
    return (
        "Вопрос от пользователя\n\n"
        f"Имя: {get_display_name(user)}\n"
        f"Telegram: {username}\n\n"
        f"Вопрос: {question}\n\n"
        f"Дата: {now}"
    )


# ---------------------------------------------------------------------------
# Клавиатуры
# ---------------------------------------------------------------------------

def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
            for row in rows
        ]
    )


def kb_start() -> InlineKeyboardMarkup:
    return kb([[("Да, давайте", "survey_start")]])


def kb_problem() -> InlineKeyboardMarkup:
    return kb([[(v, f"prob_{k}")] for k, v in PROBLEM_OPTIONS.items()])


def kb_duration() -> InlineKeyboardMarkup:
    return kb([[(v, f"dur_{k}")] for k, v in DURATION_OPTIONS.items()])


def kb_goal() -> InlineKeyboardMarkup:
    return kb([[(v, f"goal_{k}")] for k, v in GOAL_OPTIONS.items()])


def kb_contact() -> InlineKeyboardMarkup:
    return kb([
        [("Написать в Telegram", "q2_tg")],
        [("Позвонить мне",       "q2_phone")],
    ])


def kb_result() -> InlineKeyboardMarkup:
    return kb([
        [("Получить бесплатную консультацию", "book")],
        [("Узнать подробнее о методах",        "methods_menu")],
    ])


def kb_booked() -> InlineKeyboardMarkup:
    return kb([[("Вернуться в меню", "menu")]])


def kb_menu() -> InlineKeyboardMarkup:
    return kb([
        [("Пройти опрос",                     "survey_start")],
        [("Узнать о методах",                 "methods_menu")],
        [("Получить бесплатную консультацию", "book_direct")],
        [("Задать вопрос",                    "ask_question")],
    ])


def kb_methods() -> InlineKeyboardMarkup:
    return kb(
        [[(v, f"method_{k}")] for k, v in METHOD_NAMES.items()]
        + [[("← Назад в меню", "menu")]]
    )


def kb_method_back() -> InlineKeyboardMarkup:
    return kb([
        [("Получить бесплатную консультацию", "book")],
        [("← К списку методов",               "methods_menu")],
    ])


def kb_phone_share() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    source = message.text.split()[-1] if len(message.text.split()) > 1 else ""

    if source == "site":
        text = (
            "Здравствуйте.\n\n"
            "Меня зовут Ольга Чайка — специалист по натуральным "
            "методам оздоровления.\n\n"
            "Помогла более 120 людям с похожими запросами. "
            "Первая консультация — бесплатно.\n\n"
            "Расскажите немного о себе — подберём подходящий вариант."
        )
    else:
        text = (
            "Здравствуйте.\n\n"
            "Меня зовут Ольга Чайка — специалист по натуральным "
            "методам оздоровления.\n\n"
            "Помогу подобрать подходящий метод. "
            "Первая консультация — бесплатно.\n\n"
            "Это займёт меньше минуты."
        )

    await message.answer(text, reply_markup=kb_start())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Чем могу помочь?", reply_markup=kb_menu())


# ---------------------------------------------------------------------------
# Меню
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "menu")
async def cb_menu(cb: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("Чем могу помочь?", reply_markup=kb_menu())
    await cb.answer()


# ---------------------------------------------------------------------------
# Опрос: Q1 — Проблема (problem)
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "survey_start")
async def cb_survey_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Survey.q_problem)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "Что сейчас беспокоит больше всего?",
        reply_markup=kb_problem(),
    )
    await cb.answer()


@router.callback_query(Survey.q_problem, F.data.startswith("prob_"))
async def cb_problem(cb: CallbackQuery, state: FSMContext):
    """
    Сохраняет: problem = "stress" | "pain" | "fatigue" | "general"
    Следующий вопрос: duration (с эхо на problem в заголовке)
    """
    key = cb.data.removeprefix("prob_")
    await state.update_data(problem=key)
    await state.set_state(Survey.q_duration)
    await cb.message.edit_reply_markup(reply_markup=None)

    # Пример текста: "Боли в спине и шее — это хорошо поддаётся работе.
    #                 Как давно это беспокоит?"
    await cb.message.answer(
        build_duration_question(key),
        reply_markup=kb_duration(),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Опрос: Q2 — Давность (duration)
# ---------------------------------------------------------------------------

@router.callback_query(Survey.q_duration, F.data.startswith("dur_"))
async def cb_duration(cb: CallbackQuery, state: FSMContext):
    """
    Сохраняет: duration = "less_month" | "few_months" | "long_time" | "chronic"
    Следующий вопрос: goal (с эхо на duration в заголовке)
    """
    key = cb.data.removeprefix("dur_")
    await state.update_data(duration=key)
    await state.set_state(Survey.q_goal)
    await cb.message.edit_reply_markup(reply_markup=None)

    # Пример текста: "Несколько месяцев — уже достаточно, чтобы разобраться.
    #                 Чего вы хотите достичь в первую очередь?"
    await cb.message.answer(
        build_goal_question(key),
        reply_markup=kb_goal(),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Опрос: Q3 — Цель (goal)
# ---------------------------------------------------------------------------

@router.callback_query(Survey.q_goal, F.data.startswith("goal_"))
async def cb_goal(cb: CallbackQuery, state: FSMContext):
    """
    Сохраняет: goal = "fast" | "gradual" | "understand"
    Следующий вопрос: способ связи (с эхо на goal в заголовке)
    """
    key = cb.data.removeprefix("goal_")
    await state.update_data(goal=key)
    await state.set_state(Survey.q_contact)
    await cb.message.edit_reply_markup(reply_markup=None)

    # Пример текста: "Разобраться в причине — хорошая стратегия.
    #                 Как Ольге удобнее передать вам результат подбора?"
    await cb.message.answer(
        build_contact_question(key),
        reply_markup=kb_contact(),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Опрос: Q4 — Способ связи (contact)
# ---------------------------------------------------------------------------

@router.callback_query(Survey.q_contact, F.data == "q2_tg")
async def cb_q2_tg(cb: CallbackQuery, state: FSMContext):
    """
    Telegram: имя и контакт берём из профиля автоматически.
    Нет текстового ввода — нет барьера. Пользователь сразу видит результат.
    """
    name = get_display_name(cb.from_user)
    username = cb.from_user.username or ""
    contact = f"@{username}" if username else name

    await state.update_data(q2="tg", contact=contact)
    await state.set_state(None)
    await cb.message.edit_reply_markup(reply_markup=None)

    data = await state.get_data()
    await cb.message.answer(
        build_result_text(data, name),
        reply_markup=kb_result(),
    )
    await cb.answer()


@router.callback_query(Survey.q_contact, F.data == "q2_phone")
async def cb_q2_phone(cb: CallbackQuery, state: FSMContext):
    await state.update_data(q2="phone")
    await state.set_state(Survey.contact_ph)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "Укажите номер — Ольга позвонит в удобное время.",
        reply_markup=kb_phone_share(),
    )
    await cb.answer()


@router.message(Survey.contact_ph, F.contact)
async def msg_contact_shared(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(contact=phone)
    await state.set_state(None)
    data = await state.get_data()
    name = get_display_name(message.from_user)
    await message.answer(
        build_result_text(data, name),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("", reply_markup=kb_result())


@router.message(Survey.contact_ph)
async def msg_contact_phone_text(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(None)
    data = await state.get_data()
    name = get_display_name(message.from_user)
    await message.answer(
        build_result_text(data, name),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer("", reply_markup=kb_result())


# ---------------------------------------------------------------------------
# Запись на консультацию
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "book")
async def cb_book(cb: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    name = get_display_name(cb.from_user)

    if SPECIALIST_CHAT_ID:
        notification = build_specialist_notification(data, cb.from_user)
        await bot.send_message(SPECIALIST_CHAT_ID, notification)

    await cb.message.edit_reply_markup(reply_markup=None)

    # Подтверждение: конкретика снимает тревогу после нажатия кнопки.
    await cb.message.answer(
        f"Отлично, {name}.\n\n"
        "Ольга уже видит ваш запрос.\n\n"
        "Она напишет вам лично — обычно в течение нескольких часов.",
        reply_markup=kb_booked(),
    )
    await cb.answer()


@router.callback_query(F.data == "book_direct")
async def cb_book_direct(cb: CallbackQuery, state: FSMContext):
    """Прямая запись из меню — спрашиваем только способ связи."""
    await state.set_state(Survey.q_contact)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "Как Ольге удобнее с вами связаться?",
        reply_markup=kb_contact(),
    )
    await cb.answer()


# ---------------------------------------------------------------------------
# Вопрос специалисту
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "ask_question")
async def cb_ask_question(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Survey.question)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "Напишите ваш вопрос — Ольга ответит лично."
    )
    await cb.answer()


@router.message(Survey.question)
async def msg_question(message: Message, state: FSMContext, bot: Bot):
    notification = build_question_notification(message.from_user, message.text)
    if SPECIALIST_CHAT_ID:
        await bot.send_message(SPECIALIST_CHAT_ID, notification)
    await state.set_state(None)

    await message.answer(
        "Вопрос получен.\n\n"
        "Ольга ответит вам лично — обычно в течение нескольких часов.",
        reply_markup=kb_booked(),
    )


# ---------------------------------------------------------------------------
# Методы
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "methods_menu")
async def cb_methods_menu(cb: CallbackQuery):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        "Выберите метод, чтобы узнать подробнее:",
        reply_markup=kb_methods(),
    )
    await cb.answer()


@router.callback_query(F.data.startswith("method_"))
async def cb_method(cb: CallbackQuery):
    key = cb.data.removeprefix("method_")
    text = METHOD_TEXTS.get(key)
    if not text:
        await cb.answer("Метод не найден.")
        return
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(text, reply_markup=kb_method_back())
    await cb.answer()


# ---------------------------------------------------------------------------
# Запуск
# ---------------------------------------------------------------------------

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан. Заполните файл .env")
    if not SPECIALIST_CHAT_ID:
        log.warning("SPECIALIST_CHAT_ID не задан — уведомления не будут отправляться.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
