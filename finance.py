from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from db import get_conn
from student_model import Student
from datetime import datetime

class FinanceDashboard(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.refresh_students()

    def refresh_students(self):
        self.ids.students_box.clear_widgets()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT student_id, first_name, last_name, tuition_balance FROM students ORDER BY student_id')
        rows = cur.fetchall()
        for r in rows:
            sid = r['student_id']
            name = f"{r['first_name']} {r['last_name'] or ''}".strip()
            bal = r['tuition_balance'] or 0.0
            # compute total paid
            cur.execute('SELECT IFNULL(SUM(amount),0) as total_paid FROM tuition_payments WHERE student_id=?', (sid,))
            paid_row = cur.fetchone()
            total_paid = paid_row['total_paid'] if paid_row else 0.0
            debt = bal if bal and bal > 0 else 0.0
            box = BoxLayout()
            box.add_widget(Label(text=f"{sid} - {name}", halign='left'))
            box.add_widget(Label(text=f"Balance: {bal:.2f} | Paid: {total_paid:.2f} | Debt: {debt:.2f}", halign='right'))
            btn_history = Button(text='History', size_hint_x=None, width=80)
            btn_history.bind(on_release=lambda inst, s=sid: self.show_history(s))
            box.add_widget(btn_history)
            btn_pay = Button(text='Record Payment', size_hint_x=None, width=120)
            btn_pay.bind(on_release=lambda inst, s=sid: self.record_payment_popup(s))
            box.add_widget(btn_pay)
            self.ids.students_box.add_widget(box)
        conn.close()

    def show_history(self, student_id):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT amount, method, paid_at, payer FROM tuition_payments WHERE student_id=? ORDER BY paid_at DESC', (student_id,))
        rows = cur.fetchall()
        conn.close()
        lines = [f"{r['paid_at']}: {r['amount']} ({r['method']}) by {r.get('payer', '') or 'Unknown'}" for r in rows]
        if not lines:
            lines = ['No payments']
        from kivy.uix.label import Label
        pop = Popup(title=f'Payments - {student_id}', content=Label(text='\n'.join(lines)), size_hint=(.8,.8))
        pop.open()

    def record_payment_popup(self, student_id):
        s = Student.get_by_id(student_id)
        if not s:
            return
        content = BoxLayout(orientation='vertical', spacing=6)
        amt = TextInput(hint_text='Amount', input_filter='float')
        method = TextInput(hint_text='Method (cash/card)')
        payer = TextInput(hint_text='Payer name (who paid)')
        btns = BoxLayout(size_hint_y=None, height='36dp')
        save = Button(text='Record', color=(1,1,1,1))
        cancel = Button(text='Cancel', color=(1,1,1,1))
        btns.add_widget(save)
        btns.add_widget(cancel)
        content.add_widget(amt)
        content.add_widget(method)
        content.add_widget(payer)
        content.add_widget(btns)
        pop = Popup(title=f'Record Payment - {student_id}', content=content, size_hint=(.6,.5))

        def do_record(instance):
            try:
                amount = float(amt.text.strip())
            except Exception:
                amount = 0.0
            m = method.text.strip() or 'cash'
            p = payer.text.strip() or None
            if amount > 0:
                s.pay_tuition(amount, method=m, payer=p)
                self.refresh_students()
            pop.dismiss()

        def do_cancel(instance):
            pop.dismiss()

        save.bind(on_release=do_record)
        cancel.bind(on_release=do_cancel)
        pop.open()

    def filter_balances(self):
        # show only students with positive balance
        self.ids.students_box.clear_widgets()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute('SELECT student_id, first_name, last_name, tuition_balance FROM students WHERE tuition_balance>0 ORDER BY tuition_balance DESC')
        rows = cur.fetchall()
        for r in rows:
            sid = r['student_id']
            name = f"{r['first_name']} {r['last_name'] or ''}".strip()
            bal = r['tuition_balance'] or 0.0
            # compute total paid
            cur.execute('SELECT IFNULL(SUM(amount),0) as total_paid FROM tuition_payments WHERE student_id=?', (sid,))
            paid_row = cur.fetchone()
            total_paid = paid_row['total_paid'] if paid_row else 0.0
            debt = bal if bal and bal > 0 else 0.0
            box = BoxLayout()
            box.add_widget(Label(text=f"{sid} - {name}", halign='left'))
            box.add_widget(Label(text=f"Balance: {bal:.2f} | Paid: {total_paid:.2f} | Debt: {debt:.2f}", halign='right'))
            btn_history = Button(text='History', size_hint_x=None, width=80)
            btn_history.bind(on_release=lambda inst, s=sid: self.show_history(s))
            box.add_widget(btn_history)
            btn_pay = Button(text='Record Payment', size_hint_x=None, width=120)
            btn_pay.bind(on_release=lambda inst, s=sid: self.record_payment_popup(s))
            box.add_widget(btn_pay)
            self.ids.students_box.add_widget(box)
        conn.close()

    def logout(self):
        from kivy.app import App
        from kivy.uix.screenmanager import ScreenManager
        app = App.get_running_app()
        root = app.root
        for child in root.children:
            if isinstance(child, ScreenManager):
                child.current = 'home'
                return
