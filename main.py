
from kivy.app import App
from kivy.properties import ListProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from student_model import Student, list_all_courses, list_courses_for_program
import db
from datetime import datetime

from admin import AdminDashboard


class StudentDashboard(BoxLayout):
    student = None

    def set_student(self, s):
        """Set dashboard to display given Student instance."""
        if not s:
            return
        self.student = s
        self.ids.name_label.text = f"Name: {s.first_name} {s.last_name}"
        self.ids.program_label.text = f"Program: {s.program}"
        self.ids.balance_label.text = f"Tuition Balance: {s.tuition_balance}"
        self.ids.gender_label.text = f"Gender: {s.gender or '-'}"
        self.ids.dob_label.text = f"DOB: {s.dob or '-'}"
        try:
            if s.photo_path:
                self.ids.profile_photo.source = s.photo_path
            else:
                self.ids.profile_photo.source = ''
        except Exception:
            pass
        self.update_time_info()
        self.update_status_display()
        self.refresh_courses()

    def update_status_display(self):
        if not self.student:
            return
        self.ids.registered_label.text = f"Registered: {'Yes' if self.student.is_registered() else 'No'}"
        self.ids.enrolled_label.text = f"Enrolled: {'Yes' if self.student.is_enrolled() else 'No'}"

    def toggle_registered(self):
        if not self.student:
            return
        current = self.student.is_registered()
        self.student.set_registered(not current)
        # reload student from DB to refresh state
        s = Student.get_by_id(self.student.student_id)
        self.student = s
        self.update_status_display()

    def logout(self):
        from kivy.app import App
        from kivy.uix.screenmanager import ScreenManager
        app = App.get_running_app()
        root = app.root
        # find the ScreenManager child of root and switch to home
        for child in root.children:
            if isinstance(child, ScreenManager):
                child.current = 'home'
                return


    def update_time_info(self):
        now = datetime.now()
        # simple semester mapping: months 1-6 -> Semester 1, 7-12 -> Semester 2
        month = now.month
        semester = 'Semester 1' if month <= 6 else 'Semester 2'
        year = now.year
        date_str = now.strftime('%Y-%m-%d %H:%M:%S')
        # set labels if they exist
        try:
            self.ids.semester_label.text = f"Semester: {semester}"
            self.ids.year_label.text = f"Year: {year}"
            self.ids.date_label.text = f"Date: {date_str}"
        except Exception:
            pass

    def show_profile(self):
        self.ids.screen_manager.current = 'profile'
        self.update_time_info()
        self.refresh_courses()

    def show_catalog(self):
        self.ids.screen_manager.current = 'catalog'
        self.refresh_catalog()

    def show_results(self):
        self.ids.screen_manager.current = 'results'
        self.refresh_results()

    def refresh_courses(self):
        # enrolled courses list in profile screen with drop buttons
        self.ids.courses_box.clear_widgets()
        if not self.student:
            return
        for c in self.student.list_courses():
            box = BoxLayout(size_hint_y=None, height='32dp')
            lbl = Label(text=f"{c['course_code']} - {c.get('title','')}", halign='left', size_hint_x=1)
            lbl.bind(size=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
            box.add_widget(lbl)
            btn = Button(text='Drop', size_hint_x=None, width='80', color=(1,1,1,1))
            btn.bind(on_release=lambda inst, code=c['course_code']: self.drop_course(code))
            box.add_widget(btn)
            self.ids.courses_box.add_widget(box)

    def refresh_catalog(self):
        # show available courses for student's program (if set) otherwise show all
        self.ids.catalog_box.clear_widgets()
        courses = []
        try:
            if self.student and self.student.program:
                courses = list_courses_for_program(self.student.program)
            if not courses:
                courses = list_all_courses()
        except Exception:
            courses = list_all_courses()
        for c in courses:
            box = BoxLayout(size_hint_y=None, height='32dp')
            lbl = Label(text=f"{c['course_code']} - {c.get('title','')}", halign='left', size_hint_x=1)
            lbl.bind(size=lambda inst, *a: setattr(inst, 'text_size', (inst.width, None)))
            box.add_widget(lbl)
            btn = Button(text='Enroll', size_hint_x=None, width='80', color=(1,1,1,1))
            btn.bind(on_release=lambda inst, code=c['course_code']: self.enroll_from_catalog(code))
            box.add_widget(btn)
            self.ids.catalog_box.add_widget(box)

    def refresh_results(self):
        self.ids.results_box.clear_widgets()
        if not self.student:
            self.ids.gpa_label.text = 'GPA: -'
            return
        results = self.student.get_transcript()
        for r in results:
            self.ids.results_box.add_widget(Label(text=f"{r['course_code']}: {r.get('grade','-')} ({r.get('credits',0)}cr)", size_hint_y=None, height='28dp'))
        gpa = self.student.calculate_gpa()
        self.ids.gpa_label.text = f"GPA: {gpa if gpa is not None else '-'}"

    def enroll_from_catalog(self, course_code):
        if not self.student:
            return
        self.student.enroll_course(course_code)
        # refresh both profile and catalog
        self.refresh_courses()
        self.refresh_catalog()

    def drop_course(self, course_code):
        if not self.student:
            return
        self.student.drop_course(course_code)
        self.refresh_courses()
        self.refresh_catalog()

    def register_courses(self):
        if not self.student:
            return
        # simple registration: enroll into sample CS101 (real registrations handled by admin/registry)
        from datetime import datetime as _dt
        now = _dt.now()
        term = f"{now.year}T1" if now.month <= 6 else f"{now.year}T2"
        self.student.enroll_course('CS101', title='Intro to CS', credits=3, term=term)
        self.refresh_courses()
        self.update_status_display()

    def pay_tuition(self):
        if not self.student:
            return
        from kivy.uix.popup import Popup
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        content = BoxLayout(orientation='vertical', spacing=6)
        ti = TextInput(hint_text='Enter amount', input_filter='float')
        btns = BoxLayout(size_hint_y=None, height='36dp', spacing=6)
        save = Button(text='Pay', color=(1,1,1,1))
        cancel = Button(text='Cancel', color=(1,1,1,1))
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(ti)
        content.add_widget(btns)
        pop = Popup(title='Pay Tuition', content=content, size_hint=(.6,.4))

        def do_pay(instance):
            amt_text = ti.text.strip()
            if amt_text:
                try:
                    amt = float(amt_text)
                    self.student.pay_tuition(amt, method='card')
                    s = Student.get_by_id(self.student.student_id)
                    self.student = s
                    self.ids.balance_label.text = f"Tuition Balance: {s.tuition_balance}"
                    self.update_status_display()
                except Exception:
                    pass
            pop.dismiss()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_pay)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def view_transcript(self):
        if not self.student:
            return
        results = self.student.get_transcript()
        msg = '\n'.join([f"{r['course_code']}: {r['grade']}" for r in results]) or 'No results'
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        content = Label(text=msg)
        pop = Popup(title='Transcript', content=content, size_hint=(.8,.8))
        pop.open()

    def generate_report(self):
        if not self.student:
            return
        rpt = self.student.generate_report()
        text = f"ID: {rpt['student_id']}\nName: {rpt['name']}\nProgram: {rpt['program']}\nLevel: {rpt['level']}\nGPA: {rpt['gpa']}\nTuition: {rpt['tuition_balance']}"
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        pop = Popup(title='Student Report', content=Label(text=text), size_hint=(.8,.6))
        pop.open()


