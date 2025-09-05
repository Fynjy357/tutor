from aiogram import Router
from handlers.registration.callbacks import router as callbacks_router
from handlers.registration.messages import router as messages_router
from handlers.registration.states import RegistrationStates

router = Router()
router.include_router(callbacks_router)
router.include_router(messages_router)

__all__ = ['router', 'RegistrationStates']