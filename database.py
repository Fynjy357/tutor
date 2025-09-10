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
            try:
                cursor.execute('ALTER TABLE lessons ADD COLUMN group_id INTEGER')
            except sqlite3.OperationalError:
                # Поле уже существует - игнорируем ошибку
                pass
            
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT s.id, s.full_name 
                    FROM students s 
                    JOIN student_groups gs ON s.id = gs.student_id 
                    WHERE gs.group_id = ?
                """, (group_id,))
                
                students = cursor.fetchall()
                return [{'id': student[0], 'full_name': student[1]} for student in students]
                
        except Exception as e:
            logger.error(f"Ошибка при получении учеников группы: {e}")
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
        """Получает неоплаченные занятия студента"""
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
                LEFT JOIN tutors t ON l.tutor_id = t.id
                LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id AND l.student_id = lr.student_id
                WHERE l.student_id = ? 
                AND (lr.lesson_paid = FALSE OR lr.lesson_paid IS NULL)
                AND l.status = 'completed'
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


# Создаем глобальный экземпляр базы данных
db = Database()