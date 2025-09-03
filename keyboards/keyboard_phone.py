from aiogram.utils.keyboard import  ReplyKeyboardMarkup, KeyboardButton

def get_phone_keyboard():
    # Создаем Reply-клавиатуру (не инлайн) для запроса номера телефона
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )