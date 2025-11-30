import json
import os
from tkinter import *
from tkinter import messagebox, ttk
from cryptography.fernet import Fernet
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ====================== رمزنگاری قوی ======================
PASSWORD = b"eisenhower_matrix_secret_2025"
SALT = b"salt_1234567890!"


def get_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(PASSWORD))
    return key


fernet = Fernet(get_key())
TASKS_FILE = "tasks.enc"  # فایل رمزنگاری شده


def save_tasks(tasks):
    data = json.dumps(tasks, ensure_ascii=False).encode('utf-8')
    encrypted = fernet.encrypt(data)
    with open(TASKS_FILE, "wb") as f:
        f.write(encrypted)


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "rb") as f:
            encrypted = f.read()
        decrypted = fernet.decrypt(encrypted)
        return json.loads(decrypted.decode('utf-8'))
    except Exception:
        messagebox.showerror("خطا", "فایل تسک‌ها خراب است یا کلید اشتباه است.\nیک فایل جدید ساخته شد.")
        return []


# ====================== رنگ پاستیلی ======================
def get_pastel_color(importance, urgency):
    score = importance + urgency
    if score >= 10:   return "#ff5252"
    if score >= 9:    return "#ff6b6b"
    if score >= 8:    return "#ff8a80"
    if score >= 7:    return "#ff9e9e"
    if score >= 6:    return "#ffbbbb"
    if score >= 5:    return "#dcedc8"
    if score >= 4:
        return "#c8e6c9"
    else:
        return "#b2dfdb"


# ====================== پنجره اضافه کردن تسک ======================
def add_task():
    modal = Toplevel(root)
    modal.title("Add New Task")
    modal.geometry("420x520")
    modal.configure(bg="#f8f9fa")
    modal.transient(root)
    modal.grab_set()
    modal.resizable(False, False)

    Label(modal, text="Add New Task", font=("Segoe UI", 18, "bold"), bg="#f8f9fa", fg="#2d3436").pack(pady=(30, 20))

    Label(modal, text="Task Name", font=("Segoe UI", 10), bg="#f8f9fa", fg="#2d3436").pack(anchor="w", padx=50)
    name_entry = ttk.Entry(modal, font=("Segoe UI", 11), width=35)
    name_entry.pack(pady=(8, 25), padx=50)
    name_entry.focus()

    # Urgency
    Label(modal, text="Urgency", font=("Segoe UI", 11, "bold"), bg="#f8f9fa", fg="#e74c3c").pack(anchor="w", padx=50)
    urgency_var = IntVar(value=3)
    urgency_scale = ttk.Scale(modal, from_=1, to=5, orient="horizontal", variable=urgency_var, length=300)
    urgency_scale.pack(pady=(10, 5), padx=50)
    ul = Frame(modal, bg="#f8f9fa")
    Label(ul, text="Not Urgent", fg="#7f8c8d", bg="#f8f9fa").pack(side=LEFT, padx=20)
    Label(ul, text="Very Urgent", fg="#e74c3c", font=("Segoe UI", 9, "bold"), bg="#f8f9fa").pack(side=RIGHT, padx=20)
    ul.pack()

    # Importance
    Label(modal, text="Importance", font=("Segoe UI", 11, "bold"), bg="#f8f9fa", fg="#27ae60").pack(anchor="w", padx=50,
                                                                                                    pady=(25, 0))
    importance_var = IntVar(value=3)
    importance_scale = ttk.Scale(modal, from_=1, to=5, orient="horizontal", variable=importance_var, length=300)
    importance_scale.pack(pady=(10, 5), padx=50)
    il = Frame(modal, bg="#f8f9fa")
    Label(il, text="Not Important", fg="#7f8c8d", bg="#f8f9fa").pack(side=LEFT, padx=20)
    Label(il, text="Very Important", fg="#27ae60", font=("Segoe UI", 9, "bold"), bg="#f8f9fa").pack(side=RIGHT, padx=20)
    il.pack()

    btn_frame = Frame(modal, bg="#f8f9fa")
    btn_frame.pack(pady=40)

    def confirm_add():
        name = name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Please enter a task name!", parent=modal)
            return
        u = urgency_var.get()
        i = importance_var.get()
        tasks = load_tasks()
        tasks.append({"name": name, "urgency": u, "importance": i})
        save_tasks(tasks)
        messagebox.showinfo("Success ✓", f'"{name}" added to matrix!', parent=modal)
        modal.destroy()
        refresh_matrix()

    def cancel():
        modal.destroy()

    ttk.Button(btn_frame, text="  Cancel  ", command=cancel).pack(side=LEFT, padx=15)
    ttk.Button(btn_frame, text="  Add Task  ", command=confirm_add).pack(side=LEFT, padx=15)

    modal.bind("<Return>", lambda e: confirm_add())
    modal.bind("<Escape>", lambda e: cancel())


