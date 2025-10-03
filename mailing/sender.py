# mailing/sender.py
import asyncio
import json
import os
from datetime import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile
from .models import BonusMailing
from database import db


class MailingSender:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bonus_mailing = BonusMailing(db)
    
    async def check_db_time(self):
        """Проверяет текущее время в БД"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT datetime('now'), datetime('now', 'localtime')")
                result = cursor.fetchone()
                print(f"🕒 Время в БД: UTC={result[0]}, Local={result[1]}")
                print(f"🕒 Время Python: {datetime.now()}")
        except Exception as e:
            print(f"❌ Ошибка проверки времени БД: {e}")
    
    async def send_active_mailings(self):
        """Отправляет активные рассылки"""
        try:
            # Проверяем время
            await self.check_db_time()
            
            mailings = self.bonus_mailing.get_all_mailings()
            current_time = datetime.now()
            
            print(f"🕒 Проверка рассылок в {current_time}")
            
            sent_count = 0
            for mailing in mailings:
                if not mailing['is_active']:
                    continue
                
                start_date = datetime.fromisoformat(mailing['start_date'])
                end_date = datetime.fromisoformat(mailing['end_date'])
                
                print(f"📧 Рассылка #{mailing['id']}: {start_date} - {end_date}")
                print(f"🕒 Текущее время: {current_time}")
                print(f"✅ Активна: {start_date <= current_time <= end_date}")
                
                # Проверяем, что текущее время в периоде рассылки
                if start_date <= current_time <= end_date:
                    count = await self._send_mailing(mailing)
                    sent_count += count
                    print(f"✅ Рассылка #{mailing['id']} отправлена {count} пользователям")
                else:
                    print(f"⏸️ Рассылка #{mailing['id']} не активна в данный момент")
                    
            if sent_count > 0:
                print(f"📧 Всего отправлено {sent_count} рассылок")
            else:
                print("ℹ️ Активных рассылок для отправки не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка при отправке рассылок: {e}")
    
    async def _send_mailing(self, mailing: dict) -> int:
        """Отправляет конкретную рассылку и возвращает количество отправленных"""
        sent_count = 0
        try:
            # Получаем пользователей по тарифам
            users = await self._get_users_by_tariffs(mailing)
            
            print(f"👥 Для рассылки #{mailing['id']} найдено пользователей: {len(users)}")
            
            if not users:
                print(f"⚠️ Для рассылки #{mailing['id']} не найдено подходящих пользователей")
                return 0
            
            file_paths = json.loads(mailing['file_paths']) if mailing['file_paths'] else []
            
            for user_id in users:
                try:
                    # Проверяем, не отправляли ли уже эту рассылку пользователю
                    if self.bonus_mailing.is_mailing_sent_to_user(mailing['id'], user_id):
                        print(f"⚠️ Рассылка #{mailing['id']} уже отправлена пользователю {user_id}")
                        continue
                    
                    # Отправляем сообщение
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode="HTML"
                    )
                    
                    # Отправляем файлы через BufferedInputFile
                    for file_path in file_paths:
                        try:
                            if os.path.exists(file_path):
                                # Читаем файл в память и создаем BufferedInputFile
                                with open(file_path, 'rb') as file:
                                    file_data = file.read()
                                
                                input_file = BufferedInputFile(
                                    file_data,
                                    filename=os.path.basename(file_path)
                                )
                                
                                await self.bot.send_document(
                                    chat_id=user_id,
                                    document=input_file,
                                    caption="🎁 Бонусный материал"
                                )
                                print(f"✅ Файл {os.path.basename(file_path)} отправлен пользователю {user_id}")
                            else:
                                print(f"❌ Файл не найден: {file_path}")
                                
                        except Exception as e:
                            print(f"❌ Ошибка отправки файла {file_path}: {e}")
                    
                    sent_count += 1
                    
                    # Логируем отправку
                    self.bonus_mailing.log_mailing_sent(mailing['id'], user_id, 'sent')
                    print(f"✅ Отправлено пользователю {user_id}")
                    
                    # Пауза между отправками
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
                    # Логируем ошибку
                    self.bonus_mailing.log_mailing_sent(mailing['id'], user_id, 'error', str(e))
                    
        except Exception as e:
            print(f"❌ Ошибка при отправке рассылки {mailing['id']}: {e}")
        
        return sent_count
    
    async def _get_users_by_tariffs(self, mailing: dict) -> list:
        """Получает список пользователей по выбранным тарифам из таблицы payments"""
        tariffs = json.loads(mailing['tariffs'])
        users = []
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Используем Python datetime для получения текущего времени
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                start_date_str = mailing['start_date'].replace('T', ' ').split('.')[0]  # Форматируем дату начала
                
                if tariffs:  # Если выбраны конкретные тарифы
                    placeholders = ','.join(['?'] * len(tariffs))
                    query = f'''
                        SELECT DISTINCT user_id 
                        FROM payments 
                        WHERE tariff_name IN ({placeholders}) 
                        AND status = 'succeeded'
                        AND valid_until >= ?
                        AND updated_at >= ?
                    '''
                    cursor.execute(query, tariffs + [current_time, start_date_str])
                else:  # Если все тарифы (пустой список)
                    query = '''
                        SELECT DISTINCT user_id 
                        FROM payments 
                        WHERE status = 'succeeded'
                        AND valid_until >= ?
                        AND updated_at >= ?
                    '''
                    cursor.execute(query, [current_time, start_date_str])
                
                users = [row[0] for row in cursor.fetchall()]
                
                print(f"🔍 Запрос: {query}")
                print(f"🔍 Параметры: {tariffs + [current_time, start_date_str] if tariffs else [current_time, start_date_str]}")
                print(f"🔍 Найдено записей: {len(users)}")
                
                # Дополнительная отладочная информация
                if users:
                    cursor.execute(f'''
                        SELECT user_id, tariff_name, valid_until, updated_at
                        FROM payments 
                        WHERE user_id = ? 
                        AND status = 'succeeded'
                        ORDER BY valid_until DESC
                        LIMIT 1
                    ''', (users[0],))
                    user_info = cursor.fetchone()
                    if user_info:
                        print(f"🔍 Пример пользователя: ID={user_info[0]}, тариф='{user_info[1]}', valid_until={user_info[2]}, updated_at={user_info[3]}")
            
        except Exception as e:
            print(f"❌ Ошибка получения пользователей: {e}")
        
        return users

# Фоновая задача для периодической проверки
async def mailing_scheduler(bot: Bot):
    """Планировщик рассылок"""
    sender = MailingSender(bot)
    
    print("🚀 Планировщик рассылок запущен")
    
    while True:
        try:
            await sender.send_active_mailings()
            # Проверяем каждые 5 минут
            await asyncio.sleep(300)
        except Exception as e:
            print(f"❌ Ошибка в планировщике рассылок: {e}")
            await asyncio.sleep(60)
