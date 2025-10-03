# mailing/models.py
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional

class MailingConfig:
    # Путь к папке с файлами
    FILES_DIR = "mailing/files"
    
    # Доступные тарифы
    AVAILABLE_TARIFFS = ["1 месяц", "6 месяцев", "1 год"]

class BonusMailing:
    def __init__(self, db):
        self.db = db
        self._ensure_files_dir()
        # УБРАНО: _ensure_table_exists() - таблицы уже созданы в database.py
    
    def _ensure_files_dir(self):
        """Создает папку для файлов если её нет"""
        os.makedirs(MailingConfig.FILES_DIR, exist_ok=True)
    
    def create_mailing(self, message_text: str, file_paths: List[str], 
                      tariffs: List[str], start_date: datetime, end_date: datetime) -> int:
        """Создает новую бонусную рассылку"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO bonus_mailings 
                (message_text, file_paths, tariffs, start_date, end_date)
                VALUES (?, ?, ?, ?, ?)
                ''', (message_text, json.dumps(file_paths), json.dumps(tariffs), 
                     start_date.isoformat(), end_date.isoformat()))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Ошибка при создании рассылки: {e}")
            return None
    
    def get_all_mailings(self) -> List[dict]:
        """Получает все рассылки"""
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM bonus_mailings ORDER BY created_at DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении рассылок: {e}")
            return []
    
    def get_mailing_by_id(self, mailing_id: int) -> Optional[dict]:
        """Получает рассылку по ID"""
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bonus_mailings WHERE id = ?', (mailing_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Ошибка при получении рассылки: {e}")
            return None
    
    def update_mailing(self, mailing_id: int, **kwargs):
        """Обновляет рассылку"""
        try:
            allowed_fields = ['message_text', 'file_paths', 'tariffs', 'start_date', 'end_date', 'is_active']
            updates = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    if field in ['file_paths', 'tariffs']:
                        value = json.dumps(value)
                    elif field in ['start_date', 'end_date'] and isinstance(value, datetime):
                        value = value.isoformat()
                    updates.append(f"{field} = ?")
                    values.append(value)
            
            if updates:
                values.append(mailing_id)
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f'''
                    UPDATE bonus_mailings 
                    SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    ''', values)
                    conn.commit()
        except Exception as e:
            print(f"Ошибка при обновлении рассылки: {e}")
    
    def delete_mailing(self, mailing_id: int):
        """Удаляет рассылку"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM bonus_mailings WHERE id = ?', (mailing_id,))
                conn.commit()
        except Exception as e:
            print(f"Ошибка при удалении рассылки: {e}")
    
    def is_mailing_sent_to_user(self, mailing_id: int, user_id: int) -> bool:
        """Проверяет, была ли уже отправлена рассылка пользователю"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT id FROM mailing_logs 
                WHERE mailing_id = ? AND user_id = ? AND status = 'sent'
                ''', (mailing_id, user_id))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Ошибка проверки отправки: {e}")
            return False
    
    def log_mailing_sent(self, mailing_id: int, user_id: int, status: str = 'sent', error_message: str = None):
        """Логирует отправку рассылки"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                INSERT INTO mailing_logs 
                (mailing_id, user_id, status, error_message)
                VALUES (?, ?, ?, ?)
                ''', (mailing_id, user_id, status, error_message))
                conn.commit()
                print(f"✅ Запись добавлена в mailing_logs: mailing_id={mailing_id}, user_id={user_id}, status={status}")
        except Exception as e:
            print(f"❌ Ошибка логирования отправки: {e}")