# ====================== پاک کردن و رفرش ======================
def clear_all_tasks():
    if messagebox.askyesno("Clear All", "Delete all tasks permanently?"):
        save_tasks([])
        refresh_matrix()


def refresh_matrix():
    for widget in matrix_frame.winfo_children():
        widget.destroy()

    tasks = load_tasks()

    Label(matrix_frame, text="Eisenhower Matrix 5×5", font=("Segoe UI", 18, "bold"), fg="#2d3436", bg="#f8f9fa") \
        .grid(row=0, column=0, columnspan=7, pady=(10, 30))

    Label(matrix_frame, text="Importance ↓\nUrgency →", font=("Segoe UI", 11, "bold"), bg="#2d3436", fg="white",
          padx=12, pady=15) \
        .grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    for col, text in enumerate(["5\nVery Urgent", "4\nUrgent", "3\nMedium", "2\nLow", "1\nNot Urgent"], 1):
        Label(matrix_frame, text=text, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=12) \
            .grid(row=1, column=col, padx=5, pady=5, sticky="nsew")

    for row, text in enumerate(["5 Very Important", "4 Important", "3 Medium", "2 Low", "1 Not Important"], 2):
        Label(matrix_frame, text=text, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=10) \
            .grid(row=row, column=0, padx=5, pady=5, sticky="nsew")

    for urgency in range(1, 6):
        for importance in range(1, 6):
            r = importance + 1
            c = urgency
            color = get_pastel_color(importance, urgency)
            cell = Frame(matrix_frame, bg=color, highlightbackground="#dfe6e9", highlightthickness=2)
            cell.grid(row=r, column=c, padx=7, pady=7, sticky="nsew")

            cell_tasks = [t for t in tasks if t["urgency"] == urgency and t["importance"] == importance]

            if cell_tasks:
                Label(cell, text=f"{len(cell_tasks)} task{'s' if len(cell_tasks) > 1 else ''}",
                      bg=color, fg="#2d3436", font=("Segoe UI", 9, "bold")).pack(anchor="nw", padx=10, pady=(10, 3))
                for t in cell_tasks[:15]:
                    Label(cell, text="• " + t["name"], bg=color, fg="#2d3436", font=("Segoe UI", 10),
                          anchor="w", justify="left", wraplength=300).pack(anchor="w", padx=12, pady=1)
                if len(cell_tasks) > 15:
                    Label(cell, text=f"⋯ +{len(cell_tasks) - 15} more", bg=color, fg="#636e72", font=("Segoe UI", 9)) \
                        .pack(anchor="w", padx=12, pady=5)
            else:
                Label(cell, text="Drop tasks here", bg=color, fg="#95a5a6", font=("Segoe UI", 11, "italic")) \
                    .pack(expand=True)

    for i in range(7):
        matrix_frame.grid_columnconfigure(i, weight=1)
        if i > 0:
            matrix_frame.grid_rowconfigure(i + 1, weight=1)


# ====================== پنجره اصلی ======================
root = Tk()
root.title("Eisenhower Matrix 5×5 - Secure & Encrypted")
root.geometry("1300x800")
root.minsize(950, 650)
root.configure(bg="#f8f9fa")
ttk.Style().theme_use("clam")

Label(root, text="Eisenhower Matrix", font=("Segoe UI", 28, "bold"), bg="#f8f9fa", fg="#2d3436").pack(pady=(30, 8))
Label(root, text="Your tasks are encrypted and private", font=("Segoe UI", 11), bg="#f8f9fa", fg="#27ae60").pack(
    pady=(0, 30))

btns = Frame(root, bg="#f8f9fa")
btns.pack(pady=10)
ttk.Button(btns, text="  Add New Task  ", command=add_task).pack(side=LEFT, padx=18)
ttk.Button(btns, text="  Refresh  ", command=refresh_matrix).pack(side=LEFT, padx=18)
ttk.Button(btns, text="  Clear All  ", command=clear_all_tasks).pack(side=LEFT, padx=18)

canvas = Canvas(root, bg="#f8f9fa", highlightthickness=0)
scroll_x = ttk.Scrollbar(root, orient="horizontal", command=canvas.xview)
scroll_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

scroll_frame = Frame(canvas, bg="#f8f9fa")
canvas_win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
matrix_frame = Frame(scroll_frame, bg="#f8f9fa")
matrix_frame.pack(padx=40, pady=40, expand=True, fill="both")

canvas.pack(side="top", fill="both", expand=True, padx=20, pady=20)
scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")


def resize(e=None):
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.itemconfig(canvas_win, width=canvas.winfo_width())


canvas.bind("<Configure>", resize)
scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

refresh_matrix()
root.mainloop()