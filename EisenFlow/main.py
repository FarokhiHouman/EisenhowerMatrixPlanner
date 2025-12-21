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
    QGraphicsDropShadowEffect, QScrollArea, QMenu
)
from PySide6.QtCore import (
    Qt, QMimeData, Signal, QObject, QPropertyAnimation, QEasingCurve
)
from PySide6.QtGui import (
    QPalette, QColor, QDrag, QPixmap, QFont, QPainter, QCursor
)

# SQLCipher for database encryption
from sqlcipher3 import dbapi2 as sqlite

# -------------------- Crypto Setup --------------------
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logging.basicConfig(level=logging.INFO)

USERS_DIR = Path.home() / ".eisenflow_users"
USERS_DIR.mkdir(exist_ok=True)

def derive_db_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    return kdf.derive(password.encode('utf-8'))

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
        self.salt = self._get_or_create_salt()
        self.db_key = derive_db_key(password, self.salt)
        self.conn = None
        self._connect()
        self._create_table()
        del password

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
            key_hex = self.db_key.hex()
            self.conn.execute(f"PRAGMA key = \"x'{key_hex}'\"")
            self.conn.execute("PRAGMA kdf_iter = 256000")
            self.conn.execute("PRAGMA cipher_page_size = 4096")
            self.conn.execute("PRAGMA foreign_keys = ON")
            del self.db_key
            del key_hex
        except Exception as e:
            logging.error(f"Error connecting to database: {e}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()

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

    def get_tasks_by_quadrant(self, quadrant: str) -> List[Task]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, title, description, quadrant, status FROM tasks WHERE quadrant=?", (quadrant,))
            rows = cur.fetchall()
            return [Task(row[1], row[2], row[3], row[4], uuid.UUID(row[0])) for row in rows]
        except Exception as e:
            logging.error(f"Error reading tasks: {e}")
            return []

    def get_all_tasks(self) -> List[Task]:
        try:
            cur = self.conn.cursor()
            cur.execute("SELECT id, title, description, quadrant, status FROM tasks")
            rows = cur.fetchall()
            return [Task(row[1], row[2], row[3], row[4], uuid.UUID(row[0])) for row in rows]
        except Exception as e:
            logging.error(f"Error reading all tasks: {e}")
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
            logging.error(f"Error adding task: {e}")
            QMessageBox.critical(None, "خطا", "امکان افزودن وظیفه وجود ندارد.")

    def update_task(self, task: Task):
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE tasks SET title=?, description=?, quadrant=?, status=? WHERE id=?",
                    (task.title, task.description, task.quadrant, task.status, str(task.id))
                )
            signals.tasks_changed.emit()
        except Exception as e:
            logging.error(f"Error updating task: {e}")

    def delete_task(self, task_id: uuid.UUID):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM tasks WHERE id=?", (str(task_id),))
            signals.tasks_changed.emit()
        except Exception as e:
            logging.error(f"Error deleting task: {e}")

    def change_password(self, old_password: str, new_password: str):
        try:
            old_key = derive_db_key(old_password, self.salt)
            old_key_hex = old_key.hex()
            self.conn.execute(f"PRAGMA key = \"x'{old_key_hex}'\"")
            new_key = derive_db_key(new_password, self.salt)
            new_key_hex = new_key.hex()
            self.conn.execute(f"PRAGMA rekey = \"x'{new_key_hex}'\"")
            del old_key, old_key_hex, new_key, new_key_hex
        except Exception as e:
            logging.error(f"Error changing password: {e}")
            raise

