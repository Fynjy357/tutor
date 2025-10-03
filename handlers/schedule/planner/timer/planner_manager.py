# handlers/schedule/planner/timer/planner_manager.py
import logging
from datetime import datetime
from .planner_engine import planner_engine
from payment.models import PaymentManager  # Добавляем импорт

logger = logging.getLogger(__name__)

class PlannerManager:
    async def start_planner(self):
        """Запускает планер"""
        try:
            await planner_engine.start_planner()
            logger.info("Планер успешно запущен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при запуске планера: {e}")
            return False
    
    async def stop_planner(self):
        """Останавливает планер"""
        try:
            await planner_engine.stop_planner()
            logger.info("Планер успешно остановлен")
            return True
        except Exception as e:
            logger.error(f"Ошибка при остановке планера: {e}")
            return False
    
    async def force_check(self):
        """Принудительная проверка и создание занятий (игнорируя last_created)"""
        try:
            # Временно отключаем проверку last_created для принудительной проверки
            original_method = planner_engine._should_create_lessons
            planner_engine._should_create_lessons = lambda task: True
            
            await planner_engine._check_and_create_lessons()
            
            # Восстанавливаем оригинальный метод
            planner_engine._should_create_lessons = original_method
            
            logger.info("Принудительная проверка планера выполнена")
            return True
        except Exception as e:
            logger.error(f"Ошибка при принудительной проверке: {e}")
            return False
    
    def get_planner_status(self) -> dict:
        """Возвращает статус планера"""
        return {
            'is_running': planner_engine.is_running,
            'last_check': datetime.now().isoformat() if planner_engine.is_running else None
        }
    
    # 🔥 НОВЫЙ МЕТОД: Принудительная активация/деактивация для репетитора
    async def update_tutor_planner_status(self, telegram_id: int, has_subscription: bool):
        """Обновляет статус планера для репетитора"""
        try:
            from database import db

            
            tutor_id = db.get_tutor_id_by_telegram_id(telegram_id)
            if not tutor_id:
                logger.error(f"Репетитор не найден для telegram_id {telegram_id}")
                return False
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                if has_subscription:
                    # Включаем планер
                    cursor.execute('''
                    UPDATE planner_actions SET is_active = 1 WHERE tutor_id = ?
                    ''', (tutor_id,))
                    logger.info(f"Планер включен для репетитора {tutor_id}")
                else:
                    # Отключаем планер
                    cursor.execute('''
                    UPDATE planner_actions SET is_active = 0 WHERE tutor_id = ?
                    ''', (tutor_id,))
                    logger.info(f"Планер отключен для репетитора {tutor_id}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса планера для репетитора {telegram_id}: {e}")
            return False

planner_manager = PlannerManager()
