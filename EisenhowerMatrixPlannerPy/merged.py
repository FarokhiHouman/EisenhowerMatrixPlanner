### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\main.py
# main.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from ui.main_window import MainWindow
from database.db import init_db
from apscheduler.schedulers.background import BackgroundScheduler
from services.task_service import increase_urgency_for_near_deadlines

# تم فوق‌العاده زیبا — از بهترین تم‌های موجود
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("dark-blue")  # یا "green" یا "blue"

app = ctk.CTk()
app.title(" Eisenhower Matrix Planner")
app.geometry("1500x950")
app.minsize(1100, 750)

# آیکون (اختیاری — یه آیکون خوشگل بذار تو assets/icon.ico)
# app.iconbitmap("assets/icon.ico")

init_db()
window = MainWindow(app)
window.pack(fill="both", expand=True)

app.mainloop()

scheduler = BackgroundScheduler()
scheduler.add_job(increase_urgency_for_near_deadlines, "interval", minutes=30)
scheduler.start()


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\database\db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "eisenhower.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine)

def init_db():
    from .models import Base
    Base.metadata.create_all(bind=engine)


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\database\models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    importance = Column(Integer, nullable=False)   # ۱ تا ۱۰
    urgency = Column(Integer, nullable=False)      # ۱ تا ۱۰
    canvas_x = Column(Float)                       # موقعیت واقعی روی کانواس
    canvas_y = Column(Float)
    deadline = Column(DateTime, nullable=True)
    status = Column(String, default="pending")     # pending, in_progress, done
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.title} ({self.importance}/{self.urgency})>"


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\database\__init__.py



### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\services\task_service.py
from database.db import SessionLocal
from database.models import Task
from datetime import datetime, timedelta

def get_session():
    return SessionLocal()

def create_task(title: str, importance: int = 5, urgency: int = 5, canvas_x=None, canvas_y=None):
    session = get_session()
    try:
        task = Task(title=title, importance=importance, urgency=urgency,
                    canvas_x=canvas_x, canvas_y=canvas_y)
        session.add(task)
        session.commit()
        session.refresh(task)
        return task
    finally:
        session.close()

# افزایش خودکار urgency وقتی deadline نزدیک است
def increase_urgency_for_near_deadlines():
    session = get_session()
    try:
        now = datetime.utcnow()
        soon = now + timedelta(days=2)
        tasks = session.query(Task).filter(Task.deadline != None,
                                          Task.deadline <= soon,
                                          Task.urgency < 10).all()
        for t in tasks:
            t.urgency = min(10, t.urgency + 2)
            t.updated_at = now
        session.commit()
    finally:
        session.close()


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\services\__init__.py



### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\animations.py
# ui/animations.py
# توابع easing برای انیمیشن نرم

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\main_window.py
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


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\matrix_canvas.py
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


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\task_card.py
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


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\task_dialog.py
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


### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\ui\__init__.py



### FILE: C:\Users\farok\Documents\EisenhowerMatrixPlanner\EisenhowerMatrixPlannerPy\utils\logger.py
# utils/logger.py
# لاگ‌گیری حرفه‌ای با structlog + رنگ + فایل + کنسول

import structlog
import logging
import sys
from datetime import datetime
from pathlib import Path

# ایجاد پوشه logs اگر وجود نداشته باشه
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# تنظیمات پایه logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(f"logs/app_{datetime.now():%Y%m%d}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# تنظیمات structlog برای خروجی زیبا و ساختاریافته
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.JSONRenderer()  # برای فایل — خوانا و قابل جستجو
    ],
    logger_factory=structlog.PrintLoggerFactory(sys.stdout),
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    cache_logger_on_first_use=True,
)

# لاگر اصلی برنامه
log = structlog.get_logger("eisenhower_matrix")

# برای نمایش زیبا در کنسول (اختیاری)
try:
    from rich.logging import RichHandler
    logging.getLogger().handlers = [RichHandler(markup=True)]
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    )
except ImportError:
    pass  # اگر rich نصب نبود، از حالت ساده استفاده کن

# تابع کمکی برای لاگ کردن با اطلاعات بیشتر
def log_event(event: str, **kwargs):
    log.info(event, source="app", timestamp=datetime.now().isoformat(), **kwargs)


