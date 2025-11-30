import json
import os
import uuid
import secrets
import base64
import shutil
from tkinter import *
from tkinter import ttk, messagebox, simpledialog
from argon2 import low_level
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidTag
from typing import List, Dict, Any

# ====================== تنظیمات امنیتی ======================
TASKS_FILE = "tasks.eisen.enc"
CONFIG_FILE = "config.json"

# ====================== مدل تسک ======================
class Task:
    def __init__(self, name: str, urgency: int = 3, importance: int = 3, task_id: str = None):
        self.id = task_id or str(uuid.uuid4())
        self.name = name.strip()
        self.urgency = urgency
        self.importance = importance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "urgency": self.urgency,
            "importance": self.importance
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        return Task(data["name"], data["urgency"], data["importance"], data["id"])

# ====================== مدیریت رمزنگاری و ذخیره‌سازی ======================
class SecureStorage:
    def __init__(self):
        self.fernet: Fernet | None = None
        self.salt: bytes | None = None
        self._load_or_create_config()

    def _load_or_create_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.salt = bytes.fromhex(config["salt"])
        else:
            self.salt = secrets.token_bytes(16)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"salt": self.salt.hex()}, f)

    def unlock(self, password: str) -> bool:
        try:
            key_material = low_level.hash_secret_raw(
                secret=password.encode(),
                salt=self.salt,
                time_cost=4,
                memory_cost=102400,
                parallelism=8,
                hash_len=32,
                type=low_level.Type.ID
            )
            key = base64.urlsafe_b64encode(key_material)
            self.fernet = Fernet(key)
            if os.path.exists(TASKS_FILE):
                with open(TASKS_FILE, "rb") as f:
                    encrypted_data = f.read()
                if encrypted_data:
                    self.fernet.decrypt(encrypted_data)
            return True
        except (InvalidToken, Exception):
            return False

    def save_tasks(self, tasks: List[Task]) -> None:
        if not self.fernet:
            raise RuntimeError("Storage not unlocked")
        data = json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2)
        encrypted = self.fernet.encrypt(data.encode("utf-8"))
        with open(TASKS_FILE, "wb") as f:
            f.write(encrypted)

    def load_tasks(self) -> List[Task]:
        if not os.path.exists(TASKS_FILE):
            return []
        if not self.fernet:
            raise RuntimeError("Storage not unlocked")
        try:
            with open(TASKS_FILE, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
            tasks_data = json.loads(decrypted.decode("utf-8"))
            return [Task.from_dict(t) for t in tasks_data]
        except (InvalidTag, InvalidToken, json.JSONDecodeError):
            messagebox.showerror("خطا", "رمز عبور اشتباه یا فایل خراب است.")
            return []

# ====================== بقیه کد ======================
class EisenhowerApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("Eisenhower Matrix 5×5 - Secure & Professional")
        self.root.geometry("1400x900")
        self.root.minsize(1000, 700)
        self.root.configure(bg="#f8f9fa")
        self.storage = SecureStorage()
        self.tasks: List[Task] = []
        self.cells: Dict[tuple, Frame] = {}
        self.task_labels: Dict[str, Label] = {}
        self.drag_task = None
        self.authenticate_and_start()


    def on_task_press(self, event, task: Task):
        # ذخیره موقعیت کلیک و زمان
        self.drag_task = task
        self.click_x = event.x_root
        self.click_y = event.y_root
        self.click_time = event.time
        # برای جلوگیری از تداخل، cursor رو فعلاً تغییر نده

    def on_task_release(self, event, task: Task):
        # اگر ماوس خیلی کم حرکت کرده و زمان کم گذشته → کلیک ساده است → ادیت
        dx = abs(event.x_root - self.click_x)
        dy = abs(event.y_root - self.click_y)
        dt = event.time - self.click_time

        if dx < 8 and dy < 8 and dt < 400:  # کلیک ساده (کمتر از ۴۰۰ میلی‌ثانیه و ۸ پیکسل)
            self.edit_task(task)

        # ریست کردن برای درگ بعدی
        self.drag_task = None

    def on_task_drag(self, event):
        if not self.drag_task:
            return
        # اگر واقعاً درگ شد، نشانگر عوض شود
        event.widget.config(cursor="fleur")


    def on_drop(self, event):
        if not self.drag_task:
            return

        dropped = False
        for (u, i), frame in self.cells.items():
            widget_under = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget_under and (widget_under == frame or widget_under.winfo_parent() == str(frame)):
                self.drag_task.urgency = u
                self.drag_task.importance = i
                dropped = True
                break

        if dropped:
            self.save_tasks()
            self.refresh_matrix()

        self.drag_task = None
        event.widget.config(cursor="hand2")
    def authenticate_and_start(self):
        if os.path.exists(TASKS_FILE):
            for _ in range(3):
                password = simpledialog.askstring("رمز عبور", "رمز عبور را وارد کنید:", show='*')
                if password is None:
                    exit()
                if self.authenticate(password):
                    self.setup_ui()
                    return
            messagebox.showerror("خطا", "رمز عبور اشتباه است. برنامه بسته می‌شود.")
            exit()
        else:
            password = simpledialog.askstring("ایجاد رمز عبور", "رمز عبور جدید تنظیم کنید (حداقل ۶ کاراکتر):", show='*')
            if not password or len(password) < 6:
                messagebox.showerror("خطا", "رمز عبور باید حداقل ۶ کاراکتر باشد.")
                exit()
            confirm = simpledialog.askstring("تأیید رمز", "رمز عبور را دوباره وارد کنید:", show='*')
            if password != confirm:
                messagebox.showerror("خطا", "رمز عبورها یکسان نیستند.")
                exit()
            if self.authenticate(password):
                self.setup_ui()

    def authenticate(self, password: str) -> bool:
        if self.storage.unlock(password):
            self.tasks = self.storage.load_tasks()
            return True
        return False

    def setup_ui(self):
        Label(self.root, text="Eisenhower Matrix 5×5", font=("Segoe UI", 28, "bold"), bg="#f8f9fa", fg="#2d3436").pack(pady=(20, 5))
        Label(self.root, text="Drag & Drop • Left Click: Edit • Right Click: Delete • Hover: Tooltip", font=("Segoe UI", 10), bg="#f8f9fa", fg="#636e72").pack(pady=(0, 15))

        toolbar = Frame(self.root, bg="#f8f9fa")
        toolbar.pack(pady=10)
        ttk.Button(toolbar, text=" Add Task ", command=self.add_task).pack(side=LEFT, padx=8)
        ttk.Button(toolbar, text=" Clear All ", command=self.clear_all).pack(side=LEFT, padx=8)
        ttk.Button(toolbar, text=" Change Password ", command=self.change_password).pack(side=LEFT, padx=8)

        search_frame = Frame(self.root, bg="#f8f9fa")
        search_frame.pack(pady=10)
        Label(search_frame, text="جستجو:", bg="#f8f9fa", anchor="e").pack(side=LEFT)
        self.search_var = StringVar()
        self.search_var.trace("w", lambda *_: self.refresh_matrix())
        ttk.Entry(search_frame, textvariable=self.search_var, width=40).pack(side=LEFT, padx=10)

        self.matrix_frame = Frame(self.root, bg="#f8f9fa")
        self.matrix_frame.pack(padx=40, pady=30, fill="both", expand=True)
        self.build_matrix_grid()
        self.refresh_matrix()

    def get_pastel_color(self, i: int, u: int) -> str:
        s = i + u
        return ["#b2dfdb","#c8e6c9","#dcedc8","#ffbbbb","#ff9e9e","#ff8a80","#ff6b6b","#ff5252"][min(s-2,7)]

    def build_matrix_grid(self):
        Label(self.matrix_frame, text="Eisenhower Matrix", font=("Segoe UI", 18, "bold"), bg="#f8f9fa", fg="#2d3436").grid(row=0, column=0, columnspan=7, pady=20)
        Label(self.matrix_frame, text="Importance ↓\nUrgency →", bg="#2d3436", fg="white", font=("Segoe UI", 11, "bold")).grid(row=1, column=0, sticky="nsew")
        for c, t in enumerate(["1 Not Urgent","2 Low","3 Medium","4 Urgent","5 Very Urgent"], 1):
            Label(self.matrix_frame, text=t, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold")).grid(row=1, column=c, sticky="nsew")
        for r, t in enumerate(["5 Very Imp.","4 Imp.","3 Med.","2 Low","1 Not Imp."], 2):
            Label(self.matrix_frame, text=t, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="nsew")
        for u in range(1,6):
            for i in range(5,0,-1):
                cell = Frame(self.matrix_frame, bg=self.get_pastel_color(i,u), highlightbackground="#dfe6e9", highlightthickness=2)
                cell.grid(row=7-i, column=u, padx=8, pady=8, sticky="nsew")
                canvas_cell = Canvas(cell, bg=cell["bg"], highlightthickness=0)
                scroll = ttk.Scrollbar(cell, orient="vertical", command=canvas_cell.yview)
                inner = Frame(canvas_cell, bg=cell["bg"])
                canvas_cell.create_window((0,0), window=inner, anchor="nw")
                canvas_cell.configure(yscrollcommand=scroll.set)
                canvas_cell.pack(side="left", fill="both", expand=True)
                scroll.pack(side="right", fill="y")
                inner.bind("<Configure>", lambda e, c=canvas_cell: c.configure(scrollregion=c.bbox("all")))
                inner.bind("<Configure>", lambda e, inn=inner: self.update_wraplengths(inn))
                self.cells[(u, i)] = inner
        for j in range(7):
            self.matrix_frame.grid_columnconfigure(j, weight=1)
        for j in range(1,7):
            self.matrix_frame.grid_rowconfigure(j, weight=1)

    def update_wraplengths(self, inner):
        width = inner.winfo_width() - 20
        for child in inner.winfo_children():
            if isinstance(child, Label) and child.cget("text").startswith("• "):
                child.config(wraplength=max(100, width))
    def on_drop(self, event):
        if not self.drag_task:
            return

        dropped = False
        for (u, i), frame in self.cells.items():
            widget_under = event.widget.winfo_containing(event.x_root, event.y_root)
            if widget_under and (widget_under == frame or str(widget_under.master) == str(frame)):
                self.drag_task.urgency = u
                self.drag_task.importance = i
                dropped = True
                break

        if dropped:
            self.save_tasks()
            self.refresh_matrix()

        self.drag_task = None
        event.widget.config(cursor="hand2")

    def refresh_matrix(self):
        search = self.search_var.get().lower()

        # پاک کردن لیبل‌های قبلی
        for lbl in list(self.task_labels.values()):
            lbl.destroy()
        self.task_labels.clear()

        for (u, i), frame in self.cells.items():
            for w in list(frame.winfo_children()):
                w.destroy()

            tasks_here = [t for t in self.tasks
                          if t.urgency == u and t.importance == i
                          and (not search or search in t.name.lower() or search in t.id.lower())]

            if not tasks_here:
                Label(frame, text="Drop tasks here", bg=frame["bg"], fg="#95a5a6",
                      font=("Segoe UI", 11, "italic")).pack(pady=30)
            else:
                Label(frame, text=f"{len(tasks_here)} task{'s' if len(tasks_here) > 1 else ''}",
                      bg=frame["bg"], fg="#2d3436", font=("Segoe UI", 9, "bold")
                      ).pack(anchor="nw", padx=8, pady=(8, 4))

                for task in tasks_here:
                    lbl = Label(
                        frame,
                        text="• " + task.name,
                        bg=frame["bg"],
                        fg="#2d3436",
                        font=("Segoe UI", 10),
                        anchor="e",
                        justify="right",
                        cursor="hand2"
                    )
                    lbl.pack(anchor="e", padx=10, pady=1, fill="x")

                    # کلیک ساده → ویرایش
                    lbl.bind("<ButtonPress-1>", lambda e, t=task: self.on_task_press(e, t))
                    lbl.bind("<ButtonRelease-1>", lambda e, t=task: self.on_task_release(e, t))
                    lbl.bind("<B1-Motion>", lambda e: self.on_task_drag(e))

                    # کلیک راست → حذف
                    lbl.bind("<Button-3>", lambda e, t=task: self.delete_task(t))

                    ToolTip(lbl, "کلیک: ویرایش • کلیک راست: حذف • بکشید: جابجایی")
                    self.task_labels[task.id] = lbl

        # بروزرسانی wraplength بعد از رندر شدن ویجت‌ها
        self.root.after(100, self._update_all_wraplengths)

    def _update_all_wraplengths(self):
        for inner in self.cells.values():
            self.update_wraplengths(inner)


    def add_task(self):
        self.edit_task(Task("", 3, 3))

    def edit_task(self, task: Task):
        modal = Toplevel(self.root)
        modal.title("New Task" if not task.name else "Edit Task")
        modal.geometry("440x560")
        modal.configure(bg="#f8f9fa")
        modal.transient(self.root)
        modal.grab_set()
        Label(modal, text="Task Name", bg="#f8f9fa", font=("Segoe UI", 11), anchor="w").pack(anchor="w", padx=50, pady=(40,5))
        name_entry = ttk.Entry(modal, font=("Segoe UI", 12), width=40)
        name_entry.insert(0, task.name)
        name_entry.pack(pady=10, padx=50)
        name_entry.focus()
        Label(modal, text="Urgency", bg="#f8f9fa", fg="#e74c3c", font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w", padx=50, pady=(30,5))
        uv = IntVar(value=task.urgency)
        ttk.Scale(modal, from_=1, to=5, variable=uv, length=320).pack(padx=50)
        Label(modal, text="Not Urgent ← → Very Urgent", fg="#7f8c8d", bg="#f8f9fa").pack()
        Label(modal, text="Importance", bg="#f8f9fa", fg="#27ae60", font=("Segoe UI", 11, "bold"), anchor="w").pack(anchor="w", padx=50, pady=(30,5))
        iv = IntVar(value=task.importance)
        ttk.Scale(modal, from_=1, to=5, variable=iv, length=320).pack(padx=50)
        Label(modal, text="Not Important ← → Very Important", fg="#7f8c8d", bg="#f8f9fa").pack()
        def save():
            n = name_entry.get().strip()
            if not n:
                messagebox.showerror("خطا", "نام تسک نمی‌تواند خالی باشد!")
                return
            if any(t.name.lower() == n.lower() for t in self.tasks if t.id != task.id):
                messagebox.showerror("خطا", "نام تسک تکراری است!")
                return
            task.name = n
            task.urgency = uv.get()
            task.importance = iv.get()
            if task.id not in [t.id for t in self.tasks]:
                self.tasks.append(task)
            self.save_tasks()
            modal.destroy()
            self.refresh_matrix()
        btns = Frame(modal, bg="#f8f9fa")
        btns.pack(pady=40)
        ttk.Button(btns, text="Cancel", command=modal.destroy).pack(side=LEFT, padx=20)
        ttk.Button(btns, text="Save", command=save).pack(side=LEFT, padx=20)
        modal.bind("<Return>", lambda e: save())
        modal.bind("<Escape>", lambda e: modal.destroy())

    def delete_task(self, task: Task):
        if messagebox.askyesno("حذف", f"حذف «{task.name}»؟"):
            self.tasks = [t for t in self.tasks if t.id != task.id]
            self.save_tasks()
            self.refresh_matrix()

    def clear_all(self):
        if messagebox.askyesno("همه را پاک کن", "همه تسک‌ها حذف شوند؟"):
            self.tasks.clear()
            self.save_tasks()
            self.refresh_matrix()

    def change_password(self):
        old = simpledialog.askstring("رمز فعلی", "رمز عبور فعلی:", show='*')
        if not self.authenticate(old):
            messagebox.showerror("خطا", "رمز فعلی اشتباه است.")
            return
        new = simpledialog.askstring("رمز جدید", "رمز جدید (حداقل ۶ کاراکتر):", show='*')
        if not new or len(new) < 6:
            messagebox.showerror("خطا", "رمز جدید معتبر نیست.")
            return
        confirm = simpledialog.askstring("تأیید", "تکرار رمز جدید:", show='*')
        if new != confirm:
            messagebox.showerror("خطا", "رمز جدید مطابقت ندارد.")
            return
        # پشتیبان‌گیری
        if os.path.exists(TASKS_FILE):
            shutil.copy(TASKS_FILE, TASKS_FILE + ".bak")
        old_salt = self.storage.salt
        self.storage.salt = secrets.token_bytes(16)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"salt": self.storage.salt.hex()}, f)
        if self.storage.unlock(new):
            try:
                self.storage.save_tasks(self.tasks)
                messagebox.showinfo("موفق", "رمز عبور تغییر کرد.")
            except Exception as e:
                # بازگردانی در صورت شکست
                self.storage.salt = old_salt
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump({"salt": self.storage.salt.hex()}, f)
                self.storage.unlock(old)
                messagebox.showerror("خطا", f"خطا در تغییر رمز: {e}. رمز قبلی بازگردانده شد.")
        else:
            self.storage.salt = old_salt
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"salt": self.storage.salt.hex()}, f)
            messagebox.showerror("خطا", "خطا در باز کردن با رمز جدید.")

    def save_tasks(self):
        try:
            self.storage.save_tasks(self.tasks)
        except (RuntimeError, ValueError, OSError) as e:
            messagebox.showerror("خطا", f"خطا در ذخیره: {e}")

class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tip:
            return
        x, y = self.widget.winfo_rootx() + 25, self.widget.winfo_rooty() + 25
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        Label(self.tip, text=self.text, bg="#ffffe0", relief="solid", borderwidth=1, font=("Segoe UI", 9), padx=8, pady=4).pack()

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

if __name__ == "__main__":
    try:
        from argon2 import low_level
    except ImportError:
        print("Please install argon2-cffi: pip install argon2-cffi")
        exit()
    root = Tk()
    app = EisenhowerApp(root)
    root.mainloop()