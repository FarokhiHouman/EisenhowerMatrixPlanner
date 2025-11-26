import sys
from pathlib import Path

# اضافه کردن پوشه اصلی به مسیر
sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk
from ui.main_window import MainWindow
from database.db import init_db
from apscheduler.schedulers.background import BackgroundScheduler
from services.task_service import increase_urgency_for_near_deadlines

# تنظیمات تم
ctk.set_appearance_mode("system")      # system / dark / light
ctk.set_default_color_theme("blue")

# پنجره اصلی
app = ctk.CTk()
app.title("Eisenhower Matrix Planner")
app.geometry("1400x900")
app.minsize(1000, 700)

# دیتابیس و UI
init_db()
window = MainWindow(app)
window.pack(fill="both", expand=True)   # درست: MainWindow را pack می‌کنیم

# شروع برنامه
app.mainloop()

# پس‌زمینه: افزایش خودکار urgency
scheduler = BackgroundScheduler()
scheduler.add_job(increase_urgency_for_near_deadlines, "interval", minutes=30)
scheduler.start()