# pip install customtkinter argon2-cffi cryptography tkcalendar matplotlib plyer
import json
import os
import uuid
import secrets
import base64
import shutil
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import customtkinter as ctk
import tkinter.messagebox
import tkinter.simpledialog  # برای fallback اگر لازم باشد
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
ctk.set_default_color_theme("dark-blue")

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
        self.due_date = due_date
        self.tags = tags or []
        self.order = order
        self.completed = completed
        self.completed_date = completed_date

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "urgency": self.urgency, "importance": self.importance,
            "description": self.description, "due_date": self.due_date, "tags": self.tags,
            "order": self.order, "completed": self.completed, "completed_date": self.completed_date
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        return Task(
            data.get("name", ""), data.get("urgency", 3), data.get("importance", 3),
            data.get("description", ""), data.get("due_date"), data.get("tags", []),
            data.get("order", 0), data.get("completed", False), data.get("completed_date"), data.get("id")
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
        self.last_backup: Optional[str] = None
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
        today = datetime.now().strftime("%Y-%m-%d")
        self.last_backup = today
        backup_file = os.path.join(BACKUP_DIR, f"profile_{self.profile}_backup_{today.replace('-', '')}.enc")
        shutil.copy(self.tasks_file, backup_file)

    def load_tasks(self) -> List[Task]:
        if not os.path.exists(self.tasks_file):
            return []
        try:
            with open(self.tasks_file, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
            return [Task.from_dict(t) for t in json.loads(decrypted.decode())]
        except:
            tkinter.messagebox.showerror("Error", "Wrong password or corrupted file.")
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
        self.status_label = None
        self.backup_label = None
        self.undo_stack: List[Dict] = []

        if not self.authenticate_and_start():
            self.root.destroy()
            return

        self.setup_ui()
        self.start_notification_thread()
        self.root.mainloop()

    def select_profile(self) -> str | None:
        dialog = ctk.CTkToplevel()
        dialog.title("Profile Management")
        dialog.geometry("560x680")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="Manage Profiles", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20)

        frame = ctk.CTkScrollableFrame(dialog)
        frame.pack(pady=10, padx=30, fill="both", expand=True)

        profiles = sorted([f[len("profile_"):-len("_config.json")] for f in os.listdir() if f.endswith("_config.json")])

        selected = [None]

        def refresh_list():
            for w in frame.winfo_children():
                w.destroy()
            current = sorted([f[len("profile_"):-len("_config.json")] for f in os.listdir() if f.endswith("_config.json")])
            if not current:
                ctk.CTkLabel(frame, text="No profiles found.", font=ctk.CTkFont(size=14, slant="italic")).pack(pady=100)
                return
            for p in current:
                row = ctk.CTkFrame(frame)
                row.pack(fill="x", pady=6, padx=10)
                ctk.CTkButton(row, text=p, width=320, height=50, font=ctk.CTkFont(size=16),
                              command=lambda n=p: (selected.__setitem__(0, n), dialog.destroy())).pack(side="left", padx=5)
                ctk.CTkButton(row, text="Rename", width=100, command=lambda n=p: rename_profile(n)).pack(side="left", padx=5)
                ctk.CTkButton(row, text="Delete", width=100, fg_color="#c0392b", command=lambda n=p: delete_profile(n)).pack(side="left", padx=5)

        def delete_profile(name):
            if tkinter.messagebox.askyesno("Delete Profile", f"Permanently delete profile '{name}'?"):
                for f in [f"profile_{name}_config.json", f"profile_{name}_tasks.enc"]:
                    if os.path.exists(f):
                        os.remove(f)
                refresh_list()

        def rename_profile(old):
            new = self.input_dialog("Rename Profile", "New name:", old)
            if new and new != old and re.match(r"^[a-zA-Z0-9_-]+$", new) and new not in profiles:
                os.rename(f"profile_{old}_config.json", f"profile_{new}_config.json")
                os.rename(f"profile_{old}_tasks.enc", f"profile_{new}_tasks.enc")
                refresh_list()
            elif new:
                tkinter.messagebox.showerror("Invalid", "Name invalid or already exists.")

        def create_new():
            name = self.input_dialog("New Profile", "Enter profile name:")
            if name and re.match(r"^[a-zA-Z0-9_-]+$", name) and name not in profiles:
                selected[0] = name
                dialog.destroy()
            elif name:
                tkinter.messagebox.showerror("Invalid", "Name contains invalid characters or already exists.")

        refresh_list()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Create New Profile", command=create_new, width=220, height=48, font=ctk.CTkFont(size=16)).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=150, height=48).pack(side="right", padx=20)

        dialog.wait_window()
        return selected[0]

    def input_dialog(self, title: str, prompt: str, default: str = "") -> str | None:
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=prompt, font=ctk.CTkFont(size=16)).pack(pady=20)
        entry = ctk.CTkEntry(dialog, width=300)
        entry.insert(0, default)
        entry.pack(pady=10)
        entry.focus()

        result = [None]
        def ok():
            result[0] = entry.get().strip()
            dialog.destroy()
        ctk.CTkButton(dialog, text="OK", command=ok).pack(pady=10)
        dialog.bind("<Return>", lambda e: ok())
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
            if tkinter.messagebox.askyesno("Reset Data?", "Too many attempts. Reset profile data?"):
                self.storage.reset_data()
                return self.authenticate_and_start()
            return False
        else:
            while True:
                pwd = self.show_password_dialog("Set New Password (min 6 chars)", "Create Password")
                if pwd is None or len(pwd) < 6:
                    if pwd is None:
                        return False
                    tkinter.messagebox.showwarning("Error", "Password must be at least 6 characters.")
                    continue
                confirm = self.show_password_dialog("Confirm Password", "Confirm")
                if pwd != confirm:
                    tkinter.messagebox.showwarning("Error", "Passwords do not match.")
                    continue
                self.storage.unlock(pwd)
                self.storage.save_tasks([])
                return True

    def show_password_dialog(self, label_text: str, title: str) -> str | None:
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.geometry("450x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes("-topmost", True)

        ctk.CTkLabel(dialog, text="🔒", font=ctk.CTkFont(size=70)).pack(pady=(20, 10))
        ctk.CTkLabel(dialog, text=label_text, font=ctk.CTkFont(size=16)).pack(pady=(0, 10))
        ctk.CTkLabel(dialog, text="Minimum 6 characters", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(0, 20))

        entry = ctk.CTkEntry(dialog, width=340, height=50, show="•", font=ctk.CTkFont(size=18))
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
        ctk.CTkButton(btn_frame, text="Cancel", command=cancel, width=140).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="OK", command=ok, width=140).pack(side="right", padx=10)

        dialog.bind("<Return>", lambda e: ok())
        dialog.bind("<Escape>", lambda e: cancel())
        dialog.wait_window()
        return result[0]

    def setup_ui(self):
        self.root.title(f"Eisenhower Matrix Pro - {self.profile}")
        self.root.minsize(1300, 800)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Header
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(pady=20, fill="x", padx=40)
        ctk.CTkLabel(header, text="Eisenhower Matrix 5×5", font=ctk.CTkFont(size=44, weight="bold")).pack(side="left")
        self.progress_label = ctk.CTkLabel(header, text="", font=ctk.CTkFont(size=24))
        self.progress_label.pack(side="right")

        # Toolbar
        toolbar = ctk.CTkFrame(self.root)
        toolbar.pack(fill="x", padx=40, pady=(0, 15))

        left_toolbar = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_toolbar.pack(side="left")

        buttons = [
            ("Add Task", self.add_task, 160),
            ("Toggle Completed", self.toggle_hide_completed, 240),
            ("Export", self.export_tasks, 140),
            ("Import", self.import_tasks, 140),
            ("Restore Backup", self.restore_backup, 180),
            ("Change Password", self.change_password, 200),
            ("Statistics", self.show_statistics, 160),
        ]
        for text, cmd, w in buttons:
            ctk.CTkButton(left_toolbar, text=text, command=cmd, width=w, height=42, font=ctk.CTkFont(size=14)).pack(side="left", padx=7)

        # Filter tab
        filter_tab = ctk.CTkTabview(toolbar)
        filter_tab.pack(side="right", padx=20)
        filter_tab.add("Search & Filters")

        filter_frame = filter_tab.tab("Search & Filters")

        self.search_entry = ctk.CTkEntry(filter_frame, placeholder_text="Search tasks...", width=300, height=42)
        self.search_entry.pack(pady=10, padx=20, fill="x")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_matrix())

        filters_row = ctk.CTkFrame(filter_frame)
        filters_row.pack(pady=10, padx=20, fill="x")

        filter_data = [
            ("Urgency", ["All", "1", "2", "3", "4", "5"]),
            ("Importance", ["All", "1", "2", "3", "4", "5"]),
            ("Tags", ["All"]),
            ("Due Date", ["All", "Today", "This Week", "Overdue"])
        ]
        for label, values in filter_data:
            ctk.CTkLabel(filters_row, text=label + ":", font=ctk.CTkFont(size=13)).grid(row=filter_data.index((label, values)), column=0, padx=10, sticky="e")
            var = ctk.StringVar(value="All")
            self.search_vars[label.lower().replace(" ", "_")] = var
            combo = ctk.CTkComboBox(filters_row, values=values, variable=var, width=150)
            combo.grid(row=filter_data.index((label, values)), column=1, padx=10)
            combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_matrix())
            if label == "Tags":
                self.tag_combo_widget = combo

        ctk.CTkButton(filter_frame, text="Reset Filters", command=self.reset_filters, width=200).pack(pady=10)

        # Matrix
        matrix_container = ctk.CTkFrame(self.root)
        matrix_container.pack(fill="both", expand=True, padx=40, pady=10)
        grid_frame = ctk.CTkFrame(matrix_container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(grid_frame, text="Importance ↓ | Urgency →", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=1, columnspan=5, pady=15)

        for i, text in enumerate(["1 Very Low", "2 Low", "3 Medium", "4 High", "5 Very High"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#2c3e50", text_color="white").grid(row=1, column=i+1, sticky="nsew", padx=5, pady=5)

        for i, text in enumerate(["5 Very High", "4 High", "3 Medium", "2 Low", "1 Very Low"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#2c3e50", text_color="white").grid(row=i+2, column=0, sticky="nsew", padx=5, pady=5)

        colors = {
            (1,5): "#d5f5e3", (2,5): "#a3e4d7", (3,5): "#73c6b6", (4,5): "#48c9b0", (5,5): "#1abc9c",
            (1,4): "#d6eaf8", (2,4): "#a9cce3", (3,4): "#7fb3d5", (4,4): "#5499c7", (5,4): "#2980b9",
            (1,3): "#fef9e7", (2,3): "#fcf3cf", (3,3): "#f9e79f", (4,3): "#f7dc6f", (5,3): "#f4d03f",
            (1,2): "#fadbd8", (2,2): "#f5b7b1", (3,2): "#f1948a", (4,2): "#ec7063", (5,2): "#e74c3c",
            (1,1): "#fadbd8", (2,1): "#f5b7b1", (3,1): "#f1948a", (4,1): "#ec7063", (5,1): "#c0392b",
        }

        for urgency in range(1, 6):
            for importance in range(5, 0, -1):
                cell_color = colors.get((urgency, importance), "#f0f0f0")
                cell = ctk.CTkScrollableFrame(grid_frame, fg_color=cell_color, corner_radius=20, border_width=3, border_color="#bdc3c7" if (urgency, importance) == (5,5) else "transparent")
                cell.grid(row=6-importance+1, column=urgency, padx=12, pady=12, sticky="nsew")
                self.cells[(urgency, importance)] = cell

        for i in range(6):
            grid_frame.grid_columnconfigure(i, weight=1)
            if i > 0:
                grid_frame.grid_rowconfigure(i+1, weight=1)

        self.root.bind("<Control-n>", lambda e: self.add_task())
        self.root.bind("<Control-f>", lambda e: self.search_entry.focus())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<space>", lambda e: self.toggle_selected_completed() if self.selected_task else None)

        # Status bar
        status_frame = ctk.CTkFrame(self.root, height=35, fg_color="transparent")
        status_frame.pack(fill="x", side="bottom", pady=(0, 10))
        self.status_label = ctk.CTkLabel(status_frame, text=f"Profile: {self.profile} | Ready", font=ctk.CTkFont(size=13), text_color="gray60")
        self.status_label.pack(side="left", padx=25)
        self.backup_label = ctk.CTkLabel(status_frame, text="", font=ctk.CTkFont(size=12), text_color="gray70")
        self.backup_label.pack(side="right", padx=25)

        self.refresh_matrix()
        self.update_progress()
        self.update_backup_label()

    def update_progress(self):
        if not self.tasks:
            self.progress_label.configure(text="0% Completed")
            return
        completed_count = sum(1 for t in self.tasks if t.completed)
        percent = int(completed_count / len(self.tasks) * 100)
        self.progress_label.configure(text=f"{percent}% Completed ({completed_count}/{len(self.tasks)})")

    def update_backup_label(self):
        if self.storage.last_backup:
            self.backup_label.configure(text=f"Last backup: {self.storage.last_backup}")
        else:
            self.backup_label.configure(text="No backup yet")

    def reset_filters(self):
        for var in self.search_vars.values():
            var.set("All")
        self.search_entry.delete(0, "end")
        self.refresh_matrix()

    def toggle_hide_completed(self):
        self.storage.hide_completed = not self.storage.hide_completed
        self.storage._save_config()
        self.refresh_matrix()
        self.update_progress()

    def toggle_selected_completed(self):
        if self.selected_task:
            self.toggle_completed(self.selected_task, not self.selected_task.completed)

    def refresh_matrix(self):
        if self.status_label:
            self.status_label.configure(text="Refreshing matrix...")
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
                ctk.CTkLabel(cell, text="Do First!", text_color="#e74c3c", font=ctk.CTkFont(weight="bold", size=14)).pack(anchor="nw", padx=10)

            for task in tasks_here:
                original_color = "#f0f0f0" if task.completed else "#ffffff"
                card = ctk.CTkFrame(cell, fg_color=original_color, corner_radius=12, border_width=2, border_color="#bdc3c7")
                card.pack(fill="x", pady=6, padx=12)

                check_var = ctk.BooleanVar(value=task.completed)
                check = ctk.CTkCheckBox(card, text="", variable=check_var,
                                        command=lambda t=task, v=check_var: self.toggle_completed(t, v.get()))
                check.pack(side="left", padx=10)

                name_text = f"~~{task.name}~~" if task.completed else task.name
                name_label = ctk.CTkLabel(card, text=name_text, font=ctk.CTkFont(size=16, weight="bold" if not task.completed else "normal"), anchor="w")
                name_label.pack(side="left", padx=5)

                info_frame = ctk.CTkFrame(card, fg_color="transparent")
                info_frame.pack(side="right", padx=10)

                if task.due_date:
                    due_date = datetime.fromisoformat(task.due_date).strftime("%Y-%m-%d")
                    due_label = ctk.CTkLabel(info_frame, text=due_date, font=ctk.CTkFont(size=10), text_color="gray50")
                    due_label.pack(anchor="e")
                    if datetime.fromisoformat(task.due_date).date() < datetime.now().date():
                        overdue_label = ctk.CTkLabel(info_frame, text="OVERDUE", text_color="#e74c3c", font=ctk.CTkFont(size=10, weight="bold"))
                        overdue_label.pack(anchor="e")

                if task.tags:
                    tags_str = ", ".join(task.tags)
                    tags_label = ctk.CTkLabel(info_frame, text=tags_str, font=ctk.CTkFont(size=10), text_color="gray60")
                    tags_label.pack(anchor="e")

                if task.description:
                    desc_preview = task.description[:50] + "..." if len(task.description) > 50 else task.description
                    desc_label = ctk.CTkLabel(card, text=desc_preview, font=ctk.CTkFont(size=11, slant="italic"), text_color="gray70", anchor="w", justify="left")
                    desc_label.pack(side="left", padx=5, pady=(5,0), fill="x", expand=True)

                card.bind("<Button-1>", lambda e, t=task: self.select_and_edit(t))
                card.bind("<Button-3>", lambda e, t=task: self.delete_task(t))
                card.bind("<ButtonPress-1>", lambda e, w=card, oc=original_color, c=cell: self.start_drag(w, oc, c))
                card.bind("<ButtonRelease-1>", lambda e: self.drop(e))

                self.task_widgets[task.id] = card

            if not tasks_here:
                placeholder = ctk.CTkLabel(cell, text="Drop tasks here", text_color="gray50", font=ctk.CTkFont(size=14, slant="italic"))
                placeholder.pack(expand=True)

        self.update_progress()
        if self.status_label:
            self.status_label.configure(text=f"Profile: {self.profile} | {len(self.tasks)} tasks")

    def start_drag(self, widget, original_color, cell):
        self.drag_data["widget"] = widget
        self.drag_data["original_color"] = original_color
        self.drag_data["cell"] = cell
        widget.configure(fg_color="#a0a0a0", border_width=4, border_color="#3498db")
        widget.lift()

    def drop(self, event):
        if not self.drag_data["widget"]:
            return
        widget = self.drag_data["widget"]
        widget.configure(fg_color=self.drag_data["original_color"], border_width=2, border_color="#bdc3c7")

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
        dialog.geometry("650x900")
        dialog.transient(self.root)
        dialog.grab_set()

        main_frame = ctk.CTkScrollableFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(main_frame, text="Task Name", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10,5), anchor="w")
        name_entry = ctk.CTkEntry(main_frame, width=550)
        name_entry.insert(0, task.name)
        name_entry.pack(pady=5)

        ctk.CTkLabel(main_frame, text="Description", font=ctk.CTkFont(size=16)).pack(pady=(20,5), anchor="w")
        desc_text = ctk.CTkTextbox(main_frame, width=550, height=120)
        desc_text.insert("1.0", task.description)
        desc_text.pack(pady=5)

        ctk.CTkLabel(main_frame, text="Urgency", font=ctk.CTkFont(size=16)).pack(pady=(20,5), anchor="w")
        urgency_slider = ctk.CTkSlider(main_frame, from_=1, to=5, number_of_steps=4)
        urgency_slider.set(task.urgency)
        urgency_slider.pack(fill="x", pady=5)

        ctk.CTkLabel(main_frame, text="Importance", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w")
        importance_slider = ctk.CTkSlider(main_frame, from_=1, to=5, number_of_steps=4)
        importance_slider.set(task.importance)
        importance_slider.pack(fill="x", pady=5)

        ctk.CTkLabel(main_frame, text="Due Date", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w")
        due_entry = DateEntry(main_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='y-mm-dd')
        if task.due_date:
            due_entry.set_date(task.due_date)
        due_entry.pack(pady=5)

        ctk.CTkLabel(main_frame, text="Tags (comma separated)", font=ctk.CTkFont(size=16)).pack(pady=(15,5), anchor="w")
        tags_entry = ctk.CTkEntry(main_frame, width=550)
        tags_entry.insert(0, ", ".join(task.tags))
        tags_entry.pack(pady=5)

        completed_var = ctk.BooleanVar(value=task.completed)
        ctk.CTkCheckBox(main_frame, text="Completed", variable=completed_var).pack(pady=15, anchor="w")

        def save():
            name = name_entry.get().strip()
            if not name:
                tkinter.messagebox.showerror("Error", "Task name is required.")
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

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Save", command=save, width=200, height=45).pack(side="left", padx=20)
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, width=150, height=45).pack(side="right", padx=20)

    def delete_task(self, task: Task):
        if tkinter.messagebox.askyesno("Delete Task", f"Delete task '{task.name}'?"):
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
            tkinter.messagebox.showerror("Error", "Incorrect current password.")
            return
        new = self.show_password_dialog("Enter new password", "Change Password")
        if len(new) < 6:
            tkinter.messagebox.showwarning("Error", "Password too short.")
            return
        confirm = self.show_password_dialog("Confirm new password", "Change Password")
        if new != confirm:
            tkinter.messagebox.showerror("Error", "Passwords do not match.")
            return
        self.storage.change_password(old, new)
        tkinter.messagebox.showinfo("Success", "Password changed successfully.")

    def export_tasks(self):
        path = ctk.filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
            tkinter.messagebox.showinfo("Export", "Tasks exported successfully.")

    def import_tasks(self):
        path = ctk.filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                imported = [Task.from_dict(d) for d in data]
                self.tasks.extend(imported)
                self.storage.save_tasks(self.tasks)
                self.refresh_matrix()
            tkinter.messagebox.showinfo("Import", "Tasks imported successfully.")

    def restore_backup(self):
        backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith(f"profile_{self.profile}_backup_")]
        if not backups:
            tkinter.messagebox.showinfo("Backup", "No backups found.")
            return
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Select Backup")
        listbox = ctk.CTkScrollableFrame(dialog)
        listbox.pack(padx=20, pady=20, fill="both", expand=True)
        for b in sorted(backups, reverse=True):
            ctk.CTkButton(listbox, text=b, command=lambda bb=b: self.perform_restore(bb, dialog)).pack(fill="x", pady=2)

    def perform_restore(self, backup_name, dialog):
        shutil.copy(os.path.join(BACKUP_DIR, backup_name), self.storage.tasks_file)
        tkinter.messagebox.showinfo("Restore", "Backup restored. Please restart the application.")
        dialog.destroy()

    def show_statistics(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Statistics")
        dialog.geometry("800x650")
        dialog.transient(self.root)
        dialog.grab_set()

        fig, ax = plt.subplots(figsize=(6, 5))
        counts = [len([t for t in self.tasks if t.urgency == u and t.importance == i]) for i in range(5, 0, -1) for u in range(1, 6)]
        labels = [f"U{u}-I{i}" for i in range(5, 0, -1) for u in range(1, 6)]
        ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title("Task Distribution")
        canvas = FigureCanvasTkAgg(fig, dialog)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=20)

        focus = [t for t in self.tasks if t.urgency + t.importance >= 8 or (t.due_date and datetime.fromisoformat(t.due_date).date() <= datetime.now().date())]
        if focus:
            ctk.CTkLabel(dialog, text="Today's Focus:", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=30, pady=(20,5))
            for t in focus:
                ctk.CTkLabel(dialog, text=f"• {t.name}", font=ctk.CTkFont(size=14)).pack(anchor="w", padx=50)

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=20)
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def start_notification_thread(self):
        def notifier():
            last_notified = {}
            while True:
                overdue = [t for t in self.tasks if t.due_date and datetime.fromisoformat(t.due_date).date() < datetime.now().date() and not t.completed]
                for t in overdue:
                    if t.id not in last_notified or (datetime.now() - last_notified[t.id]).total_seconds() > 21600:  # هر 6 ساعت
                        notification.notify(title="Overdue Task", message=t.name, timeout=10)
                        last_notified[t.id] = datetime.now()
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