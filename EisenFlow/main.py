import sys
import uuid
import pickle
import json
import os
from pathlib import Path
from typing import Dict, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QListWidget, QListWidgetItem, QFrame, QHBoxLayout,
    QGraphicsOpacityEffect, QStackedWidget, QScrollArea
)
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, QMimeData, Signal, QObject
)
from PySide6.QtGui import QPalette, QColor, QDrag

# -------------------- Crypto --------------------
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Passphrase مخفی (در عمل باید امن‌تر مدیریت شود)
SECRET_PASSPHRASE = b"eisenflow_secret_2025_super_secure_key_change_this_in_production"

# مشتق کلید 256 بیتی
def derive_key(passphrase: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"eisenflow_fixed_salt",  # در تولید salt تصادفی بهتر است
        iterations=200000,
    )
    return kdf.derive(passphrase)

ENCRYPTION_KEY = derive_key(SECRET_PASSPHRASE)

DATA_FILE = Path.home() / "eisenflow_data.bin"

# -------------------- Communication --------------------

class Signals(QObject):
    tasks_changed = Signal()

signals = Signals()

# -------------------- Model --------------------

class Task:
    def __init__(self, title: str, description: str = "", quadrant: str = "Q1", status: str = "To Do", id=None):
        self.id = id or uuid.uuid4()
        self.title = title.strip()
        self.description = description.strip()
        self.quadrant = quadrant
        self.status = status

    def to_dict(self):
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "quadrant": self.quadrant,
            "status": self.status
        }

    @staticmethod
    def from_dict(data):
        return Task(
            title=data["title"],
            description=data["description"],
            quadrant=data["quadrant"],
            status=data["status"],
            id=uuid.UUID(data["id"])
        )


class TaskManager:
    def __init__(self):
        self.tasks: List[Task] = []
        self.load_from_file()

    def add_task(self, task: Task):
        self.tasks.append(task)
        signals.tasks_changed.emit()
        self.save_to_file()

    def move_task(self, task: Task, new_status: str, new_quadrant: str = None):
        if new_quadrant and new_quadrant != task.quadrant:
            task.quadrant = new_quadrant
        task.status = new_status
        signals.tasks_changed.emit()
        self.save_to_file()

    def get_tasks_by_quadrant(self, quadrant: str) -> List[Task]:
        return [t for t in self.tasks if t.quadrant == quadrant]

    def get_tasks_by_quadrant_and_status(self, quadrant: str, status: str) -> List[Task]:
        return [t for t in self.tasks if t.quadrant == quadrant and t.status == status]

    def save_to_file(self):
        try:
            data = [task.to_dict() for task in self.tasks]
            json_data = json.dumps(data).encode('utf-8')

            aesgcm = AESGCM(ENCRYPTION_KEY)
            nonce = os.urandom(12)
            ct = aesgcm.encrypt(nonce, json_data, None)

            with open(DATA_FILE, 'wb') as f:
                f.write(nonce + ct)
        except Exception as e:
            print(f"خطا در ذخیره‌سازی: {e}")

    def load_from_file(self):
        if not DATA_FILE.exists():
            return
        try:
            with open(DATA_FILE, 'rb') as f:
                file_data = f.read()
                nonce = file_data[:12]
                ciphertext = file_data[12:]

            aesgcm = AESGCM(ENCRYPTION_KEY)
            json_data = aesgcm.decrypt(nonce, ciphertext, None)
            data = json.loads(json_data.decode('utf-8'))

            self.tasks = [Task.from_dict(item) for item in data]
            signals.tasks_changed.emit()
        except Exception as e:
            print(f"خطا در بارگذاری داده‌ها: {e}")
            QMessageBox.warning(None, "خطا", "فایل داده خراب یا دستکاری شده است. داده‌ها پاک شدند.")
            self.tasks = []


# -------------------- Views --------------------

