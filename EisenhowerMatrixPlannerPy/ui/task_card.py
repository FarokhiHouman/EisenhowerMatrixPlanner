# ui/task_card.py
# نسخه نهایی بدون چشمک — هاور روی منطقه بزرگ، کارت ثابت و خوانا

import customtkinter as ctk
from .task_dialog import TaskDialog
from services.task_service import get_session
from tkinter import messagebox

class TaskCard:
    DOT_SIZE = 20
    HOVER_RADIUS = 80  # منطقه هاور بزرگتر از نقطه

    def __init__(self, canvas, task):
        self.canvas = canvas
        self.task = task
        self.hovered = False

        # نقطه اصلی
        self.dot = canvas.create_oval(
            0, 0, self.DOT_SIZE, self.DOT_SIZE,
            fill=self.get_color(), outline="#ffffff", width=4, tags="dot"
        )

        # منطقه هاور نامرئی (بزرگتر از نقطه)
        self.hover_zone = canvas.create_oval(
            0, 0, self.HOVER_RADIUS*2, self.HOVER_RADIUS*2,
            fill="", outline="", tags="hover_zone", state="hidden"
        )

        # کارت هاور
        self.popup = ctk.CTkFrame(
            canvas, width=300, height=170,
            corner_radius=20, fg_color=("#ffffff", "#2b2b2b"),
            border_width=2, border_color=("#e0e0e0", "#404040")
        )
        self.popup.place_forget()

        # محتوای کارت
        ctk.CTkLabel(self.popup, text=task.title,
                     font=ctk.CTkFont(size=19, weight="bold"), wraplength=260).pack(pady=(20, 8))
        ctk.CTkLabel(self.popup, text=f"Importance: {task.importance}  •  Urgency: {task.urgency}",
                     font=ctk.CTkFont(size=12)).pack(pady=(0, 15))

        btns = ctk.CTkFrame(self.popup, fg_color="transparent")
        btns.pack(pady=10)
        ctk.CTkButton(btns, text="Edit", width=100, command=self.edit).pack(side="left", padx=10)
        ctk.CTkButton(btns, text="Delete", width=100, fg_color="#e74c3c", hover_color="#c0392b",
                      command=self.delete).pack(side="left", padx=10)

        # هاور فقط روی منطقه بزرگ
        canvas.tag_bind(self.hover_zone, "<Enter>", self.show_popup)
        canvas.tag_bind(self.hover_zone, "<Leave>", self.hide_popup)
        canvas.tag_bind(self.dot, "<Enter>", self.show_popup)
        canvas.tag_bind(self.dot, "<Leave>", self.hide_popup)

        # درگ با نقطه
        canvas.tag_bind(self.dot, "<ButtonPress-1>", self.start_drag)
        canvas.tag_bind(self.dot, "<B1-Motion>", self.drag)
        canvas.tag_bind(self.dot, "<ButtonRelease-1>", self.drop)

        self.drag_data = {"x": 0, "y": 0}

    def get_color(self):
        i, u = self.task.importance, self.task.urgency
        if i >= 7 and u >= 7: return "#e74c3c"
        if i >= 7: return "#f39c12"
        if u >= 7: return "#3498db"
        return "#95a5a6"

    def place_dot(self, x, y):
        r = self.DOT_SIZE // 2
        hr = self.HOVER_RADIUS
        # نقطه
        self.canvas.coords(self.dot, x-r, y-r, x+r, y+r)
        # منطقه هاور (مرکز همان نقطه)
        self.canvas.coords(self.hover_zone, x-hr, y-hr, x+hr, y+hr)
        self.canvas.itemconfig(self.dot, fill=self.get_color())

    def show_popup(self, event=None):
        if self.hovered: return
        self.hovered = True
        x1, y1, x2, y2 = self.canvas.bbox(self.dot)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        # کارت بالای نقطه ظاهر بشه
        self.popup.place(x=cx - 150, y=cy - 200)

    def hide_popup(self, event=None):
        if not self.hovered: return
        self.hovered = False
        self.popup.place_forget()

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.canvas.move(self.dot, dx, dy)
        self.canvas.move(self.hover_zone, dx, dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        if self.hovered:
            self.show_popup()

    def drop(self, event):
        x1, y1, x2, y2 = self.canvas.bbox(self.dot)
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        i, u = self.canvas.xy_to_importance_urgency(cx, cy)

        if i != self.task.importance or u != self.task.urgency:
            self.task.importance = i
            self.task.urgency = u
            sess = get_session()
            sess.merge(self.task)
            sess.commit()
            sess.close()

        x, y = self.canvas.importance_urgency_to_xy(i, u)
        self.task.canvas_x = x
        self.task.canvas_y = y
        self.animate_to(x, y)

    def edit(self):
        dialog = TaskDialog(self.canvas.master.master, task=self.task, title="Edit Task")
        self.canvas.master.master.wait_window(dialog)
        if dialog.result:
            self.task.title = dialog.result["title"]
            self.task.importance = dialog.result["importance"]
            self.task.urgency = dialog.result["urgency"]
            sess = get_session()
            sess.merge(self.task)
            sess.commit()
            sess.close()
            # آپدیت عنوان کارت
            self.popup.winfo_children()[0].configure(text=self.task.title)
            self.popup.winfo_children()[1].configure(text=f"Importance: {self.task.importance}  •  Urgency: {self.task.urgency}")

    def delete(self):
        if messagebox.askyesno("Delete Task", f"Really delete?\n\n\"{self.task.title}\""):
            sess = get_session()
            sess.delete(self.task)
            sess.commit()
            sess.close()
            self.canvas.delete(self.dot)
            self.canvas.delete(self.hover_zone)
            self.popup.destroy()
            if self.task.id in self.canvas.cards:
                del self.canvas.cards[self.task.id]

    def animate_to(self, tx, ty, duration=400):
        # بعد:
        bbox = self.canvas.bbox(self.dot)
        if bbox is None:
            return  # اگر نقطه پاک شده بود، کاری نکن
        x1, y1, x2, y2 = bbox
        sx, sy = (x1 + x2) / 2, (y1 + y2) / 2
        steps = 25
        delay = duration // steps

        def step(n=0):
            if n <= steps:
                p = 1 - (1 - n/steps)**3
                x = sx + (tx - sx) * p
                y = sy + (ty - sy) * p
                self.place_dot(x, y)
                self.canvas.after(delay, step, n+1)
            else:
                self.place_dot(tx, ty)
        step()

        # فقط این متد رو به انتهای کلاس TaskCard اضافه کن:
        def animate_entrance(self, delay=0):
            # انیمیشن ورود ساده — فقط نقطه کمی بزرگ و کوچک بشه
            def pulse():
                self.canvas.itemconfig(self.dot, width=6)
                self.canvas.after(200, lambda: self.canvas.itemconfig(self.dot, width=4))

            self.canvas.after(delay, pulse)