# -------------------- Views --------------------
class TaskWidget(QFrame):
    def __init__(self, task: Task, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_manager = task_manager
        self.setMinimumHeight(170)
        self.setMinimumWidth(320)

        # Hybrid Glassmorphism + Neumorphism 2025
        self.setStyleSheet("""
            QFrame {
                background: rgba(35, 45, 70, 220);
                border-radius: 24px;
                border: 1px solid rgba(120, 180, 255, 80);
            }
            QFrame:hover {
                background: rgba(45, 60, 90, 240);
                border: 2px solid #78B4FF;
            }
        """)

        # Dual shadows for depth (neumorphic lift)
        outer = QGraphicsDropShadowEffect(self)
        outer.setBlurRadius(40)
        outer.setXOffset(0)
        outer.setYOffset(20)
        outer.setColor(QColor(0, 0, 0, 180))

        self.setGraphicsEffect(outer)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title_label = QLabel(task.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 20px; color: #FFFFFF;")
        layout.addWidget(title_label)

        if task.description:
            desc_label = QLabel(task.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 16px; color: #D0D0D0;")
            layout.addWidget(desc_label)

        layout.addStretch()

        status_label = QLabel(task.status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("""
            font-size: 16px; font-weight: bold; color: #FFFFFF;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(80, 140, 220, 200), stop:1 rgba(100, 160, 255, 200));
            padding: 14px; border-radius: 24px;
            border: 1px solid rgba(120, 180, 255, 120);
        """)
        layout.addWidget(status_label)

        self.setCursor(QCursor(Qt.OpenHandCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-task-id", str(self.task.id).encode())
            drag.setMimeData(mime)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            result = drag.exec(Qt.MoveAction)
            self.setCursor(QCursor(Qt.OpenHandCursor))
            if result == Qt.MoveAction:
                signals.tasks_changed.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog = EditTaskDialog(self.task, self.task_manager, self)
            if dialog.exec():
                self.task_manager.update_task(self.task)
                signals.tasks_changed.emit()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(35, 45, 70, 240);
                border-radius: 20px;
                border: 1px solid rgba(120, 180, 255, 100);
                color: #FFFFFF;
            }
        """)
        delete_action = menu.addAction("حذف وظیفه")
        action = menu.exec(event.globalPos())
        if action == delete_action:
            reply = QMessageBox.question(self, "تأیید", "حذف شود؟", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.task_manager.delete_task(self.task.id)
                signals.tasks_changed.emit()

class DraggableListWidget(QListWidget):
    def __init__(self, quadrant: str, task_manager: TaskManager):
        super().__init__()
        self.quadrant = quadrant
        self.task_manager = task_manager
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setStyleSheet("background: transparent; border: none;")

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None:
            return

        widget = self.itemWidget(item)
        if widget is None:
            return

        mime = QMimeData()
        mime.setData("application/x-task-id", str(widget.task.id).encode())

        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        drag.exec(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            self.setStyleSheet("border: 4px dashed #78B4FF; background: rgba(120, 180, 255, 60); border-radius: 25px;")
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("background: transparent; border: none;")

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            task_id_bytes = event.mimeData().data("application/x-task-id")
            task_id_str = bytes(task_id_bytes).decode('utf-8')
            task_id = uuid.UUID(task_id_str)
            for task in self.task_manager.get_all_tasks():
                if task.id == task_id:
                    task.quadrant = self.quadrant
                    self.task_manager.update_task(task)
                    break
            event.acceptProposedAction()
            signals.tasks_changed.emit()
        self.dragLeaveEvent(event)

class QuadrantWidget(QWidget):
    COLORS = {"Q1": "#FF6B6B", "Q2": "#51CF66", "Q3": "#FFD43B", "Q4": "#ADB5BD"}

    def __init__(self, key: str, label_text: str, task_manager: TaskManager):
        super().__init__()
        self.key = key
        self.label_text = label_text
        self.task_manager = task_manager

        color = self.COLORS[key]

        self.setStyleSheet(f"""
            QWidget {{
                background: rgba(25, 40, 65, 180);
                border-radius: 30px;
                border: 2px solid {color}66;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setXOffset(0)
        shadow.setYOffset(25)
        shadow.setColor(QColor(0, 0, 0, 220))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)

        header = QHBoxLayout()
        title = QLabel(label_text)
        title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        header.addWidget(title)
        header.addStretch()
        self.count = QLabel("0")
        self.count.setStyleSheet(f"font-size: 24px; color: {color}; background: rgba(0,0,0,120); padding: 14px; border-radius: 25px;")
        header.addWidget(self.count)
        layout.addLayout(header)

        self.list = DraggableListWidget(key, task_manager)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setWidget(self.list)
        layout.addWidget(scroll)

        self.setToolTip(f"{label_text}: وظایف را به اینجا بکشید")

        signals.tasks_changed.connect(self.update_views)
        self.update_views()

    def update_views(self):
        self.list.clear()
        tasks = self.task_manager.get_tasks_by_quadrant(self.key)
        for task in tasks:
            item = QListWidgetItem(self.list)
            widget = TaskWidget(task, self.task_manager)
            item.setSizeHint(widget.sizeHint())
            self.list.setItemWidget(item, widget)
        self.count.setText(str(len(tasks)))

class ModernDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet("""
            QDialog {
                background: rgba(30, 45, 70, 250);
                border-radius: 30px;
                border: 1px solid rgba(120, 180, 255, 100);
            }
            QLabel { color: #FFFFFF; font-size: 17px; font-weight: bold; }
            QLineEdit, QComboBox {
                background: rgba(50, 65, 95, 240);
                color: #FFFFFF;
                padding: 16px;
                border-radius: 18px;
                border: 1px solid rgba(120, 180, 255, 120);
                font-size: 16px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #78B4FF;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64B5FF, stop:1 #4787D9);
                color: white;
                padding: 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78B4FF, stop:1 #5A9EFF); }
            QPushButton:pressed { background: #3A6BB5; }
        """)

class AddTaskDialog(ModernDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__("افزودن وظیفه جدید", parent)
        self.task_manager = task_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.title = QLineEdit()
        self.title.setPlaceholderText("عنوان وظیفه را وارد کنید...")
        self.desc = QLineEdit()
        self.desc.setPlaceholderText("توضیحات اختیاری...")
        self.quadrant = QComboBox()
        self.quadrant.addItems(["Q1 - فوری و مهم", "Q2 - مهم اما غیرفوری", "Q3 - فوری اما غیرمهم", "Q4 - غیرفوری و غیرمهم"])

        form.addRow("عنوان:", self.title)
        form.addRow("توضیحات:", self.desc)
        form.addRow("ربع:", self.quadrant)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("افزودن")
        cancel = QPushButton("لغو")
        ok.clicked.connect(self.accept_task)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def accept_task(self):
        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان الزامی است")
            return
        q = self.quadrant.currentText().split(" - ")[0]
        task = Task(title, self.desc.text(), q)
        self.task_manager.add_task(task)
        self.accept()

class EditTaskDialog(ModernDialog):
    def __init__(self, task: Task, task_manager: TaskManager, parent=None):
        super().__init__("ویرایش وظیفه", parent)
        self.task = task
        self.task_manager = task_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.title = QLineEdit(task.title)
        self.title.setPlaceholderText("عنوان وظیفه...")
        self.desc = QLineEdit(task.description)
        self.desc.setPlaceholderText("توضیحات...")
        self.quadrant = QComboBox()
        self.quadrant.addItems(["Q1 - فوری و مهم", "Q2 - مهم اما غیرفوری", "Q3 - فوری اما غیرمهم", "Q4 - غیرفوری و غیرمهم"])
        self.quadrant.setCurrentText(f"{task.quadrant} - {['فوری و مهم','مهم اما غیرفوری','فوری اما غیرمهم','غیرفوری و غیرمهم'][int(task.quadrant[1])-1]}")

        form.addRow("عنوان:", self.title)
        form.addRow("توضیحات:", self.desc)
        form.addRow("ربع:", self.quadrant)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("به‌روزرسانی")
        cancel = QPushButton("لغو")
        ok.clicked.connect(self.accept_task)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def accept_task(self):
        title = self.title.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان الزامی است")
            return
        q = self.quadrant.currentText().split(" - ")[0]
        self.task.title = title
        self.task.description = self.desc.text()
        self.task.quadrant = q
        self.task_manager.update_task(self.task)
        self.accept()

class ChangePasswordDialog(ModernDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__("تغییر رمز عبور", parent)
        self.task_manager = task_manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(30)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.old_pass = QLineEdit()
        self.old_pass.setEchoMode(QLineEdit.Password)
        self.old_pass.setPlaceholderText("رمز عبور فعلی")
        self.new_pass = QLineEdit()
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.new_pass.setPlaceholderText("رمز عبور جدید")
        self.confirm_pass = QLineEdit()
        self.confirm_pass.setEchoMode(QLineEdit.Password)
        self.confirm_pass.setPlaceholderText("تکرار رمز عبور جدید")

        form.addRow("رمز عبور فعلی:", self.old_pass)
        form.addRow("رمز عبور جدید:", self.new_pass)
        form.addRow("تکرار:", self.confirm_pass)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        ok = QPushButton("تغییر")
        cancel = QPushButton("لغو")
        ok.clicked.connect(self.validate_and_change)
        cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(ok)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)

    def validate_and_change(self):
        old = self.old_pass.text()
        new = self.new_pass.text()
        confirm = self.confirm_pass.text()
        if not all([old, new, confirm]):
            QMessageBox.warning(self, "خطا", "تمام فیلدها الزامی هستند.")
            return
        if new != confirm:
            QMessageBox.warning(self, "خطا", "رمزهای جدید مطابقت ندارند.")
            return
        try:
            self.task_manager.change_password(old, new)
            QMessageBox.information(self, "موفقیت", "رمز عبور تغییر یافت.")
            self.accept()
        except:
            QMessageBox.critical(self, "خطا", "رمز عبور فعلی اشتباه است.")

class LoginDialog(ModernDialog):
    def __init__(self):
        super().__init__("EisenFlow - ورود / ثبت‌نام")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(70, 70, 70, 70)
        layout.setSpacing(35)

        title = QLabel("EisenFlow")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 52px; font-weight: bold; color: #78B4FF;")
        layout.addWidget(title)

        subtitle = QLabel("مدیریت هوشمند وظایف با ماتریس آیزنهاور")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 20px; color: #C0C0C0;")
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setHorizontalSpacing(25)
        form.setVerticalSpacing(20)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("نام کاربری خود را وارد کنید")
        self.username_edit.setMinimumHeight(60)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("رمز عبور")
        self.password_edit.setMinimumHeight(60)

        form.addRow("نام کاربری:", self.username_edit)
        form.addRow("رمز عبور:", self.password_edit)
        layout.addLayout(form)

        login_btn = QPushButton("ورود / ثبت‌نام")
        login_btn.setMinimumHeight(70)
        login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78B4FF, stop:1 #5A9EFF);
                color: white; padding: 20px; border-radius: 30px; font-size: 22px; font-weight: bold;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8AC4FF, stop:1 #64B5FF); }
            QPushButton:pressed { background: #3A6BB5; }
        """)
        login_btn.clicked.connect(self.try_login)
        layout.addWidget(login_btn, alignment=Qt.AlignCenter)

        self.username = None
        self.password = None

    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        if not username or not password:
            QMessageBox.warning(self, "خطا", "نام کاربری و رمز عبور الزامی است.")
            return

        db_path = USERS_DIR / f"{username}.db"
        salt_path = USERS_DIR / f"{username}_salt.bin"

        if not db_path.exists() or not salt_path.exists():
            try:
                task_manager = TaskManager(username, password)
                task_manager.close()
                QMessageBox.information(self, "موفقیت", "کاربر جدید با موفقیت ایجاد شد.")
                self.username = username
                self.password = password
                self.accept()
                return
            except:
                QMessageBox.critical(self, "خطا", "خطا در ایجاد کاربر جدید.")
                return

        try:
            task_manager = TaskManager(username, password)
            task_manager.close()
            self.username = username
            self.password = password
            self.accept()
        except:
            QMessageBox.critical(self, "خطا", "نام کاربری یا رمز عبور اشتباه است.")

class BackgroundWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background: #0F1A2B;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(15, 25, 45))

class MainWindow(QMainWindow):
    def __init__(self, username: str, password: str):
        super().__init__()
        self.setWindowTitle(f"EisenFlow – {username}")
        self.setMinimumSize(1600, 900)
        self.task_manager = TaskManager(username, password)

        bg = BackgroundWidget()
        self.setCentralWidget(bg)
        grid = QGridLayout(bg)
        grid.setSpacing(40)
        grid.setContentsMargins(50, 50, 50, 50)

        quadrants = [
            ("Q1", "فوری و مهم"),
            ("Q2", "مهم اما غیرفوری"),
            ("Q3", "فوری اما غیرمهم"),
            ("Q4", "غیرفوری و غیرمهم")
        ]

        for i, (k, l) in enumerate(quadrants):
            q = QuadrantWidget(k, l, self.task_manager)
            r, c = divmod(i, 2)
            grid.addWidget(q, r, c)
            grid.setRowStretch(r, 1)
            grid.setColumnStretch(c, 1)

        toolbar = QHBoxLayout()
        add = QPushButton("افزودن وظیفه جدید")
        add.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #64B5FF, stop:1 #4787D9);
                color: white; padding: 20px; border-radius: 30px; font-size: 20px; font-weight: bold;
                min-width: 320px; border: 2px solid rgba(120, 180, 255, 120);
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78B4FF, stop:1 #5A9EFF); }
        """)
        add.clicked.connect(lambda: AddTaskDialog(self.task_manager, self).exec())

        change = QPushButton("تغییر رمز عبور")
        change.setStyleSheet(add.styleSheet().replace("#64B5FF", "#FF9800").replace("#4787D9", "#F57C00"))

        change.clicked.connect(lambda: ChangePasswordDialog(self.task_manager, self).exec())

        toolbar.addStretch()
        toolbar.addWidget(add)
        toolbar.addWidget(change)
        toolbar.addStretch()

        grid.addLayout(toolbar, 2, 0, 1, 2, Qt.AlignCenter)

    def closeEvent(self, event):
        self.task_manager.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 12))

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 25, 45))
    palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
    palette.setColor(QPalette.Base, QColor(30, 45, 70))
    palette.setColor(QPalette.Text, QColor(240, 240, 240))
    palette.setColor(QPalette.Button, QColor(50, 70, 100))
    palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
    app.setPalette(palette)

    login = LoginDialog()
    if login.exec() == QDialog.Accepted:
        win = MainWindow(login.username, login.password)
        win.show()
        sys.exit(app.exec())