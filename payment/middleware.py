# payment/middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable
from .models import PaymentManager
from database import db  # Импортируем базу данных

class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self):
        # ⭐️ СПИСОК ПРЕМИУМ-ФУНКЦИЙ (только их проверяем)
        self.premium_commands = [
            '/premium', '/pro', '/expert', '/generate', '/analyze',
            '/deep', '/advanced', '/custom'
        ]
        
        self.premium_callbacks = [
            'edit_datetime', 'planner_', 'planner_add_task', 'planner_type_', 'planner_student_', 
            'planner_group_', 'planner_weekday_', 'planner_back_to_', 'back_to_planner', 'statistics_menu'
        ]

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        real_event = None
        
        if event.message:
            real_event = event.message
        elif event.callback_query:
            real_event = event.callback_query
        
        if not real_event:
            return await handler(event, data)
        
        # 🔥 ВАЖНО: ЕСЛИ ПОЛЬЗОВАТЕЛЬ АДМИН - ПРОПУСКАЕМ ВСЕ ПРОВЕРКИ
        user_id = real_event.from_user.id
        if db.is_admin(user_id):
            return await handler(event, data)
        
        # 🔍 Проверяем, является ли это премиум-функцией
        is_premium_feature = False
        
        if (isinstance(real_event, Message) and real_event.text and
            any(real_event.text.startswith(cmd) for cmd in self.premium_commands)):
            is_premium_feature = True
        
        elif (isinstance(real_event, CallbackQuery) and real_event.data and
              any(real_event.data.startswith(cb) for cb in self.premium_callbacks)):
            is_premium_feature = True
        
        # 🆓 Если это НЕ премиум-функция - пропускаем сразу
        if not is_premium_feature:
            return await handler(event, data)
        
        # ⭐️ Если это премиум-функция - проверяем подписку
        has_active_subscription = await PaymentManager.check_subscription(user_id)
        
        if not has_active_subscription:
            if isinstance(real_event, Message):
                await real_event.answer(
                    "❌ Это премиум-функция! Требуется активная подписка.\n\n"
                    "💎 Для доступа оформите подписку в настройках.",
                    reply_markup=data.get('reply_markup')
                )
            elif isinstance(real_event, CallbackQuery):
                # ⚡️ ВАЖНО: Используем всплывающее окно (alert) вместо сообщения
                await real_event.answer(
                    "❌ Это премиум-функция! Требуется активная подписка.\n\n"
                    "💎 Для доступа оформите подписку в настройках.",
                    show_alert=True  # ← ВОТ ЭТО КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
                )
            return
        
        return await handler(event, data)