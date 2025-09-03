# handlers/groups/handlers.py
from aiogram import Router
from handlers.groups import add_students_groups, general_handlers, list_groups, name_groups_handler, save_handlers


router = Router()
router.include_router(general_handlers)
router.include_router(name_groups_handler)
router.include_router(save_handlers)
router.include_router(list_groups)
router.include_router(add_students_groups)