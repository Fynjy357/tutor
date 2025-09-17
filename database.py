import sqlite3
import logging
from typing import Optional
import uuid
from datetime import date, datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name='tutor_bot.db'):
        self.db_name = db_name
        self.init_db()
        self.logger = logging.getLogger(__name__)

    def get_connection(self):
        """Создает и возвращает соединение с базой данных"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row  # Для работы с dict-like строками
        
        return conn

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
                status TEXT DEFAULT 'active',
                user_role TEXT DEFAULT 'user'
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
                timezone TEXT DEFAULT 'Europe/Moscow',
                notification_time TEXT DEFAULT '09:00',
                notification_enabled BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (tutor_id) REFERENCES tutors (id)
            )
            ''')
                    # НОВАЯ таблица основных учеников (уникальные студенты)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT,
                parent_phone TEXT,
                student_telegram_id INTEGER UNIQUE,
                parent_telegram_id INTEGER UNIQUE,
                student_username TEXT,
                parent_username TEXT,
                timezone TEXT DEFAULT 'Europe/Moscow',
                notification_time TEXT DEFAULT '09:00',
                notification_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
                    # таблица родителей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_parents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT,
                parent_telegram_id INTEGER UNIQUE,
                parent_username TEXT,
                timezone TEXT DEFAULT 'Europe/Moscow',
                notification_time TEXT DEFAULT '09:00',
                notification_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            # Для существующих таблиц - добавляем поле если его нет
            try:
                cursor.execute('ALTER TABLE lessons ADD COLUMN reminder_sent INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                # Поле уже существует - игнорируем ошибку
                pass

            # Таблица подтверждений занятий
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS lesson_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                confirmed BOOLEAN,
                confirmed_at TIMESTAMP,
                notified_at TIMESTAMP,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id),
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
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS lesson_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lesson_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                lesson_held BOOLEAN,
                lesson_paid BOOLEAN,
                homework_done BOOLEAN,
                student_performance TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lesson_id) REFERENCES lessons (id),
                FOREIGN KEY (student_id) REFERENCES students (id),
                UNIQUE(lesson_id, student_id)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INTEGER PRIMARY KEY,
                valid_until TEXT NOT NULL,
                tariff TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES tutors (telegram_id)
            )
            ''')
            # Обращения
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',  -- new, in_progress, resolved
                FOREIGN KEY (user_id) REFERENCES tutors (telegram_id)
            )
            ''')
            
            # Таблица платежей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_id TEXT UNIQUE NOT NULL,
                tariff_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valid_until TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES tutors (telegram_id)
            )
            ''')
            try:
                cursor.execute('ALTER TABLE lessons ADD COLUMN group_id INTEGER')
            except sqlite3.OperationalError:
                # Поле уже существует - игнорируем ошибку
                pass
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutor_settings (
                tutor_id INTEGER PRIMARY KEY,
                reminder_hours_before INTEGER DEFAULT 1,
                FOREIGN KEY (tutor_id) REFERENCES tutors (id)
            )
            ''')
            # Таблица реферальных переходов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                visitor_telegram_id INTEGER NOT NULL,
                referral_code TEXT NOT NULL,
                status TEXT DEFAULT 'awaiting',
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES tutors (id),
                UNIQUE(visitor_telegram_id, status)
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS student_migration_map (
                old_id INTEGER PRIMARY KEY,
                main_id INTEGER NOT NULL,
                migration_status TEXT DEFAULT 'pending',
                migrated_at TIMESTAMP,
                FOREIGN KEY (main_id) REFERENCES main_students (id)
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
        """Возвращает данные реpетитора по ID"""
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

    def update_student_telegram_id(self, student_id: int, telegram_id: int, 
                              username: str, role: str, timezone: str = None) -> bool:
        """Обновление Telegram ID ученика с часовым поясом"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if role == 'student':
                    # Обновляем данные для ученика
                    cursor.execute(
                        '''UPDATE students 
                        SET student_telegram_id = ?, 
                            student_username = ?,
                            timezone = COALESCE(?, timezone)
                        WHERE id = ?''',
                        (telegram_id, username, timezone, student_id)
                    )
                else:
                    # Обновляем данные для родителя
                    cursor.execute(
                        '''UPDATE students 
                        SET parent_telegram_id = ?, 
                            parent_username = ?,
                            timezone = COALESCE(?, timezone)
                        WHERE id = ?''',
                        (telegram_id, username, timezone, student_id)
                    )
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Ошибка обновления Telegram ID: {e}")
            return False

    # def update_student_telegram_id(self, student_id, telegram_id, username, user_type):
    #     """Привязывает Telegram аккаунт к ученику"""
    #     try:
    #         with self.get_connection() as conn:
    #             cursor = conn.cursor()
    #             if user_type == 'student':
    #                 cursor.execute(
    #                     'UPDATE students SET student_telegram_id = ?, student_username = ? WHERE id = ?',
    #                     (telegram_id, username, student_id)
    #                 )
    #             else:
    #                 cursor.execute(
    #                     'UPDATE students SET parent_telegram_id = ?, parent_username = ? WHERE id = ?',
    #                     (telegram_id, username, student_id)
    #                 )
    #             conn.commit()
    #             return True
    #     except Exception as e:
    #         logger.error(f"Ошибка при привязке Telegram аккаунта: {e}")
    #         return False

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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE students SET {field_name} = ? WHERE id = ?",
                    (field_value, student_id)
                )
                conn.commit()
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
                    s.phone as student_phone
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
                
                cursor.execute('''
                SELECT l.*, s.full_name as student_name,
                    g.id as group_id, g.name as group_name
                FROM lessons l
                LEFT JOIN students s ON l.student_id = s.id
                LEFT JOIN student_groups sg ON s.id = sg.student_id
                LEFT JOIN groups g ON sg.group_id = g.id AND g.tutor_id = l.tutor_id
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
        
    def add_lesson(self, tutor_id: int, student_id: int, lesson_date: datetime, 
                duration: int, price: float, status: str = "planned", group_id: int = None):
        """Добавляет новое занятие (индивидуальное или групповое)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO lessons (tutor_id, student_id, lesson_date, duration, price, status, group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (tutor_id, student_id, lesson_date, duration, price, status, group_id))
                conn.commit()
                logger.info(f"Добавлено занятие: student_id={student_id}, group_id={group_id}")
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

    def get_students_by_group(self, group_id: int):
        """Получить всех учеников группы"""
        try:
            logger.info(f"🔥 GET_STUDENTS_BY_GROUP CALLED: group_id={group_id}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # ИСПРАВЛЕННЫЙ ЗАПРОС - используем правильное название таблицы student_groups!
                cursor.execute("""
                    SELECT s.id, s.full_name 
                    FROM students s 
                    JOIN student_groups gs ON s.id = gs.student_id 
                    WHERE gs.group_id = ?
                """, (group_id,))
                
                students = cursor.fetchall()
                result = [{'id': student[0], 'full_name': student[1]} for student in students]
                
                logger.info(f"🔥 FOUND {len(result)} STUDENTS IN GROUP {group_id}")
                return result
                
        except Exception as e:
            logger.error(f"🔥 ERROR in get_students_by_group: {e}", exc_info=True)
            return []

    def get_tutor_groups(self, tutor_id: int):
        """Получить все группы репетитора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                logger.info(f"Поиск групп для tutor_id: {tutor_id}")
                
                cursor.execute('SELECT id, name FROM groups WHERE tutor_id = ?', (tutor_id,))
                groups = cursor.fetchall()
                
                logger.info(f"Найдено групп: {len(groups)} для tutor_id: {tutor_id}")
                for group in groups:
                    logger.info(f"Группа: {group}")
                
                return groups
                    
        except Exception as e:
            logger.error(f"Ошибка при получении групп репетитора: {e}")
            return []

    def add_group_lesson(self, tutor_id: int, group_id: int, lesson_date: datetime, 
                    duration: int, price: float, status: str = "planned"):
        """Добавляет занятие для всей группы"""
        try:
            # Получаем всех учеников группы
            students = self.get_students_in_group(group_id)
            if not students:
                logger.error(f"Группа {group_id} пустая")
                return False
            
            logger.info(f"Добавление занятий для группы {group_id}: {len(students)} учеников")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for student in students:
                    logger.info(f"Добавление занятия для student_id={student['id']}, group_id={group_id}")
                    cursor.execute('''
                    INSERT INTO lessons (tutor_id, student_id, lesson_date, duration, price, status, group_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (tutor_id, student['id'], lesson_date, duration, price, status, group_id))
                
                conn.commit()
                logger.info(f"Успешно добавлено {len(students)} занятий для группы {group_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при добавлении группового занятия: {e}")
            return False

    def get_lesson_by_id(self, lesson_id):
        """Получить занятие по ID с информацией о студенте и репетиторе"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT l.*, 
                    s.full_name as student_name, 
                    s.student_telegram_id,
                    t.full_name as tutor_name,
                    t.telegram_id as tutor_telegram_id
                FROM lessons l 
                LEFT JOIN students s ON l.student_id = s.id 
                LEFT JOIN tutors t ON l.tutor_id = t.id
                WHERE l.id = ?
                ''', (lesson_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении занятия по ID: {e}")
            return None


    # def get_lesson_by_id(self, lesson_id):
    #     """Получить занятие по ID"""
    #     try:
    #         with self.get_connection() as conn:
    #             conn.row_factory = sqlite3.Row
    #             cursor = conn.cursor()
                
    #             cursor.execute('''
    #             SELECT l.*, s.full_name as student_name 
    #             FROM lessons l 
    #             LEFT JOIN students s ON l.student_id = s.id 
    #             WHERE l.id = ?
    #             ''', (lesson_id,))
                
    #             result = cursor.fetchone()
    #             return dict(result) if result else None
    #     except Exception as e:
    #         logger.error(f"Ошибка при получении занятия по ID: {e}")
    #         return None

    def update_lesson_datetime(self, lesson_id, new_datetime):
        """Обновить дату/время занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lessons SET lesson_date = ? WHERE id = ?', (new_datetime, lesson_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении даты/времени: {e}")
            return False

    def update_lesson_price(self, lesson_id, new_price):
        """Обновить стоимость занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lessons SET price = ? WHERE id = ?', (new_price, lesson_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении стоимости: {e}")
            return False

    def update_lesson_duration(self, lesson_id, new_duration):
        """Обновить длительность занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lessons SET duration = ? WHERE id = ?', (new_duration, lesson_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении длительности: {e}")
            return False

    def update_lesson_student(self, lesson_id, student_id):
        """Обновить ученика занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lessons SET student_id = ?, group_id = NULL WHERE id = ?', (student_id, lesson_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении ученика: {e}")
            return False

    def update_lesson_group(self, lesson_id, group_id):
        """Обновить группу занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE lessons SET group_id = ?, student_id = NULL WHERE id = ?', (group_id, lesson_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении группы: {e}")
            return False

    def delete_lesson(self, lesson_id):
        """Удалить занятие"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении занятия: {e}")
            return False
        
    def update_group_lesson_datetime(self, group_id: int, new_datetime: str) -> bool:
        """Обновить дату/время для всех занятий группы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE lessons SET lesson_date = ? WHERE group_id = ?", (new_datetime, group_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении даты/времени группы: {e}")
            return False

    def update_group_lesson_price(self, group_id: int, price: float) -> bool:
        """Обновить стоимость для всех занятий группы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE lessons SET price = ? WHERE group_id = ?", (price, group_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении стоимости группы: {e}")
            return False

    def update_group_lesson_duration(self, group_id: int, duration: int) -> bool:
        """Обновить длительность для всех занятий группы"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE lessons SET duration = ? WHERE group_id = ?", (duration, group_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении длительности группы: {e}")
            return False

    def get_lessons_by_date(self, tutor_id: int, date_str: str) -> list:
        """Получить занятия на определенную дату"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = """
                SELECT l.id, l.lesson_date, l.duration, l.price, l.status, 
                    l.group_id, l.student_id,
                    s.full_name as student_name,
                    g.name as group_name
                FROM lessons l
                LEFT JOIN students s ON l.student_id = s.id
                LEFT JOIN groups g ON l.group_id = g.id
                WHERE l.tutor_id = ? AND DATE(l.lesson_date) = ?
                ORDER BY l.lesson_date
                """
                cursor.execute(query, (tutor_id, date_str))
                lessons = cursor.fetchall()
                return [dict(lesson) for lesson in lessons]
        except Exception as e:
            logger.error(f"Ошибка при получении занятий по дате: {e}")
            return []
    def get_student_by_telegram_id(self, telegram_id):
        """Получает ученика по telegram_id (студента)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM students WHERE student_telegram_id = ?', 
                            (telegram_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ученика по telegram_id: {e}")
            return None
        
    def get_parent_by_telegram_id(self, telegram_id):
        """Получает родителя по telegram_id (студента или родителя)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM students WHERE parent_telegram_id = ?', 
                            (telegram_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении ученика по telegram_id: {e}")
            return None
    
    
    def get_upcoming_lessons_for_notification(self):
        """Получает занятия, которые нужно уведомить (за 24 часа)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                query = '''
                SELECT l.*, s.full_name as student_name, s.student_telegram_id,
                    t.full_name as tutor_name, t.telegram_id as tutor_telegram_id
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                WHERE l.lesson_date BETWEEN datetime('now', '+23 hours') AND datetime('now', '+25 hours')
                AND l.status = 'planned'
                AND NOT EXISTS (
                    SELECT 1 FROM lesson_confirmations lc 
                    WHERE lc.lesson_id = l.id AND lc.notified_at IS NOT NULL
                )
                '''
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении занятий для уведомления: {e}")
            return []

    def create_confirmation_record(self, lesson_id, student_id):
        """Создает запись для подтверждения занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO lesson_confirmations (lesson_id, student_id, notified_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (lesson_id, student_id))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании записи подтверждения: {e}")
            return None
        
    def update_confirmation(self, lesson_id, student_id, confirmed):
        """Обновляет статус подтверждения занятия"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE lesson_confirmations 
                SET confirmed = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE lesson_id = ? AND student_id = ?
                ''', (confirmed, lesson_id, student_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении подтверждения: {e}")
            return False
    def save_lesson_report(self, lesson_id, student_id, lesson_held=None, 
                        lesson_paid=None, homework_done=None, student_performance=None):
        """Сохраняет отчет по занятию"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли уже запись
                cursor.execute('SELECT id FROM lesson_reports WHERE lesson_id = ? AND student_id = ?', 
                            (lesson_id, student_id))
                existing = cursor.fetchone()
                
                if existing:
                    # Обновляем существующую запись
                    updates = []
                    params = []
                    
                    if lesson_held is not None:
                        updates.append("lesson_held = ?")
                        params.append(lesson_held)
                    if lesson_paid is not None:
                        updates.append("lesson_paid = ?")
                        params.append(lesson_paid)
                    if homework_done is not None:
                        updates.append("homework_done = ?")
                        params.append(homework_done)
                    if student_performance is not None:
                        updates.append("student_performance = ?")
                        params.append(student_performance)
                    
                    if updates:
                        params.extend([lesson_id, student_id])
                        cursor.execute(f'''
                        UPDATE lesson_reports 
                        SET {", ".join(updates)} 
                        WHERE lesson_id = ? AND student_id = ?
                        ''', params)
                else:
                    # Создаем новую запись
                    cursor.execute('''
                    INSERT INTO lesson_reports 
                    (lesson_id, student_id, lesson_held, lesson_paid, homework_done, student_performance)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (lesson_id, student_id, lesson_held, lesson_paid, homework_done, student_performance))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчета: {e}")
            return False

    def get_lesson_report(self, lesson_id, student_id):
        """Получает отчет по занятию"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM lesson_reports 
                WHERE lesson_id = ? AND student_id = ?
                ''', (lesson_id, student_id))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении отчета: {e}")
            return None

    def is_lesson_report_complete(self, lesson_id, student_id):
        """Проверяет, полностью ли заполнен отчет"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT lesson_held, lesson_paid, homework_done, student_performance 
                FROM lesson_reports 
                WHERE lesson_id = ? AND student_id = ?
                ''', (lesson_id, student_id))
                result = cursor.fetchone()
                
                if result:
                    return all(result)  # Все поля должны быть заполнены
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке отчета: {e}")
            return False
    def has_free_access(self, telegram_id: int) -> bool:
        """Проверяет, есть ли у пользователя бесплатный доступ"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_role FROM tutors WHERE telegram_id = ?', (telegram_id,))
                result = cursor.fetchone()
                
                if result and result[0] in ['admin', 'vip', 'moderator', 'tester']:
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при проверке бесплатного доступа: {e}")
            return False

    def is_admin(self, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_role FROM tutors WHERE telegram_id = ?', (telegram_id,))
                result = cursor.fetchone()
                return result and result[0] == 'admin'
        except Exception as e:
            logger.error(f"Ошибка при проверке администратора: {e}")
            return False
    def get_student_unpaid_lessons(self, student_id: int):
        """Получает неоплаченные занятия студента (ТОЛЬКО те, у которых есть отчет и они не оплачены)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    l.price,
                    t.full_name as tutor_name,
                    lr.lesson_held,
                    lr.lesson_paid
                FROM lessons l
                INNER JOIN tutors t ON l.tutor_id = t.id
                INNER JOIN lesson_reports lr ON l.id = lr.lesson_id
                WHERE l.student_id = ? 
                AND l.status = 'completed'
                AND lr.lesson_held = TRUE  -- занятие действительно проведено
                AND lr.lesson_paid = FALSE -- и не оплачено
                ORDER BY l.lesson_date DESC
                ''', (student_id,))
                
                unpaid_lessons = [dict(row) for row in cursor.fetchall()]
                return unpaid_lessons
        except Exception as e:
            logger.error(f"Ошибка при получении неоплаченных занятий: {e}")
            return []
    def get_student_undone_homeworks(self, student_id: int):
        """Получает невыполненные домашние работы студента"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    t.full_name as tutor_name,
                    lr.homework_done,
                    lr.student_performance
                FROM lessons l
                LEFT JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id AND l.student_id = lr.student_id
                WHERE l.student_id = ? 
                AND lr.homework_done = FALSE
                AND l.status = 'completed'
                ORDER BY l.lesson_date DESC
                ''', (student_id,))
                
                undone_homeworks = [dict(row) for row in cursor.fetchall()]
                return undone_homeworks
        except Exception as e:
            logger.error(f"Ошибка при получении невыполненных домашних работ: {e}")
            return []
        
    def get_student_upcoming_lessons(self, student_id: int, days: int = 30):
        """Получает предстоящие занятия студента на указанное количество дней вперед"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    l.price,
                    t.full_name as tutor_name,
                    l.status
                FROM lessons l
                LEFT JOIN tutors t ON l.tutor_id = t.id
                WHERE l.student_id = ? 
                AND l.lesson_date >= datetime('now')
                AND l.lesson_date <= datetime('now', ? || ' days')
                AND l.status = 'planned'
                ORDER BY l.lesson_date ASC
                ''', (student_id, days))
                
                upcoming_lessons = [dict(row) for row in cursor.fetchall()]
                return upcoming_lessons
        except Exception as e:
            logger.error(f"Ошибка при получении предстоящих занятий: {e}")
            return []
    def get_dates_with_reports(self, tutor_id):
        """Получает даты, для которых есть отчеты"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT DATE(l.lesson_date) as lesson_date
                FROM lesson_reports lr
                JOIN lessons l ON lr.lesson_id = l.id
                WHERE l.tutor_id = ? 
                ORDER BY lesson_date DESC
            ''', (tutor_id,))
            dates = [row[0] for row in cursor.fetchall()]
            return [datetime.strptime(date_str, '%Y-%m-%d').date() for date_str in dates]

    def get_reports_by_date(self, tutor_id, selected_date):
        """Получает отчеты по дате"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    lr.*, 
                    s.full_name as student_name,
                    l.lesson_date,
                    TIME(l.lesson_date) as lesson_time
                FROM lesson_reports lr
                JOIN lessons l ON lr.lesson_id = l.id
                JOIN students s ON lr.student_id = s.id
                WHERE l.tutor_id = ? AND DATE(l.lesson_date) = ?
                ORDER BY l.lesson_date
            ''', (tutor_id, selected_date.strftime('%Y-%m-%d')))
            
            reports = []
            for row in cursor.fetchall():
                report = dict(row)
                # Преобразуем строку времени в объект времени
                if 'lesson_time' in report and report['lesson_time']:
                    try:
                        report['time'] = datetime.strptime(report['lesson_time'], '%H:%M:%S').strftime('%H:%M')
                    except ValueError:
                        report['time'] = report['lesson_time']
                reports.append(report)
            return reports

    def get_report_by_id(self, report_id):
        """Получает отчет по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    lr.*, 
                    s.full_name as student_name,
                    l.lesson_date,
                    TIME(l.lesson_date) as lesson_time
                FROM lesson_reports lr
                JOIN lessons l ON lr.lesson_id = l.id
                JOIN students s ON lr.student_id = s.id
                WHERE lr.id = ?
            ''', (report_id,))
            
            row = cursor.fetchone()
            if row:
                report = dict(row)
                # Преобразуем строку даты в объект date
                if 'lesson_date' in report and report['lesson_date']:
                    report['lesson_date'] = datetime.strptime(report['lesson_date'], '%Y-%m-%d %H:%M:%S').date()
                return report
            return None

    def update_report_attendance(self, report_id, new_value):
        """Обновляет статус присутствия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lesson_reports 
                SET lesson_held = ? 
                WHERE id = ?
            ''', (new_value, report_id))
            conn.commit()

    def update_report_payment(self, report_id, new_value):
        """Обновляет статус оплаты"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lesson_reports 
                SET lesson_paid = ? 
                WHERE id = ?
            ''', (new_value, report_id))
            conn.commit()

    def update_report_homework(self, report_id, new_value):
        """Обновляет статус домашнего задания"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lesson_reports 
                SET homework_done = ? 
                WHERE id = ?
            ''', (new_value, report_id))
            conn.commit()

    def update_report_comment(self, report_id, new_comment):
        """Обновляет комментарий к отчету"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE lesson_reports 
                SET student_performance = ? 
                WHERE id = ?
            ''', (new_comment, report_id))
            conn.commit()
    def get_lessons_for_reminder(self):
        """Получает все занятия, которые начнутся в ближайшие 60 минут"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Логируем оба времени для отладки
                cursor.execute("SELECT datetime('now') as utc_time, datetime('now', 'localtime') as local_time")
                times = cursor.fetchone()
                logger.info(f"🕒 UTC время в БД: {times['utc_time']}")
                logger.info(f"🏠 Локальное время в БД: {times['local_time']}")
                
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    l.group_id,
                    s.full_name as student_name,
                    t.telegram_id as tutor_telegram_id,
                    t.full_name as tutor_name,
                    l.reminder_sent
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                WHERE l.status = 'planned'
                AND l.lesson_date > datetime('now', 'localtime')
                AND l.lesson_date <= datetime('now', 'localtime', '+60 minutes')
                AND l.reminder_sent = 0
                ''')
                
                results = [dict(row) for row in cursor.fetchall()]
                return results
                
        except Exception as e:
            logger.error(f"💥 Ошибка при получении занятий для напоминания: {e}")
            return []

    def mark_reminder_sent(self, lesson_id: int):
        """Отмечает, что напоминание для занятия было отправлено"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE lessons SET reminder_sent = 1 WHERE id = ?
                ''', (lesson_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при отметке отправленного напоминания: {e}")
            return False

    def reset_reminders_for_past_lessons(self):
        """Сбрасывает флаги напоминаний для прошедших занятий"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE lessons 
                SET reminder_sent = 0 
                WHERE status = 'planned' 
                AND lesson_date < datetime('now')
                AND reminder_sent = 1
                ''')
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Ошибка при сбросе напоминаний: {e}")
            return 0    
    # Редактирование времени напоминания уведомлений для репетитора:
    def set_reminder_time(self, tutor_id: int, hours_before: int):
        """Устанавливает время напоминания для репетитора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT OR REPLACE INTO tutor_settings 
                (tutor_id, reminder_hours_before) 
                VALUES (?, ?)
                ''', (tutor_id, hours_before))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при установке времени напоминания: {e}")
            return False

    def get_reminder_time(self, tutor_id: int):
        """Получает время напоминания для репетитора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT reminder_hours_before FROM tutor_settings 
                WHERE tutor_id = ?
                ''', (tutor_id,))
                result = cursor.fetchone()
                return result[0] if result else 1  # По умолчанию 1 час
        except Exception as e:
            logger.error(f"Ошибка при получении времени напоминания: {e}")
            return 1

    def get_feedback_messages(self, status=None):
        """Получение списка обращений"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
                cursor = conn.cursor()
                
                if status:
                    cursor.execute("SELECT * FROM feedback_messages WHERE status = ? ORDER BY created_at DESC", (status,))
                else:
                    cursor.execute("SELECT * FROM feedback_messages ORDER BY created_at DESC")
                
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении списка обращений: {e}")
            return []

    def update_feedback_status(self, feedback_id, status):
        """Обновление статуса обращения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE feedback_messages SET status = ? WHERE id = ?",
                    (status, feedback_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса обращения: {e}")
            return False

    def save_feedback_message(self, user_id, user_name, message):
        """Сохранение нового обращения"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO feedback_messages (user_id, user_name, message) VALUES (?, ?, ?)",
                    (user_id, user_name, message)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при сохранении обращения: {e}")
            return None

    def get_feedback_message_by_id(self, feedback_id):
        """Получение обращения по ID"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = lambda cursor, row: dict(zip([col[0] for col in cursor.description], row))
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM feedback_messages WHERE id = ?", (feedback_id,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении обращения по ID: {e}")
            return None

    def get_feedback_stats(self):
        """Получение статистики по обращениям"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM feedback_messages 
                    GROUP BY status
                """)
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.error(f"Ошибка при получении статистики обращений: {e}")
            return {}
    
    def save_payment_id(self, user_id: int, payment_id: str, tariff_name: str, amount: float):
        """Сохраняет ID платежа в базу данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу для платежей если ее нет
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    payment_id TEXT UNIQUE NOT NULL,
                    tariff_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES tutors (telegram_id)
                )
                ''')
                
                # Вставляем запись о платеже
                cursor.execute('''
                INSERT INTO payments (user_id, payment_id, tariff_name, amount)
                VALUES (?, ?, ?, ?)
                ''', (user_id, payment_id, tariff_name, amount))
                                # Создаем таблицу для платежей если ее нет
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    payment_id TEXT UNIQUE NOT NULL,
                    tariff_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES tutors (telegram_id)
                )
                ''')
                conn.commit()
                logger.info(f"Payment saved: user_id={user_id}, payment_id={payment_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error saving payment: {e}")
            return False

    def get_last_payment_id(self, user_id: int) -> Optional[str]:
        """Получает ID последнего платежа пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT payment_id FROM payments 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting last payment: {e}")
            return None

    def update_payment_status(self, payment_id: str, status: str):
        """Обновляет статус платежа"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE payments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE payment_id = ?
                ''', (status, payment_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Error updating payment status: {e}")
            return False

    def get_payment_info(self, payment_id: str) -> Optional[dict]:
        """Получает информацию о платеже"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM payments WHERE payment_id = ?
                ''', (payment_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except sqlite3.Error as e:
            logger.error(f"Error getting payment info: {e}")
            return None

    def get_user_payments(self, user_id: int) -> list:
        """Получает все платежи пользователя"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM payments 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                ''', (user_id,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting user payments: {e}")
            return []
    def get_earnings_by_period(self, tutor_id: int, start_date: date, end_date: date) -> float:
        """Возвращает сумму заработка за указанный период по оплаченным занятиям"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT COALESCE(SUM(l.price), 0) as total_earnings
                FROM lessons l
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
                WHERE l.tutor_id = ? 
                AND DATE(l.lesson_date) BETWEEN ? AND ?
                AND l.status = 'completed'
                AND lr.lesson_paid = 1  -- Добавляем проверку оплаты
                ''', (tutor_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                
                result = cursor.fetchone()
                return float(result[0]) if result and result[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении заработка за период: {e}")
            return 0.0
        
    def get_total_students_count(self, tutor_id: int) -> int:
        """Возвращает общее количество учеников у репетитора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT COUNT(DISTINCT s.id) 
                FROM students s
                WHERE s.tutor_id = ?
                ''', (tutor_id,))
                
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при получении количества учеников: {e}")
            return 0
        
    def get_tutor_phone(self, telegram_id: int) -> Optional[str]:
        """Получить телефон репетитора по его telegram_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT phone FROM tutors WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        
    def check_tutor_subscription(self, tutor_id: int) -> bool:
        """
        Проверяет наличие активной подписки у репетитора на основе таблицы payments
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Сначала получаем telegram_id репетитора по его id
                cursor.execute('SELECT telegram_id FROM tutors WHERE id = ?', (tutor_id,))
                tutor_data = cursor.fetchone()
                
                if not tutor_data:
                    logger.warning(f"Репетитор с id={tutor_id} не найден")
                    return False
                    
                telegram_id = tutor_data[0]
                
                # Теперь проверяем подписку по telegram_id
                cursor.execute('''
                SELECT COUNT(*) FROM payments 
                WHERE user_id = ? 
                AND status = 'succeeded'
                AND valid_until >= datetime('now')
                ORDER BY created_at DESC
                LIMIT 1
                ''', (telegram_id,))
                
                result = cursor.fetchone()
                has_subscription = result[0] > 0 if result else False
                
                logger.debug(f"Проверка подписки: tutor_id={tutor_id}, telegram_id={telegram_id}, результат={has_subscription}")
                
                return has_subscription
                
        except Exception as e:
            logger.error(f"Ошибка при проверке подписки для репетитора {tutor_id}: {e}")
            return False
        
    def create_referral_visit(self, referrer_id: int, visitor_telegram_id: int, referral_code: str):
        """Создает или ОБНОВЛЯЕТ реферальный переход"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже запись для этого пользователя
                cursor.execute(
                    "SELECT id FROM referrals WHERE visitor_telegram_id = ?",
                    (visitor_telegram_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # ОБНОВЛЯЕМ существующую запись
                    cursor.execute(
                        "UPDATE referrals SET referrer_id = ?, referral_code = ?, visit_date = datetime('now') WHERE visitor_telegram_id = ?",
                        (referrer_id, referral_code, visitor_telegram_id)
                    )
                    logger.info(f"Обновлен реферальный переход для пользователя {visitor_telegram_id}")
                else:
                    # СОЗДАЕМ новую запись
                    cursor.execute(
                        "INSERT INTO referrals (referrer_id, visitor_telegram_id, referral_code, visit_date) VALUES (?, ?, ?, datetime('now'))",
                        (referrer_id, visitor_telegram_id, referral_code)
                    )
                    logger.info(f"Создан новый реферальный переход для пользователя {visitor_telegram_id}")
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании реферального перехода: {e}")
            return False

    def get_tutor_by_referral_code(self, referral_code: str):
        """Находит репетитора по реферальному коду (части ссылки после start=)"""
        try:
            # Формируем полную ссылку для поиска
            # full_promo_link = f"https://t.me/egeTOP100_bot?start={referral_code}"
            full_promo_link = f"https://t.me/TutorPlanetBot?start={referral_code}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, telegram_id, full_name, phone, promo_code FROM tutors WHERE promo_code = ?",
                    (full_promo_link,)
                )
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            logger.error(f"Ошибка поиска репетитора по промо-коду {referral_code}: {e}")
            return None
        
    def is_user_tutor(self, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь репетитором"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM tutors WHERE telegram_id = ?",
                (telegram_id,)
            )
            return cursor.fetchone() is not None


    def create_or_update_referral_visit(self, referrer_id: int, visitor_telegram_id: int, referral_code: str):
        """Создает или обновляет реферальный переход с системой статусов"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, есть ли уже awaiting запись для этого пользователя
                cursor.execute(
                    "SELECT id, referral_code FROM referrals WHERE visitor_telegram_id = ? AND status = 'awaiting'",
                    (visitor_telegram_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    existing_id, existing_code = existing
                    
                    # Если тот же referral_code - ничего не делаем
                    if existing_code == referral_code:
                        logger.info(f"Повторный переход по той же ссылке: {visitor_telegram_id}")
                        return True
                    
                    # Если другой referral_code - помечаем старый как inactive
                    cursor.execute(
                        "UPDATE referrals SET status = 'inactive', updated_at = datetime('now') WHERE id = ?",
                        (existing_id,)
                    )
                    logger.info(f"Старая реферальная ссылка помечена как inactive: {existing_id}")
                
                # Создаем новую запись со статусом awaiting
                cursor.execute(
                    "INSERT INTO referrals (referrer_id, visitor_telegram_id, referral_code, status) VALUES (?, ?, ?, 'awaiting')",
                    (referrer_id, visitor_telegram_id, referral_code)
                )
                
                conn.commit()
                logger.info(f"Создан новый реферальный переход: {referrer_id} -> {visitor_telegram_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при обработке реферального перехода: {e}")
            return False
        
    def activate_referral(self, visitor_telegram_id: int, registered_tutor_id: int):
        """Активирует реферальную связь при регистрации пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Находим актуальный awaiting переход
                cursor.execute(
                    "SELECT id, referrer_id FROM referrals WHERE visitor_telegram_id = ? AND status = 'awaiting' ORDER BY visited_at DESC LIMIT 1",
                    (visitor_telegram_id,)
                )
                referral = cursor.fetchone()
                
                if referral:
                    referral_id, referrer_id = referral
                    
                    # Меняем статус на active
                    cursor.execute(
                        "UPDATE referrals SET status = 'active', updated_at = datetime('now') WHERE id = ?",
                        (referral_id,)
                    )
                    
                    # Сохраняем окончательную связь (опционально)
                    cursor.execute(
                        "INSERT INTO final_referrals (referrer_id, referred_tutor_id, registration_date) VALUES (?, ?, datetime('now'))",
                        (referrer_id, registered_tutor_id)
                    )
                    
                    conn.commit()
                    logger.info(f"Реферал активирован: {referrer_id} -> {registered_tutor_id}")
                    return referrer_id
                
                logger.info(f"Не найдено awaiting рефералов для пользователя: {visitor_telegram_id}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при активации реферала: {e}")
            return None
    def activate_referral(self, visitor_telegram_id: int, registered_tutor_id: int):
        """Активирует реферальную связь при регистрации пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Находим awaiting переход для этого пользователя
                cursor.execute(
                    "SELECT id, referrer_id FROM referrals WHERE visitor_telegram_id = ? AND status = 'awaiting'",
                    (visitor_telegram_id,)
                )
                referral = cursor.fetchone()
                
                if referral:
                    referral_id, referrer_id = referral
                    
                    # Меняем статус на active
                    cursor.execute(
                        "UPDATE referrals SET status = 'active', updated_at = datetime('now') WHERE id = ?",
                        (referral_id,)
                    )
                    
                    conn.commit()
                    logger.info(f"Реферал активирован: ID {referral_id}, статус изменен на active")
                    return referrer_id
                
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при активации реферала: {e}")
            return None
    def get_lessons_for_reminder_grouped(self):
        """Получает занятия для напоминания, группируя групповые занятия"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT DISTINCT
                    l.group_id,
                    MIN(l.id) as lesson_id,
                    l.lesson_date,
                    l.duration,
                    g.name as group_name,
                    t.telegram_id as tutor_telegram_id,
                    t.full_name as tutor_name,
                    l.reminder_sent,
                    COUNT(DISTINCT l.student_id) as student_count
                FROM lessons l
                JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN groups g ON l.group_id = g.id
                WHERE l.status = 'planned'
                AND l.lesson_date > datetime('now', 'localtime')
                AND l.lesson_date <= datetime('now', 'localtime', '+60 minutes')
                AND l.reminder_sent = 0
                GROUP BY l.group_id, l.lesson_date, l.duration
                HAVING COUNT(*) > 0
                ''')
                
                results = [dict(row) for row in cursor.fetchall()]
                return results
                
        except Exception as e:
            logger.error(f"💥 Ошибка при получении групповых занятий для напоминания: {e}")
            return []
    def add_student_to_main_table(self, student_id: int, full_name: str, phone: str, 
                                    telegram_id: int, username: str, timezone: str, tutor_id: int):
        """Добавляет студента в таблицу main_students, если его еще нет"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # ✅ ПРОВЕРЯЕМ - если студент уже есть в main_students, НИЧЕГО НЕ ДЕЛАЕМ
                cursor.execute('''
                    SELECT id FROM main_students 
                    WHERE student_telegram_id = ? OR parent_telegram_id = ?
                ''', (telegram_id, telegram_id))
                
                existing = cursor.fetchone()
                
                if existing:
                    # ✅ Студент уже есть в main_students - пропускаем добавление
                    return True
                else:
                    # ✅ Создаем новую запись только если студента еще нет
                    cursor.execute('''
                        INSERT INTO main_students 
                        (full_name, phone, student_telegram_id, 
                        student_username, timezone, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (full_name, phone, telegram_id, username, timezone))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка при работе с main_students: {e}")
            return False

    def get_main_student_by_telegram_id(self, telegram_id: int):
        """Получает основного студента по telegram_id (ученика или родителя)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM main_students 
                    WHERE student_telegram_id = ? OR parent_telegram_id = ?
                ''', (telegram_id, telegram_id))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Ошибка при получении основного студента: {e}")
            return None

    def get_tutors_for_main_student(self, main_student_id: int):
        """Получает всех репетиторов, прикрепленных к студенту из main_students (только active и paused)"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT t.* 
                    FROM tutors t
                    JOIN students s ON t.id = s.tutor_id
                    JOIN main_students ms ON (s.student_telegram_id = ms.student_telegram_id 
                                        OR s.parent_telegram_id = ms.parent_telegram_id)
                    WHERE ms.id = ? AND t.status IN ('active', 'paused')
                    ORDER BY t.full_name
                ''', (main_student_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка при получении репетиторов для студента: {e}")
            return []

    def get_all_students_for_main_student(self, main_student_id: int):
        """Получает все записи студентов из разных репетиторов для основного студента"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT s.*, t.full_name as tutor_name, t.phone as tutor_phone
                    FROM students s
                    JOIN tutors t ON s.tutor_id = t.id
                    JOIN main_students ms ON (s.student_telegram_id = ms.student_telegram_id 
                                        OR s.parent_telegram_id = ms.parent_telegram_id)
                    WHERE ms.id = ?
                    ORDER BY t.full_name
                ''', (main_student_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех записей студента: {e}")
            return []
        
    def get_student_undone_homeworks_from_reports(self, student_id):
        """Получает невыполненные домашние задания для студента"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    t.full_name as tutor_name,
                    lr.homework_done,
                    lr.student_performance
                FROM lessons l
                JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
                WHERE l.student_id = ?
                AND l.status = 'completed'
                AND (lr.homework_done = FALSE OR lr.homework_done IS NULL)
                ORDER BY l.lesson_date DESC
                ''', (student_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"❌ Ошибка в get_student_undone_homeworks_from_reports: {e}")
            return []
    def get_unpaid_lessons_for_student(self, student_id):
        """Получает неоплаченные занятия для студента"""
        try:
            query = """
                SELECT lr.*, l.lesson_date, l.duration, l.price
                FROM lesson_reports lr
                JOIN lessons l ON lr.lesson_id = l.id
                WHERE l.student_id = ?
                AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
                ORDER BY l.lesson_date DESC
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (student_id,))
                results = cursor.fetchall()
                
                # Преобразуем sqlite3.Row в словари
                unpaid_lessons = []
                for row in results:
                    unpaid_lessons.append(dict(row))
                
                return unpaid_lessons
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка в get_unpaid_lessons_for_student: {e}")
            return []
        
    def add_parent_to_main_table(self, full_name: str, phone: str, 
                            telegram_id: int, username: str, timezone: str) -> bool:
        """Добавляет родителя в таблицу main_parents, если его еще нет"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем - если родитель уже есть в main_parents, НИЧЕГО НЕ ДЕЛАЕМ
                cursor.execute('SELECT id FROM main_parents WHERE parent_telegram_id = ?', (telegram_id,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Родитель уже есть в main_parents - пропускаем добавление
                    return True
                else:
                    # Создаем новую запись только если родителя еще нет
                    cursor.execute('''
                        INSERT INTO main_parents 
                        (full_name, phone, parent_telegram_id, 
                        parent_username, timezone, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (full_name, phone, telegram_id, username, timezone))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка при работе с main_parents: {e}")
            return False

    def get_main_parent_by_telegram_id(self, telegram_id: int):
        """Получает основного родителя по telegram_id"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM main_parents WHERE parent_telegram_id = ?', (telegram_id,))
                result = cursor.fetchone()
                return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Ошибка при получении основного родителя: {e}")
            return None
    def get_students_by_parent_telegram_id(self, parent_telegram_id: int):
        """Получает всех учеников по parent_telegram_id"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM students WHERE parent_telegram_id = ?', (parent_telegram_id,))
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
        except Exception as e:
            self.logger.error(f"Ошибка при получении учеников родителя: {e}")
            return []
    def get_tutors_for_parent(self, parent_telegram_id: int):
        """Получает всех репетиторов родителя - ЕДИНЫЙ СТАНДАРТ"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # ИСПРАВЛЕНО: используем ТОТ ЖЕ стандарт, что и в get_parent_homeworks
                cursor.execute('''
                SELECT DISTINCT 
                    t.id, 
                    t.full_name, 
                    t.telegram_id,
                    t.status,
                    t.phone
                FROM tutors t
                JOIN students s ON t.id = s.tutor_id
                WHERE s.parent_telegram_id = ?
                AND t.status IN ('active', 'paused')
                ORDER BY t.full_name
                ''', (parent_telegram_id,))
                
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"👨‍🏫 Найдено репетиторов для родителя {parent_telegram_id}: {len(results)}")
                return results
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении репетиторов родителя: {e}")
            return []

    def get_parent_unpaid_lessons(self, parent_telegram_id: int):
        """Получает неоплаченные занятия родителя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    l.price,
                    s.full_name as student_name,
                    t.full_name as tutor_name,
                    COALESCE(lr.lesson_held, 1) as lesson_held,
                    COALESCE(lr.lesson_paid, 0) as lesson_paid
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id AND lr.student_id = s.id
                WHERE s.parent_telegram_id = ?
                AND l.status = 'completed'
                AND lr.id IS NOT NULL  -- ДОБАВЛЕНО: должен быть отчет
                AND lr.lesson_paid = 0  -- ИЗМЕНЕНО: только явно неоплаченные
                ORDER BY l.lesson_date DESC
                ''', (parent_telegram_id,))
                
                results = [dict(row) for row in cursor.fetchall()]
                logger.info(f"💰 Найдено неоплаченных занятий для родителя {parent_telegram_id}: {len(results)}")
                return results
                
        except Exception as e:
            logger.error(f"Ошибка при получении неоплаченных занятий родителя: {e}")
            return []
        
        
    def get_parent_homeworks(self, parent_telegram_id: int):
        """Получает домашние задания родителя"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.duration,
                    s.full_name as student_name,
                    t.full_name as tutor_name,
                    lr.homework_done,
                    lr.student_performance
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
                WHERE s.parent_telegram_id = ?
                AND l.status = 'completed'
                AND (lr.homework_done = FALSE OR lr.homework_done IS NULL)
                ORDER BY l.lesson_date DESC
                ''', (parent_telegram_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении домашних заданий родителя: {e}")
            return []
    def get_parent_students(self, parent_telegram_id: int):
        """Получает всех учеников родителя"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT s.*, t.full_name as tutor_name
                FROM students s
                LEFT JOIN tutors t ON s.tutor_id = t.id
                WHERE s.parent_telegram_id = ?
                ORDER BY s.full_name
                ''', (parent_telegram_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении учеников родителя: {e}")
            return []
    def debug_parent_connections(self, parent_telegram_id: int):
        """Отладочный метод для проверки связей родителя"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                debug_info = {
                    'parent_telegram_id': parent_telegram_id,
                    'found_in_students': False,
                    'found_in_main_parents': False,
                    'students_count': 0,
                    'tutors_count': 0,
                    'students_details': [],
                    'tutors_details': [],
                    'unpaid_lessons_count': 0,
                    'unpaid_lessons_details': []
                }
                
                # 1. Проверяем, есть ли родитель в students
                cursor.execute('''
                SELECT id, full_name, parent_telegram_id, student_telegram_id, tutor_id
                FROM students 
                WHERE parent_telegram_id = ?
                ''', (parent_telegram_id,))
                
                students = cursor.fetchall()
                debug_info['students_count'] = len(students)
                debug_info['found_in_students'] = len(students) > 0
                
                for student in students:
                    student_info = dict(student)
                    debug_info['students_details'].append(student_info)
                
                # 2. Проверяем, есть ли родитель в main_parents
                cursor.execute('''
                SELECT id, full_name, parent_telegram_id, parent_username
                FROM main_parents 
                WHERE parent_telegram_id = ?
                ''', (parent_telegram_id,))
                
                main_parent = cursor.fetchone()
                debug_info['found_in_main_parents'] = main_parent is not None
                if main_parent:
                    debug_info['main_parent_info'] = dict(main_parent)
                
                # 3. Проверяем репетиторов через students
                cursor.execute('''
                SELECT DISTINCT t.id, t.full_name, t.telegram_id, t.status
                FROM tutors t
                JOIN students s ON t.id = s.tutor_id
                WHERE s.parent_telegram_id = ?
                ''', (parent_telegram_id,))
                
                tutors = cursor.fetchall()
                debug_info['tutors_count'] = len(tutors)
                
                for tutor in tutors:
                    tutor_info = dict(tutor)
                    debug_info['tutors_details'].append(tutor_info)
                
                # 4. Проверяем неоплаченные занятия (двумя способами)
                # Способ 1: через lesson_reports
                cursor.execute('''
                SELECT COUNT(*) as count
                FROM lesson_reports lr
                JOIN lessons l ON lr.lesson_id = l.id
                JOIN students s ON l.student_id = s.id
                WHERE s.parent_telegram_id = ?
                AND l.status = 'completed'
                AND lr.lesson_held = 1
                AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
                ''', (parent_telegram_id,))
                
                unpaid_count_1 = cursor.fetchone()
                debug_info['unpaid_via_reports'] = unpaid_count_1['count'] if unpaid_count_1 else 0
                
                # Способ 2: напрямую через lessons (если нет отчетов)
                cursor.execute('''
                SELECT COUNT(*) as count
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                WHERE s.parent_telegram_id = ?
                AND l.status = 'completed'
                AND NOT EXISTS (
                    SELECT 1 FROM lesson_reports lr 
                    WHERE lr.lesson_id = l.id 
                    AND lr.lesson_paid = 1
                )
                ''', (parent_telegram_id,))
                
                unpaid_count_2 = cursor.fetchone()
                debug_info['unpaid_via_lessons'] = unpaid_count_2['count'] if unpaid_count_2 else 0
                
                # Детали неоплаченных занятий
                cursor.execute('''
                SELECT 
                    l.id as lesson_id,
                    l.lesson_date,
                    l.price,
                    s.full_name as student_name,
                    t.full_name as tutor_name,
                    lr.lesson_paid,
                    lr.lesson_held
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id AND lr.student_id = s.id
                WHERE s.parent_telegram_id = ?
                AND l.status = 'completed'
                ORDER BY l.lesson_date DESC
                ''', (parent_telegram_id,))
                
                all_lessons = cursor.fetchall()
                debug_info['all_lessons_count'] = len(all_lessons)
                
                for lesson in all_lessons:
                    lesson_info = dict(lesson)
                    debug_info['unpaid_lessons_details'].append(lesson_info)
                
                return debug_info
                
        except Exception as e:
            logger.error(f"❌ Ошибка в debug_parent_connections: {e}")
            return {'error': str(e)}

# Создаем глобальный экземпляр базы данных
db = Database()