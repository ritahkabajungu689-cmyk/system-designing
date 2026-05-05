from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from db import get_conn, create_user
from student_model import Student, list_all_courses


class RegistryDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
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
            box = BoxLayout()
            box.add_widget(Label(text=f"{sid} - {name} ({program})", halign='left'))
            btn_view = Button(text='View', size_hint_x=None, width=60, color=(1,1,1,1))
            btn_view.bind(on_release=lambda inst, s=sid: self.view_student(s))
            box.add_widget(btn_view)
            btn_enroll = Button(text='Enroll', size_hint_x=None, width=70, color=(1,1,1,1))
            btn_enroll.bind(on_release=lambda inst, s=sid: self.enroll_popup(s))
            box.add_widget(btn_enroll)
            btn_reg = Button(text='Register', size_hint_x=None, width=70, color=(1,1,1,1))
            btn_reg.bind(on_release=lambda inst, s=sid: self.register_student(s))
            box.add_widget(btn_reg)
            self.ids.students_box.add_widget(box)

    def add_student_popup(self):
        content = BoxLayout(orientation='vertical', spacing=6)
        sid = TextInput(hint_text='Student ID')
        fname = TextInput(hint_text='First name')
        lname = TextInput(hint_text='Last name')
        dob = TextInput(hint_text='DOB (YYYY-MM-DD)')
        program = Spinner(text='Select Program', values=('CS101 - Computer Science','CS102 - Cyber Security','SE101 - Software Engineering','DA101 - Data Analysis','AM101 - AI & ML','IT101 - Information Technology'))
        admission = TextInput(hint_text='Admission Year', input_filter='int')
        btns = BoxLayout(size_hint_y=None, height='36dp', spacing=6)
        save = Button(text='Save', color=(1,1,1,1))
        cancel = Button(text='Cancel')
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(sid)
        content.add_widget(fname)
        content.add_widget(lname)
        content.add_widget(dob)
        content.add_widget(program)
        content.add_widget(admission)
        content.add_widget(btns)
        pop = Popup(title='Add Student (Registry)', content=content, size_hint=(.8,.8))

        def do_save(instance):
            if not sid.text.strip():
                pop.dismiss(); return
            prog = None
            if program.text and program.text != 'Select Program':
                prog = program.text.split(' - ')[0]
            s = Student(student_id=sid.text.strip(), first_name=fname.text.strip() or '-', last_name=lname.text.strip() or '-', dob=dob.text.strip() or None, program=prog, admission_year=int(admission.text) if admission.text.isdigit() else None)
            s.register()
            pop.dismiss()
            self.refresh_students()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_save)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def enroll_popup(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        content = BoxLayout(orientation='vertical', spacing=6)
        # show program-specific course options when possible
        try:
            from student_model import list_courses_for_program, list_all_courses
            options = list_courses_for_program(s.program) if s.program else []
            if not options:
                options = list_all_courses()
            spinner_vals = [f"{c['course_code']} - {c['title']}" for c in options]
        except Exception:
            spinner_vals = []
        course_spinner = Spinner(text='Select Course', values=spinner_vals)
        title = TextInput(hint_text='Course title (optional)')
        credits = TextInput(hint_text='Credits', input_filter='int')
        term = TextInput(hint_text='Term (e.g., 2026T1)')
        btns = BoxLayout(size_hint_y=None, height='36dp', spacing=6)
        save = Button(text='Enroll', color=(1,1,1,1))
        cancel = Button(text='Cancel')
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(course_spinner)
        content.add_widget(title)
        content.add_widget(credits)
        content.add_widget(term)
        content.add_widget(btns)
        pop = Popup(title=f'Enroll Student {student_id}', content=content, size_hint=(.8,.6))

        def do_enroll(instance):
            sel = course_spinner.text or ''
            c = sel.split(' - ')[0].strip() if ' - ' in sel else sel.strip()
            t = term.text.strip() or None
            ttl = title.text.strip() or None
            cr = int(credits.text) if credits.text.isdigit() else 3
            if c:
                s.enroll_course(c, title=ttl, credits=cr, term=t)
                pop.dismiss()
                self.refresh_students()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_enroll)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def register_student(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        s.set_registered(True)
        self.refresh_students()

    def view_student(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        rpt = s.generate_report()
        lines = [f"ID: {rpt['student_id']}", f"Name: {rpt['name']}", f"Program: {rpt['program']}", f"Level: {rpt['level']}", f"GPA: {rpt['gpa']}", f"Tuition: {rpt['tuition_balance']}"]
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
