from aiogram import Router, types
from aiogram.filters import Command

from keyboards.registration import get_registration_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов
    """
    
    await message.answer(
        welcome_text,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )