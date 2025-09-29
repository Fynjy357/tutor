# report_pdf/pdf_generator.py
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import Color, black, white
from reportlab.lib.utils import ImageReader
from datetime import datetime
import os

class PDFReportGenerator:
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 50
        self.line_height = 15
        
        # Регистрируем русские шрифты
        try:
            # Попробуем зарегистрировать стандартные шрифты с поддержкой кириллицы
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
            self.font_normal = 'DejaVuSans'
            self.font_bold = 'DejaVuSans-Bold'
        except:
            try:
                # Альтернативный шрифт
                pdfmetrics.registerFont(TTFont('ArialUnicode', 'arial.ttf'))
                self.font_normal = 'ArialUnicode'
                self.font_bold = 'ArialUnicode'
            except:
                # Если шрифты не найдены, используем стандартные (могут быть проблемы с кириллицей)
                self.font_normal = 'Helvetica'
                self.font_bold = 'Helvetica-Bold'
    
    def create_monthly_report(self, tutor_data: dict, lessons: list, month: int, year: int) -> io.BytesIO:
        """Создает PDF отчет за месяц"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Русские названия месяцев
        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        
        # Текущая позиция Y
        y_position = self.page_height - self.margin
        
        # Заголовок отчета
        self._draw_header(c, f"Отчет за {month_names[month]} {year} года", y_position)
        y_position -= 40
        
        # Информация о репетиторе
        self._draw_tutor_info(c, tutor_data, y_position)
        y_position -= 60
        
        # Статистика
        stats = self._calculate_statistics(lessons)
        y_position = self._draw_statistics(c, stats, y_position)
        
        # Таблица занятий
        y_position -= 20
        y_position = self._draw_lessons_table(c, lessons, y_position)
        
        # Футер
        self._draw_footer(c)
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def _draw_header(self, c, title: str, y: float):
        """Рисует заголовок отчета"""
        c.setFont(self.font_bold, 18)
        c.drawString(self.margin, y, title)
        # Линия под заголовком
        c.line(self.margin, y - 10, self.page_width - self.margin, y - 10)
    
    def _draw_tutor_info(self, c, tutor_data: dict, y: float):
        """Рисует информацию о репетиторе"""
        c.setFont(self.font_bold, 12)
        c.drawString(self.margin, y, "Репетитор:")
        c.setFont(self.font_normal, 12)
        c.drawString(self.margin + 80, y, tutor_data.get('name', 'Не указано'))
        
        c.setFont(self.font_bold, 12)
        c.drawString(self.margin, y - 20, "Телефон:")
        c.setFont(self.font_normal, 12)
        c.drawString(self.margin + 80, y - 20, tutor_data.get('phone', 'Не указано'))
    
    def _calculate_statistics(self, lessons: list) -> dict:
        """Рассчитывает статистику по занятиям"""
        total_lessons = len(lessons)
        total_earnings = sum(lesson.get('price', 0) for lesson in lessons)
        completed_lessons = len([l for l in lessons if l.get('status') == 'completed'])
        individual_lessons = len([l for l in lessons if not l.get('group_id')])
        group_lessons = len([l for l in lessons if l.get('group_id')])
        
        return {
            'total_lessons': total_lessons,
            'total_earnings': total_earnings,
            'completed_lessons': completed_lessons,
            'individual_lessons': individual_lessons,
            'group_lessons': group_lessons
        }
    
    def _draw_statistics(self, c, stats: dict, y: float) -> float:
        """Рисует блок статистики"""
        c.setFont(self.font_bold, 14)
        c.drawString(self.margin, y, "Статистика:")
        y -= 25
        
        statistics = [
            f"Всего занятий: {stats['total_lessons']}",
            f"Проведено: {stats['completed_lessons']}",
            f"Индивидуальных: {stats['individual_lessons']}",
            f"Групповых: {stats['group_lessons']}",
            f"Общий доход: {stats['total_earnings']} руб"
        ]
        
        c.setFont(self.font_normal, 12)
        for stat in statistics:
            c.drawString(self.margin + 20, y, stat)
            y -= self.line_height
        
        return y
    
    def _draw_lessons_table(self, c, lessons: list, y: float) -> float:
        """Рисует таблицу занятий"""
        if not lessons:
            c.setFont(self.font_normal, 12)
            c.drawString(self.margin, y, "Занятий за этот период нет")
            return y - 30
        
        # Заголовок таблицы
        c.setFont(self.font_bold, 14)
        c.drawString(self.margin, y, "Расписание занятий:")
        y -= 25
        
        # Заголовки столбцов
        headers = ["Дата", "Время", "Ученик/Группа", "Длит.", "Стоим.", "Статус"]
        col_widths = [60, 60, 150, 50, 60, 80]
        
        c.setFont(self.font_bold, 10)
        x = self.margin
        for i, header in enumerate(headers):
            c.drawString(x, y, header)
            x += col_widths[i]
        
        # Линия под заголовками
        y -= 5
        c.line(self.margin, y, self.page_width - self.margin, y)
        y -= 10
        
        # Данные занятий
        c.setFont(self.font_normal, 9)
        for lesson in sorted(lessons, key=lambda x: x.get('lesson_date', '')):
            # Проверяем, нужна ли новая страница
            if y < 100:
                c.showPage()
                y = self.page_height - self.margin
                # Повторяем заголовки на новой странице
                c.setFont(self.font_bold, 10)
                x = self.margin
                for i, header in enumerate(headers):
                    c.drawString(x, y, header)
                    x += col_widths[i]
                y -= 15
                c.line(self.margin, y, self.page_width - self.margin, y)
                y -= 10
                c.setFont(self.font_normal, 9)
            
            lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
            
            # Данные в столбцах
            x = self.margin
            data = [
                lesson_date.strftime('%d.%m'),
                lesson_date.strftime('%H:%M'),
                self._get_lesson_description(lesson),
                f"{lesson.get('duration', 0)} мин",
                f"{lesson.get('price', 0)} руб",
                self._get_status_russian(lesson.get('status', ''))
            ]
            
            for i, value in enumerate(data):
                # Обрезаем длинные тексты чтобы помещались в колонки
                if i == 2:  # Колонка с именами
                    if len(value) > 20:
                        value = value[:20] + "..."
                c.drawString(x, y, str(value))
                x += col_widths[i]
            
            y -= self.line_height
        
        return y
    
    def _get_lesson_description(self, lesson: dict) -> str:
        """Возвращает описание занятия (ученик или группа)"""
        if lesson.get('group_id'):
            return lesson.get('group_name', f'Группа #{lesson["group_id"]}')
        else:
            return lesson.get('student_name', 'Не указан')
    
    def _get_status_russian(self, status: str) -> str:
        """Переводит статус на русский"""
        status_map = {
            'planned': 'Запланировано',
            'completed': 'Проведено', 
            'cancelled': 'Отменено'
        }
        return status_map.get(status, status)
    
    def _draw_footer(self, c):
        """Рисует футер"""
        c.setFont(self.font_normal, 8)
        c.drawString(
            self.margin, 
            30, 
            f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
