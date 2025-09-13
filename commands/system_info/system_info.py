from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from commands.config import SUPER_ADMIN_ID
import platform
import socket
import datetime
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, List, Tuple
import asyncio

router = Router()

def get_disk_usage(path: str = '.') -> Dict[str, float]:
    """Получение информации о использовании диска"""
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path), None, ctypes.pointer(total_bytes), ctypes.pointer(free_bytes)
            )
            total = total_bytes.value
            free = free_bytes.value
            used = total - free
        else:  # Linux/Mac
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            used = total - free
            
        return {
            'total': total,
            'used': used,
            'free': free,
            'percent': (used / total) * 100 if total > 0 else 0
        }
    except:
        return {'total': 0, 'used': 0, 'free': 0, 'percent': 0}

def get_memory_info() -> Dict[str, float]:
    """Получение информации о памяти"""
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullExtendedVirtual", ctypes.c_ulonglong),
                ]

            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
            
            return {
                'total': memory_status.ullTotalPhys,
                'available': memory_status.ullAvailPhys,
                'used': memory_status.ullTotalPhys - memory_status.ullAvailPhys,
                'percent': memory_status.dwMemoryLoad
            }
        else:  # Linux/Mac
            with open('/proc/meminfo', 'r') as mem:
                lines = mem.readlines()
                total = int(lines[0].split()[1]) * 1024
                available = int(lines[2].split()[1]) * 1024
                
            return {
                'total': total,
                'available': available,
                'used': total - available,
                'percent': ((total - available) / total) * 100 if total > 0 else 0
            }
    except:
        return {'total': 0, 'available': 0, 'used': 0, 'percent': 0}

def get_cpu_info() -> Dict[str, str]:
    """Получение информации о CPU"""
    info = {}
    
    try:
        if os.name == 'nt':  # Windows
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            info['name'] = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            info['cores'] = str(os.cpu_count())
        else:  # Linux/Mac
            with open('/proc/cpuinfo', 'r') as cpuinfo:
                for line in cpuinfo:
                    if line.strip() and ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'model name':
                            info['name'] = value
                        elif key == 'cpu cores':
                            info['cores'] = value
            if 'cores' not in info:
                info['cores'] = str(os.cpu_count() or 1)
    except:
        info['name'] = "Неизвестный процессор"
        info['cores'] = str(os.cpu_count() or 1)
    
    return info

