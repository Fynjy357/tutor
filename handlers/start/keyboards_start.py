# keyboards/registration.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup, InlineKeyboardButton

def get_registration_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Зарегистрироваться",
            callback_data="start_registration"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="О боте",
            callback_data="about_bot"
        )
    )
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Отменить регистрацию",
            callback_data="cancel_registration"
        )
    )
    return builder.as_markup()
def get_promo_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Пропустить",
            callback_data="skip_promo"
        )
    )
    return builder.as_markup()

#Клавиатура для родителей
def get_parent_welcome_keyboard() -> InlineKeyboardMarkup:
    """Создает инлайн клавиатуру для родителя"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Посмотреть задолженности", 
                    callback_data="parent_homeworks"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Посмотреть неоплаченные занятия", 
                    callback_data="parent_unpaid_lessons"
                )
            ]
        ]
    )
    
    return keyboard

#Клавиатура для учеников
def get_student_welcome_keyboard() -> InlineKeyboardMarkup:
    """Создает инлайн клавиатуру для ученика"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Посмотреть домашние работы", 
                    callback_data="stud_view_homeworks"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Посмотреть неоплаченные занятия", 
                    callback_data="stud_view_unpaid"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Предстоящие занятия", 
                    callback_data="stud_view_upcoming"
                )
            ]
        ]
    )
    return keyboard