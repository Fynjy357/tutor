import sqlite3

def create_database():
    # Подключение к базе данных
    conn = sqlite3.connect('tutor_db.sqlite')
    cursor = conn.cursor()
    
    # Создание таблиц
    cursor.executescript('''
    -- Таблица Репетиторы
    CREATE TABLE IF NOT EXISTS Tutors (
        tutor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT,
        it_id INTEGER
    );

    -- Таблица Группы
    CREATE TABLE IF NOT EXISTS Groups (
        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        status TEXT,
        tutor_id INTEGER,
        FOREIGN KEY (tutor_id) REFERENCES Tutors(tutor_id)
    );

    -- Таблица Ученики
    CREATE TABLE IF NOT EXISTS Students (
        student_id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        status TEXT,
        it_id INTEGER,
        parent_it_id INTEGER,
        phone TEXT,
        tutor_id INTEGER,
        FOREIGN KEY (tutor_id) REFERENCES Tutors(tutor_id)
    );

    -- Таблица связи Ученики-Группы (многие ко многим)
    CREATE TABLE IF NOT EXISTS Student_Group (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES Students(student_id),
        FOREIGN KEY (group_id) REFERENCES Groups(group_id),
        UNIQUE(student_id, group_id)
    );

    -- Таблица Занятия
    CREATE TABLE IF NOT EXISTS Lessons (
        lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_type TEXT NOT NULL,
        lesson_frequency TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        student_id INTEGER,
        group_id INTEGER,
        cost INTEGER NOT NULL,
        status TEXT NOT NULL,
        tutor_id INTEGER NOT NULL,
        FOREIGN KEY (tutor_id) REFERENCES Tutors(tutor_id),
        FOREIGN KEY (student_id) REFERENCES Students(student_id),
        FOREIGN KEY (group_id) REFERENCES Groups(group_id),
        CHECK (
            (student_id IS NOT NULL AND group_id IS NULL) OR 
            (student_id IS NULL AND group_id IS NOT NULL)
        )
    );

    -- Таблица Отзывы
    CREATE TABLE IF NOT EXISTS Reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        review_text TEXT,
        status TEXT NOT NULL,
        FOREIGN KEY (lesson_id) REFERENCES Lessons(lesson_id),
        FOREIGN KEY (student_id) REFERENCES Students(student_id)
    );
    ''')
    
    # Сохранение изменений и закрытие соединения
    conn.commit()
    conn.close()
    print("База данных 'tutor_db.sqlite' успешно создана со всеми таблицами!")

if __name__ == "__main__":
    create_database()