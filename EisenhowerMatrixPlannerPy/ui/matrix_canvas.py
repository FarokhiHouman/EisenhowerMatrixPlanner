# ui/matrix_canvas.py
# نسخه نهایی — نقطه‌ها هرگز پاک نمی‌شن، resize کاملاً پایدار، شاهکار واقعی!

import customtkinter as ctk
from ui.task_card import TaskCard
from services.task_service import get_session
from database.models import Task

class MatrixCanvas(ctk.CTkCanvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.cards = {}
        self.bind("<Configure>", self.on_resize)

        # فقط یک بار پس‌زمینه بکش
        self.after(300, self.draw_background)

    def draw_background(self):
        self.delete("bg")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 100 or h < 100:
            self.after(300, self.draw_background)
            return

        hw, hh = w / 2, h / 2
        mode = "dark" if ctk.get_appearance_mode() == "Dark" else "light"
        colors = {
            "light": ["#ffeef8", "#fffbe6", "#ebfff0", "#f8f9fa"],
            "dark":  ["#2c1b1b", "#2c2b1b", "#1b2c1b", "#1e1e1e"]
        }
        c = colors[mode]

        # چهار ربع
        self.create_rectangle(0, 0, hw, hh, fill=c[0], outline="", tags="bg")
        self.create_rectangle(hw, 0, w, hh, fill=c[1], outline="", tags="bg")
        self.create_rectangle(0, hh, hw, h, fill=c[2], outline="", tags="bg")
        self.create_rectangle(hw, hh, w, h, fill=c[3], outline="", tags="bg")

        # عنوان ربع‌ها
        labels = ["Do First", "Schedule", "Delegate", "Eliminate"]
        sub = ["Important + Urgent", "Important", "Urgent", "Neither"]
        positions = [
            (hw/2, hh * 0.3),
            (w - hw/2, hh * 0.3),
            (hw/2, h - hh * 0.3),
            (w - hw/2, h - hh * 0.3)
        ]

        for i, ((x, y), main, subt) in enumerate(zip(positions, labels, sub)):
            color = ["#e74c3c", "#f39c12", "#27ae60", "#95a5a6"][i]
            self.create_text(x, y, text=main, font=("Segoe UI", 26, "bold"), fill=color, tags="bg")
            self.create_text(x, y + 35, text=subt, font=("Segoe UI", 12), fill=("gray50", "gray60")[mode=="dark"], tags="bg")

        # شبکه
        grid_color = "#e0e0e0" if mode == "light" else "#333333"
        for i in range(1, 10):
            x = i / 9 * w
            y = i / 9 * h
            self.create_line(x, 0, x, h, fill=grid_color, dash=(4, 8), tags="bg")
            self.create_line(0, y, w, y, fill=grid_color, dash=(4, 8), tags="bg")

    def on_resize(self, event=None):
        # فقط پس‌زمینه رو آپدیت کن
        self.draw_background()
        # نقطه‌ها رو جابجا کن — هرگز پاک نکن!
        self.reposition_all_tasks()

    def load_tasks(self):
        # فقط یک بار اجرا بشه — تسک‌ها رو بساز و دیگه دست نزن!
        if self.cards:
            return  # اگر قبلاً ساخته شده، دیگه کاری نکن

        session = get_session()
        tasks = session.query(Task).all()
        session.close()

        for task in tasks:
            card = TaskCard(self, task)
            self.cards[task.id] = card

            x = task.canvas_x
            y = task.canvas_y
            if x is None or y is None:
                x, y = self.importance_urgency_to_xy(task.importance, task.urgency)
                task.canvas_x = x
                task.canvas_y = y
                sess = get_session()
                sess.merge(task)
                sess.commit()
                sess.close()

            card.place_dot(x, y)

        # اولین جابجایی بعد از لود
        self.after(500, self.reposition_all_tasks)

    def reposition_all_tasks(self):
        # فقط موقعیت نقطه‌ها رو آپدیت کن — هرگز پاک نکن!
        for card in self.cards.values():
            x, y = self.importance_urgency_to_xy(card.task.importance, card.task.urgency)
            card.animate_to(x, y, duration=300)

    def importance_urgency_to_xy(self, importance: int, urgency: int):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: w = 1400
        if h <= 1: h = 900
        return (importance - 1) / 9 * w, (urgency - 1) / 9 * h

    def xy_to_importance_urgency(self, x, y):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: w = 1400
        if h <= 1: h = 900
        return max(1, min(10, round(x / w * 9) + 1)), max(1, min(10, round(y / h * 9) + 1))