def get_system_uptime() -> str:
    """Получение времени работы системы"""
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            lib = ctypes.windll.kernel32
            tick_count = lib.GetTickCount64()
            uptime_seconds = tick_count // 1000
        else:  # Linux/Mac
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
        
        hours, remainder = divmod(uptime_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        
        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{int(days)}д")
        if hours > 0:
            uptime_parts.append(f"{int(hours)}ч")
        if minutes > 0:
            uptime_parts.append(f"{int(minutes)}м")
        if seconds > 0 and len(uptime_parts) < 2:
            uptime_parts.append(f"{int(seconds)}с")
            
        return ' '.join(uptime_parts) if uptime_parts else "0с"
    except:
        return "Неизвестно"

def get_bot_uptime() -> str:
    """Получение времени работы бота"""
    try:
        # Простой способ - время запуска модуля
        start_time = datetime.datetime.fromtimestamp(Path(__file__).stat().st_mtime)
        uptime = datetime.datetime.now() - start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        uptime_parts = []
        if days > 0:
            uptime_parts.append(f"{days}д")
        if hours > 0:
            uptime_parts.append(f"{hours}ч")
        if minutes > 0:
            uptime_parts.append(f"{minutes}м")
        if seconds > 0:
            uptime_parts.append(f"{seconds}с")
            
        return ' '.join(uptime_parts) if uptime_parts else "0с"
    except:
        return "Неизвестно"

def get_system_info() -> Dict[str, str]:
    """Получение информации о системе"""
    info = {}
    
    # Информация о платформе
    info['platform'] = platform.platform()
    info['system'] = platform.system()
    info['release'] = platform.release()
    info['version'] = platform.version()
    info['architecture'] = platform.architecture()[0]
    
    # Информация о Python
    info['python_version'] = platform.python_version()
    info['python_implementation'] = platform.python_implementation()
    
    # Информация о CPU
    cpu_info = get_cpu_info()
    info['processor'] = cpu_info.get('name', 'Неизвестный процессор')
    info['cpu_cores'] = cpu_info.get('cores', '1')
    
    # Информация о памяти
    memory = get_memory_info()
    info['memory_total'] = f"{memory['total'] / (1024**3):.1f} GB"
    info['memory_available'] = f"{memory['available'] / (1024**3):.1f} GB"
    info['memory_used'] = f"{memory['used'] / (1024**3):.1f} GB"
    info['memory_percent'] = f"{memory['percent']:.1f}%"
    
    # Информация о диске
    disk = get_disk_usage()
    info['disk_total'] = f"{disk['total'] / (1024**3):.1f} GB"
    info['disk_used'] = f"{disk['used'] / (1024**3):.1f} GB"
    info['disk_free'] = f"{disk['free'] / (1024**3):.1f} GB"
    info['disk_percent'] = f"{disk['percent']:.1f}%"
    
    # Сетевая информация
    hostname = socket.gethostname()
    info['hostname'] = hostname
    try:
        info['ip_address'] = socket.gethostbyname(hostname)
    except:
        info['ip_address'] = "Не удалось определить"
    
    # Время работы
    info['system_uptime'] = get_system_uptime()
    info['bot_uptime'] = get_bot_uptime()
    
    # Информация о процессе
    info['pid'] = str(os.getpid())
    info['working_dir'] = os.getcwd()
    
    return info

def get_bot_info() -> Dict[str, str]:
    """Получение информации о боте"""
    info = {}
    
    # Информация о файлах бота
    bot_files = [
        'bot.py', 'commands/', 'handlers/', 'tutor_bot.db', 
        'logs/', 'backups/', '.env', 'requirements.txt'
    ]
    
    file_info = []
    total_size = 0
    
    for file_path in bot_files:
        path = Path(file_path)
        if path.exists():
            if path.is_file():
                size = path.stat().st_size
                total_size += size
                file_info.append(f"📄 {file_path} ({size/1024:.1f} KB)")
            else:
                # Для папок считаем общий размер
                folder_size = 0
                for f in path.rglob('*'):
                    if f.is_file():
                        folder_size += f.stat().st_size
                total_size += folder_size
                file_info.append(f"📁 {file_path}/ ({folder_size/1024:.1f} KB)")
        else:
            file_info.append(f"❌ {file_path} (отсутствует)")
    
    info['files'] = file_info
    info['total_size'] = f"{total_size / (1024**2):.2f} MB"
    
    # Размер базы данных
    db_path = Path("tutor_bot.db")
    if db_path.exists():
        db_size = db_path.stat().st_size
        info['db_size'] = f"{db_size / (1024**2):.2f} MB"
        info['db_tables'] = get_database_tables_count(db_path)
    else:
        info['db_size'] = "Не найдена"
        info['db_tables'] = "0"
    
    # Количество лог файлов
    logs_dir = Path("logs")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.log"))
        info['log_files'] = str(len(log_files))
    else:
        info['log_files'] = "0"
    
    return info

def get_database_tables_count(db_path: Path) -> str:
    """Получение количества таблиц в базе данных"""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        count = cursor.fetchone()[0]
        conn.close()
        return str(count)
    except:
        return "Неизвестно"

def format_system_info(info: Dict[str, str]) -> str:
    """Форматирование информации о системе в читаемый вид"""
    message = "🖥️ *ИНФОРМАЦИЯ О СИСТЕМЕ*\n\n"
    
    message += "💻 *Система:*\n"
    message += f"• ОС: {info['platform']}\n"
    message += f"• Архитектура: {info['architecture']}\n"
    message += f"• Процессор: {info['processor'][:50]}...\n"
    message += f"• Ядер: {info['cpu_cores']}\n\n"
    
    message += "🧠 *Память:*\n"
    message += f"• Всего: {info['memory_total']}\n"
    message += f"• Использовано: {info['memory_used']} ({info['memory_percent']})\n"
    message += f"• Доступно: {info['memory_available']}\n\n"
    
    message += "💾 *Диск:*\n"
    message += f"• Всего: {info['disk_total']}\n"
    message += f"• Использовано: {info['disk_used']} ({info['disk_percent']})\n"
    message += f"• Свободно: {info['disk_free']}\n\n"
    
    message += "🌐 *Сеть:*\n"
    message += f"• Хост: {info['hostname']}\n"
    message += f"• IP: {info['ip_address']}\n\n"
    
    message += "⏰ *Время работы:*\n"
    message += f"• Система: {info['system_uptime']}\n"
    message += f"• Бот: {info['bot_uptime']}\n\n"
    
    message += "🐍 *Python:*\n"
    message += f"• Версия: {info['python_version']}\n"
    message += f"• PID: {info['pid']}\n"
    message += f"• Рабочая папка: {info['working_dir']}\n"
    
    return message

def format_bot_info(info: Dict[str, str]) -> str:
    """Форматирование информации о боте"""
    message = "🤖 *ИНФОРМАЦИЯ О БОТЕ*\n\n"
    
    message += f"📊 *Общий размер:* {info['total_size']}\n"
    message += f"🗄️ *База данных:* {info['db_size']} ({info['db_tables']} таблиц)\n"
    message += f"📋 *Лог файлов:* {info['log_files']}\n\n"
    
    message += "📁 *Файлы проекта:*\n"
    for file_info in info['files'][:8]:  # Показываем первые 8 файлов
        message += f"• {file_info}\n"
    
    if len(info['files']) > 8:
        message += f"• ... и еще {len(info['files']) - 8} файлов/папок\n"
    
    return message

@router.message(Command("system_info"))
async def admin_system_info(message: Message):
    """Получение информации о системе"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        status_msg = await message.answer("🔄 Сбор информации о системе...")
        
        # Получаем информацию
        system_info = get_system_info()
        bot_info = get_bot_info()
        
        # Форматируем и отправляем
        system_message = format_system_info(system_info)
        bot_message = format_bot_info(bot_info)
        
        # Отправляем частями
        await status_msg.edit_text(system_message, parse_mode='Markdown')
        await asyncio.sleep(1)
        await message.answer(bot_message, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации о системе: {e}")

@router.message(Command("disk_info"))
async def admin_disk_info(message: Message):
    """Детальная информация о диске"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        disk_info = get_disk_usage()
        project_size = 0
        
        # Считаем размер проекта
        for path in Path('.').rglob('*'):
            if path.is_file():
                project_size += path.stat().st_size
        
        message_text = (
            "💾 *ИНФОРМАЦИЯ О ДИСКЕ*\n\n"
            f"📦 *Весь диск:*\n"
            f"• Всего: {disk_info['total'] / (1024**3):.1f} GB\n"
            f"• Использовано: {disk_info['used'] / (1024**3):.1f} GB\n"
            f"• Свободно: {disk_info['free'] / (1024**3):.1f} GB\n"
            f"• Заполнено: {disk_info['percent']:.1f}%\n\n"
            f"📁 *Проект бота:*\n"
            f"• Размер: {project_size / (1024**3):.2f} GB\n"
            f"• Папка: {os.getcwd()}\n"
        )
        
        await message.answer(message_text, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации о диске: {e}")

async def admin_bot_files(message: Message):
    """Список файлов бота с размерами"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        status_msg = await message.answer("📁 Сканирование файлов проекта...")
        
        # Получаем список всех файлов и папок в проекте
        files_info = []
        total_size = 0
        file_count = 0
        folder_count = 0
        
        for item in Path('.').iterdir():
            if item.is_file():
                size = item.stat().st_size
                total_size += size
                file_count += 1
                files_info.append(f"📄 {item.name} ({size/1024:.1f} KB)")
            elif item.is_dir() and not item.name.startswith('.'):  # Исключаем скрытые папки
                folder_size = 0
                folder_files = 0
                for f in item.rglob('*'):
                    if f.is_file():
                        folder_size += f.stat().st_size
                        folder_files += 1
                
                total_size += folder_size
                file_count += folder_files
                folder_count += 1
                files_info.append(f"📁 {item.name}/ ({folder_size/1024:.1f} KB, {folder_files} файлов)")
        
        # Сортируем по размеру (по убыванию)
        files_info.sort(key=lambda x: float(x.split('(')[1].split()[0]), reverse=True)
        
        message_text = (
            f"📊 *ФАЙЛЫ ПРОЕКТА*\n\n"
            f"📦 *Общая статистика:*\n"
            f"• Всего файлов: {file_count}\n"
            f"• Папок: {folder_count}\n"
            f"• Общий размер: {total_size / (1024**2):.2f} MB\n\n"
            f"📋 *Самые крупные файлы/папки:*\n"
        )
        
        # Добавляем топ-10 самых крупных файлов/папок
        for i, file_info in enumerate(files_info[:10], 1):
            message_text += f"{i}. {file_info}\n"
        
        if len(files_info) > 10:
            message_text += f"\n... и еще {len(files_info) - 10} элементов"
        
        await status_msg.edit_text(message_text, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при сканировании файлов: {e}")
async def admin_python_info(message: Message):
    """Информация о Python окружении"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        # Получаем информацию о Python
        python_info = {
            'version': platform.python_version(),
            'implementation': platform.python_implementation(),
            'compiler': platform.python_compiler(),
            'build': platform.python_build(),
            'executable': sys.executable,
            'path': sys.path[:3] + ['...'] + sys.path[-2:] if len(sys.path) > 5 else sys.path
        }
        
        # Получаем список установленных пакетов
        try:
            import pkg_resources
            installed_packages = []
            for dist in pkg_resources.working_set:
                installed_packages.append(f"{dist.project_name}=={dist.version}")
            
            # Сортируем и берем топ-15 самых важных
            important_packages = [
                'aiogram', 'aiohttp', 'sqlite3', 'python-dotenv', 
                'pytz', 'requests', 'pillow', 'numpy', 'pandas'
            ]
            
            top_packages = []
            for pkg in important_packages:
                for installed in installed_packages:
                    if pkg in installed.lower():
                        top_packages.append(installed)
                        break
            
            # Добавляем еще несколько случайных пакетов до 15
            other_packages = [p for p in installed_packages if p not in top_packages]
            top_packages.extend(other_packages[:15 - len(top_packages)])
            
        except ImportError:
            top_packages = ["Не удалось получить список пакетов (pkg_resources)"]
        
        # Формируем сообщение
        message_text = (
            "🐍 *ИНФОРМАЦИЯ О PYTHON*\n\n"
            f"🔧 *Версия:* {python_info['version']}\n"
            f"🏗️ *Реализация:* {python_info['implementation']}\n"
            f"⚙️ *Компилятор:* {python_info['compiler']}\n"
            f"📦 *Сборка:* {python_info['build'][0]} ({python_info['build'][1]})\n"
            f"🚀 *Исполняемый файл:* {python_info['executable']}\n\n"
            "📁 *Пути импорта:*\n"
        )
        
        # Добавляем пути импорта
        for i, path in enumerate(python_info['path']):
            if i < 3 or i >= len(python_info['path']) - 2:
                message_text += f"• {path}\n"
            elif i == 3:
                message_text += "• ...\n"
        
        message_text += f"\n📋 *Установленные пакеты ({len(top_packages)} из {len(installed_packages) if 'installed_packages' in locals() else '?'}):*\n"
        
        for i, pkg in enumerate(top_packages[:15], 1):
            message_text += f"{i}. {pkg}\n"
        
        if len(top_packages) > 15:
            message_text += f"... и еще {len(top_packages) - 15} пакетов"
        
        await message.answer(message_text, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации о Python: {e}")

@router.message(Command("system_health"))
async def admin_system_health(message: Message):
    """Проверка здоровья системы"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        status_msg = await message.answer("🩺 Проверка здоровья системы...")
        
        checks = []
        
        # Проверка диска
        disk = get_disk_usage()
        disk_status = "✅" if disk['percent'] < 90 else "⚠️" if disk['percent'] < 95 else "❌"
        checks.append(f"{disk_status} Диск: {disk['percent']:.1f}% заполнено")
        
        # Проверка памяти
        memory = get_memory_info()
        memory_status = "✅" if memory['percent'] < 80 else "⚠️" if memory['percent'] < 90 else "❌"
        checks.append(f"{memory_status} Память: {memory['percent']:.1f}% использовано")
        
        # Проверка базы данных
        db_path = Path("tutor_bot.db")
        db_status = "✅" if db_path.exists() else "❌"
        db_size = db_path.stat().st_size if db_path.exists() else 0
        checks.append(f"{db_status} База данных: {db_size / (1024**2):.2f} MB")
        
        # Проверка логов
        logs_dir = Path("logs")
        log_status = "✅" if logs_dir.exists() and list(logs_dir.glob("*.log")) else "⚠️"
        log_count = len(list(logs_dir.glob("*.log"))) if logs_dir.exists() else 0
        checks.append(f"{log_status} Лог файлы: {log_count} шт")
        
        # Проверка .env файла
        env_path = Path(".env")
        env_status = "✅" if env_path.exists() else "❌"
        checks.append(f"{env_status} Файл .env: {'найден' if env_status == '✅' else 'отсутствует'}")
        
        # Общая оценка
        error_count = sum(1 for check in checks if '❌' in check)
        warning_count = sum(1 for check in checks if '⚠️' in check)
        
        if error_count > 0:
            overall_status = "❌ Критическое состояние"
        elif warning_count > 0:
            overall_status = "⚠️ Требует внимания"
        else:
            overall_status = "✅ Отличное состояние"
        
        message_text = (
            f"🩺 *ПРОВЕРКА ЗДОРОВЬЯ СИСТЕМЫ*\n\n"
            f"📊 *Общий статус:* {overall_status}\n"
            f"❌ Ошибки: {error_count}, ⚠️ Предупреждения: {warning_count}\n\n"
            "🔍 *Результаты проверок:*\n"
        )
        
        for check in checks:
            message_text += f"• {check}\n"
        
        message_text += (
            f"\n💡 *Рекомендации:*\n"
            f"{'• Проверьте наличие критических ошибок' if error_count > 0 else ''}"
            f"{'• Обратите внимание на предупреждения' if warning_count > 0 else '• Система в отличном состоянии!'}"
        )
        
        await status_msg.edit_text(message_text, parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке здоровья системы: {e}")

# Добавляем хэндлер для помощи по командам
@router.message(Command("system_help"))
async def admin_system_help(message: Message):
    """Помощь по системным командам"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    help_text = (
        "🤖 *СИСТЕМНЫЕ КОМАНДЫ ДЛЯ АДМИНИСТРАТОРА*\n\n"
        "📊 *Мониторинг:*\n"
        "• `/system_info` - полная информация о системе\n"
        "• `/disk_info` - информация о диске\n"
        "• `/bot_files` - список файлов проекта\n"
        "• `/python_info` - информация о Python\n"
        "• `/system_health` - проверка здоровья системы\n\n"
        "🛠️ *Управление:*\n"
        "• `/restart` - перезагрузка бота\n"
        "• `/shutdown` - выключение бота\n"
        "• `/logs` - просмотр логов\n\n"
        "📋 *Статистика:*\n"
        "• `/stats` - статистика бота\n"
        "• `/users` - список пользователей\n"
        "• `/db_stats` - статистика базы данных\n\n"
        "❓ *Помощь:*\n"
        "• `/system_help` - эта справка\n\n"
        "⚠️ *Только для супер-администратора*"
    )
    
    await message.answer(help_text, parse_mode='Markdown')