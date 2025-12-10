# pip install customtkinter argon2-cffi cryptography tkcalendar matplotlib plyer
import json
import os
import uuid
import secrets
import base64
import shutil
from typing import List, Dict, Any
from datetime import datetime, timedelta
import customtkinter as ctk
from argon2 import low_level
from cryptography.fernet import Fernet
from cryptography.exceptions import InvalidTag
from tkcalendar import DateEntry
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from plyer import notification
import threading
import time

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

BACKUP_DIR = "backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

class Task:
    def __init__(self, name: str, urgency: int = 3, importance: int = 3, description: str = "", due_date: str = None,
                 tags: List[str] = None, order: int = 0, completed: bool = False, completed_date: str = None, task_id: str = None):
        self.id = task_id or str(uuid.uuid4())
        self.name = name.strip()
        self.urgency = urgency
        self.importance = importance
        self.description = description
        self.due_date = due_date  # ISO format "YYYY-MM-DD"
        self.tags = tags or []
        self.order = order
        self.completed = completed
        self.completed_date = completed_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "urgency": self.urgency,
            "importance": self.importance,
            "description": self.description,
            "due_date": self.due_date,
            "tags": self.tags,
            "order": self.order,
            "completed": self.completed,
            "completed_date": self.completed_date
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        return Task(
            data.get("name", ""),
            data.get("urgency", 3),
            data.get("importance", 3),
            data.get("description", ""),
            data.get("due_date"),
            data.get("tags", []),
            data.get("order", 0),
            data.get("completed", False),
            data.get("completed_date"),
            data.get("id")
        )

