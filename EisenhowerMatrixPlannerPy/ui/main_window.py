# ui/main_window.py
import customtkinter as ctk
from .matrix_canvas import MatrixCanvas
from .task_dialog import TaskDialog
from services.task_service import create_task, get_session  # اضافه شد
from database.models import Task
from tkinter import filedialog, messagebox
from datetime import datetime
import io
from PIL import Image

class MainWindow(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.master = master
        self.setup_ui()
        self.create_canvas()

    def setup_ui(self):
        title = ctk.CTkLabel(self.master, text="Eisenhower Matrix Planner", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(pady=(20, 10))

        toolbar = ctk.CTkFrame(self.master, height=50)
        toolbar.pack(fill="x", padx=20, pady=(0, 10))
        toolbar.pack_propagate(False)

        ctk.CTkButton(toolbar, text="+ New Task", width=130, font=ctk.CTkFont(size=14, weight="bold"),
                      command=self.add_new_task).pack(side="left", padx=10, pady=8)

        self.theme_switch = ctk.CTkSwitch(toolbar, text="Dark Mode", command=self.toggle_theme)
        self.theme_switch.pack(side="right", padx=20, pady=8)
        if ctk.get_appearance_mode() == "Dark":
            self.theme_switch.select()

        ctk.CTkButton(toolbar, text="Export to PNG", command=self.export_to_png).pack(side="right", padx=10, pady=8)

    def create_canvas(self):
        canvas_frame = ctk.CTkFrame(self.master)
        canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.canvas = MatrixCanvas(canvas_frame, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # اسکرول‌بارها
        v_scroll = ctk.CTkScrollbar(canvas_frame, orientation="vertical", command=self.canvas.yview)
        h_scroll = ctk.CTkScrollbar(canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")

        self.canvas.after(300, self.canvas.load_tasks)  # صبر کنیم تا کامل باز بشه

    def add_new_task(self):
        dialog = TaskDialog(self.master, title="Create New Task")
        self.master.wait_window(dialog)
        if not dialog.result:
            return

        task = create_task(
            title=dialog.result["title"],
            importance=dialog.result["importance"],
            urgency=dialog.result["urgency"]
        )

        x, y = self.canvas.importance_urgency_to_xy(task.importance, task.urgency)
        task.canvas_x = x
        task.canvas_y = y

        # ذخیره موقعیت
        sess = get_session()
        sess.merge(task)
        sess.commit()
        sess.close()

        self.refresh_canvas()

    def refresh_canvas(self):
        for card in self.canvas.cards.values():
            card.destroy()
        self.canvas.cards.clear()
        self.canvas.load_tasks()

    def toggle_theme(self):
        mode = "dark" if self.theme_switch.get() else "light"
        ctk.set_appearance_mode(mode)

    def export_to_png(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile=f"eisenhower-matrix-{datetime.now():%Y%m%d-%H%M%S}.png"
        )
        if not file_path:
            return
        try:
            ps = self.canvas.postscript(colormode='color')
            img = Image.open(io.BytesIO(ps.encode('utf-8')))
            img.save(file_path, "PNG")
            messagebox.showinfo("Success", f"Saved:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed:\n{e}")