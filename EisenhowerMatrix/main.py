# pip install customtkinter argon2-cffi cryptography
import json
import os
import uuid
import secrets
import base64
import shutil
from typing import List, Dict, Any
import customtkinter as ctk
from argon2 import low_level
from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidTag

# Appearance settings
ctk.set_appearance_mode("System")  # "Dark", "Light", "System"
ctk.set_default_color_theme("blue")

TASKS_FILE = "tasks.eisen.enc"
CONFIG_FILE = "config.json"


class Task:
    def __init__(self, name: str, urgency: int = 3, importance: int = 3, task_id: str = None):
        self.id = task_id or str(uuid.uuid4())
        self.name = name.strip()
        self.urgency = urgency
        self.importance = importance

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "urgency": self.urgency, "importance": self.importance}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        return Task(data["name"], data["urgency"], data["importance"], data["id"])


class SecureStorage:
    def __init__(self):
        self.fernet = None
        self.salt = None
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
                    encrypted = f.read()
                if encrypted:
                    self.fernet.decrypt(encrypted)
            return True
        except:
            return False

    def save_tasks(self, tasks: List[Task]):
        if not self.fernet:
            raise RuntimeError("Storage not unlocked")
        data = json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2)
        encrypted = self.fernet.encrypt(data.encode())
        with open(TASKS_FILE, "wb") as f:
            f.write(encrypted)

    def load_tasks(self) -> List[Task]:
        if not os.path.exists(TASKS_FILE):
            return []
        try:
            with open(TASKS_FILE, "rb") as f:
                decrypted = self.fernet.decrypt(f.read())
            return [Task.from_dict(t) for t in json.loads(decrypted.decode())]
        except:
            ctk.CTkMessagebox(title="Error", message="Wrong password or file corrupted.", icon="cancel")
            return []


class EisenhowerApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Eisenhower Matrix Pro")
        self.root.geometry("1500x900")
        self.root.minsize(1100, 700)

        self.storage = SecureStorage()
        self.tasks: List[Task] = []
        self.cells: Dict[tuple, ctk.CTkScrollableFrame] = {}
        self.task_widgets: Dict[str, ctk.CTkFrame] = {}
        self.search_entry = None

        self.drag_data = {"task": None, "widget": None, "offset_x": 0, "offset_y": 0}

        if not self.authenticate_and_start():
            return

        self.setup_ui()
        self.root.mainloop()

    def authenticate_and_start(self) -> bool:
        if os.path.exists(TASKS_FILE):
            for _ in range(3):
                pwd = self.show_password_dialog("Enter Password", "Login to Eisenhower Matrix")
                if pwd is None:
                    return False
                if self.storage.unlock(pwd):
                    self.tasks = self.storage.load_tasks()
                    return True
            ctk.CTkMessagebox(title="Error", message="Incorrect password. Access denied.", icon="cancel")
            return False
        else:
            while True:
                pwd = self.show_password_dialog("Set New Password (min 6 chars)", "Create Password")
                if pwd is None:
                    return False
                if len(pwd) < 6:
                    ctk.CTkMessagebox(title="Error", message="Password must be at least 6 characters.", icon="warning")
                    continue
                confirm = self.show_password_dialog("Confirm Password", "Confirm")
                if pwd != confirm:
                    ctk.CTkMessagebox(title="Error", message="Passwords do not match.", icon="warning")
                    continue
                if self.storage.unlock(pwd):
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

        ctk.CTkLabel(dialog, text="lock", font=ctk.CTkFont(size=60)).pack(pady=(30,10))
        ctk.CTkLabel(dialog, text=label_text, font=ctk.CTkFont(size=16)).pack(pady=(0,20))

        entry = ctk.CTkEntry(dialog, width=320, height=50, show="•", font=ctk.CTkFont(size=18), corner_radius=15)
        entry.pack(pady=10)
        entry.focus()

        result = None

        def ok():
            nonlocal result
            result = entry.get()
            dialog.destroy()

        def cancel():
            nonlocal result
            result = None
            dialog.destroy()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(btn_frame, text="Cancel", width=130, command=cancel, fg_color="gray30").pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="OK", width=130, command=ok, fg_color="#1f6aa5").pack(side="right", padx=15)

        dialog.bind("<Return>", lambda e: ok())
        dialog.bind("<Escape>", lambda e: cancel())

        dialog.wait_window()
        return result

    def setup_ui(self):
        # Header
        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.pack(pady=20, fill="x", padx=40)

        ctk.CTkLabel(header, text="Eisenhower Matrix 5×5", font=ctk.CTkFont(size=40, weight="bold")).pack()
        ctk.CTkLabel(header, text="Left Click: Edit • Right Click: Delete • Drag & Drop: Move",
                     font=ctk.CTkFont(size=15), text_color="gray60").pack(pady=(8,0))

        # Toolbar
        toolbar = ctk.CTkFrame(self.root)
        toolbar.pack(fill="x", padx=40, pady=(0,20))

        ctk.CTkButton(toolbar, text="Add Task", width=200, height=50,
                      command=self.add_task, font=ctk.CTkFont(size=16), corner_radius=12).pack(side="left", padx=12, pady=10)
        ctk.CTkButton(toolbar, text="Clear All", width=160, height=50,
                      command=self.clear_all, corner_radius=12).pack(side="left", padx=8, pady=10)
        ctk.CTkButton(toolbar, text="Change Password", width=180, height=50,
                      command=self.change_password, corner_radius=12).pack(side="left", padx=8, pady=10)

        self.search_entry = ctk.CTkEntry(toolbar, placeholder_text="Search tasks...", width=400, height=50,
                                         font=ctk.CTkFont(size=16), corner_radius=12)
        self.search_entry.pack(side="right", padx=20, pady=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_matrix())

        # Matrix container
        matrix_container = ctk.CTkFrame(self.root)
        matrix_container.pack(fill="both", expand=True, padx=40, pady=10)

        grid_frame = ctk.CTkFrame(matrix_container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        ctk.CTkLabel(grid_frame, text="Importance ↓    |    Urgency →", font=ctk.CTkFont(size=18, weight="bold"),
                     fg_color="#2c3e50", text_color="white", corner_radius=10, pady=15
                     ).grid(row=0, column=1, columnspan=5, sticky="ew", pady=(0,15))

        # Urgency headers
        for i, text in enumerate(["1 Very Low", "2 Low", "3 Medium", "4 High", "5 Very High"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"),
                         fg_color="#34495e", text_color="white", corner_radius=8).grid(row=1, column=i+1, sticky="nsew", padx=5, pady=5)

        # Importance headers
        for i, text in enumerate(["5 Very High", "4 High", "3 Medium", "2 Low", "1 Very Low"]):
            ctk.CTkLabel(grid_frame, text=text, font=ctk.CTkFont(size=13, weight="bold"),
                         fg_color="#34495e", text_color="white", corner_radius=8).grid(row=i+2, column=0, sticky="nsew", padx=5, pady=5)

        # Colors
        colors = {
            (1,5): "#e3fcec", (2,5): "#b5e8cc", (3,5): "#80d6a3", (4,5): "#4db683", (5,5): "#1b9e6c",
            (1,4): "#e8f5e9", (2,4): "#c8e6c9", (3,4): "#a7d8b0", (4,4): "#81c784", (5,4): "#43a047",
            (1,3): "#fffde7", (2,3): "#fff59d", (3,3): "#fff176", (4,3): "#ffee58", (5,3): "#fdd835",
            (1,2): "#fff3e0", (2,2): "#ffccbc", (3,2): "#ffab91", (4,2): "#ff8a65", (5,2): "#ff7043",
            (1,1): "#ffebee", (2,1): "#ffcdd2", (3,1): "#ef9a9a", (4,1): "#e57373", (5,1): "#f44336",
        }

        # Create cells
        for urgency in range(1, 6):
            for importance in range(5, 0, -1):
                cell = ctk.CTkScrollableFrame(grid_frame, fg_color=colors.get((urgency, importance), "#f0f0f0"),
                                             corner_radius=15, border_width=2, border_color="#bdc3c7")
                cell.grid(row=6-importance+1, column=urgency, padx=10, pady=10, sticky="nsew")
                self.cells[(urgency, importance)] = cell

        for i in range(6):
            grid_frame.grid_columnconfigure(i, weight=1)
            if i > 0:
                grid_frame.grid_rowconfigure(i+1, weight=1)

        self.refresh_matrix()

    def refresh_matrix(self):
        search_text = self.search_entry.get().lower() if self.search_entry else ""

        for widget in self.task_widgets.values():
            widget.destroy()
        self.task_widgets.clear()

        for (u, i), cell in self.cells.items():
            for w in cell.winfo_children():
                w.destroy()

            tasks_here = [t for t in self.tasks
                          if t.urgency == u and t.importance == i
                          and (not search_text or search_text in t.name.lower())]

            if not tasks_here:
                ctk.CTkLabel(cell, text="Drop tasks here", text_color="gray50",
                             font=ctk.CTkFont(size=15, slant="italic")).pack(pady=30)
            else:
                ctk.CTkLabel(cell, text=f"{len(tasks_here)} task{'s' if len(tasks_here)>1 else ''}",
                             font=ctk.CTkFont(size=12, weight="bold"), text_color="#2c3e50"
                             ).pack(anchor="nw", padx=15, pady=(15,5))

                for task in tasks_here:
                    card = ctk.CTkFrame(cell, fg_color="white", corner_radius=14, cursor="hand2")
                    card.pack(pady=8, padx=15, fill="x", ipady=12)

                    ctk.CTkLabel(card, text=task.name, font=ctk.CTkFont(size=16, weight="bold"),
                                 text_color="#2c3e50", anchor="w", padx=20).pack(fill="x")

                    card.bind("<Button-1>", lambda e, t=task: self.edit_task(t))
                    card.bind("<Button-3>", lambda e, t=task: self.delete_task(t))
                    card.bind("<ButtonPress-1>", lambda e, w=card, t=task: self.start_drag(e, w, t))
                    card.bind("<B1-Motion>", self.do_drag)
                    card.bind("<ButtonRelease-1>", self.drop)

                    card.bind("<Enter>", lambda e, c=card: c.configure(fg_color="#f0f8ff"))
                    card.bind("<Leave>", lambda e, c=card: c.configure(fg_color="white"))

                    self.task_widgets[task.id] = card

    def start_drag(self, event, widget, task):
        self.drag_data["task"] = task
        self.drag_data["widget"] = widget
        self.drag_data["offset_x"] = event.x
        self.drag_data["offset_y"] = event.y
        widget.lift()

    def do_drag(self, event):
        if self.drag_data["widget"]:
            x = self.root.winfo_pointerx() - self.drag_data["offset_x"]
            y = self.root.winfo_pointery() - self.drag_data["offset_y"]
            self.drag_data["widget"].place(x=x, y=y)

    def drop(self, event):
        if not self.drag_data["task"]:
            return

        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        for (u, i), cell in self.cells.items():
            if (cell.winfo_rootx() < x < cell.winfo_rootx() + cell.winfo_width() and
                cell.winfo_rooty() < y < cell.winfo_rooty() + cell.winfo_height()):
                self.drag_data["task"].urgency = u
                self.drag_data["task"].importance = i
                self.storage.save_tasks(self.tasks)
                self.refresh_matrix()
                break

        if self.drag_data["widget"]:
            self.drag_data["widget"].place_forget()
        self.drag_data = {"task": None, "widget": None}

    def add_task(self):
        self.edit_task(Task(""))

    def edit_task(self, task: Task):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Edit Task" if task.name else "New Task")
        dialog.geometry("520x620")
        dialog.transient(self.root)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Task Name", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(40,10), padx=50, anchor="w")
        name_entry = ctk.CTkEntry(dialog, font=ctk.CTkFont(size=18), height=50, corner_radius=12)
        name_entry.pack(pady=10, padx=50, fill="x")
        name_entry.insert(0, task.name)
        name_entry.focus()

        ctk.CTkLabel(dialog, text="Urgency", font=ctk.CTkFont(size=16), text_color="#e74c3c").pack(pady=(30,8), padx=50, anchor="w")
        urgency = ctk.CTkSlider(dialog, from_=1, to=5, number_of_steps=4)
        urgency.set(task.urgency)
        urgency.pack(pady=10, padx=50, fill="x")

        ctk.CTkLabel(dialog, text="Importance", font=ctk.CTkFont(size=16), text_color="#27ae60").pack(pady=(25,8), padx=50, anchor="w")
        importance = ctk.CTkSlider(dialog, from_=1, to=5, number_of_steps=4)
        importance.set(task.importance)
        importance.pack(pady=10, padx=50, fill="x")

        def save():
            name = name_entry.get().strip()
            if not name:
                ctk.CTkMessagebox.show_error("Task name cannot be empty!")
                return
            if any(t.name.lower() == name.lower() for t in self.tasks if t.id != task.id):
                ctk.CTkMessagebox.show_error("A task with this name already exists!")
                return

            task.name = name
            task.urgency = int(urgency.get())
            task.importance = int(importance.get())
            if task.id not in [t.id for t in self.tasks]:
                self.tasks.append(task)

            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save Changes", command=save, width=250, height=55,
                     font=ctk.CTkFont(size=18, weight="bold"), corner_radius=15).pack(pady=40)
        dialog.bind("<Return>", lambda e: save())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def delete_task(self, task: Task):
        if ctk.CTkMessagebox.askyesno("Delete", f"Delete \"{task.name}\"?"):
            self.tasks = [t for t in self.tasks if t.id != task.id]
            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()

    def clear_all(self):
        if ctk.CTkMessagebox.askyesno("Clear All", "Delete all tasks?"):
            self.tasks.clear()
            self.storage.save_tasks(self.tasks)
            self.refresh_matrix()

    def change_password(self):
        ctk.CTkMessagebox.show_info("Coming Soon", "This feature will be added soon!")


if __name__ == "__main__":
    try:
        from argon2 import low_level
    except ImportError:
        print("Please run: pip install argon2-cffi customtkinter cryptography")
        exit()
    EisenhowerApp()