class SecureStorage:
    def __init__(self, profile: str):
        self.profile = profile
        self.tasks_file = f"profile_{profile}_tasks.enc"
        self.config_file = f"profile_{profile}_config.json"
        self.fernet = None
        self.salt = None
        self.appearance = "System"
        self.geometry = "1500x900"
        self.hide_completed = False
        self._load_or_create_config()

    def _load_or_create_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.salt = bytes.fromhex(config.get("salt", ""))
                self.appearance = config.get("appearance", "System")
                self.geometry = config.get("geometry", "1500x900")
                self.hide_completed = config.get("hide_completed", False)
        else:
            self.salt = secrets.token_bytes(16)
            self._save_config()

    def _save_config(self):
        config = {
            "salt": self.salt.hex(),
            "appearance": self.appearance,
            "geometry": self.geometry,
            "hide_completed": self.hide_completed
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f)

    def unlock(self, password: str) -> bool:
        try:
            key_material = low_level.hash_secret_raw(
                secret=password.encode(), salt=self.salt,
                time_cost=4, memory_cost=102400, parallelism=8,
                hash_len=32, type=low_level.Type.ID
            )
            key = base64.urlsafe_b64encode(key_material)
            self.fernet = Fernet(key)
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, "rb") as f:
                    encrypted = f.read()
                if encrypted:
                    self.fernet.decrypt(encrypted)
            return True
        except:
            return False

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.unlock(old_password):
            return False
        tasks = self.load_tasks()
        self.salt = secrets.token_bytes(16)
        self.unlock(new_password)
        self.save_tasks(tasks)
        self._save_config()
        return True

    def save_tasks(self, tasks: List[Task]):
        if not self.fernet:
            raise RuntimeError("Storage not unlocked")
        data = json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2)
        encrypted = self.fernet.encrypt(data.encode())
        with open(self.tasks_file, "wb") as f:
            f.write(encrypted)
        today = datetime.now().strftime("%Y%m%d")
        backup_file = os.path.join(BACKUP_DIR, f"profile_{self.profile}_backup_{today}.enc")
        shutil.copy(self.tasks_file, backup_file)

    def load_tasks(self) -> List[Task]:
        if not os.path.exists(self.tasks_file):
            return []
        try:
            with open(self.tasks_file, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
            return [Task.from_dict(t) for t in json.loads(decrypted.decode())]
        except:
            ctk.messagebox.showerror("Error", "Wrong password or corrupted file.")
            return []

    def reset_data(self):
        for file in [self.tasks_file, self.config_file]:
            if os.path.exists(file):
                os.remove(file)

class EisenhowerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.profile = self.select_profile()
        if not self.profile:
            self.root.destroy()
            return
        self.storage = SecureStorage(self.profile)
        self.tasks: List[Task] = []
        self.cells: Dict[tuple, ctk.CTkScrollableFrame] = {}
        self.task_widgets: Dict[str, ctk.CTkFrame] = {}
        self.selected_task: Task | None = None
        self.drag_data = {"widget": None, "cell": None, "original_color": None}
        self.search_vars = {}
        self.all_tags = set()
        self.tag_combo_widget = None

        if not self.authenticate_and_start():
            self.root.destroy()
            return

        self.setup_ui()
        self.start_notification_thread()
        self.root.mainloop()

    def select_profile(self) -> str | None:
        dialog = ctk.CTkToplevel()
        dialog.title("Select or Create Profile")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.grab_set()

        profiles = [f[len("profile_"):-len("_config.json")] for f in os.listdir() if f.endswith("_config.json")]

        var = ctk.StringVar(value=profiles[0] if profiles else "")
        if profiles:
            ctk.CTkOptionMenu(dialog, values=profiles, variable=var).pack(pady=20, padx=40, fill="x")

        entry = ctk.CTkEntry(dialog, placeholder_text="Enter new profile name")
        entry.pack(pady=10, padx=40, fill="x")

        result = [None]
        def ok():
            name = entry.get().strip() or var.get()
            if name:
                result[0] = name
            dialog.destroy()
        ctk.CTkButton(dialog, text="OK", command=ok, width=200).pack(pady=20)
        dialog.wait_window()
        return result[0]

    def authenticate_and_start(self) -> bool:
        ctk.set_appearance_mode(self.storage.appearance)
        self.root.geometry(self.storage.geometry)

        if os.path.exists(self.storage.tasks_file):
            for _ in range(3):
                pwd = self.show_password_dialog("Enter Password", "Login")
                if pwd is None:
                    return False
                if self.storage.unlock(pwd):
                    self.tasks = self.storage.load_tasks()
                    return True
            if ctk.messagebox.askyesno("Reset Data?", "Too many attempts. Reset profile data?"):
                self.storage.reset_data()
                return self.authenticate_and_start()
            return False
        else:
            while True:
                pwd = self.show_password_dialog("Set New Password (min 6 chars)", "Create Password")
                if pwd is None or len(pwd) < 6:
                    if pwd is None:
                        return False
                    ctk.messagebox.showwarning("Error", "Password must be at least 6 characters.")
                    continue
                confirm = self.show_password_dialog("Confirm Password", "Confirm")
                if pwd != confirm:
                    ctk.messagebox.showwarning("Error", "Passwords do not match.")
                    continue
                self.storage.unlock(pwd)
                self.storage.save_tasks([])
                return True

    def show_password_dialog(self, label_text: str, title: str) -> str | None:
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.geometry("420x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="🔒", font=ctk.CTkFont(size=60)).pack(pady=(30, 10))
        ctk.CTkLabel(dialog, text=label_text, font=ctk.CTkFont(size=16)).pack(pady=(0, 20))

        entry = ctk.CTkEntry(dialog, width=320, height=50, show="•", font=ctk.CTkFont(size=18))
        entry.pack(pady=10)
        entry.focus()

        result = [None]
        def ok():
            result[0] = entry.get()
            dialog.destroy()
        def cancel():
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, width=130).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="OK", command=ok, width=130).pack(side="right", padx=10)

        dialog.bind("<Return>", lambda e: ok())
        dialog.bind("<Escape>", lambda e: cancel())
        dialog.wait_window()
        return result[0]

    def setup_ui(self):
        self.root.title(f"Eisenhower Matrix Pro - {self.profile}")
        self.root.minsize(1100, 700)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Header with progress
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(pady=20, fill="x", padx=40)
        self.title_label = ctk.CTkLabel(header, text="Eisenhower Matrix 5×5", font=ctk.CTkFont(size=40, weight="bold"))
        self.title_label.pack(side="left")
        self.progress_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=20))
        self.progress_label.pack(side="right")

        # Toolbar
        toolbar = ctk.CTkFrame(self.root)
        toolbar.pack(fill="x", padx=40, pady=(0, 20))

        ctk.CTkButton(toolbar, text="Add Task", command=self.add_task, width=140).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Toggle Completed Tasks", command=self.toggle_hide_completed, width=200).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Export", command=self.export_tasks, width=120).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Import", command=self.import_tasks, width=120).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Restore Backup", command=self.restore_backup, width=140).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Change Password", command=self.change_password, width=160).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="Statistics", command=self.show_statistics, width=120).pack(side="left", padx=5)

        # Search and filters
        search_frame = ctk.CTkFrame(toolbar)
        search_frame.pack(side="right", padx=10)

        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search tasks...", width=250)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_matrix())

        filter_data = [
            ("Urgency", ["All", "1", "2", "3", "4", "5"]),
            ("Importance", ["All", "1", "2", "3", "4", "5"]),
            ("Tags", ["All"]),
            ("Due Date", ["All", "Today", "This Week", "Overdue"])
        ]
        for label, values in filter_data:
            var = ctk.StringVar(value="All")
            self.search_vars[label.lower().replace(" ", "_")] = var
            combo = ctk.CTkComboBox(search_frame, values=values, variable=var, width=130)
            combo.pack(side="left", padx=3)
            combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_matrix())
            ctk.CTkLabel(search_frame, text=label + ":", font=ctk.CTkFont(size=12)).pack(side="left", padx=2)
            if label == "Tags":
                self.tag_combo_widget = combo

        # Matrix
        matrix_container = ctk.CTkFrame(self.root)
        matrix_container.pack(fill="both", expand=True, padx=40, pady=10)
        grid_frame = ctk.CTkFrame(matrix_container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(grid_frame, text="Importance ↓ | Urgency →", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=1, columnspan=5, pady=10)

        for i, text in enumerate(["1 Very Low", "2 Low", "3 Medium", "4 High", "5 Very High"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#34495e", text_color="white").grid(row=1, column=i+1, sticky="nsew", padx=5, pady=5)

        for i, text in enumerate(["5 Very High", "4 High", "3 Medium", "2 Low", "1 Very Low"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#34495e", text_color="white").grid(row=i+2, column=0, sticky="nsew", padx=5, pady=5)

        colors = {
            (1,5): "#e3fcec", (2,5): "#b5e8cc", (3,5): "#80d6a3", (4,5): "#4db683", (5,5): "#1b9e6c",
            (1,4): "#e8f5e9", (2,4): "#c8e6c9", (3,4): "#a7d8b0", (4,4): "#81c784", (5,4): "#43a047",
            (1,3): "#fffde7", (2,3): "#fff59d", (3,3): "#fff176", (4,3): "#ffee58", (5,3): "#fdd835",
            (1,2): "#fff3e0", (2,2): "#ffccbc", (3,2): "#ffab91", (4,2): "#ff8a65", (5,2): "#ff7043",
            (1,1): "#ffebee", (2,1): "#ffcdd2", (3,1): "#ef9a9a", (4,1): "#e57373", (5,1): "#f44336",
        }

        for urgency in range(1, 6):
            for importance in range(5, 0, -1):
                cell = ctk.CTkScrollableFrame(grid_frame, fg_color=colors.get((urgency, importance), "#f0f0f0"), corner_radius=15, border_width=2)
                cell.grid(row=6-importance+1, column=urgency, padx=10, pady=10, sticky="nsew")
                self.cells[(urgency, importance)] = cell

        for i in range(6):
            grid_frame.grid_columnconfigure(i, weight=1)
            if i > 0:
                grid_frame.grid_rowconfigure(i+1, weight=1)

        self.root.bind("<Control-n>", lambda e: self.add_task())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus())
        self.root.bind("<Delete>", lambda e: self.delete_selected())

        self.refresh_matrix()
        self.update_progress()

    def update_progress(self):
        if not self.tasks:
            self.progress_label.configure(text="0% Completed")
            return
        completed_count = sum(1 for t in self.tasks if t.completed)
        percent = int(completed_count / len(self.tasks) * 100)
        self.progress_label.configure(text=f"{percent}% Completed ({completed_count}/{len(self.tasks)})")

    def toggle_hide_completed(self):
        self.storage.hide_completed = not self.storage.hide_completed
        self.storage._save_config()
        self.refresh_matrix()
        self.update_progress()

    def refresh_matrix(self):
        search_text = self.search_entry.get().lower()
        filters = {k: v.get() for k, v in self.search_vars.items()}

        # Update tags filter
        current_tags = {tag for t in self.tasks for tag in t.tags}
        if self.tag_combo_widget and current_tags != self.all_tags:
            self.all_tags = current_tags
            current = self.search_vars["tags"].get()
            new_values = ["All"] + sorted(self.all_tags)
            self.tag_combo_widget.configure(values=new_values)
            if current not in new_values:
                self.search_vars["tags"].set("All")

        # Clear widgets
        for widget in self.task_widgets.values():
            widget.destroy()
        self.task_widgets.clear()

        for (u, i), cell in self.cells.items():
            for child in cell.winfo_children():
                child.destroy()

            tasks_here = [t for t in self.tasks if t.urgency == u and t.importance == i]
            if self.storage.hide_completed:
                tasks_here = [t for t in tasks_here if not t.completed]

            # Apply filters
            if search_text:
                tasks_here = [t for t in tasks_here if search_text in t.name.lower() or search_text in t.description.lower()]
            if filters.get("urgency", "All") != "All":
                tasks_here = [t for t in tasks_here if t.urgency == int(filters["urgency"])]
            if filters.get("importance", "All") != "All":
                tasks_here = [t for t in tasks_here if t.importance == int(filters["importance"])]
            if filters.get("tags", "All") != "All":
                tasks_here = [t for t in tasks_here if filters["tags"] in t.tags]
            if filters.get("due_date", "All") != "All":
                today = datetime.now().date()
                week_end = today + timedelta(days=7)
                filtered = []
                for t in tasks_here:
                    if not t.due_date:
                        continue
                    due = datetime.fromisoformat(t.due_date).date()
                    if filters["due_date"] == "Today" and due == today:
                        filtered.append(t)
                    elif filters["due_date"] == "This Week" and today <= due <= week_end:
                        filtered.append(t)
                    elif filters["due_date"] == "Overdue" and due < today:
                        filtered.append(t)
                tasks_here = filtered

            tasks_here.sort(key=lambda t: t.order)

            count_label = ctk.CTkLabel(cell, text=f"{len(tasks_here)} task{'s' if len(tasks_here) > 1 else ''}", font=ctk.CTkFont(size=12, weight="bold"))
            count_label.pack(anchor="nw", padx=10, pady=5)

            if u >= 4 and i >= 4:
                ctk.CTkLabel(cell, text="Do First!", text_color="red", font=ctk.CTkFont(weight="bold")).pack(anchor="nw", padx=10)

            for task in tasks_here:
                original_color = "#f0f0f0" if task.completed else "white"
                card = ctk.CTkFrame(cell, fg_color=original_color, corner_radius=10, cursor="hand2")
                card.pack(fill="x", pady=4, padx=10)

                check_var = ctk.BooleanVar(value=task.completed)
                check = ctk.CTkCheckBox(card, text="", variable=check_var,
                                        command=lambda t=task, v=check_var: self.toggle_completed(t, v.get()))
                check.pack(side="left", padx=8)

                name_text = f"~~{task.name}~~" if task.completed else task.name
                name_label = ctk.CTkLabel(card, text=name_text, font=ctk.CTkFont(size=16, weight="normal" if task.completed else "bold"), anchor="w")
                name_label.pack(side="left", padx=5)

                if task.due_date and datetime.fromisoformat(task.due_date).date() < datetime.now().date():
                    ctk.CTkLabel(card, text="OVERDUE", text_color="red").pack(side="right", padx=10)

                if task.tags:
                    tags_str = ", ".join(task.tags[:3])
                    ctk.CTkLabel(card, text=tags_str, text_color="gray50", font=ctk.CTkFont(size=10)).pack(side="right", padx=10)

                card.bind("<Button-1>", lambda e, t=task: self.select_and_edit(t))
                card.bind("<Button-3>", lambda e, t=task: self.delete_task(t))
                card.bind("<ButtonPress-1>", lambda e, w=card, oc=original_color, c=cell: self.start_drag(w, oc, c))
                card.bind("<ButtonRelease-1>", lambda e: self.drop(e))

                self.task_widgets[task.id] = card

            if not tasks_here:
                ctk.CTkLabel(cell, text="Drop tasks here", text_color="gray50", font=ctk.CTkFont(slant="italic")).pack(pady=30)

        self.update_progress()

    def start_drag(self, widget, original_color, cell):
        self.drag_data["widget"] = widget
        self.drag_data["original_color"] = original_color
        self.drag_data["cell"] = cell
        widget.configure(fg_color="#d0d0d0")  # تغییر رنگ برای شبیه‌سازی drag
        widget.lift()

    def drop(self, event):
        if not self.drag_data["widget"]:
            return
        widget = self.drag_data["widget"]
        widget.configure(fg_color=self.drag_data["original_color"])

        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        target = None
        for (u, i), cell in self.cells.items():
            if cell.winfo_rootx() < x < cell.winfo_rootx() + cell.winfo_width() and cell.winfo_rooty() < y < cell.winfo_rooty() + cell.winfo_height():
                target = (u, i, cell)
                break

        if target:
            task = next(t for t in self.tasks if self.task_widgets[t.id] == widget)
            old_u, old_i = task.urgency, task.importance
            task.urgency, task.importance = target[0], target[1]

            if old_u == task.urgency and old_i == task.importance:
                children = [w for w in target[2].winfo_children() if isinstance(w, ctk.CTkFrame)]
                new_index = children.index(widget) if widget in children else len(children)
                tasks_in_cell = [t for t in self.tasks if t.urgency == task.urgency and t.importance == task.importance]
                tasks_in_cell.sort(key=lambda t: t.order)
                for idx, t in enumerate(tasks_in_cell):
                    t.order = idx if t.id != task.id else new_index

            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()

        self.drag_data = {"widget": None, "original_color": None, "cell": None}

    def toggle_completed(self, task: Task, value: bool):
        task.completed = value
        task.completed_date = datetime.now().isoformat() if value else None
        self.storage.save_tasks(self.tasks)
        self.refresh_matrix()

    def add_task(self):
        self.edit_task(Task(""))

    def edit_task(self, task: Task):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Edit Task" if task.name else "New Task")
        dialog.geometry("600x850")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Task Name", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(30,5), anchor="w", padx=50)
        name_entry = ctk.CTkEntry(dialog, width=500)
        name_entry.insert(0, task.name)
        name_entry.pack(pady=5, padx=50)

        ctk.CTkLabel(dialog, text="Description", font=ctk.CTkFont(size=16)).pack(pady=(20,5), anchor="w", padx=50)
        desc_text = ctk.CTkTextbox(dialog, width=500, height=100)
        desc_text.insert("1.0", task.description)
        desc_text.pack(pady=5, padx=50)

        ctk.CTkLabel(dialog, text="Urgency", font=ctk.CTkFont(size=16)).pack(pady=(20,5), anchor="w", padx=50)
        urgency_slider = ctk.CTkSlider(dialog, from_=1, to=5, number_of_steps=4)
        urgency_slider.set(task.urgency)
        urgency_slider.pack(fill="x", padx=50)

        ctk.CTkLabel(dialog, text="Importance", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w", padx=50)
        importance_slider = ctk.CTkSlider(dialog, from_=1, to=5, number_of_steps=4)
        importance_slider.set(task.importance)
        importance_slider.pack(fill="x", padx=50)

        ctk.CTkLabel(dialog, text="Due Date", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w", padx=50)
        due_entry = DateEntry(dialog, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        if task.due_date:
            due_entry.set_date(task.due_date)
        due_entry.pack(pady=5, padx=50)

        ctk.CTkLabel(dialog, text="Tags (comma separated)", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w", padx=50)
        tags_entry = ctk.CTkEntry(dialog, width=500)
        tags_entry.insert(0, ", ".join(task.tags))
        tags_entry.pack(pady=5, padx=50)

        completed_var = ctk.BooleanVar(value=task.completed)
        ctk.CTkCheckBox(dialog, text="Completed", variable=completed_var).pack(pady=10)

        def save():
            name = name_entry.get().strip()
            if not name:
                ctk.messagebox.showerror("Error", "Task name is required.")
                return
            task.name = name
            task.description = desc_text.get("1.0", "end").strip()
            task.urgency = int(urgency_slider.get())
            task.importance = int(importance_slider.get())
            due = due_entry.get_date().strftime("%Y-%m-%d") if due_entry.get() else None
            task.due_date = due
            task.tags = [t.strip() for t in tags_entry.get().split(",") if t.strip()]
            task.completed = completed_var.get()
            task.completed_date = datetime.now().isoformat() if task.completed else task.completed_date

            if task.id not in [t.id for t in self.tasks]:
                max_order = max((t.order for t in self.tasks if t.urgency == task.urgency and t.importance == task.importance), default=-1)
                task.order = max_order + 1
                self.tasks.append(task)

            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save", command=save, width=200, height=40).pack(pady=30)

    def delete_task(self, task: Task):
        if ctk.messagebox.askyesno("Delete Task", f"Delete task '{task.name}'?"):
            self.tasks = [t for t in self.tasks if t.id != task.id]
            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()

    def delete_selected(self):
        if self.selected_task:
            self.delete_task(self.selected_task)

    def select_and_edit(self, task: Task):
        self.selected_task = task
        self.edit_task(task)

    def change_password(self):
        old = self.show_password_dialog("Enter current password", "Change Password")
        if not old or not self.storage.unlock(old):
            ctk.messagebox.showerror("Error", "Incorrect current password.")
            return
        new = self.show_password_dialog("Enter new password", "Change Password")
        if len(new) < 6:
            ctk.messagebox.showwarning("Error", "Password too short.")
            return
        confirm = self.show_password_dialog("Confirm new password", "Change Password")
        if new != confirm:
            ctk.messagebox.showerror("Error", "Passwords do not match.")
            return
        self.storage.change_password(old, new)
        ctk.messagebox.showinfo("Success", "Password changed successfully.")

    def export_tasks(self):
        path = ctk.filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
            ctk.messagebox.showinfo("Export", "Tasks exported successfully.")

    def import_tasks(self):
        path = ctk.filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                imported = [Task.from_dict(d) for d in data]
                self.tasks.extend(imported)
                self.storage.save_tasks(self.tasks)
                self.refresh_matrix()
            ctk.messagebox.showinfo("Import", "Tasks imported successfully.")

    def restore_backup(self):
        backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith(f"profile_{self.profile}_backup_")]
        if not backups:
            ctk.messagebox.showinfo("Backup", "No backups found.")
            return
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Backup")
        listbox = ctk.CTkScrollableFrame(dialog)
        listbox.pack(padx=20, pady=20, fill="both", expand=True)
        for b in sorted(backups, reverse=True):
            ctk.CTkButton(listbox, text=b, command=lambda bb=b: self.perform_restore(bb, dialog)).pack(fill="x", pady=2)

    def perform_restore(self, backup_name, dialog):
        shutil.copy(os.path.join(BACKUP_DIR, backup_name), self.storage.tasks_file)
        ctk.messagebox.showinfo("Restore", "Backup restored. Please restart the application.")
        dialog.destroy()

    def show_statistics(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Statistics")
        dialog.geometry("800x600")

        fig, ax = plt.subplots(figsize=(6, 5))
        counts = [len([t for t in self.tasks if t.urgency == u and t.importance == i]) for i in range(5, 0, -1) for u in range(1, 6)]
        labels = [f"U{u}-I{i}" for i in range(5, 0, -1) for u in range(1, 6)]
        ax.pie(counts, labels=labels, autopct='%1.1f%%')
        ax.set_title("Task Distribution")
        canvas = FigureCanvasTkAgg(fig, dialog)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20)

        focus = [t for t in self.tasks if t.urgency + t.importance >= 8 or (t.due_date and datetime.fromisoformat(t.due_date).date() <= datetime.now().date())]
        if focus:
            ctk.CTkLabel(dialog, text="Today's Focus:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20)
            for t in focus:
                ctk.CTkLabel(dialog, text=f"• {t.name}").pack(anchor="w", padx=40)

    def start_notification_thread(self):
        def notifier():
            while True:
                overdue = [t for t in self.tasks if t.due_date and datetime.fromisoformat(t.due_date).date() < datetime.now().date() and not t.completed]
                for t in overdue:
                    notification.notify(title="Overdue Task", message=t.name, timeout=10)
                time.sleep(3600)
        threading.Thread(target=notifier, daemon=True).start()

    def on_closing(self):
        self.storage.geometry = f"{self.root.winfo_width()}x{self.root.winfo_height()}"
        self.storage.appearance = ctk.get_appearance_mode()
        self.storage._save_config()
        self.storage.save_tasks(self.tasks)
        self.root.destroy()

if __name__ == "__main__":
    EisenhowerApp()