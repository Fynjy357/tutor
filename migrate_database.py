# migrate_database.py
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Мигрирует базу данных, добавляя недостающие колонки"""
    try:
        conn = sqlite3.connect('tutor_bot.db')
        cursor = conn.cursor()
        
        # Создаем временную таблицу с новой структурой
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS students_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT,
            parent_phone TEXT,
            status TEXT DEFAULT 'active',
            tutor_id INTEGER,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            student_telegram_id INTEGER,
            parent_telegram_id INTEGER,
            student_token TEXT,
            parent_token TEXT,
            delete_after TIMESTAMP,
            student_username TEXT,
            parent_username TEXT,
            FOREIGN KEY (tutor_id) REFERENCES tutors (id)
        )
        ''')
        
        # Копируем данные из старой таблицы в новую
        cursor.execute('''
        INSERT INTO students_new 
        (id, full_name, phone, parent_phone, status, tutor_id, registration_date)
        SELECT id, full_name, phone, parent_phone, status, tutor_id, registration_date
        FROM students
        ''')
        
        # Удаляем старую таблицу
        cursor.execute('DROP TABLE students')
        
        # Переименовываем новую таблицу
        cursor.execute('ALTER TABLE students_new RENAME TO students')
        
        # Создаем индексы для уникальных полей
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_student_token ON students(student_token)')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_parent_token ON students(parent_token)')
        
        # Проверяем и добавляем telegram_id в tutors если нужно
        cursor.execute("PRAGMA table_info(tutors)")
        existing_tutor_columns = [column[1] for column in cursor.fetchall()]
        
        if 'telegram_id' not in existing_tutor_columns:
            # Создаем временную таблицу для tutors
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutors_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                promo_code TEXT DEFAULT '0',
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
            ''')
            
            # Копируем данные
            cursor.execute('''
            INSERT INTO tutors_new 
            (id, full_name, phone, promo_code, registration_date, status)
            SELECT id, full_name, phone, promo_code, registration_date, status
            FROM tutors
            ''')
            
            # Удаляем старую таблицу
            cursor.execute('DROP TABLE tutors')
            
            # Переименовываем новую таблицу
            cursor.execute('ALTER TABLE tutors_new RENAME TO tutors')
            
            logger.info("Добавлена колонка telegram_id в tutors")
        
        conn.commit()
        logger.info("Миграция базы данных завершена успешно!")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при миграции базы данных: {e}")
        # В случае ошибки откатываем изменения
        conn.rollback()
    finally:
        if conn:
            conn.close()

def backup_database():
    """Создает backup базы данных"""
    if os.path.exists('tutor_bot.db'):
        import shutil
        shutil.copy2('tutor_bot.db', 'tutor_bot_backup.db')
        logger.info("Создан backup базы данных: tutor_bot_backup.db")

if __name__ == "__main__":
    backup_database()
    migrate_database()