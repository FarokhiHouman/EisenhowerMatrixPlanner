# ui/matrix_canvas.py
# نسخه نهایی — بدون خطای رنگ، بدون خطای آرگومان، کاملاً پایدار

import customtkinter as ctk
from ui.task_card import TaskCard
from ui.animations import ease_out_cubic
from services.task_service import get_session
from database.models import Task

class MatrixCanvas(ctk.CTkCanvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.cards = {}
        self.grid_size = 10
        self.bind("<Configure>", self.on_resize)
        self.after(100, self.on_resize)  # اولین بار

    def on_resize(self, event=None):
        self.width = self.winfo_width()
        self.height = self.winfo_height()
        if self.width < 100 or self.height < 100:
            return

        self.delete("all")
        self.draw_background()
        self.reposition_all_cards()

    def draw_background(self):
        w, h = self.width, self.height
        hw, hh = w / 2, h / 2

        # چهار ربع
        self.create_rectangle(0, 0, hw, hh, fill="#ffcccc", outline="")
        self.create_rectangle(hw, 0, w, hh, fill="#ffffcc", outline="")
        self.create_rectangle(0, hh, hw, h, fill="#ccffcc", outline="")
        self.create_rectangle(hw, hh, w, h, fill="#dddddd", outline="")

        # خطوط شبکه — با رنگ قابل قبول برای همه سیستم‌ها
        grid_color = "#aaaaaa" if ctk.get_appearance_mode() == "Light" else "#555555"
        for i in range(1, self.grid_size):
            x = i / (self.grid_size - 1) * w
            y = i / (self.grid_size - 1) * h
            self.create_line(x, 0, x, h, fill=grid_color, dash=(4, 8))
            self.create_line(0, y, w, y, fill=grid_color, dash=(4, 8))

    def load_tasks(self):
        session = get_session()
        tasks = session.query(Task).all()
        session.close()

        for card in self.cards.values():
            card.destroy()
        self.cards.clear()

        for i, task in enumerate(tasks):
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

            card.place(x=x - card.WIDTH//2, y=y - card.HEIGHT//2)
            card.animate_entrance(delay=i * 80)

    def reposition_all_cards(self):
        for card in self.cards.values():
            x, y = self.importance_urgency_to_xy(card.task.importance, card.task.urgency)
            card.animate_to(x - card.WIDTH//2, y - card.HEIGHT//2, duration=300)

    # فقط ۲ آرگومان می‌گیره — درست
    def importance_urgency_to_xy(self, importance: int, urgency: int):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1:
            w, h = 1200, 800  # fallback
        x = (importance - 1) / (self.grid_size - 1) * w
        y = (urgency - 1) / (self.grid_size - 1) * h
        return x, y

    def xy_to_importance_urgency(self, x, y):
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1: w = 1200
        if h <= 1: h = 800
        i = round(x / w * (self.grid_size - 1)) + 1
        u = round(y / h * (self.grid_size - 1)) + 1
        return max(1, min(10, i)), max(1, min(10, u))