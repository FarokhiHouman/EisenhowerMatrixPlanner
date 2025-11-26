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