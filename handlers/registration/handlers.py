from aiogram import Router
from . import callbacks, messages

router = Router()
router.include_router(callbacks.router)
router.include_router(messages.router)