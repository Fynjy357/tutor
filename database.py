import sqlite3
import logging
from datetime import datetime

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
            
            conn.commit()
        logger.info("База данных инициализирована")

    def add_tutor(self, telegram_id, full_name, phone, promo_code='0'):
        """Добавляет нового репетитора в базу данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO tutors (telegram_id, full_name, phone, promo_code)
            VALUES (?, ?, ?, ?)
            ''', (telegram_id, full_name, phone, promo_code))
            conn.commit()
            logger.info(f"Добавлен репетитор: {full_name}")
            return cursor.lastrowid

    def get_tutor_by_telegram_id(self, telegram_id):
        """Возвращает данные репетитора по telegram_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tutors WHERE telegram_id = ?', (telegram_id,))
            return cursor.fetchone()

    def update_tutor(self, telegram_id, full_name=None, phone=None, promo_code=None):
        """Обновляет данные репетитора"""
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

    def check_promo_code(self, promo_code):
        """Проверяет валидность промокода"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT * FROM promo_codes 
            WHERE code = ? AND is_active = TRUE 
            AND (valid_until IS NULL OR valid_until > datetime('now'))
            AND (usage_limit IS NULL OR used_count < usage_limit)
            ''', (promo_code,))
            return cursor.fetchone()

    def use_promo_code(self, promo_code):
        """Увеличивает счетчик использования промокода"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE promo_codes SET used_count = used_count + 1 
            WHERE code = ? AND is_active = TRUE
            ''', (promo_code,))
            conn.commit()

# Создаем глобальный экземпляр базы данных
db = Database()