class StudentApp(App):
    primary_color = ListProperty([0.105882,0.149019,0.231372,1])
    secondary_color = ListProperty([0.254902,0.352941,0.466667,1])
    background_color = ListProperty([0.972549,0.976471,0.980392,1])
    text_color = ListProperty([0.05098,0.105882,0.164706,1])
    highlight_color = ListProperty([0.878431,0.882353,0.866667,1])

    def build(self):
        db.init_db()
        Builder.load_file('theme.kv')
        from kivy.uix.screenmanager import ScreenManager, Screen
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        root = BoxLayout(orientation='vertical')
        top = BoxLayout(size_hint_y=None, height='40dp')
        from kivy.graphics import Color, Rectangle
        with top.canvas.before:
            Color(*self.primary_color)
            _top_rect = Rectangle(pos=top.pos, size=top.size)
        def _update_top_rect(instance, value):
            _top_rect.pos = instance.pos
            _top_rect.size = instance.size
        top.bind(pos=_update_top_rect, size=_update_top_rect)
        title = Label(text='[b]University Student Record management system[/b]', size_hint_x=1, halign='center', valign='middle', shorten=True, shorten_from='right', markup=True, color=(1,1,1,1))
        top.add_widget(title)
        root.add_widget(top)

        sm = ScreenManager()
        # home screen
        home = Screen(name='home')
        hl = BoxLayout(orientation='vertical', padding=20, spacing=10)
        b1 = Button(text='[b]Student View[/b]', size_hint_y=None, height='60dp', markup=True, color=(1,1,1,1))
        b2 = Button(text='[b]Admin View[/b]', size_hint_y=None, height='60dp', markup=True, color=(1,1,1,1))
        b3 = Button(text='[b]Registry View[/b]', size_hint_y=None, height='60dp', markup=True, color=(1,1,1,1))
        b4 = Button(text='[b]Finance View[/b]', size_hint_y=None, height='60dp', markup=True, color=(1,1,1,1))
        b5 = Button(text='[b]Lecturer View[/b]', size_hint_y=None, height='60dp', markup=True, color=(1,1,1,1))
        hl.add_widget(b1)
        hl.add_widget(b2)
        hl.add_widget(b3)
        hl.add_widget(b4)
        hl.add_widget(b5)
        home.add_widget(hl)
        sm.add_widget(home)
        root.add_widget(sm)

        def load_student_view(*args):
            if not sm.has_screen('student'):
                Builder.load_file('student_dashboard.kv')
                student_dash = StudentDashboard()
                s = Student.get_by_id('S001')
                if not s:
                    s = Student(student_id='S001', first_name='Joshua', last_name='Ayebale', dob='2003-11-24', admission_year=2022, program='CS101')
                    s.register()
                else:
                    s.update_profile(first_name='Joshua', last_name='Ayebale', dob='2003-11-24', program='CS101')
                    s = Student.get_by_id('S001')
                student_dash.set_student(s)
                scr = Screen(name='student')
                scr.add_widget(student_dash)
                sm.add_widget(scr)
            sm.current = 'student'

        def load_admin_view(*args):
            if not sm.has_screen('admin'):
                Builder.load_file('admin_dashboard.kv')
                admin_dash = AdminDashboard()
                scr = Screen(name='admin')
                scr.add_widget(admin_dash)
                sm.add_widget(scr)
            sm.current = 'admin'

        def load_registry_view(*args):
            if not sm.has_screen('registry'):
                Builder.load_file('registry_dashboard.kv')
                from registry import RegistryDashboard
                registry_dash = RegistryDashboard()
                scr = Screen(name='registry')
                scr.add_widget(registry_dash)
                sm.add_widget(scr)
            sm.current = 'registry'

        def load_finance_view(*args):
            if not sm.has_screen('finance'):
                Builder.load_file('finance_dashboard.kv')
                from finance import FinanceDashboard
                finance_dash = FinanceDashboard()
                scr = Screen(name='finance')
                scr.add_widget(finance_dash)
                sm.add_widget(scr)
            sm.current = 'finance'

        def load_lecturer_view(*args):
            if not sm.has_screen('lecturer'):
                Builder.load_file('lecturer_dashboard.kv')
                from lecturer import LecturerDashboard
                lect_dash = LecturerDashboard()
                scr = Screen(name='lecturer')
                scr.add_widget(lect_dash)
                sm.add_widget(scr)
            sm.current = 'lecturer'

        b1.bind(on_release=load_student_view)
        b2.bind(on_release=load_admin_view)
        b3.bind(on_release=load_registry_view)
        b4.bind(on_release=load_finance_view)
        b5.bind(on_release=load_lecturer_view)

        return root


if __name__ == '__main__':
    StudentApp().run()
