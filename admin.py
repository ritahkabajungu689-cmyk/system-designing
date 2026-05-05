from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.lang import Builder
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from db import get_conn, create_user
from student_model import Student



class AdminDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # populate students list
        self.refresh_students()

    def refresh_students(self):
        self.ids.students_box.clear_widgets()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT student_id, first_name, last_name, program, status FROM students ORDER BY student_id')
        rows = cur.fetchall()
        conn.close()
        for r in rows:
            sid = r['student_id']
            name = f"{r['first_name']} {r['last_name'] or ''}".strip()
            program = r['program'] or '-'
            status = r['status'] or '-'
            box = BoxLayout()
            box.add_widget(Label(text=f"{sid} - {name} ({program})", halign='left', text_size=(None, None)))
            btn_view = Button(text='View', size_hint_x=None, width=100, color=(1,1,1,1))
            btn_view.bind(on_release=lambda inst, s=sid: self.view_student(s))
            box.add_widget(btn_view)
            btn_results = Button(text='Results', size_hint_x=None, width=120, color=(1,1,1,1))
            btn_results.bind(on_release=lambda inst, s=sid: self.add_result_popup(s))
            box.add_widget(btn_results)
            btn_reg = Button(text='Reg/Der', size_hint_x=None, width=120, color=(1,1,1,1))
            btn_reg.bind(on_release=lambda inst, s=sid: self.toggle_registered(s))
            box.add_widget(btn_reg)
            btn_del = Button(text='Delete', size_hint_x=None, width=120, color=(1,1,1,1))
            btn_del.bind(on_release=lambda inst, s=sid: self.delete_student(s))
            box.add_widget(btn_del)
            self.ids.students_box.add_widget(box)

    def add_student_popup(self):
        content = BoxLayout(orientation='vertical', spacing=6)
        sid = TextInput(hint_text='Student ID')
        fname = TextInput(hint_text='First name')
        lname = TextInput(hint_text='Last name')
        dob = TextInput(hint_text='DOB (YYYY-MM-DD)')
        # program spinner
        program_spinner = Spinner(text='Select Program', values=('CS101 - Computer Science','CS102 - Cyber Security','SE101 - Software Engineering','DA101 - Data Analysis','AM101 - AI & ML','IT101 - Information Technology'))
        admission = TextInput(hint_text='Admission Year', input_filter='int')
        btns = BoxLayout(size_hint_y=None, height='36dp', spacing=6)
        save = Button(text='Save')
        cancel = Button(text='Cancel')
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(sid)
        content.add_widget(fname)
        content.add_widget(lname)
        content.add_widget(dob)
        content.add_widget(program_spinner)
        content.add_widget(admission)
        content.add_widget(btns)
        pop = Popup(title='Add Student', content=content, size_hint=(.8,.8))

        def do_save(instance):
            if not sid.text.strip():
                pop.dismiss(); return
            prog = None
            if program_spinner.text and program_spinner.text != 'Select Program':
                prog = program_spinner.text.split(' - ')[0]
            s = Student(student_id=sid.text.strip(), first_name=fname.text.strip() or '-', last_name=lname.text.strip() or '-', dob=dob.text.strip() or None, program=prog, admission_year=int(admission.text) if admission.text.isdigit() else None)
            s.register()
            try:
                # create corresponding user account for student with default password
                create_user(s.student_id, f"student@{s.student_id}", 'student', s.student_id)
            except Exception:
                pass
            pop.dismiss()
            self.refresh_students()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_save)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def delete_student(self, student_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM students WHERE student_id=?', (student_id,))
        conn.commit()
        conn.close()
        self.refresh_students()

    def toggle_registered(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        s.set_registered(not s.is_registered())
        self.refresh_students()

    def add_result_popup(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        content = BoxLayout(orientation='vertical', spacing=6)
        course = TextInput(hint_text='Course code')
        grade = TextInput(hint_text='Grade (e.g., A, B+)')
        credits = TextInput(hint_text='Credits', input_filter='int')
        term = TextInput(hint_text='Term (e.g., 2026T1)')
        btns = BoxLayout(size_hint_y=None, height='36dp', spacing=6)
        save = Button(text='Save')
        cancel = Button(text='Cancel')
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(course)
        content.add_widget(grade)
        content.add_widget(credits)
        content.add_widget(term)
        content.add_widget(btns)
        pop = Popup(title=f'Add Result - {student_id}', content=content, size_hint=(.8,.6))

        def do_save(instance):
            c = course.text.strip()
            g = grade.text.strip()
            cr = int(credits.text) if credits.text.isdigit() else 3
            t = term.text.strip() or None
            if c and g:
                s.record_result(c, g, credits=cr, term=t)
            pop.dismiss()
            self.refresh_students()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_save)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def view_student(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        rpt = s.generate_report()
        lines = [f"ID: {rpt['student_id']}", f"Name: {rpt['name']}", f"Program: {rpt['program']}", f"Level: {rpt['level']}", f"GPA: {rpt['gpa']}", f"Tuition: {rpt['tuition_balance']}"]
        # add courses and results count
        lines.append('--- Courses ---')
        for c in rpt['courses']:
            lines.append(f"{c['course_code']} - {c.get('title','')} ({c.get('credits',0)}cr)")
        lines.append('--- Results ---')
        for r in rpt['results']:
            lines.append(f"{r['course_code']}: {r.get('grade','-')}")
        from kivy.uix.label import Label
        pop = Popup(title=f'Student {student_id}', content=Label(text='\n'.join(lines)), size_hint=(.8,.8))
        pop.open()

    def logout(self):
        from kivy.app import App
        from kivy.uix.screenmanager import ScreenManager
        app = App.get_running_app()
        root = app.root
        for child in root.children:
            if isinstance(child, ScreenManager):
                child.current = 'home'
                return
