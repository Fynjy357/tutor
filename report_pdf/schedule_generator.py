import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from datetime import datetime
from calendar import monthrange
import os

class SchedulePDFGenerator:
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 30  # Уменьшил margin для большего пространства
        self.line_height = 12
        self.cell_padding = 3
        
        # Улучшенная регистрация шрифтов с поддержкой кириллицы
        self._register_fonts()
    
    def _register_fonts(self):
        """Регистрирует шрифты с поддержкой кириллицы"""
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
            self.font_normal = 'DejaVuSans'
            self.font_bold = 'DejaVuSans-Bold'
        except:
            try:
                pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
                pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
                self.font_normal = 'Arial'
                self.font_bold = 'Arial-Bold'
            except:
                self.font_normal = 'Helvetica'
                self.font_bold = 'Helvetica-Bold'
    
    def create_monthly_schedule(self, tutor_data: dict, schedule_data: dict) -> io.BytesIO:
        """Создает PDF расписание за месяц с отладкой"""
        print("=== DEBUG: Начало генерации PDF ===")
        print(f"DEBUG: tutor_data: {tutor_data}")
        print(f"DEBUG: schedule_data keys: {schedule_data.keys()}")
        """Создает PDF расписание за месяц в красивом календарном формате"""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        month_names = {
            1: "ЯНВАРЬ", 2: "ФЕВРАЛЬ", 3: "МАРТ", 4: "АПРЕЛЬ",
            5: "МАЙ", 6: "ИЮНЬ", 7: "ИЮЛЬ", 8: "АВГУСТ",
            9: "СЕНТЯБРЬ", 10: "ОКТЯБРЬ", 11: "НОЯБРЬ", 12: "ДЕКАБРЬ"
        }
        
        year = schedule_data['year']
        month = schedule_data['month']
        daily_schedule = schedule_data.get('daily_schedule', {})
        print(f"DEBUG: Дней с расписанием: {len(daily_schedule)}")

        
        y_position = self.page_height - self.margin
        
        # Заголовок
        self._draw_header(c, f"{month_names[month]} {year} >", y_position)
        y_position -= 50  # Уменьшил отступ
        
        # Информация о репетиторе
        self._draw_tutor_info(c, tutor_data, y_position)
        y_position -= 25  # Уменьшил отступ
        
        # Календарь на месяц с увеличенными ячейками
        y_position = self._draw_calendar(c, year, month, daily_schedule, y_position)
        
        # Футер
        self._draw_footer(c)
        
        c.save()
        buffer.seek(0)
        return buffer
    
    def _draw_header(self, c, title: str, y: float):
        """Рисует заголовок"""
        c.setFont(self.font_bold, 18)  # Уменьшил размер шрифта
        c.setFillColor(colors.HexColor("#2c3e50"))
        c.drawString(self.margin, y, title)
        
        c.setStrokeColor(colors.HexColor("#e74c3c"))
        c.setLineWidth(1.5)
        c.line(self.margin, y - 10, self.page_width - self.margin, y - 10)
    
    def _draw_tutor_info(self, c, tutor_data: dict, y: float):
        """Информация о репетиторе"""
        c.setFont(self.font_bold, 9)  # Уменьшил размер шрифта
        c.setFillColor(colors.HexColor("#7f8c8d"))
        
        tutor_name = tutor_data.get('name', 'Не указано')
        tutor_phone = tutor_data.get('phone', 'Не указано')
        info_text = f"Репетитор: {tutor_name} | Телефон: {tutor_phone}"
        
        c.drawString(self.margin, y, info_text)
    
    def _draw_calendar(self, c, year: int, month: int, daily_schedule: dict, y_start: float) -> float:
        """Рисует календарь на месяц с увеличенными ячейками"""
        col_width = (self.page_width - 2 * self.margin) / 7
        row_height = 100  # УВЕЛИЧИЛ высоту ячеек для большего количества занятий
        header_height = 20  # Уменьшил заголовок
        
        week_days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        
        y = y_start
        
        # Заголовок дней недели
        for i, day in enumerate(week_days):
            x = self.margin + i * col_width
            
            c.setFillColor(colors.HexColor("#34495e"))
            c.setStrokeColor(colors.HexColor("#2c3e50"))
            c.rect(x, y - header_height, col_width, header_height, fill=1, stroke=1)
            
            c.setFont(self.font_bold, 10)  # Уменьшил шрифт
            c.setFillColor(colors.white)
            c.drawCentredString(x + col_width/2, y - header_height + 6, day)
        
        y -= header_height + 5
        
        # Получаем информацию о месяце
        first_day, num_days = monthrange(year, month)
        current_day = 1
        current_row = 0
        
        while current_day <= num_days:
            if y - row_height < 50:
                c.showPage()
                y = self.page_height - self.margin
                
                for i, day in enumerate(week_days):
                    x = self.margin + i * col_width
                    c.setFillColor(colors.HexColor("#34495e"))
                    c.setStrokeColor(colors.HexColor("#2c3e50"))
                    c.rect(x, y - header_height, col_width, header_height, fill=1, stroke=1)
                    c.setFont(self.font_bold, 10)
                    c.setFillColor(colors.white)
                    c.drawCentredString(x + col_width/2, y - header_height + 6, day)
                y -= header_height + 5
            
            # Рисуем строку календаря
            for day_of_week in range(7):
                if current_day > num_days:
                    break
                
                if current_row == 0 and day_of_week < first_day:
                    x = self.margin + day_of_week * col_width
                    self._draw_empty_cell(c, x, y, col_width, row_height)
                    continue
                
                x = self.margin + day_of_week * col_width
                date_str = f"{year}-{month:02d}-{current_day:02d}"
                
                if date_str in daily_schedule and daily_schedule[date_str].get('lessons'):
                    self._draw_day_with_lessons(c, x, y, col_width, row_height, 
                                              current_day, daily_schedule[date_str])
                else:
                    self._draw_empty_cell(c, x, y, col_width, row_height, current_day)
                
                current_day += 1
            
            y -= row_height + 3  # Уменьшил отступ между строками
            current_row += 1
        
        return y
    
    def _draw_empty_cell(self, c, x: float, y: float, width: float, height: float, day: int = None):
        """Рисует пустую ячейку календаря"""
        c.setFillColor(colors.HexColor("#f8f9fa"))
        c.setStrokeColor(colors.HexColor("#dee2e6"))
        c.rect(x, y - height, width, height, fill=1, stroke=1)
        
        if day:
            c.setFont(self.font_normal, 9)
            c.setFillColor(colors.HexColor("#6c757d"))
            c.drawString(x + 5, y - height + 6, str(day))
    
    def _draw_day_with_lessons(self, c, x: float, y: float, width: float, height: float, 
                          day: int, day_data: dict):
        """Рисует ячейку календаря с занятиями - ИСПРАВЛЕННОЕ УСЛОВИЕ"""
        print(f"DEBUG: Рисуем день {day} с занятиями")
        
        c.setFillColor(colors.HexColor("#e8f5e8"))
        c.setStrokeColor(colors.HexColor("#c8e6c9"))
        c.rect(x, y - height, width, height, fill=1, stroke=1)
        
        # Номер дня
        c.setFont(self.font_bold, 10)
        c.setFillColor(colors.HexColor("#2e7d32"))
        c.drawString(x + 4, y - height + 6, str(day))
        
        lessons = day_data.get('lessons', [])
        print(f"DEBUG: Найдено занятий: {len(lessons)}")
        
        lesson_y = y - height + 20  # Начальная позиция
        max_lessons = 6
        
        # ИСПРАВЛЕННОЕ УСЛОВИЕ: lesson_y должен быть ВЫШЕ нижней границы ячейки
        bottom_limit = y - height + 15  # Минимальная высота для текста от низа ячейки
        print(f"DEBUG: y={y}, height={height}, lesson_y начальное={lesson_y}, bottom_limit={bottom_limit}")
        
        for i, lesson in enumerate(lessons[:max_lessons]):
            print(f"DEBUG: Обработка занятия {i}, lesson_y={lesson_y}, bottom_limit={bottom_limit}")
            
            # ПРАВИЛЬНОЕ УСЛОВИЕ: есть ли место для отрисовки?
            if lesson_y >= bottom_limit:  # lesson_y должен быть >= нижнего предела
                try:
                    # Безопасное извлечение времени
                    lesson_date_str = lesson.get('lesson_date', '')
                    
                    if lesson_date_str:
                        lesson_time = datetime.strptime(lesson_date_str, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')
                    else:
                        lesson_time = "??:??"
                    
                    student_name = self._get_lesson_description(lesson)
                    print(f"DEBUG: Время: {lesson_time}, Студент: {student_name}")
                    
                    # Цвет точки статуса
                    status_color = {
                        'planned': '#3498db',
                        'completed': '#27ae60', 
                        'cancelled': '#e74c3c'
                    }.get(lesson.get('status', 'planned'), '#3498db')
                    
                    # Точка статуса
                    c.setFillColor(colors.HexColor(status_color))
                    c.circle(x + 4, lesson_y - 1, 1, fill=1)
                    
                    # Формируем текст занятия
                    lesson_text = f"{lesson_time} {student_name}"
                    print(f"DEBUG: Текст занятия: '{lesson_text}'")
                    
                    # Рисуем текст
                    c.setFont(self.font_normal, 6)
                    c.setFillColor(colors.HexColor("#2c3e50"))
                    c.drawString(x + 8, lesson_y - 2, lesson_text)
                    
                    lesson_y -= 7
                    print(f"DEBUG: Новый lesson_y: {lesson_y}")
                    
                except Exception as e:
                    print(f"DEBUG: Ошибка при отрисовке занятия {i}: {e}")
                    continue
            else:
                print(f"DEBUG: Нет места для занятия {i}, lesson_y={lesson_y} < bottom_limit={bottom_limit}")
                break
        
        # Счетчик дополнительных занятий
        if len(lessons) > max_lessons:
            c.setFont(self.font_normal, 5)
            c.setFillColor(colors.HexColor("#7f8c8d"))
            c.drawString(x + 4, bottom_limit - 5, f"+{len(lessons) - max_lessons} ещё...")
        
        # Общее количество занятий в углу
        c.setFont(self.font_bold, 7)
        c.setFillColor(colors.HexColor("#2e7d32"))
        c.drawRightString(x + width - 4, y - height + 6, f"{len(lessons)}")


    
    def _get_lesson_description(self, lesson: dict) -> str:
        """Упрощенное описание занятия"""
        try:
            if lesson.get('group_id'):
                return "Группа"
            else:
                student_name = lesson.get('student_name', 'Студент')
                parts = student_name.split()
                return parts[0] if parts else student_name[:6]  # Только фамилия
        except:
            return "Урок"


    
    def _draw_footer(self, c):
        """Рисует футер"""
        c.setFont(self.font_normal, 7)
        c.setFillColor(colors.HexColor("#95a5a6"))
        c.drawString(
            self.margin, 
            25, 
            f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )