import sqlite3
import logging
import uuid
from datetime import date, datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='tutor_bot.db'):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Создает и возвращает соединение с базой данных"""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Инициализирует базу данных и создает таблицы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей (репетиторов)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                promo_code TEXT DEFAULT '0',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
            ''')
            
            # Таблица учеников
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT,
                parent_phone TEXT,
                status TEXT DEFAULT 'active',
                tutor_id INTEGER,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                student_telegram_id INTEGER,
                parent_telegram_id INTEGER,
                student_token TEXT UNIQUE,
                parent_token TEXT UNIQUE,
                delete_after TIMESTAMP,
                student_username TEXT,
                parent_username TEXT,
                FOREIGN KEY (tutor_id) REFERENCES tutors (id)
            )
            ''')
            
            # Таблица занятий
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tutor_id INTEGER,
                student_id INTEGER,
                lesson_date TIMESTAMP,
                duration INTEGER,
                price REAL,
                status TEXT DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tutor_id) REFERENCES tutors (id),
                FOREIGN KEY (student_id) REFERENCES students (id)
            )
            ''')
            
            # Таблица промокодов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_percent INTEGER DEFAULT 0,
                discount_amount REAL DEFAULT 0,
                valid_until TIMESTAMP,
                usage_limit INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            )
            ''')
            
            # Таблица групп
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                tutor_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tutor_id) REFERENCES tutors (id)
            )
            ''')
            
            # Таблица связи учеников и групп
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                group_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students (id),
                FOREIGN KEY (group_id) REFERENCES groups (id),
                UNIQUE(student_id, group_id)
            )
            ''')
            
            conn.commit()
        logger.info("База данных инициализирована")

    def add_tutor(self, telegram_id, full_name, phone, promo_code='0'):
        """Добавляет нового репетитора в базу данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO tutors (telegram_id, full_name, phone, promo_code)
                VALUES (?, ?, ?, ?)
                ''', (telegram_id, full_name, phone, promo_code))
                conn.commit()
                logger.info(f"Добавлен репетитор: {full_name}")
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении репетитора: {e}")
            return None

    def get_tutor_by_telegram_id(self, telegram_id):
        """Возвращает данные репетитора по telegram_id"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tutors WHERE telegram_id = ?', (telegram_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении репетитора: {e}")
            return None

    def get_tutor_by_id(self, tutor_id):
        """Возвращает данные репетитора по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tutors WHERE id = ?', (tutor_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении репетитора по ID: {e}")
            return None

    def update_tutor(self, telegram_id, full_name=None, phone=None, promo_code=None):
        """Обновляет данные репетитора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if full_name:
                    updates.append("full_name = ?")
                    params.append(full_name)
                if phone:
                    updates.append("phone = ?")
                    params.append(phone)
                if promo_code:
                    updates.append("promo_code = ?")
                    params.append(promo_code)
                    
                if updates:
                    params.append(telegram_id)
                    cursor.execute(f'UPDATE tutors SET {", ".join(updates)} WHERE telegram_id = ?', params)
                    conn.commit()
                    logger.info(f"Обновлены данные репетитора: {telegram_id}")
                    return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении репетитора: {e}")
            return False

    def check_promo_code(self, promo_code):
        """Проверяет валидность промокода"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM promo_codes 
                WHERE code = ? AND is_active = TRUE 
                AND (valid_until IS NULL OR valid_until > datetime('now'))
                AND (usage_limit IS NULL OR used_count < usage_limit)
                ''', (promo_code,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при проверке промокода: {e}")
            return None

    def use_promo_code(self, promo_code):
        """Увеличивает счетчик использования промокода"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE promo_codes SET used_count = used_count + 1 
                WHERE code = ? AND is_active = TRUE
                ''', (promo_code,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при использовании промокода: {e}")
            return False
    
    def add_student(self, full_name, phone, parent_phone, status, tutor_id):
        """Добавляет нового ученика"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO students (full_name, phone, parent_phone, status, tutor_id)
                VALUES (?, ?, ?, ?, ?)
                ''', (full_name, phone, parent_phone, status, tutor_id))
                conn.commit()
                logger.info(f"Добавлен ученик: {full_name}")
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении ученика: {e}")
            return None

    def get_students_by_tutor(self, tutor_id):
        """Получает всех учеников репетитора"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM students 
                WHERE tutor_id = ? 
                ORDER BY full_name
                ''', (tutor_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении учеников: {e}")
            return []

    def get_student_by_id(self, student_id):
        """Получает ученика по ID"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ученика: {e}")
            return None

    def get_tutor_id_by_telegram_id(self, telegram_id):
        """Получает ID репетитора по telegram_id"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM tutors WHERE telegram_id = ?', (telegram_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ID репетитора: {e}")
            return None

    def generate_invite_token(self):
        """Генерирует уникальный токен для приглашения"""
        return str(uuid.uuid4())

    def update_student_token(self, student_id, token, token_type):
        """Обновляет токен приглашения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if token_type == 'student':
                    cursor.execute('UPDATE students SET student_token = ? WHERE id = ?', (token, student_id))
                else:
                    cursor.execute('UPDATE students SET parent_token = ? WHERE id = ?', (token, student_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            return False

    def get_student_by_token(self, token, token_type):
        """Находит ученика по токену"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                if token_type == 'student':
                    cursor.execute('SELECT * FROM students WHERE student_token = ?', (token,))
                else:
                    cursor.execute('SELECT * FROM students WHERE parent_token = ?', (token,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при поиске ученика по токену: {e}")
            return None

    def update_student_telegram_id(self, student_id, telegram_id, username, user_type):
        """Привязывает Telegram аккаунт к ученику"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if user_type == 'student':
                    cursor.execute(
                        'UPDATE students SET student_telegram_id = ?, student_username = ? WHERE id = ?',
                        (telegram_id, username, student_id)
                    )
                else:
                    cursor.execute(
                        'UPDATE students SET parent_telegram_id = ?, parent_username = ? WHERE id = ?',
                        (telegram_id, username, student_id)
                    )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при привязке Telegram аккаунта: {e}")
            return False

    def block_student(self, student_id, delete_after=None):
        """Блокирует ученика"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE students SET status = "blocked", delete_after = ? WHERE id = ?',
                    (delete_after, student_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при блокировке ученика: {e}")
            return False

    def unblock_student(self, student_id):
        """Разблокирует ученика"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE students SET status = "active", delete_after = NULL WHERE id = ?',
                    (student_id,)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при разблокировке ученика: {e}")
            return False

    def update_student(self, student_id, full_name=None, phone=None, parent_phone=None, status=None):
        """Обновляет данные ученика"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                updates = []
                params = []
                
                if full_name:
                    updates.append("full_name = ?")
                    params.append(full_name)
                if phone:
                    updates.append("phone = ?")
                    params.append(phone)
                if parent_phone:
                    updates.append("parent_phone = ?")
                    params.append(parent_phone)
                if status:
                    updates.append("status = ?")
                    params.append(status)
                    
                if updates:
                    params.append(student_id)
                    cursor.execute(f'UPDATE students SET {", ".join(updates)} WHERE id = ?', params)
                    conn.commit()
                    logger.info(f"Обновлены данные ученика: {student_id}")
                    return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении ученика: {e}")
            return False
        
    def update_student_field(self, student_id, field_name, field_value):
        """Обновляет конкретное поле ученика"""
        try:
            # Используйте self.get_connection() вместо self.conn
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE students SET {field_name} = ? WHERE id = ?",
                    (field_value, student_id)
                )
                conn.commit()  # Явное сохранение изменений
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении поля {field_name} ученика {student_id}: {e}")
            return False
        
    def get_lessons_by_date_range(self, tutor_id: int, start_date: date, end_date: date):
        """Получает занятия репетитора за период с полной информацией"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id,
                    l.tutor_id,
                    l.student_id,
                    l.lesson_date,
                    l.duration,
                    l.price,
                    l.status,
                    l.created_at,
                    s.full_name as student_name,
                    s.phone as student_phone,
                    s.grade as student_grade,
                    s.school as student_school
                FROM lessons l
                LEFT JOIN students s ON l.student_id = s.id
                WHERE l.tutor_id = ? AND date(l.lesson_date) BETWEEN ? AND ?
                ORDER BY l.lesson_date
                ''', (tutor_id, start_date, end_date))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении занятий: {e}")
            return []
    def get_lessons_by_student(self, student_id: int):
        """Получает все занятия студента"""
        try:
                with self.get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute('''
                    SELECT l.*, t.full_name as tutor_name
                    FROM lessons l
                    LEFT JOIN tutors t ON l.tutor_id = t.id
                    WHERE l.student_id = ?
                    ORDER BY l.lesson_date DESC
                    ''', (student_id,))
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении занятий студента: {e}")
        return []

    def get_upcoming_lessons(self, tutor_id: int, days: int = 7):
        """Получает ближайшие занятия репетитора"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Отладочная информация
                print(f"Поиск занятий для tutor_id: {tutor_id}")
                
                # Сначала посмотрим ВСЕ занятия этого репетитора
                cursor.execute('''
                SELECT l.*, s.full_name as student_name
                FROM lessons l
                LEFT JOIN students s ON l.student_id = s.id
                WHERE l.tutor_id = ?
                ORDER BY l.lesson_date
                ''', (tutor_id,))
                
                all_lessons = [dict(row) for row in cursor.fetchall()]
                print(f"Все занятия репетитора: {len(all_lessons)}")
                for lesson in all_lessons:
                    print(f"Урок: {lesson}")
                
                # Теперь ищем ближайшие
                cursor.execute('''
                SELECT l.*, s.full_name as student_name
                FROM lessons l
                LEFT JOIN students s ON l.student_id = s.id
                WHERE l.tutor_id = ? 
                AND l.lesson_date >= datetime('now')
                AND l.lesson_date <= datetime('now', ? || ' days')
                AND l.status = 'planned'
                ORDER BY l.lesson_date
                ''', (tutor_id, days))
                
                result = [dict(row) for row in cursor.fetchall()]
                print(f"Найдено ближайших занятий: {len(result)}")
                
                return result
                
        except Exception as e:
            logger.error(f"Ошибка при получении ближайших занятий: {e}")
            print(f"Ошибка: {e}")
            return []
        
    def add_lesson(self, tutor_id: int, student_id: int, lesson_date: str, 
               duration: int, price: float):
        """Добавляет новое занятие"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO lessons (tutor_id, student_id, lesson_date, duration, price)
                VALUES (?, ?, ?, ?, ?)
                ''', (tutor_id, student_id, lesson_date, duration, price))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении занятия: {e}")
            return None
        
    def add_group(self, name: str, tutor_id: int):
        """Добавляет новую группу"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO groups (name, tutor_id)
                VALUES (?, ?)
                ''', (name, tutor_id))
                conn.commit()
                logger.info(f"Добавлена группа: {name}")
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении группы: {e}")
            return None

    def get_groups_by_tutor(self, tutor_id: int):
        """Получает все группы репетитора"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT g.*, COUNT(sg.student_id) as student_count
                FROM groups g
                LEFT JOIN student_groups sg ON g.id = sg.group_id
                WHERE g.tutor_id = ?
                GROUP BY g.id
                ORDER BY g.name
                ''', (tutor_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении групп: {e}")
            return []

    def get_group_by_id(self, group_id: int):
        """Получает группу по ID"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM groups WHERE id = ?', (group_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении группы: {e}")
            return None

    def add_student_to_group(self, student_id: int, group_id: int):
        """Добавляет ученика в группу"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT OR IGNORE INTO student_groups (student_id, group_id)
                VALUES (?, ?)
                ''', (student_id, group_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при добавлении ученика в группу: {e}")
            return False

    def remove_student_from_group(self, student_id: int, group_id: int):
        """Удаляет ученика из группы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                DELETE FROM student_groups 
                WHERE student_id = ? AND group_id = ?
                ''', (student_id, group_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении ученика из группы: {e}")
            return False

    def get_students_in_group(self, group_id: int):
        """Получает всех учеников в группе"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT s.* 
                FROM students s
                JOIN student_groups sg ON s.id = sg.student_id
                WHERE sg.group_id = ?
                ORDER BY s.full_name
                ''', (group_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении учеников группы: {e}")
            return []

    def get_available_students_for_group(self, tutor_id: int, group_id: int):
        """Получает учеников, которых можно добавить в группу"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT s.* 
                FROM students s
                WHERE s.tutor_id = ? 
                AND s.id NOT IN (
                    SELECT student_id FROM student_groups WHERE group_id = ?
                )
                ORDER BY s.full_name
                ''', (tutor_id, group_id))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении доступных учеников: {e}")
            return []

    def delete_group(self, group_id: int):
        """Удаляет группу"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Сначала удаляем связи с учениками
                cursor.execute('DELETE FROM student_groups WHERE group_id = ?', (group_id,))
                # Затем удаляем саму группу
                cursor.execute('DELETE FROM groups WHERE id = ?', (group_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении группы: {e}")
            return False

    def update_group_name(self, group_id: int, new_name: str):
        """Обновляет название группы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE groups SET name = ? WHERE id = ?', (new_name, group_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении названия группы: {e}")
            return False
# Создаем глобальный экземпляр базы данных
db = Database()