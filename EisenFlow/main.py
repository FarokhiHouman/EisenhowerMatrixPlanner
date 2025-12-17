import sys
import uuid
import os
import logging
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QListWidget, QListWidgetItem, QFrame, QHBoxLayout,
    QGraphicsOpacityEffect, QStackedWidget, QScrollArea, QMenu, QStatusBar
)
from PySide6.QtCore import (
    Qt, QSize, QPropertyAnimation, QEasingCurve, QMimeData, Signal, QObject, QEvent
)
from PySide6.QtGui import (
    QPalette, QColor, QDrag, QCursor, QPixmap, QBrush, QFont
)

# SQLCipher برای رمزنگاری پایگاه داده
from sqlcipher3 import dbapi2 as sqlite

# -------------------- Crypto Setup --------------------
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logging.basicConfig(level=logging.INFO)

USERS_DIR = Path.home() / ".eisenflow_users"
USERS_DIR.mkdir(exist_ok=True)

def derive_db_key(password: str, salt: bytes) -> str:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    key = kdf.derive(password.encode('utf-8'))
    return "".join(f"{b:02x}" for b in key)

# -------------------- Communication --------------------
class Signals(QObject):
    tasks_changed = Signal()

signals = Signals()

# -------------------- Model --------------------
class Task:
    def __init__(self, title: str, description: str = "", quadrant: str = "Q1",
                 status: str = "To Do", task_id: Optional[uuid.UUID] = None):
        self.id = task_id or uuid.uuid4()
        self.title = title.strip()
        self.description = description.strip()
        self.quadrant = quadrant
        self.status = status

class TaskManager:
    def __init__(self, username: str, password: str):
        self.username = username
        self.db_path = USERS_DIR / f"{username}.db"
        self.password = password
        self.salt = self._get_or_create_salt()
        self.db_key = derive_db_key(password, self.salt)
        self.conn = None
        self._connect()
        self._create_table()

    def _get_or_create_salt(self) -> bytes:
        salt_file = USERS_DIR / f"{self.username}_salt.bin"
        if salt_file.exists():
            return salt_file.read_bytes()
        salt = os.urandom(16)
        salt_file.write_bytes(salt)
        return salt

    def _connect(self):
        try:
            self.conn = sqlite.connect(str(self.db_path))
            self.conn.execute(f"PRAGMA key = '{self.db_key}'")
            self.conn.execute("PRAGMA foreign_keys = ON")
        except Exception as e:
            logging.error(f"خطا در اتصال به پایگاه داده: {e}")
            raise

    def _create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    quadrant TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)

    def get_all_tasks(self) -> List[Task]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, title, description, quadrant, status FROM tasks")
            rows = cur.fetchall()
            return [Task(row[1], row[2], row[3], row[4], uuid.UUID(row[0])) for row in rows]
        except Exception as e:
            logging.error(f"خطا در خواندن وظایف: {e}")
            return []

    def add_task(self, task: Task):
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT INTO tasks (id, title, description, quadrant, status) VALUES (?, ?, ?, ?, ?)",
                    (str(task.id), task.title, task.description, task.quadrant, task.status)
                )
            signals.tasks_changed.emit()
        except Exception as e:
            logging.error(f"خطا در افزودن وظیفه: {e}")
            QMessageBox.critical(None, "خطا", "نمی‌توان وظیفه را افزود.")

    def update_task(self, task: Task):
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE tasks SET title=?, description=?, quadrant=?, status=? WHERE id=?",
                    (task.title, task.description, task.quadrant, task.status, str(task.id))
                )
            signals.tasks_changed.emit()
        except Exception as e:
            logging.error(f"خطا در به‌روزرسانی: {e}")

    def delete_task(self, task_id: uuid.UUID):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM tasks WHERE id=?", (str(task_id),))
            signals.tasks_changed.emit()
        except Exception as e:
            logging.error(f"خطا در حذف: {e}")

    def get_tasks_by_quadrant(self, quadrant: str) -> List[Task]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, title, description, quadrant, status FROM tasks WHERE quadrant=?", (quadrant,))
        rows = cur.fetchall()
        return [Task(row[1], row[2], row[3], row[4], uuid.UUID(row[0])) for row in rows]

    def get_tasks_by_quadrant_and_status(self, quadrant: str, status: str) -> List[Task]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, title, description, quadrant, status FROM tasks WHERE quadrant=? AND status=?", (quadrant, status))
        rows = cur.fetchall()
        return [Task(row[1], row[2], row[3], row[4], uuid.UUID(row[0])) for row in rows]

