from db import get_conn, init_db
from datetime import datetime

# Simple grade to points mapping (4.0 scale)
GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D': 1.0, 'F': 0.0
}


class Student:
    def __init__(self, student_id, first_name, last_name, dob=None, gender=None,
                 contact=None, address=None, admission_year=None, program=None,
                 level=None, status='active', photo_path=None, tuition_balance=0.0):
        self.student_id = student_id
        self.first_name = first_name
        self.last_name = last_name
        self.dob = dob
        self.gender = gender
        self.contact = contact
        self.address = address
        self.admission_year = admission_year
        self.program = program
        self.level = level
        self.status = status
        self.photo_path = photo_path
        self.tuition_balance = float(tuition_balance or 0.0)

    def register(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('''INSERT OR REPLACE INTO students(student_id, first_name, last_name, dob, gender, contact, address, admission_year, program, level, status, photo_path, tuition_balance)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (self.student_id, self.first_name, self.last_name, self.dob, self.gender, self.contact, self.address, self.admission_year, self.program, self.level, self.status, self.photo_path, self.tuition_balance))
        conn.commit()
        conn.close()

    def update_profile(self, **kwargs):
        allowed = ['first_name','last_name','dob','gender','contact','address','admission_year','program','level','status','photo_path']
        fields = []
        vals = []
        for k,v in kwargs.items():
            if k in allowed:
                fields.append(f"{k}=?")
                vals.append(v)
        if not fields:
            return
        vals.append(self.student_id)
        conn = get_conn()
        conn.cursor().execute(f"UPDATE students SET {', '.join(fields)} WHERE student_id=?", vals)
        conn.commit()
        conn.close()

    @classmethod
    def get_by_id(cls, student_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT * FROM students WHERE student_id=?', (student_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return cls(**row)

    def enroll_course(self, course_code, title=None, credits=3, term=None):
        conn = get_conn()
        cur = conn.cursor()
        # Ensure course exists
        if title is not None:
            cur.execute('INSERT OR IGNORE INTO courses(course_code, title, credits) VALUES(?,?,?)', (course_code, title, credits))
        else:
            cur.execute('INSERT OR IGNORE INTO courses(course_code, credits) VALUES(?,?)', (course_code, credits))
        cur.execute('INSERT OR IGNORE INTO enrollments(student_id, course_code, term) VALUES(?,?,?)', (self.student_id, course_code, term))
        conn.commit()
        conn.close()

    def drop_course(self, course_code):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM enrollments WHERE student_id=? AND course_code=?', (self.student_id, course_code))
        conn.commit()
        conn.close()

    def list_courses(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT c.course_code, c.title, c.credits, e.term FROM courses c JOIN enrollments e ON c.course_code=e.course_code WHERE e.student_id=?', (self.student_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def pay_tuition(self, amount, method='cash', payer=None):
        amount = float(amount)
        conn = get_conn()
        cur = conn.cursor()
        # try to store payer if column exists
        try:
            cur.execute('INSERT INTO tuition_payments(student_id, amount, method, payer) VALUES(?,?,?,?)', (self.student_id, amount, method, payer))
        except Exception:
            cur.execute('INSERT INTO tuition_payments(student_id, amount, method) VALUES(?,?,?)', (self.student_id, amount, method))
        # decrement balance (assumes tuition_balance represents amount owed)
        cur.execute('UPDATE students SET tuition_balance = IFNULL(tuition_balance,0) - ? WHERE student_id=?', (amount, self.student_id))
        conn.commit()
        conn.close()

    def record_result(self, course_code, grade, credits=3, term=None):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('INSERT INTO results(student_id, course_code, grade, credits, term) VALUES(?,?,?,?,?)', (self.student_id, course_code, grade, credits, term))
        conn.commit()
        conn.close()

    def get_results(self):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT course_code, grade, credits, term FROM results WHERE student_id=?', (self.student_id,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def calculate_gpa(self):
        results = self.get_results()
        total_points = 0.0
        total_credits = 0.0
        for r in results:
            grade = r.get('grade')
            credits = float(r.get('credits') or 0)
            pts = GRADE_POINTS.get(grade.upper(), None)
            if pts is None:
                continue
            total_points += pts * credits
            total_credits += credits
        if total_credits == 0:
            return None
        return round(total_points / total_credits, 2)

    def get_transcript(self):
        return self.get_results()

    def generate_report(self):
        return {
            'student_id': self.student_id,
            'name': f"{self.first_name} {self.last_name}",
            'program': self.program,
            'level': self.level,
            'tuition_balance': self.tuition_balance,
            'gpa': self.calculate_gpa(),
            'courses': self.list_courses(),
            'results': self.get_results()
        }

    def is_registered(self):
        """Return True if student's status indicates registration."""
        return str(self.status).lower() in ('registered', 'active', 'enrolled')

    def set_registered(self, flag=True):
        """Set student's registration status and persist to DB."""
        self.status = 'registered' if flag else 'unregistered'
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('UPDATE students SET status=? WHERE student_id=?', (self.status, self.student_id))
        conn.commit()
        conn.close()

    def is_enrolled(self):
        """Return True if the student has any enrollments."""
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(1) as c FROM enrollments WHERE student_id=?', (self.student_id,))
        row = cur.fetchone()
        conn.close()
        return (row['c'] if row else 0) > 0




def add_course(course_code, title, credits=3):
    """Add or update a course in the catalog."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO courses(course_code, title, credits) VALUES(?,?,?)', (course_code, title, credits))
    conn.commit()
    conn.close()


def list_all_courses():
    """Return all courses in the catalog."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT course_code, title, credits FROM courses ORDER BY course_code')
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_courses_for_program(program_code):
    """Return courses assigned to a specific program code. Case-insensitive."""
    if not program_code:
        return []
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''SELECT c.course_code, c.title, c.credits
                   FROM courses c JOIN program_courses pc ON c.course_code=pc.course_code
                   WHERE UPPER(pc.program_code)=UPPER(?) ORDER BY c.course_code''', (program_code,))
    rows = cur.fetchall()
    conn.close()
    results = [dict(r) for r in rows]
    if not results:
        # fallback: try mapping common program names to program codes
        name = (program_code or '').lower()
        mapping = {
            'computer': 'CS101',
            'cyber': 'CS102',
            'software': 'SE101',
            'data': 'DA101',
            'ai': 'AM101',
            'ml': 'AM101',
            'information': 'IT101',
            'it': 'IT101'
        }
        for k, v in mapping.items():
            if k in name:
                return list_courses_for_program(v)
    return results


# Initialize DB when module loaded (safe)
init_db()

