# handlers/students/utils.py
import logging

logger = logging.getLogger(__name__)

def format_student_info(student):
    """Форматирует информацию об ученике для отображения"""
    try:
        # Безопасный доступ к данным
        status_text = student.get('status', 'active')
        
        # Обработка delete_after
        if student.get('delete_after'):
            status_text = f"{status_text} (будет удален {student['delete_after']})"
        
        # Обработка Telegram аккаунтов
        student_tg = f"{student['student_username']}" if student.get('student_username') else "не привязан"
        parent_tg = f"{student['parent_username']}" if student.get('parent_username') else "не привязан"
        
        # Безопасный доступ к телефонным номерам
        phone = student.get('phone', '-')
        parent_phone = student.get('parent_phone', '-')
        
        # Исправлено: используем registration_date вместо created_at
        registration_date = student.get('registration_date', 'не указана')
        
        return (
            f"👤 <b>Информация об ученике</b>\n\n"
            f"<b>ФИО:</b> {student.get('full_name', 'Не указано')}\n"
            f"<b>Телефон:</b> {phone if phone != '-' else 'не указан'}\n"
            f"<b>Телефон родителя:</b> {parent_phone if parent_phone != '-' else 'не указан'}\n"
            f"<b>Статус:</b> {status_text}\n"
            f"<b>ТГ ученика:</b> {student_tg}\n"
            f"<b>ТГ родителя:</b> {parent_tg}\n"
            f"<b>Дата добавления:</b> {registration_date}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при форматировании информации об ученике: {e}")
        return "❌ Ошибка при загрузке информации об ученике"

def get_students_stats(students):
    """Возвращает статистику по ученикам"""
    try:
        if not students:
            return "Всего учеников: 0\nАктивных: 0\n\n"
        
        active_count = sum(1 for s in students if str(s.get('status', '')).lower() == 'active')
        return f"Всего учеников: {len(students)}\nАктивных: {active_count}\n\n"
        
    except Exception as e:
        logger.error(f"Ошибка при подсчете статистики учеников: {e}")
        return "Всего учеников: ?\nАктивных: ?\n\n"