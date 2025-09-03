from aiogram import Router
from handlers.registration.callbacks import router as callbacks_router
from handlers.registration.states import RegistrationStates

router = Router()
router.include_router(callbacks_router)

__all__ = ['router', 'RegistrationStates']