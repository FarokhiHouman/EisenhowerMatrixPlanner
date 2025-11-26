# ui/main_window.py — نسخه نهایی بدون حاشیه اضافی

import customtkinter as ctk
from .matrix_canvas import MatrixCanvas
from .task_dialog import TaskDialog
from services.task_service import create_task, get_session
from tkinter import filedialog, messagebox
from datetime import datetime
import io
from PIL import Image

class MainWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.master = master
        self.setup_ui()

    def setup_ui(self):
        # هدر خیلی کوچیک و شیک
        header = ctk.CTkFrame(self.master, height=90, fg_color=("gray10", "gray90"), corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="Eisenhower Matrix",
            font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"),
            text_color=("#2ecc71", "#27ae60")
        )
        title.pack(pady=20)

        # نوار ابزار
        toolbar = ctk.CTkFrame(self.master, height=70, fg_color=("gray14", "gray92"))
        toolbar.pack(fill="x", padx=20, pady=(0, 10))
        toolbar.pack_propagate(False)

        left = ctk.CTkFrame(toolbar, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkButton(
            left, text="+ New Task", width=160, height=44,
            font=ctk.CTkFont(size=15, weight="bold"), corner_radius=12,
            fg_color=("#2ecc71", "#27ae60"), hover_color=("#27ae60", "#219a52"),
            command=self.add_new_task
        ).pack(side="left", padx=10, pady=10)

        right = ctk.CTkFrame(toolbar, fg_color="transparent")
        right.pack(side="right")

        self.theme_switch = ctk.CTkSwitch(right, text="Dark Mode", command=self.toggle_theme)
        self.theme_switch.pack(side="right", padx=20, pady=10)
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()

        ctk.CTkButton(right, text="Export PNG", width=130, command=self.export_to_png).pack(side="right", padx=10, pady=10)

        # کانواس تمام صفحه!
        canvas_frame = ctk.CTkFrame(self.master, fg_color=("gray98", "gray10"))
        canvas_frame.pack(fill="both", expand=True, padx=0, pady=0)  # بدون padx/pady!

        self.canvas = MatrixCanvas(canvas_frame, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # لود تسک‌ها بعد از آماده شدن
        self.canvas.after(500, self.canvas.load_tasks)

    def add_new_task(self):
        dialog = TaskDialog(self.master, title="New Task")
        self.master.wait_window(dialog)
        if dialog.result:
            task = create_task(**dialog.result)
            x, y = self.canvas.importance_urgency_to_xy(task.importance, task.urgency)
            task.canvas_x, task.canvas_y = x, y
            sess = get_session()
            sess.merge(task); sess.commit(); sess.close()
            self.canvas.load_tasks()

    def toggle_theme(self):
        ctk.set_appearance_mode("dark" if self.theme_switch.get() else "light")

    def export_to_png(self):
        file = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if file:
            ps = self.canvas.postscript(colormode='color')
            Image.open(io.BytesIO(ps.encode('utf-8'))).save(file, "PNG")
            messagebox.showinfo("موفقیت", "تصویر با موفقیت ذخیره شد!")