# -------------------- Views --------------------
class TaskWidget(QFrame):
    FIXED_HEIGHT = 160

    def __init__(self, task: Task, task_manager: TaskManager):
        super().__init__()
        self.task = task
        self.task_manager = task_manager
        self.setFixedHeight(self.FIXED_HEIGHT)
        self.setMinimumWidth(260)
        self.setStyleSheet(self.get_style_for_quadrant(task.quadrant))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(task.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 18px; color: #FFFFFF; text-shadow: 1px 1px 2px black;")
        title_label.setFont(QFont("Tahoma", 18, QFont.Bold))
        layout.addWidget(title_label)

        if task.description:
            desc_label = QLabel(task.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 14px; color: #EEEEEE;")
            layout.addWidget(desc_label)

        layout.addStretch()

        status_label = QLabel(task.status)
        status_label.setAlignment(Qt.AlignRight)
        status_label.setStyleSheet("font-size: 14px; color: #FFD700; font-style: italic; background-color: rgba(0,0,0,100); padding: 5px; border-radius: 8px;")
        layout.addWidget(status_label)

    @staticmethod
    def get_style_for_quadrant(quadrant: str) -> str:
        colors = {
            "Q1": "background-color: #C21807; border: 5px solid #FFD700; border-radius: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.6);",
            "Q2": "background-color: #008080; border: 5px solid #FFD700; border-radius: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.6);",
            "Q3": "background-color: #FF8C00; border: 5px solid #FFD700; border-radius: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.6);",
            "Q4": "background-color: #4B0082; border: 5px solid #FFD700; border-radius: 20px; box-shadow: 5px 5px 15px rgba(0,0,0,0.6);",
        }
        return colors.get(quadrant, "background-color: #6b7280; border: 5px solid #FFD700; border-radius: 20px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-task-id", str(self.task.id).encode())
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog = EditTaskDialog(self.task, self.task_manager)
            if dialog.exec():
                self.task_manager.update_task(self.task)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        delete_action = menu.addAction("حذف وظیفه")
        action = menu.exec(event.globalPos())
        if action == delete_action:
            reply = QMessageBox.question(
                self,
                "تأیید حذف",
                "آیا از حذف این وظیفه مطمئن هستید؟ این عمل قابل بازگشت نیست.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.task_manager.delete_task(self.task.id)

class DraggableListWidget(QListWidget):
    def __init__(self, quadrant: str, status: Optional[str], task_manager: TaskManager):
        super().__init__()
        self.quadrant = quadrant
        self.status = status
        self.task_manager = task_manager
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QListWidget { background-color: rgba(0,0,0,150); border: 3px solid #FFD700; border-radius: 15px; }
            QListWidget::item { margin: 10px; padding: 5px; }
            QListWidget[dropTarget=true] { border: 5px solid #00FFFF; background-color: rgba(0,255,255,100); }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            event.acceptProposedAction()
            self.setProperty("dropTarget", True)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dropTarget", False)
        self.style().polish(self)

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            task_id_str = event.mimeData().data("application/x-task-id").data().decode()
            task_id = uuid.UUID(task_id_str)
            tasks = self.task_manager.get_all_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                new_quadrant = self.quadrant
                new_status = self.status or task.status
                task.quadrant = new_quadrant
                task.status = new_status
                self.task_manager.update_task(task)
            event.acceptProposedAction()

class QuadrantWidget(QWidget):
    def __init__(self, key: str, label_text: str, task_manager: TaskManager):
        super().__init__()
        self.key = key
        self.label_text = label_text
        self.task_manager = task_manager

        self.setStyleSheet("""
            background-color: rgba(0, 50, 80, 200); 
            border: 4px solid #FFD700; 
            border-radius: 25px;
            box-shadow: 10px 10px 20px rgba(0,0,0,0.8);
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        title_label = QLabel(label_text)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFD700; text-shadow: 2px 2px 4px black;")
        header.addWidget(title_label)
        header.addStretch()
        self.count_label = QLabel("0 وظیفه")
        self.count_label.setStyleSheet("font-size: 20px; color: #FFFFFF;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.stack = QStackedWidget()

        # Overview Grid
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        self.overview_widget = QWidget()
        self.overview_grid = QGridLayout(self.overview_widget)
        self.overview_grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.overview_grid.setSpacing(15)
        overview_scroll.setWidget(self.overview_widget)
        self.stack.addWidget(overview_scroll)

        # Kanban Columns
        kanban = QWidget()
        kanban_layout = QHBoxLayout(kanban)
        kanban_layout.setSpacing(20)
        self.columns = {}
        for status in ["To Do", "Doing", "Done"]:
            col = QVBoxLayout()
            lbl = QLabel(status)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; color: #FFD700; font-size: 18px; margin-bottom: 10px;")
            col.addWidget(lbl)
            list_widget = DraggableListWidget(key, status, task_manager)
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

        while self.overview_grid.count():
            item = self.overview_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row, col = 0, 0
        for task in sorted(tasks, key=lambda t: t.title.lower()):
            widget = TaskWidget(task, self.task_manager)
            self.overview_grid.addWidget(widget, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        self.count_label.setText(f"{len(tasks)} وظیفه")

        for status, list_widget in self.columns.items():
            list_widget.clear()
            col_tasks = self.task_manager.get_tasks_by_quadrant_and_status(self.key, status)
            for task in sorted(col_tasks, key=lambda t: t.title.lower()):
                widget = TaskWidget(task, self.task_manager)
                item = QListWidgetItem(list_widget)
                item.setSizeHint(QSize(240, TaskWidget.FIXED_HEIGHT + 20))
                list_widget.addItem(item)
                list_widget.setItemWidget(item, widget)

# -------------------- Dialogs --------------------
class AddTaskDialog(QDialog):
    def __init__(self, task_manager: TaskManager):
        super().__init__()
        self.task_manager = task_manager
        self.setWindowTitle("افزودن وظیفه جدید")
        self.setStyleSheet("background-color: #001F3F; color: #FFD700;")
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

class EditTaskDialog(QDialog):
    def __init__(self, task: Task, task_manager: TaskManager):
        super().__init__()
        self.task = task
        self.task_manager = task_manager
        self.setWindowTitle("ویرایش وظیفه")
        self.setStyleSheet("background-color: #001F3F; color: #FFD700;")

        layout = QFormLayout(self)

        self.title_edit = QLineEdit(task.title)
        self.desc_edit = QLineEdit(task.description)
        self.quadrant_combo = QComboBox()
        self.quadrant_combo.addItems([
            "Q1: مهم و فوری",
            "Q2: مهم اما غیرفوری",
            "Q3: فوری اما غیرمهم",
            "Q4: غیرمهم و غیرفوری"
        ])
        for i in range(self.quadrant_combo.count()):
            if self.quadrant_combo.itemText(i).startswith(task.quadrant + ":"):
                self.quadrant_combo.setCurrentIndex(i)
                break

        self.status_combo = QComboBox()
        self.status_combo.addItems(["To Do", "Doing", "Done"])
        self.status_combo.setCurrentText(task.status)

        layout.addRow("عنوان:", self.title_edit)
        layout.addRow("توضیح:", self.desc_edit)
        layout.addRow("ربع:", self.quadrant_combo)
        layout.addRow("وضعیت:", self.status_combo)

        buttons = QHBoxLayout()
        ok = QPushButton("ذخیره")
        cancel = QPushButton("انصراف")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addRow(buttons)

    def accept(self):
        self.task.title = self.title_edit.text().strip()
        self.task.description = self.desc_edit.text().strip()
        self.task.quadrant = self.quadrant_combo.currentText().split(":")[0]
        self.task.status = self.status_combo.currentText()
        super().accept()

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ورود / ثبت‌نام")
        self.setFixedSize(420, 400)
        self.setStyleSheet("background-color: #001F3F; color: #FFD700;")

        layout = QVBoxLayout(self)
        layout.addStretch()

        title = QLabel("آیزن‌فلو")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 42px; font-weight: bold; color: #FFD700; text-shadow: 2px 2px 4px black;")
        layout.addWidget(title)

        form = QFormLayout()
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        form.addRow("نام کاربری:", self.username_edit)
        form.addRow("رمز عبور:", self.password_edit)

        buttons = QVBoxLayout()
        login_btn = QPushButton("ورود")
        register_btn = QPushButton("ثبت‌نام جدید")
        login_btn.clicked.connect(self.login)
        register_btn.clicked.connect(self.register)

        buttons.addWidget(login_btn)
        buttons.addWidget(register_btn)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addStretch()

    def get_credentials(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور الزامی هستند.")
            return None, None
        return username, password

    def login(self):
        username, password = self.get_credentials()
        if not username:
            return
        db_path = USERS_DIR / f"{username}.db"
        salt_path = USERS_DIR / f"{username}_salt.bin"
        if not db_path.exists() or not salt_path.exists():
            QMessageBox.warning(self, "خطا", "کاربر یافت نشد.")
            return

        try:
            key = derive_db_key(password, salt_path.read_bytes())
            conn = sqlite.connect(str(db_path))
            conn.execute(f"PRAGMA key = '{key}'")
            conn.execute("SELECT 1 FROM tasks LIMIT 1")
            conn.close()
            self.username = username
            self.password = password
            self.accept()
        except:
            QMessageBox.critical(self, "خطا", "رمز عبور اشتباه است.")

    def register(self):
        username, password = self.get_credentials()
        if not username:
            return
        db_path = USERS_DIR / f"{username}.db"
        if db_path.exists():
            QMessageBox.information(self, "اطلاع", "کاربر قبلاً وجود دارد. لطفاً وارد شوید.")
            return

        try:
            TaskManager(username, password)
            QMessageBox.information(self, "موفقیت", f"کاربر {username} با موفقیت ثبت شد.")
            self.username = username
            self.password = password
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "خطا", "خطا در ثبت‌نام.")

# -------------------- Main Window --------------------
class MainWindow(QMainWindow):
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"آیزن‌فلو – خوش آمدید {username}")
        self.resize(1700, 1000)

        self.task_manager = TaskManager(username, password)

        central = QWidget()
        self.setCentralWidget(central)
        self.grid = QGridLayout(central)
        self.grid.setSpacing(30)

        # پس‌زمینه ایرانی
        background_paths = ["bg.webp", "bg.jpg", "bg.png"]
        background_pixmap = None
        for path in background_paths:
            if os.path.exists(path):
                background_pixmap = QPixmap(path)
                if not background_pixmap.isNull():
                    break

        palette = QPalette()
        if background_pixmap and not background_pixmap.isNull():
            palette.setBrush(QPalette.Window, QBrush(background_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)))
        else:
            palette.setColor(QPalette.Window, QColor(10, 30, 60))  # پشتیبان آبی تیره
        central.setPalette(palette)

        self.quad_widgets = {}
        quadrants = [
            ("Q1", "مهم و فوری"),
            ("Q2", "مهم اما غیرفوری"),
            ("Q3", "فوری اما غیرمهم"),
            ("Q4", "غیرمهم و غیرفوری")
        ]

        for i, (key, label) in enumerate(quadrants):
            q_widget = QuadrantWidget(key, label, self.task_manager)
            q_widget.setCursor(Qt.PointingHandCursor)
            q_widget.installEventFilter(self)
            self.quad_widgets[key] = q_widget
            row = 0 if i < 2 else 1
            col = i % 2
            self.grid.addWidget(q_widget, row, col)

        self.add_btn = QPushButton("افزودن وظیفه جدید")
        self.add_btn.clicked.connect(self.add_new_task)
        self.add_btn.setStyleSheet("""
            background-color: #FFD700; color: #000080; font-size: 18px; padding: 15px; 
            border-radius: 15px; font-weight: bold; min-width: 200px;
        """)

        self.logout_btn = QPushButton("خروج از حساب")
        self.logout_btn.clicked.connect(self.logout)
        self.logout_btn.setStyleSheet("""
            background-color: #C21807; color: white; font-size: 18px; padding: 15px; 
            border-radius: 15px; font-weight: bold; min-width: 200px;
        """)

        self.exit_btn = QPushButton("← بازگشت")
        self.exit_btn.clicked.connect(self.exit_focus_mode)
        self.exit_btn.setVisible(False)
        self.exit_btn.setStyleSheet("font-size: 18px; padding: 10px; background-color: #FFD700; color: #000080; border-radius: 10px;")

        status_bar = self.statusBar()
        status_bar.addPermanentWidget(self.add_btn)
        status_bar.addPermanentWidget(self.logout_btn)
        status_bar.addPermanentWidget(self.exit_btn)

        self.current_quadrant: Optional[str] = None

        central.setAcceptDrops(True)
        central.dragEnterEvent = lambda e: e.accept() if e.mimeData().hasFormat("application/x-task-id") else None
        central.dropEvent = self.central_drop

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress and source in self.quad_widgets.values():
            key = next(k for k, w in self.quad_widgets.items() if w == source)
            self.enter_focus_mode(key)
        return super().eventFilter(source, event)

    def central_drop(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            task_id_str = event.mimeData().data("application/x-task-id").data().decode()
            task_id = uuid.UUID(task_id_str)
            tasks = self.task_manager.get_all_tasks()
            task = next((t for t in tasks if t.id == task_id), None)
            if task:
                pos = event.position().toPoint()
                for key, widget in self.quad_widgets.items():
                    if widget.geometry().contains(pos):
                        task.quadrant = key
                        self.task_manager.update_task(task)
                        break
            event.accept()

    def enter_focus_mode(self, quadrant_key: str):
        if self.current_quadrant == quadrant_key:
            return
        self.current_quadrant = quadrant_key
        self.exit_btn.setVisible(True)

        for key, q_widget in self.quad_widgets.items():
            target = 1.0 if key == quadrant_key else 0.3
            self.animate_opacity(q_widget.opacity_effect, target)
            q_widget.stack.setCurrentIndex(1 if key == quadrant_key else 0)

        stretches = {0:1, 1:1, 2:1, 3:1}
        idx = list(self.quad_widgets.keys()).index(quadrant_key)
        stretches[idx] = 4
        for i in range(2):
            for j in range(2):
                idx = i * 2 + j
                self.grid.setRowStretch(i, stretches[idx])
                self.grid.setColumnStretch(j, stretches[idx])

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

    def logout(self):
        reply = QMessageBox.question(self, "خروج", "آیا مطمئن هستید؟")
        if reply == QMessageBox.Yes:
            self.close()
            login_dialog = LoginDialog()
            if login_dialog.exec() == QDialog.Accepted:
                new_window = MainWindow(login_dialog.username, login_dialog.password)
                new_window.show()
            else:
                QApplication.quit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.current_quadrant:
            self.exit_focus_mode()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Tahoma", 12))

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 30, 60))
    palette.setColor(QPalette.WindowText, QColor(255, 215, 0))
    palette.setColor(QPalette.Base, QColor(0, 80, 100))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(255, 215, 0, 200))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 128))
    app.setPalette(palette)

    login_dialog = LoginDialog()
    if login_dialog.exec() == QDialog.Accepted:
        window = MainWindow(login_dialog.username, login_dialog.password)
        window.show()
        sys.exit(app.exec())