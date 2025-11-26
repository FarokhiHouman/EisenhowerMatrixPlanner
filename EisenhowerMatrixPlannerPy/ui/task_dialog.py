# ui/task_dialog.py
# دیالوگ ویرایش/ایجاد تسک

import customtkinter as ctk
from database.models import Task

class TaskDialog(ctk.CTkToplevel):
    def __init__(self, master, task: Task = None, title="New Task"):
        super().__init__(master)
        self.title(title)
        self.task = task
        self.result = None

        self.geometry("400x320")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text="Task Title", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
        self.entry_title = ctk.CTkEntry(self, width=300)
        self.entry_title.pack(pady=5)
        if task:
            self.entry_title.insert(0, task.title)

        ctk.CTkLabel(self, text="Importance (1–10)").pack(pady=(15, 0))
        self.slider_i = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9)
        self.slider_i.pack(pady=5, padx=50, fill="x")
        self.slider_i.set(task.importance if task else 5)

        ctk.CTkLabel(self, text="Urgency (1–10)").pack(pady=(15, 0))
        self.slider_u = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9)
        self.slider_u.pack(pady=5, padx=50, fill="x")
        self.slider_u.set(task.urgency if task else 5)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Save", command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=10)

        self.entry_title.focus()
        self.bind("<Return>", lambda e: self.save())
        self.bind("<Escape>", lambda e: self.destroy())

    def save(self):
        title = self.entry_title.get().strip()
        if not title:
            return
        self.result = {
            "title": title,
            "importance": int(self.slider_i.get()),
            "urgency": int(self.slider_u.get())
        }
        self.destroy()