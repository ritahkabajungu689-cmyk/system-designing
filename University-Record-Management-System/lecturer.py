from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from db import get_conn
from student_model import Student

# grading scale helper
def percent_to_grade(percent):
    p = float(percent)
    if p >= 70:
        return 'A'
    if p >= 65:
        return 'A-'
    if p >= 60:
        return 'B+'
    if p >= 55:
        return 'B'
    if p >= 50:
        return 'B-'
    if p >= 45:
        return 'C+'
    if p >= 40:
        return 'C'
    if p >= 35:
        return 'C-'
    if p >= 30:
        return 'D'
    return 'F'

class LecturerDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load_course(self, course_code):
        course_code = (course_code or '').strip()
        if not course_code:
            return
        # list students enrolled in course
        conn = get_conn()
        cur = conn.cursor()
        # case-insensitive match for course code and order students
        cur.execute('SELECT s.student_id, s.first_name, s.last_name, e.term FROM students s JOIN enrollments e ON s.student_id=e.student_id WHERE UPPER(e.course_code)=UPPER(?) ORDER BY s.last_name, s.student_id', (course_code,))
        rows = cur.fetchall()
        # also fetch credits (case-insensitive)
        cur.execute('SELECT credits FROM courses WHERE UPPER(course_code)=UPPER(?)', (course_code,))
        credit_row = cur.fetchone()
        credits = credit_row['credits'] if credit_row else 3
        self.ids.students_box.clear_widgets()
        if not rows:
            conn.close()
            self.ids.info.text = f'No students enrolled in {course_code}'
            return
        for r in rows:
            sid = r['student_id']
            name = f"{r['first_name']} {r['last_name'] or ''}".strip()
            row = BoxLayout(size_hint_y=None, height='90dp', orientation='vertical', spacing=4)
            top = BoxLayout(size_hint_y=None, height='28dp')
            top.add_widget(Label(text=f"{sid} - {name}", halign='left'))
            row.add_widget(top)
            # inputs for coursework and exam
            inputs = BoxLayout(size_hint_y=None, height='28dp')
            cw = TextInput(hint_text='Coursework (0-40)', input_filter='int')
            ex = TextInput(hint_text='Exam (0-60)', input_filter='int')
            btn_save = Button(text='Save Mark', size_hint_x=None, width=100, color=(1,1,1,1))
            btn_delete = Button(text='Delete Mark', size_hint_x=None, width=100, color=(1,1,1,1))
            inputs.add_widget(cw)
            inputs.add_widget(ex)
            inputs.add_widget(btn_save)
            inputs.add_widget(btn_delete)
            row.add_widget(inputs)

            def do_save(inst, sid=sid, cw=cw, ex=ex, course_code=course_code, credits=credits, term=r['term']):
                try:
                    cwv = float(cw.text.strip() or 0)
                    exv = float(ex.text.strip() or 0)
                except Exception:
                    cwv = 0.0; exv = 0.0
                # cap values
                cwv = max(0, min(40, cwv))
                exv = max(0, min(60, exv))
                final = cwv + exv
                grade = percent_to_grade(final)
                # remove existing result for student & course & term
                conn = get_conn()
                cur = conn.cursor()
                try:
                    cur.execute('DELETE FROM results WHERE student_id=? AND course_code=? AND term=?', (sid, course_code, term))
                except Exception:
                    pass
                cur.execute('INSERT INTO results(student_id, course_code, grade, credits, term) VALUES(?,?,?,?,?)', (sid, course_code, grade, credits, term))
                conn.commit()
                conn.close()
                self.ids.info.text = f'Saved mark for {sid}: final={final}, grade={grade}'

            def do_delete(inst, sid=sid, course_code=course_code, term=r['term']):
                conn = get_conn()
                cur = conn.cursor()
                cur.execute('DELETE FROM results WHERE student_id=? AND course_code=? AND term=?', (sid, course_code, term))
                conn.commit()
                conn.close()
                self.ids.info.text = f'Deleted mark for {sid} in {course_code}'

            btn_save.bind(on_release=do_save)
            btn_delete.bind(on_release=do_delete)
            self.ids.students_box.add_widget(row)

    def logout(self):
        from kivy.app import App
        from kivy.uix.screenmanager import ScreenManager
        app = App.get_running_app()
        root = app.root
        for child in root.children:
            if isinstance(child, ScreenManager):
                child.current = 'home'
                return
