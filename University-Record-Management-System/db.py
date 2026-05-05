import sqlite3
from pathlib import Path

DB_PATH = Path(r"\university.db")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        dob TEXT,
        gender TEXT,
        contact TEXT,
        address TEXT,
        admission_year INTEGER,
        program TEXT,
        level TEXT,
        status TEXT,
        photo_path TEXT,
        tuition_balance REAL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS courses (
        course_code TEXT PRIMARY KEY,
        title TEXT,
        credits INTEGER DEFAULT 3
    );

    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        course_code TEXT,
        term TEXT,
        UNIQUE(student_id, course_code),
        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY(course_code) REFERENCES courses(course_code) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tuition_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        amount REAL,
        method TEXT,
        paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        course_code TEXT,
        grade TEXT,
        credits INTEGER,
        term TEXT,
        FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE,
        FOREIGN KEY(course_code) REFERENCES courses(course_code) ON DELETE CASCADE
    );
    ''')
    conn.commit()
    # ensure default courses exist
    try:
        default_courses = [
            # program entries (kept for compatibility)
            ('CS101', 'Computer Science', 3),
            ('CS102', 'Cyber Security', 3),
            ('SE101', 'Software Engineering', 3),
            ('DA101', 'Data Analysis', 3),
            ('AM101', 'AI & ML', 3),
            ('IT101', 'Information Technology', 3),
            # Computer Science course units
            ('CS111', 'Discrete Mathematics', 3),
            ('CS112', 'Data Structures & Algorithms', 3),
            ('CS113', 'Object Oriented Programming', 3),
            ('CS114', 'Capstone Project', 6),
            ('CN001', 'Networking', 3),
            # Cyber Security units
            ('CS1021', 'Ethical Hacking', 3),
            ('CS1022', 'Linux Environment', 3),
        ]
        for code, title, credits in default_courses:
            cur.execute('INSERT OR IGNORE INTO courses(course_code, title, credits) VALUES(?,?,?)', (code, title, credits))
        conn.commit()
    except Exception:
        pass

    # ensure program->course mappings table exists and seed mappings
    try:
        cur.execute('CREATE TABLE IF NOT EXISTS program_courses (program_code TEXT, course_code TEXT, PRIMARY KEY(program_code, course_code), FOREIGN KEY(course_code) REFERENCES courses(course_code) ON DELETE CASCADE)')
        # mappings
        mappings = {
            'CS101': ['CS111','CS112','CS113','CS114','CN001'],
            'CS102': ['CN001','CS1021','CS1022'],
            'SE101': ['CS111','CS112','CS113','CS114','CN001'],
            'DA101': ['CS111','CS112','CS113','CS114','CN001'],
            'AM101': ['CS111','CS112','CS113','CS114','CN001'],
            'IT101': ['CS111','CS112','CS113','CS114','CN001'],
        }
        for prog, courses in mappings.items():
            for cc in courses:
                cur.execute('INSERT OR IGNORE INTO program_courses(program_code, course_code) VALUES(?,?)', (prog, cc))
        conn.commit()
    except Exception:
        pass

    # migration: ensure payer column exists in tuition_payments
    try:
        cur.execute("PRAGMA table_info(tuition_payments)")
        cols = [r[1] for r in cur.fetchall()]
        if 'payer' not in cols:
            cur.execute("ALTER TABLE tuition_payments ADD COLUMN payer TEXT;")
            conn.commit()
    except Exception:
        # ignore migration failures on older SQLite versions
        pass
    conn.close()

    # helper functions for users/auth
    def create_user(username, password, role, student_id=None):
        conn2 = get_conn()
        cur2 = conn2.cursor()
        cur2.execute('INSERT OR IGNORE INTO users(username, password, role, student_id) VALUES(?,?,?,?)', (username, password, role, student_id))
        conn2.commit()
        conn2.close()

    def authenticate_user(username, password):
        conn2 = get_conn()
        cur2 = conn2.cursor()
        cur2.execute('SELECT username, role, student_id FROM users WHERE username=? AND password=?', (username, password))
        row = cur2.fetchone()
        conn2.close()
        return dict(row) if row else None

    # expose helpers at module level
    globals()['create_user'] = create_user
    globals()['authenticate_user'] = authenticate_user


if __name__ == '__main__':
    init_db()
    print('DB initialized at', DB_PATH)