class TaskWidget(QFrame):
    FIXED_HEIGHT = 140

    def __init__(self, task: Task):
        super().__init__()
        self.task = task
        self.setFixedHeight(self.FIXED_HEIGHT)
        self.setMinimumWidth(220)
        self.setStyleSheet(self.get_style_for_quadrant(task.quadrant))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(task.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #eee;")
        layout.addWidget(title_label)

        if task.description:
            desc_label = QLabel(task.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 13px; color: #ccc;")
            layout.addWidget(desc_label)

        layout.addStretch()

        status_label = QLabel(task.status)
        status_label.setAlignment(Qt.AlignRight)
        status_label.setStyleSheet("font-size: 12px; color: #aaa; font-style: italic;")
        layout.addWidget(status_label)

    @staticmethod
    def get_style_for_quadrant(quadrant: str) -> str:
        colors = {
            "Q1": "background-color: #ff5555; border: 3px solid #ff0000; border-radius: 12px;",
            "Q2": "background-color: #55ff55; border: 3px solid #00aa00; border-radius: 12px;",
            "Q3": "background-color: #ffff55; border: 3px solid #aaaa00; border-radius: 12px;",
            "Q4": "background-color: #aaaaaa; border: 3px solid #666666; border-radius: 12px;",
        }
        return colors.get(quadrant, "background-color: #888888; border-radius: 12px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-task-pickle", pickle.dumps(self.task))
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)


class DraggableListWidget(QListWidget):
    def __init__(self, quadrant: str, status: str = None):
        super().__init__()
        self.quadrant = quadrant
        self.status = status
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QListWidget { background-color: rgba(255,255,255,30); border: 2px dashed #666; border-radius: 10px; }
            QListWidget::item { margin: 6px; }
            QListWidget[dropTarget=true] { border: 3px solid #00ff00; background-color: rgba(0,255,0,50); }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-pickle"):
            event.acceptProposedAction()
            self.setProperty("dropTarget", True)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dropTarget", False)
        self.style().polish(self)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-pickle"):
            task = pickle.loads(event.mimeData().data("application/x-task-pickle"))
            new_quadrant = self.quadrant
            new_status = self.status if self.status else task.status
            # پیدا کردن TaskManager از طریق والد
            parent = self.parent()
            while parent and not hasattr(parent, 'task_manager'):
                parent = parent.parent()
            if parent:
                parent.task_manager.move_task(task, new_status, new_quadrant)
            event.acceptProposedAction()


# -------------------- Quadrant Widget --------------------

class QuadrantWidget(QWidget):
    def __init__(self, key: str, label_text: str, task_manager: TaskManager):
        super().__init__()
        self.key = key
        self.label_text = label_text
        self.task_manager = task_manager

        self.setStyleSheet("background-color: #2a2a2a; border: 2px solid #555; border-radius: 16px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title_label = QLabel(label_text)
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        header.addWidget(title_label)
        header.addStretch()
        self.count_label = QLabel("0 وظیفه")
        self.count_label.setStyleSheet("font-size: 16px; color: #aaa;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.stack = QStackedWidget()

        # Overview
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        self.overview_grid_widget = QWidget()
        self.overview_grid = QGridLayout(self.overview_grid_widget)
        self.overview_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.overview_grid.setSpacing(15)
        overview_scroll.setWidget(self.overview_grid_widget)
        self.stack.addWidget(overview_scroll)

        # Kanban
        kanban = QWidget()
        kanban_layout = QHBoxLayout(kanban)
        kanban_layout.setSpacing(20)
        self.columns = {}
        for status in ["To Do", "Doing", "Done"]:
            col = QVBoxLayout()
            lbl = QLabel(status)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: white; margin-bottom: 10px;")
            col.addWidget(lbl)
            list_widget = DraggableListWidget(key, status)
            col.addWidget(list_widget)
            self.columns[status] = list_widget
            kanban_layout.addLayout(col)
        self.stack.addWidget(kanban)

        layout.addWidget(self.stack)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        signals.tasks_changed.connect(self.update_views)
        self.update_views()

    def update_views(self):
        tasks = self.task_manager.get_tasks_by_quadrant(self.key)
        grid = self.overview_grid
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row, col = 0, 0
        for task in sorted(tasks, key=lambda t: t.title.lower()):
            widget = TaskWidget(task)
            grid.addWidget(widget, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        self.count_label.setText(f"{len(tasks)} وظیفه")

        for status, list_widget in self.columns.items():
            list_widget.clear()
            tasks_in_col = self.task_manager.get_tasks_by_quadrant_and_status(self.key, status)
            for task in sorted(tasks_in_col, key=lambda t: t.title.lower()):
                widget = TaskWidget(task)
                item = QListWidgetItem(list_widget)
                item.setSizeHint(QSize(240, TaskWidget.FIXED_HEIGHT + 20))
                list_widget.addItem(item)
                list_widget.setItemWidget(item, widget)


# -------------------- Dialog & Main --------------------

class AddTaskDialog(QDialog):
    def __init__(self, task_manager: TaskManager):
        super().__init__()
        self.task_manager = task_manager
        self.setWindowTitle("افزودن وظیفه جدید")
        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("اجباری*")
        self.desc_edit = QLineEdit()
        self.quadrant_combo = QComboBox()
        self.quadrant_combo.addItems([
            "Q1: مهم و فوری",
            "Q2: مهم اما غیرفوری",
            "Q3: فوری اما غیرمهم",
            "Q4: غیرمهم و غیرفوری"
        ])

        layout.addRow("عنوان*:", self.title_edit)
        layout.addRow("توضیح:", self.desc_edit)
        layout.addRow("ربع:", self.quadrant_combo)

        buttons = QHBoxLayout()
        ok = QPushButton("اضافه کن")
        cancel = QPushButton("انصراف")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addRow(buttons)

    def accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان الزامی است.")
            return
        quadrant = self.quadrant_combo.currentText().split(":")[0]
        task = Task(title, self.desc_edit.text().strip(), quadrant, "To Do")
        self.task_manager.add_task(task)
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EisenFlow – ماتریس آیزنهاور با کانبان")
        self.resize(1600, 900)

        self.task_manager = TaskManager()

        central = QWidget()
        self.setCentralWidget(central)
        self.grid = QGridLayout(central)
        self.grid.setSpacing(30)

        self.quad_widgets: Dict[str, QuadrantWidget] = {}
        quadrants = [
            ("Q1", "مهم و فوری"),
            ("Q2", "مهم اما غیرفوری"),
            ("Q3", "فوری اما غیرمهم"),
            ("Q4", "غیرمهم و غیرفوری")
        ]

        for i, (key, label) in enumerate(quadrants):
            q_widget = QuadrantWidget(key, label, self.task_manager)
            q_widget.setCursor(Qt.PointingHandCursor)
            q_widget.mousePressEvent = lambda e, k=key: self.enter_focus_mode(k)
            self.quad_widgets[key] = q_widget
            row = 0 if i < 2 else 1
            col = i % 2
            self.grid.addWidget(q_widget, row, col)

        self.add_btn = QPushButton("افزودن وظیفه جدید")
        self.add_btn.clicked.connect(self.add_new_task)
        self.add_btn.setStyleSheet("font-size: 16px; padding: 10px;")

        self.exit_btn = QPushButton("← بازگشت")
        self.exit_btn.clicked.connect(self.exit_focus_mode)
        self.exit_btn.setVisible(False)

        status_bar = self.statusBar()
        status_bar.addPermanentWidget(self.add_btn)
        status_bar.addPermanentWidget(self.exit_btn)

        self.current_quadrant = None

        central.setAcceptDrops(True)
        central.dragEnterEvent = lambda e: e.acceptProposedAction() if e.mimeData().hasFormat("application/x-task-pickle") else None
        central.dropEvent = self.central_drop

    def central_drop(self, event):
        if event.mimeData().hasFormat("application/x-task-pickle"):
            task = pickle.loads(event.mimeData().data("application/x-task-pickle"))
            pos = event.position().toPoint()
            for key, widget in self.quad_widgets.items():
                if widget.geometry().contains(pos):
                    self.task_manager.move_task(task, task.status, key)
                    break
            event.acceptProposedAction()

    def enter_focus_mode(self, quadrant_key: str):
        if self.current_quadrant == quadrant_key:
            return
        self.current_quadrant = quadrant_key
        self.exit_btn.setVisible(True)

        for key, q_widget in self.quad_widgets.items():
            target = 1.0 if key == quadrant_key else 0.3
            self.animate_opacity(q_widget.opacity_effect, target)
            q_widget.stack.setCurrentIndex(1 if key == quadrant_key else 0)

        for i in range(2):
            for j in range(2):
                idx = i * 2 + j
                key = list(self.quad_widgets.keys())[idx]
                stretch = 4 if key == quadrant_key else 1
                self.grid.setRowStretch(i, stretch)
                self.grid.setColumnStretch(j, stretch)

    def exit_focus_mode(self):
        if not self.current_quadrant:
            return
        self.current_quadrant = None
        self.exit_btn.setVisible(False)

        for q_widget in self.quad_widgets.values():
            self.animate_opacity(q_widget.opacity_effect, 1.0)
            q_widget.stack.setCurrentIndex(0)

        for i in range(2):
            self.grid.setRowStretch(i, 1)
            self.grid.setColumnStretch(i, 1)

    def animate_opacity(self, effect, target):
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(600)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(target)
        anim.start()

    def add_new_task(self):
        dialog = AddTaskDialog(self.task_manager)
        dialog.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.current_quadrant:
            self.exit_focus_mode()

    def closeEvent(self, event):
        self.task_manager.save_to_file()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())