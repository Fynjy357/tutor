# handlers/schedule/planner/timer/planner_engine.py
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import db

from payment.models import PaymentManager  # Добавляем импорт

logger = logging.getLogger(__name__)

class PlannerEngine:
    def __init__(self):
        self.is_running = False
        self.task = None
    
    async def start_planner(self):
        """Запускает планер в фоновом режиме"""
        if self.is_running:
            logger.info("Планер уже запущен")
            return
        
        self.is_running = True
        self.task = asyncio.create_task(self._planner_loop())
        logger.info("Планер запущен")
    
    async def stop_planner(self):
        """Останавливает планер"""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Планер остановлен")
    
    async def _planner_loop(self):
        """Основной цикл планера"""
        while self.is_running:
            try:
                # Проверяем каждые 6 часов
                await self._check_and_create_lessons()
                await asyncio.sleep(7 * 24 * 60 * 60)  # 6 часов (было 7 дней)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле планера: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_create_lessons(self):
        """Проверяет и создает занятия на 2 недели вперед с проверкой подписки"""
        logger.info("Проверка планера: начало")
        
        try:
            planner_tasks = self._get_all_planner_tasks()
            
            if not planner_tasks:
                logger.info("Нет активных задач планера")
                return
            
            # 🔥 ГРУППИРУЕМ ЗАДАЧИ ПО РЕПЕТИТОРАМ И ПРОВЕРЯЕМ ПОДПИСКУ
            tutors_tasks = {}
            for task in planner_tasks:
                tutor_id = task['tutor_id']
                if tutor_id not in tutors_tasks:
                    tutors_tasks[tutor_id] = []
                tutors_tasks[tutor_id].append(task)
            
            for tutor_id, tasks in tutors_tasks.items():
                # Получаем telegram_id репетитора для проверки подписки
                telegram_id = self._get_tutor_telegram_id(tutor_id)
                if not telegram_id:
                    logger.warning(f"Не найден telegram_id для репетитора {tutor_id}")
                    continue
                
                # 🔥 ПРОВЕРЯЕМ ПОДПИСКУ
                has_active_subscription = await PaymentManager.check_subscription(telegram_id)
                
                if not has_active_subscription:
                    # Отключаем все задачи этого репетитора
                    self._deactivate_tutor_tasks(tutor_id)
                    logger.info(f"Планер отключен для репетитора {tutor_id} (нет подписки)")
                    continue
                
                # Если подписка активна - создаем занятия
                for task in tasks:
                    await self._create_lessons_for_task(task)
            
            logger.info(f"Проверка планера завершена. Обработано репетиторов: {len(tutors_tasks)}")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке планера: {e}")
    
    def _get_tutor_telegram_id(self, tutor_id: int) -> int:
        """Получает telegram_id репетитора"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT telegram_id FROM tutors WHERE id = ?', (tutor_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении telegram_id репетитора {tutor_id}: {e}")
            return None
    
    def _deactivate_tutor_tasks(self, tutor_id: int):
        """Отключает все задачи планера для репетитора"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE planner_actions SET is_active = 0 WHERE tutor_id = ?
                ''', (tutor_id,))
                conn.commit()
                logger.info(f"Отключено задач планера для репетитора {tutor_id}")
        except Exception as e:
            logger.error(f"Ошибка при отключении задач репетитора {tutor_id}: {e}")
    
    def _get_all_planner_tasks(self) -> List[Dict[str, Any]]:
        """Получает все активные задачи планера"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT pa.*, 
                    s.full_name as student_name,
                    g.name as group_name,
                    (SELECT COUNT(*) FROM lessons l WHERE l.planner_action_id = pa.id) as lessons_count
                FROM planner_actions pa
                LEFT JOIN students s ON pa.student_id = s.id
                LEFT JOIN groups g ON pa.group_id = g.id
                WHERE pa.is_active = TRUE
                ORDER BY pa.tutor_id, pa.weekday, pa.time
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении задач планера: {e}")
            return []
    
    async def _create_lessons_for_task(self, task: Dict[str, Any]):
        """Создает только недостающие занятия, не трогая существующие"""
        try:
            # Проверяем, нужно ли создавать занятия для этой задачи
            if not self._should_create_lessons(task):
                logger.debug(f"Пропускаем задачу {task['id']} - занятия уже актуальны")
                return
            
            target_dates = self._get_target_dates_for_weekday(task['weekday'])
            created_count = 0
            
            for target_date in target_dates:
                # Создаем только если занятия НЕТ или оно было удалено
                if not self._lesson_exists(task, target_date):
                    self._create_lesson(task, target_date)
                    created_count += 1
                    logger.info(f"Создано занятие: {task.get('student_name') or task.get('group_name')} на {target_date}")
                else:
                    logger.debug(f"Занятие уже существует: {target_date} - пропускаем")
            
            # Обновляем время последнего создания ТОЛЬКО если создали новые занятия
            if created_count > 0:
                self._update_last_created(task['id'])
                logger.info(f"Для задачи {task['id']} создано {created_count} новых занятий")
            else:
                logger.info(f"Для задачи {task['id']} все занятия уже существуют - ничего не создано")
        
        except Exception as e:
            logger.error(f"Ошибка при создании занятий для задачи {task['id']}: {e}")
    
    def _should_create_lessons(self, task: Dict[str, Any]) -> bool:
        """Проверяет, нужно ли создавать занятия для этой задачи"""
        # Проверяем, есть ли вообще будущие занятия для этой задачи
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT COUNT(*) FROM lessons 
            WHERE planner_action_id = ? 
            AND lesson_date > datetime('now')
            ''', (task['id'],))
            
            has_future_lessons = cursor.fetchone()[0] > 0
        
        # Если есть будущие занятия - не создаем новые
        if has_future_lessons:
            logger.debug(f"Задача {task['id']} имеет будущие занятия - пропускаем")
            return False
        
        # Если будущих занятий нет - создаем
        logger.debug(f"Задача {task['id']} не имеет будущих занятий - создаем")
        return True

    def _get_target_dates_for_weekday(self, weekday: str) -> List[datetime]:
        """Получает даты на 2 недели вперед для указанного дня недели"""
        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_weekday = weekday_map[weekday.lower()]
        today = datetime.now().date()
        dates = []
        
        # Смотрим на 2 недели вперед (14 дней)
        for days_ahead in range(21):
            future_date = today + timedelta(days=days_ahead)
            if future_date.weekday() == target_weekday:
                dates.append(future_date)
        
        return dates
    
    def _lesson_exists(self, task: Dict[str, Any], planned_date: datetime) -> bool:
        """Проверяет, есть ли уже занятие для этой задачи на ЭТОЙ неделе"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Находим начало и конец недели для planned_date
                week_start = planned_date - timedelta(days=planned_date.weekday())
                week_end = week_start + timedelta(days=6)
                
                # Проверяем, есть ли ЛЮБОЕ занятие этой задачи на этой неделе
                cursor.execute('''
                SELECT COUNT(*) FROM lessons 
                WHERE planner_action_id = ? 
                AND DATE(lesson_date) BETWEEN DATE(?) AND DATE(?)
                ''', (task['id'], week_start, week_end))
                
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # Логируем для отладки
                    cursor.execute('''
                    SELECT lesson_date FROM lessons 
                    WHERE planner_action_id = ? 
                    AND DATE(lesson_date) BETWEEN DATE(?) AND DATE(?)
                    LIMIT 1
                    ''', (task['id'], week_start, week_end))
                    
                    existing_lesson_date = cursor.fetchone()
                    if existing_lesson_date:
                        logger.debug(f"Занятие на неделе {week_start.strftime('%Y-%m-%d')} уже существует: {existing_lesson_date[0]}")
                
                return exists
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке существования занятия: {e}")
            return True

    def delete_lessons_by_planner_action(self, planner_action_id: int):
        """Удаляет все занятия, связанные с задачей планера"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                DELETE FROM lessons WHERE planner_action_id = ?
                ''', (planner_action_id,))
                conn.commit()
                logger.info(f"Удалены занятия для задачи планера {planner_action_id}")
        except Exception as e:
            logger.error(f"Ошибка при удалении занятий для задачи {planner_action_id}: {e}")

    def get_lessons_by_planner_action(self, planner_action_id: int) -> List[Dict[str, Any]]:
        """Получает все занятия, созданные по задаче планера"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM lessons WHERE planner_action_id = ? ORDER BY lesson_date
                ''', (planner_action_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении занятий для задачи {planner_action_id}: {e}")
            return []

    def _create_lesson(self, task: Dict[str, Any], lesson_date: datetime):
        """Создает занятие в базе данных"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                lesson_time = datetime.strptime(task['time'], '%H:%M').time()
                lesson_datetime = datetime.combine(lesson_date, lesson_time)
                
                if task.get('student_id'):
                    # Индивидуальное занятие
                    cursor.execute('''
                    INSERT INTO lessons (tutor_id, student_id, lesson_date, duration, price, status, planner_action_id)
                    VALUES (?, ?, ?, ?, ?, 'planned', ?)
                    ''', (task['tutor_id'], task['student_id'], lesson_datetime, 
                        task['duration'], task['price'], task['id']))
                else:
                    # Групповое занятие
                    cursor.execute('''
                    SELECT student_id FROM student_groups WHERE group_id = ?
                    ''', (task['group_id'],))
                    
                    students = cursor.fetchall()
                    
                    for student in students:
                        cursor.execute('''
                        INSERT INTO lessons (tutor_id, student_id, group_id, lesson_date, duration, price, status, planner_action_id)
                        VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
                        ''', (task['tutor_id'], student[0], task['group_id'], lesson_datetime,
                            task['duration'], task['price'], task['id']))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка при создании занятия: {e}")
            raise

    def _update_last_created(self, task_id: int):
        """Обновляет время последнего создания занятий для задачи"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE planner_actions SET last_created = ? WHERE id = ?
                ''', (datetime.now(), task_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении last_created для задачи {task_id}: {e}")

planner_engine = PlannerEngine()
