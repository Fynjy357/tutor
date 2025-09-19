import sqlite3
import os
from typing import List, Tuple, Optional
from datetime import datetime

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self, db_path: str = 'tutor_bot.db'):  # Используем вашу базу данных
        self.db_path = db_path
    
    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def create_tables(self):
        """Создание таблиц (уже есть в основной базе, поэтому пустая функция)"""
        pass  # Таблицы уже созданы в основной базе

class ConsentManager:
    """Менеджер для работы с соглашениями"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def read_document(self, filename: str) -> str:
        """Чтение документа из текущей папки"""
        try:
            # Читаем файл из текущей директории important_doc
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return "❌ Документ временно недоступен. Пожалуйста, попробуйте позже."
        except Exception as e:
            return f"❌ Ошибка при чтении документа: {str(e)}"
    
    def save_consent(self, telegram_id: int, ip_address: str, 
                    document_type: str, document_version: str, accepted: bool) -> bool:
        """Сохранение согласия в базу данных"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем существующую запись
                cursor.execute('''
                    SELECT id FROM user_consents 
                    WHERE telegram_id = ? AND document_type = ?
                ''', (telegram_id, document_type))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Обновляем существующую запись
                    cursor.execute('''
                        UPDATE user_consents 
                        SET accepted = ?, accepted_at = CURRENT_TIMESTAMP,
                            document_version = ?, ip_address = ?
                        WHERE id = ?
                    ''', (accepted, document_version, ip_address, existing[0]))
                else:
                    # Создаем новую запись
                    cursor.execute('''
                        INSERT INTO user_consents 
                        (telegram_id, ip_address, document_type, document_version, accepted)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (telegram_id, ip_address, document_type, document_version, accepted))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            print(f"Database error in save_consent: {e}")
            return False
    
    def has_user_consents(self, telegram_id: int) -> bool:
        """Проверка, есть ли у пользователя все необходимые согласия"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) FROM user_consents 
                    WHERE telegram_id = ? AND accepted = TRUE
                    AND document_type IN ('user_agreement', 'privacy_policy')
                ''', (telegram_id,))
                
                count = cursor.fetchone()[0]
                return count >= 2  # Оба согласия приняты
                
        except sqlite3.Error as e:
            print(f"Database error in has_user_consents: {e}")
            return False
    
    def get_user_consent_status(self, telegram_id: int) -> List[Tuple]:
        """Получение статуса согласий пользователя"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT document_type, accepted, accepted_at, document_version
                    FROM user_consents 
                    WHERE telegram_id = ?
                    ORDER BY accepted_at DESC
                ''', (telegram_id,))
                
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            print(f"Database error in get_user_consent_status: {e}")
            return []
    
    def get_user_consent_details(self, telegram_id: int, document_type: str) -> Optional[Tuple]:
        """Получение детальной информации о конкретном согласии"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, telegram_id, ip_address, document_type, 
                           document_version, accepted, accepted_at, created_at
                    FROM user_consents 
                    WHERE telegram_id = ? AND document_type = ?
                    ORDER BY accepted_at DESC
                    LIMIT 1
                ''', (telegram_id, document_type))
                
                return cursor.fetchone()
                
        except sqlite3.Error as e:
            print(f"Database error in get_user_consent_details: {e}")
            return None
    
    def get_all_user_consents(self, telegram_id: int) -> List[Tuple]:
        """Получение всех согласий пользователя"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, document_type, accepted, accepted_at, 
                           document_version, ip_address, created_at
                    FROM user_consents 
                    WHERE telegram_id = ?
                    ORDER BY created_at DESC
                ''', (telegram_id,))
                
                return cursor.fetchall()
                
        except sqlite3.Error as e:
            print(f"Database error in get_all_user_consents: {e}")
            return []
    
    def get_users_without_consents(self) -> List[int]:
        """Получение ID пользователей без согласий"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT DISTINCT telegram_id 
                    FROM user_consents 
                    WHERE accepted = FALSE
                    OR telegram_id NOT IN (
                        SELECT DISTINCT telegram_id 
                        FROM user_consents 
                        WHERE document_type IN ('user_agreement', 'privacy_policy')
                    )
                ''')
                
                return [row[0] for row in cursor.fetchall()]
                
        except sqlite3.Error as e:
            print(f"Database error in get_users_without_consents: {e}")
            return []
    
    def get_consent_statistics(self) -> dict:
        """Получение статистики по согласиям"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('''
                    SELECT 
                        COUNT(DISTINCT telegram_id) as total_users,
                        COUNT(CASE WHEN accepted = TRUE THEN 1 END) as accepted_consents,
                        COUNT(CASE WHEN accepted = FALSE THEN 1 END) as rejected_consents
                    FROM user_consents
                ''')
                
                stats = cursor.fetchone()
                
                # Статистика по типам документов
                cursor.execute('''
                    SELECT 
                        document_type,
                        COUNT(CASE WHEN accepted = TRUE THEN 1 END) as accepted,
                        COUNT(CASE WHEN accepted = FALSE THEN 1 END) as rejected
                    FROM user_consents
                    GROUP BY document_type
                ''')
                
                by_document = {}
                for row in cursor.fetchall():
                    by_document[row[0]] = {'accepted': row[1], 'rejected': row[2]}
                
                return {
                    'total_users': stats[0],
                    'accepted_consents': stats[1],
                    'rejected_consents': stats[2],
                    'by_document': by_document
                }
                
        except sqlite3.Error as e:
            print(f"Database error in get_consent_statistics: {e}")
            return {}

# Создаем экземпляры менеджеров для импорта
db_manager = DatabaseManager()
consent_manager = ConsentManager(db_manager)