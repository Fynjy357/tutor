from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from commands.config import SUPER_ADMIN_ID
import shutil
import os
from pathlib import Path
from datetime import datetime
import sqlite3
import zipfile
import asyncio
import subprocess
import tempfile

router = Router()

# Константа с именем файла базы данных
DATABASE_FILE = "tutor_bot.db"

def find_database_file():
    """Поиск файла базы данных в проекте"""
    possible_db_files = [
        DATABASE_FILE,
        "database.db",
        "bot.db",
        "db/tutor_bot.db",
        "data/tutor_bot.db",
        "src/tutor_bot.db",
    ]
    
    for db_file in possible_db_files:
        db_path = Path(db_file)
        if db_path.exists():
            return db_path
    
    db_files = list(Path('.').rglob('*.db'))
    if db_files:
        return db_files[0]
    
    return None

@router.message(Command("backup"))
async def admin_create_backup(message: Message):
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    backup_type = "full"
    if args:
        backup_type = args[0].lower()
    
    await create_backup(message, backup_type)

async def create_backup(message: Message, backup_type: str = "full"):
    """Создание резервной копии"""
    try:
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}_{backup_type}.zip"
        backup_path = backup_dir / backup_filename
        
        temp_dir = backup_dir / f"temp_{timestamp}"
        temp_dir.mkdir(exist_ok=True)
        
        status_msg = await message.answer("🔄 Создание резервной копии...")
        
        # Выполняем бэкап
        if backup_type == "db":
            success = await backup_database_only(temp_dir, message)
        elif backup_type == "logs":
            success = await backup_logs_only(temp_dir, message)
        else:
            success = await backup_full(temp_dir, message)
        
        if not success:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return
        
        # Создаем ZIP архив
        await create_zip_archive(temp_dir, backup_path, message)
        
        # Удаляем временную папку
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Отправляем файл пользователю
        await send_backup_file(message, backup_path, backup_type)
        
        await status_msg.edit_text("✅ Резервная копия успешно создана и отправлена!")
        await cleanup_old_backups(backup_dir)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании резервной копии: {e}")
        print(f"Ошибка создания бэкапа: {e}")

async def backup_database_only(temp_dir: Path, message: Message) -> bool:
    """Бэкап только базы данных с использованием SQLite backup API"""
    db_path = find_database_file()
    if not db_path or not db_path.exists():
        await message.answer(f"❌ Файл базы данных '{DATABASE_FILE}' не найден!")
        return False
    
    try:
        # Метод 1: Используем SQLite backup API (самый надежный)
        await message.answer("🔒 Создаем резервную копию базы данных...")
        
        # Создаем временный файл для бэкапа
        backup_db_path = temp_dir / f"backup_{db_path.name}"
        
        # Подключаемся к исходной и целевой базам
        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_db_path)
        
        # Используем backup API для безопасного копирования
        source_conn.backup(backup_conn)
        
        # Закрываем соединения
        backup_conn.close()
        source_conn.close()
        
        # Создаем SQL дамп для удобства
        await create_sql_dump(backup_db_path, temp_dir)
        
        await message.answer(f"✅ База данных успешно скопирована: {db_path.name}")
        return True
        
    except sqlite3.Error as e:
        await message.answer(f"❌ Ошибка SQLite при создании бэкапа: {e}")
        return False
    except Exception as e:
        await message.answer(f"❌ Общая ошибка при создании бэкапа БД: {e}")
        return False

