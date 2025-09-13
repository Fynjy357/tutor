from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from commands.config import SUPER_ADMIN_ID
import os
from pathlib import Path

router = Router()

@router.message(Command("logs"))
async def admin_view_logs(message: Message):
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем аргументы после команды
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    
    # Устанавливаем количество строк по умолчанию
    lines_count = 50
    
    if len(args) >= 1:
        try:
            lines_count = int(args[0])
            if lines_count <= 0:
                await message.answer("❌ Количество строк должно быть положительным числом")
                return
            if lines_count > 1000:
                await message.answer("⚠️ Максимальное количество строк - 1000. Будут показаны последние 1000 строк")
                lines_count = 1000
        except ValueError:
            await message.answer("❌ Количество строк должно быть числом")
            return
    
    await send_logs(message, lines_count)

async def send_logs(message: Message, lines_count: int):
    """Отправить последние N строк логов"""
    try:
        log_file_path = Path("logs/bot.log")
        
        # Проверяем существование файла логов
        if not log_file_path.exists():
            await message.answer("❌ Файл логов не найден: logs/bot.log")
            return
        
        # Проверяем размер файла
        file_size = log_file_path.stat().st_size
        if file_size == 0:
            await message.answer("📝 Файл логов пуст")
            return
        
        # Читаем последние N строк из файла
        logs_content = read_last_lines(log_file_path, lines_count)
        
        if not logs_content:
            await message.answer("📝 Логи не найдены или файл пуст")
            return
        
        # Отправляем логи частями (ограничение Telegram - 4096 символов)
        await send_logs_in_parts(message, logs_content, lines_count)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при чтении логов: {e}")
        print(f"Ошибка чтения логов: {e}")

def read_last_lines(file_path: Path, n: int) -> str:
    """Читает последние N строк из файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Читаем все строки и берем последние N
            lines = file.readlines()
            last_lines = lines[-n:] if len(lines) > n else lines
            return ''.join(last_lines)
    except UnicodeDecodeError:
        # Пробуем читать в бинарном режиме для файлов с другой кодировкой
        with open(file_path, 'rb') as file:
            lines = file.readlines()
            last_lines = lines[-n:] if len(lines) > n else lines
            # Пробуем декодировать с разными кодировками
            for encoding in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    decoded_lines = [line.decode(encoding) for line in last_lines]
                    return ''.join(decoded_lines)
                except UnicodeDecodeError:
                    continue
            return "❌ Не удалось декодировать файл логов"

async def send_logs_in_parts(message: Message, logs_content: str, total_lines: int):
    """Отправляет логи частями с учетом ограничений Telegram"""
    max_message_length = 4000  # Оставляем запас от 4096
    
    if len(logs_content) <= max_message_length:
        # Если все помещается в одно сообщение
        header = f"📋 Последние {total_lines} строк логов:\n\n"
        await message.answer(header + f"```\n{logs_content}\n```", parse_mode='Markdown')
    else:
        # Разбиваем на части
        header = f"📋 Последние {total_lines} строк логов (часть {{part}}):\n\n"
        
        parts = []
        current_part = ""
        lines = logs_content.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 10 > max_message_length:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        # Отправляем части с задержкой
        import asyncio
        for i, part in enumerate(parts, 1):
            part_header = header.format(part=f"{i}/{len(parts)}")
            await message.answer(part_header + f"```\n{part}\n```", parse_mode='Markdown')
            await asyncio.sleep(0.5)  # Задержка между сообщениями

# Дополнительная команда для поиска по логам
@router.message(Command("logs_search"))
async def admin_search_logs(message: Message):
    """Поиск по логам"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    
    if len(args) < 1:
        await message.answer("❌ Укажите поисковый запрос: /logs_search <текст>")
        await message.answer("📝 Пример: /logs_search error")
        return
    
    search_text = ' '.join(args)
    await search_in_logs(message, search_text)

async def search_in_logs(message: Message, search_text: str):
    """Поиск текста в логах"""
    try:
        log_file_path = Path("logs/bot.log")
        
        if not log_file_path.exists():
            await message.answer("❌ Файл логов не найден: logs/bot.log")
            return
        
        # Читаем файл и ищем совпадения
        found_lines = []
        with open(log_file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if search_text.lower() in line.lower():
                    found_lines.append(line)
        
        if not found_lines:
            await message.answer(f"🔍 По запросу '{search_text}' ничего не найдено")
            return
        
        # Берем последние 20 найденных строк
        result_lines = found_lines[-20:] if len(found_lines) > 20 else found_lines
        result_content = ''.join(result_lines)
        
        header = f"🔍 Результаты поиска '{search_text}' (последние {len(result_lines)} из {len(found_lines)}):\n\n"
        
        if len(header + result_content) > 4000:
            result_content = result_content[-3500:]  # Обрезаем если слишком длинное
            header = f"🔍 Результаты поиска '{search_text}' (последние строки):\n\n"
        
        await message.answer(header + f"```\n{result_content}\n```", parse_mode='Markdown')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при поиске в логах: {e}")

# Команда для информации о логах
@router.message(Command("logs_info"))
async def admin_logs_info(message: Message):
    """Информация о файле логов"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        log_file_path = Path("logs/bot.log")
        
        if not log_file_path.exists():
            await message.answer("❌ Файл логов не найден: logs/bot.log")
            return
        
        # Получаем информацию о файле
        file_size = log_file_path.stat().st_size
        modified_time = log_file_path.stat().st_mtime
        from datetime import datetime
        modified_date = datetime.fromtimestamp(modified_time).strftime('%d.%m.%Y %H:%M:%S')
        
        # Считаем количество строк
        line_count = 0
        with open(log_file_path, 'r', encoding='utf-8') as file:
            line_count = sum(1 for _ in file)
        
        # Форматируем размер файла
        size_kb = file_size / 1024
        size_mb = size_kb / 1024
        
        size_str = f"{file_size} байт"
        if size_mb >= 1:
            size_str = f"{size_mb:.2f} MB"
        elif size_kb >= 1:
            size_str = f"{size_kb:.2f} KB"
        
        await message.answer(
            f"📊 Информация о логах:\n\n"
            f"📁 Файл: logs/bot.log\n"
            f"📏 Размер: {size_str}\n"
            f"📈 Строк: {line_count}\n"
            f"🕐 Последнее изменение: {modified_date}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении информации о логах: {e}")