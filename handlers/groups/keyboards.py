# keyboards/groups_keyboards.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_groups_main_menu_keyboard():
    """Клавиатура главного меню групп"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Управление группами", callback_data="manage_groups")],
        [InlineKeyboardButton(text="➕ Добавить группу", callback_data="add_group")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_from_groups")]
    ])

def get_back_to_groups_menu_keyboard():
    """Клавиатура с кнопкой назад в меню групп"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_groups_menu")]
    ])

def get_group_confirm_keyboard():
    """Клавиатура подтверждения создания группы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Сохранить", callback_data="save_group")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_groups_menu")]
    ])

def get_groups_list_keyboard(groups):
    """Клавиатура со списком групп"""
    builder = InlineKeyboardBuilder()
    
    for group in groups:
        builder.row(
            InlineKeyboardButton(
                text=f"👥 {group['name']} ({group['student_count']} уч.)",
                callback_data=f"group_{group['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_groups_menu")
    )
    
    return builder.as_markup()

def get_group_management_keyboard(group_id):
    """Клавиатура управления конкретной группой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ученика", callback_data=f"add_to_group_{group_id}")],
        [InlineKeyboardButton(text="➖ Удалить ученика", callback_data=f"remove_from_group_{group_id}")],
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_group_{group_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить группу", callback_data=f"delete_group_{group_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_groups")]
    ])

def get_students_list_keyboard(students, prefix, group_id):
    """Клавиатура со списком учеников (исключая неактивных)"""
    builder = InlineKeyboardBuilder()
    
    active_students = []
    
    # Сначала фильтруем активных учеников
    for student in students:
        if student and student.get('status') != 'inactive':
            active_students.append(student)
    
    # Добавляем кнопки только для активных учеников
    for student in active_students:
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {student['full_name']}",
                callback_data=f"{prefix}_{student['id']}_to_{group_id}"
            )
        )
    
    # Всегда добавляем кнопку назад, даже если нет активных учеников
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"group_{group_id}")
    )
    
    return builder.as_markup()

def get_delete_confirmation_keyboard(group_id):
    """Клавиатура подтверждения удаления группы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{group_id}")],
        [InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"group_{group_id}")]
    ])