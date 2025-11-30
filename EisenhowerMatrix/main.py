import json
import os
from tkinter import *
from tkinter import messagebox, simpledialog
from tkinter import ttk

# ====================== Data ======================
TASKS_FILE = "tasks.json"
if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=4)

def load_tasks():   return json.load(open(TASKS_FILE, "r", encoding="utf-8"))
def save_tasks(t):  json.dump(t, open(TASKS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=4)

# ====================== Pastel Color System (درست شده!) ======================
def get_pastel_color(importance, urgency):
    score = importance + urgency  # از ۲ تا ۱۰

    # هر چی امتیاز بالاتر → قرمزتر (فوری + مهم)
    # هر چی کمتر → سبزآبی آرام
    if score >= 10:   return "#ff5252"  # قرمز پررنگ (۵+۵)
    if score >= 9:    return "#ff6b6b"
    if score >= 8:    return "#ff8a80"
    if score >= 7:    return "#ff9e9e"
    if score >= 6:    return "#ffbbbb"
    if score >= 5:    return "#dcedc8"  # سبز خیلی ملایم
    if score >= 4:    return "#c8e6c9"
    else:             return "#b2dfdb"  # سبزآبی آرام (کمترین اولویت)

# ====================== Task Functions ======================
def add_task():
    name = simpledialog.askstring("New Task", "Enter task name:")
    if not name or not name.strip(): return
    u = simpledialog.askinteger("Urgency", "Urgency (1–5):", minvalue=1, maxvalue=5)
    i = simpledialog.askinteger("Importance", "Importance (1–5):", minvalue=1, maxvalue=5)
    if u is None or i is None: return

    tasks = load_tasks()
    tasks.append({"name": name.strip(), "urgency": u, "importance": i})
    save_tasks(tasks)
    messagebox.showinfo("Success ✓", f'"{name}" added!')
    refresh_matrix()

def clear_all_tasks():
    if messagebox.askyesno("Clear All", "Delete all tasks?"):
        save_tasks([])
        refresh_matrix()

# ====================== Matrix ======================
def refresh_matrix():
    for widget in matrix_frame.winfo_children():
        widget.destroy()

    tasks = load_tasks()

    # Title
    Label(matrix_frame, text="Eisenhower Matrix 5×5", font=("Segoe UI", 18, "bold"), fg="#2d3436", bg="#f8f9fa")\
        .grid(row=0, column=0, columnspan=7, pady=(10, 30))

    # Corner
    Label(matrix_frame, text="Importance ↓\nUrgency →", font=("Segoe UI", 11, "bold"), bg="#2d3436", fg="white", padx=12, pady=15)\
        .grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    # Top headers (Urgency)
    for col, text in enumerate(["5\nVery Urgent", "4\nUrgent", "3\nMedium", "2\nLow", "1\nNot Urgent"], 1):
        Label(matrix_frame, text=text, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=12)\
            .grid(row=1, column=col, padx=5, pady=5, sticky="nsew")

    # Left headers (Importance)
    for row, text in enumerate(["5 Very Important", "4 Important", "3 Medium", "2 Low", "1 Not Important"], 2):
        Label(matrix_frame, text=text, bg="#2d3436", fg="white", font=("Segoe UI", 10, "bold"), padx=12, pady=10)\
            .grid(row=row, column=0, padx=5, pady=5, sticky="nsew")

    # 5×5 Cells
    for urgency in range(1, 6):
        for importance in range(1, 6):
            r = importance + 1
            c = urgency   # این خط رو عوض کردم! حالا ۵×۵ سمت چپ بالا هست (درست مثل ماتریس واقعی)

            color = get_pastel_color(importance, urgency)
            cell = Frame(matrix_frame, bg=color, highlightbackground="#dfe6e9", highlightthickness=2)
            cell.grid(row=r, column=c, padx=7, pady=7, sticky="nsew")

            cell_tasks = [t for t in tasks if t["urgency"] == urgency and t["importance"] == importance]

            if cell_tasks:
                Label(cell, text=f"{len(cell_tasks)} task{'s' if len(cell_tasks)>1 else ''}",
                      bg=color, fg="#2d3436", font=("Segoe UI", 9, "bold")).pack(anchor="nw", padx=10, pady=(10,3))
                for t in cell_tasks[:15]:
                    Label(cell, text="• " + t["name"], bg=color, fg="#2d3436", font=("Segoe UI", 10),
                          anchor="w", justify="left", wraplength=300).pack(anchor="w", padx=12, pady=1)
                if len(cell_tasks) > 15:
                    Label(cell, text=f"⋯ +{len(cell_tasks)-15} more", bg=color, fg="#636e72", font=("Segoe UI", 9))\
                        .pack(anchor="w", padx=12, pady=5)
            else:
                Label(cell, text="Drop tasks here", bg=color, fg="#95a5a6", font=("Segoe UI", 11, "italic"))\
                    .pack(expand=True)

    # Responsive grid
    for i in range(7):
        matrix_frame.grid_columnconfigure(i, weight=1)
        if i > 0:
            matrix_frame.grid_rowconfigure(i + 1, weight=1)

# ====================== Window ======================
root = Tk()
root.title("Eisenhower Matrix 5×5 - Pastel Edition")
root.geometry("1300x800")
root.minsize(950, 650)
root.configure(bg="#f8f9fa")

ttk.Style().theme_use("clam")

# Header
Label(root, text="Eisenhower Matrix", font=("Segoe UI", 28, "bold"), bg="#f8f9fa", fg="#2d3436").pack(pady=(30,8))
Label(root, text="Do what matters — delete what doesn't", font=("Segoe UI", 12), bg="#f8f9fa", fg="#636e72").pack(pady=(0,30))

# Buttons
btns = Frame(root, bg="#f8f9fa")
btns.pack(pady=10)
ttk.Button(btns, text="  Add New Task  ", command=add_task).pack(side=LEFT, padx=18)
ttk.Button(btns, text="  Refresh  ", command=refresh_matrix).pack(side=LEFT, padx=18)
ttk.Button(btns, text="  Clear All  ", command=clear_all_tasks).pack(side=LEFT, padx=18)

# Scrollable canvas
canvas = Canvas(root, bg="#f8f9fa", highlightthickness=0)
scroll_x = ttk.Scrollbar(root, orient="horizontal", command=canvas.xview)
scroll_y = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
canvas.configure(xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)

scroll_frame = Frame(canvas, bg="#f8f9fa")
canvas_win = canvas.create_window((0,0), window=scroll_frame, anchor="nw")

matrix_frame = Frame(scroll_frame, bg="#f8f9fa")
matrix_frame.pack(padx=40, pady=40, expand=True, fill="both")

canvas.pack(side="top", fill="both", expand=True, padx=20, pady=20)
scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")

def resize(event=None):
    canvas.configure(scrollregion=canvas.bbox("all"))
    canvas.itemconfig(canvas_win, width=canvas.winfo_width())
canvas.bind("<Configure>", resize)
scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

refresh_matrix()
root.mainloop()