async def backup_logs_only(temp_dir: Path, message: Message) -> bool:
    """Бэкап только логов"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        await message.answer("❌ Папка логов не найдена")
        return False
    
    try:
        backup_logs_dir = temp_dir / "logs"
        shutil.copytree(logs_dir, backup_logs_dir)
        await message.answer("✅ Логи скопированы")
        return True
    except Exception as e:
        await message.answer(f"❌ Ошибка при копировании логов: {e}")
        return False

async def backup_full(temp_dir: Path, message: Message) -> bool:
    """Полный бэкап"""
    # Бэкап базы данных
    db_success = await backup_database_only(temp_dir, message)
    if not db_success:
        return False
    
    # Бэкап логов
    logs_success = await backup_logs_only(temp_dir, message)
    
    # Бэкап конфигурационных файлов
    config_files = [
        "commands/config.py",
        ".env",
        "requirements.txt",
        "bot.py",
        "admin_backup.py"
    ]
    
    try:
        copied_files = []
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                backup_config_path = temp_dir / config_file
                backup_config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_path, backup_config_path)
                copied_files.append(config_file)
        
        if copied_files:
            await message.answer(f"✅ Конфиги скопированы: {', '.join(copied_files)}")
            
        return True
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при копировании конфигов: {e}")
        return False

async def create_sql_dump(db_path: Path, temp_dir: Path):
    """Создает SQL дамп базы данных"""
    try:
        dump_path = temp_dir / "database_dump.sql"
        
        with sqlite3.connect(db_path) as conn:
            with open(dump_path, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(f'{line}\n')
                    
    except Exception as e:
        print(f"Ошибка создания SQL дампа: {e}")

async def create_zip_archive(source_dir: Path, zip_path: Path, message: Message):
    """Создает ZIP архив из папки"""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        file_size = zip_path.stat().st_size
        if file_size == 0:
            await message.answer("⚠️ Создан пустой архив. Проверьте наличие данных для резервного копирования.")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при создании ZIP архива: {e}")
        raise

async def send_backup_file(message: Message, backup_path: Path, backup_type: str):
    """Отправляет файл бэкапа пользователю"""
    try:
        file_size = backup_path.stat().st_size
        
        if file_size > 45 * 1024 * 1024:
            await message.answer(
                f"⚠️ Файл бэкапа слишком большой ({file_size/1024/1024:.1f} MB). "
                f"Максимальный размер для отправки в Telegram - 50MB.\n\n"
                f"📁 Файл сохранен локально: {backup_path}"
            )
            return
        
        backup_file = FSInputFile(backup_path)
        caption = (
            f"💾 Резервная копия создана\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"📦 Тип: {backup_type}\n"
            f"📏 Размер: {file_size/1024/1024:.2f} MB"
        )
        
        await message.answer_document(
            document=backup_file,
            caption=caption,
            filename=backup_path.name
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке файла: {e}")

async def cleanup_old_backups(backup_dir: Path, keep_last: int = 10):
    """Очищает старые бэкапы"""
    try:
        backup_files = list(backup_dir.glob("backup_*.zip"))
        
        if len(backup_files) > keep_last:
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for old_file in backup_files[keep_last:]:
                old_file.unlink()
                print(f"Удален старый бэкап: {old_file.name}")
                
    except Exception as e:
        print(f"Ошибка при очистке старых бэкапов: {e}")

# Команда для проверки состояния базы данных
@router.message(Command("db_status"))
async def admin_db_status(message: Message):
    """Проверка состояния базы данных"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    db_path = find_database_file()
    if not db_path or not db_path.exists():
        await message.answer(f"❌ Файл базы данных '{DATABASE_FILE}' не найден!")
        return
    
    try:
        # Проверяем, можно ли подключиться к базе
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем информацию о таблицах
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # Получаем размер базы
        file_size = db_path.stat().st_size
        
        # Проверяем основные таблицы
        main_tables = ['tutors', 'students', 'lessons']
        missing_tables = [table for table in main_tables if table not in [t[0] for t in tables]]
        
        conn.close()
        
        status_message = (
            f"📊 Статус базы данных:\n\n"
            f"📁 Файл: {db_path.name}\n"
            f"📏 Размер: {file_size/1024/1024:.2f} MB\n"
            f"📊 Таблиц: {len(tables)}\n"
        )
        
        if missing_tables:
            status_message += f"⚠️ Отсутствуют таблицы: {', '.join(missing_tables)}\n"
        else:
            status_message += "✅ Все основные таблицы присутствуют\n"
            
        status_message += f"✅ База данных доступна для чтения/записи"
        
        await message.answer(status_message)
        
    except sqlite3.Error as e:
        await message.answer(f"❌ Ошибка подключения к базе данных: {e}")
    except Exception as e:
        await message.answer(f"❌ Общая ошибка: {e}")

# Команда для принудительного освобождения базы (опасно!)
@router.message(Command("db_unlock"))
async def admin_db_unlock(message: Message):
    """Попытка освободить заблокированную базу данных"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    await message.answer(
        "⚠️ Внимание! Эта команда может привести к потере данных!\n\n"
        "Рекомендуется:\n"
        "1. Остановить бота\n"
        "2. Сделать бэкап\n"
        "3. Перезапустить бота\n\n"
        "Используйте команду /backup для безопасного создания резервной копии."
    )