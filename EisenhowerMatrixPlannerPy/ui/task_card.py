# ui/task_card.py
# نسخه نهایی: حذف با کلیک راست + انیمیشن محو شدن بدون خطای opacity

import customtkinter as ctk
from .task_dialog import TaskDialog
from .animations import ease_out_cubic
from services.task_service import get_session
from tkinter import messagebox

class TaskCard(ctk.CTkFrame):
    WIDTH = 220
    HEIGHT = 120

    def __init__(self, canvas, task):
        super().__init__(
            canvas,
            width=self.WIDTH,
            height=self.HEIGHT,
            corner_radius=16,
            fg_color=("gray92", "gray18"),
            border_width=2,
            border_color=("gray70", "gray30")
        )
        self.canvas = canvas
        self.task = task
        self.original_fg = self.cget("fg_color")  # برای انیمیشن محو

        # عنوان
        self.title_label = ctk.CTkLabel(
            self,
            text=task.title,
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=190,
            justify="center"
        )
        self.title_label.pack(expand=True, pady=(20, 5))

        # اطلاعات
        self.info_label = ctk.CTkLabel(
            self,
            text=f"I: {task.importance} • U: {task.urgency}",
            font=ctk.CTkFont(size=11)
        )
        self.info_label.pack(pady=(0, 15))

        # رویدادها
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Double-Button-1>", self.on_edit)
        self.bind("<Button-3>", self.on_right_click)   # راست‌کلیک ویندوز/لینوکس
        self.bind("<Button-2>", self.on_right_click)   # راست‌کلیک مک

        for widget in (self.title_label, self.info_label):
            widget.bind("<ButtonPress-1>", self.on_press)
            widget.bind("<B1-Motion>", self.on_drag)
            widget.bind("<ButtonRelease-1>", self.on_release)
            widget.bind("<Double-Button-1>", self.on_edit)
            widget.bind("<Button-3>", self.on_right_click)
            widget.bind("<Button-2>", self.on_right_click)

        self.bind("<Enter>", lambda e: self.configure(border_width=5))
        self.bind("<Leave>", lambda e: self.configure(border_width=2))

        self.start_x = self.start_y = 0

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.lift()

    def on_drag(self, event):
        x = self.winfo_x() + event.x - self.start_x
        y = self.winfo_y() + event.y - self.start_y
        self.place(x=x, y=y)

    def on_release(self, event):
        center_x = self.winfo_x() + self.WIDTH // 2
        center_y = self.winfo_y() + self.HEIGHT // 2
        new_i, new_u = self.canvas.xy_to_importance_urgency(center_x, center_y)

        if new_i != self.task.importance or new_u != self.task.urgency:
            self.task.importance = new_i
            self.task.urgency = new_u
            self.info_label.configure(text=f"I: {new_i} • U: {new_u}")

            sess = get_session()
            sess.merge(self.task)
            sess.commit()
            sess.close()

        x, y = self.canvas.importance_urgency_to_xy(new_i, new_u)
        self.task.canvas_x = x
        self.task.canvas_y = y
        self.animate_to(x - self.WIDTH//2, y - self.HEIGHT//2, duration=400)

    def on_edit(self, event=None):
        dialog = TaskDialog(self.canvas.master.master, task=self.task, title="Edit Task")
        self.canvas.master.master.wait_window(dialog)
        if dialog.result:
            old_i, old_u = self.task.importance, self.task.urgency
            self.task.title = dialog.result["title"]
            self.task.importance = dialog.result["importance"]
            self.task.urgency = dialog.result["urgency"]

            self.title_label.configure(text=self.task.title)
            self.info_label.configure(text=f"I: {self.task.importance} • U: {self.task.urgency}")

            if old_i != self.task.importance or old_u != self.task.urgency:
                x, y = self.canvas.importance_urgency_to_xy(self.task.importance, self.task.urgency)
                self.task.canvas_x = x
                self.task.canvas_y = y
                self.animate_to(x - self.WIDTH//2, y - self.HEIGHT//2, duration=500)

            sess = get_session()
            sess.merge(self.task)
            sess.commit()
            sess.close()

    def on_right_click(self, event):
        if messagebox.askyesno("Delete Task", f"Delete this task?\n\n\"{self.task.title}\"", icon="warning"):
            sess = get_session()
            sess.delete(self.task)
            sess.commit()
            sess.close()
            self.animate_fade_out()

    def animate_fade_out(self):
        """انیمیشن محو شدن با تغییر رنگ به سمت شفاف — بدون opacity"""
        steps = 20
        delay = 25

        # رنگ پایه (light, dark)
        base_light = "#f0f0f0"
        base_dark = "#1e1e1e"

        def fade(n=0):
            if n <= steps and self.winfo_exists():
                alpha = 1.0 - (n / steps)
                # ترکیب رنگ با پس‌زمینه
                if ctk.get_appearance_mode() == "Light":
                    new_color = "#%02x%02x%02x" % (
                        int(240 + (15 * alpha)),   # از سفید به خاکستری روشن
                        int(240 + (15 * alpha)),
                        int(240 + (15 * alpha))
                    )
                else:
                    new_color = "#%02x%02x%02x" % (
                        int(30 * alpha),
                        int(30 * alpha),
                        int(30 * alpha)
                    )
                self.configure(fg_color=new_color, border_color=new_color)
                self.after(delay, fade, n + 1)
            elif self.winfo_exists():
                self.destroy()
                if self.task.id in self.canvas.cards:
                    del self.canvas.cards[self.task.id]

        fade()

    def animate_to(self, tx, ty, duration=400):
        sx, sy = self.winfo_x(), self.winfo_y()
        steps = 25
        delay = max(1, duration // steps)

        def step(n=0):
            if n <= steps and self.winfo_exists():
                p = ease_out_cubic(n / steps)
                x = sx + (tx - sx) * p
                y = sy + (ty - sy) * p
                self.place(x=x, y=y)
                self.after(delay, step, n + 1)
            elif self.winfo_exists():
                self.place(x=tx, y=ty)

        step()

    def animate_entrance(self, delay=0):
        self.after(delay, lambda: self.animate_to(self.winfo_x(), self.winfo_y(), 600))