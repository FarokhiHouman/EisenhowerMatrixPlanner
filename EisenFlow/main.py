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
    QPalette, QColor, QDrag, QPixmap, QBrush, QFont, QPainter
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
        # پاک کردن password از حافظه پس از استفاده
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
            # پاک کردن کلید از حافظه
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
        """تغییر رمز عبور با استفاده از PRAGMA rekey"""
        try:
            # باز کردن اتصال با کلید قدیمی
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
    FIXED_HEIGHT = 180

    def __init__(self, task: Task, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task = task
        self.task_manager = task_manager
        self.setFixedHeight(self.FIXED_HEIGHT)
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(0, 50, 100, 240), stop:1 rgba(0, 30, 80, 240));
                border-radius: 30px;
                border: 3px solid #FFD700;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        title_label = QLabel(task.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 20px; color: #FFD700;")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Bold))
        layout.addWidget(title_label)

        if task.description:
            desc_label = QLabel(task.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 15px; color: #FFFFFF; background-color: rgba(0,0,0,80); padding: 10px; border-radius: 10px;")
            layout.addWidget(desc_label)

        layout.addStretch()

        status_label = QLabel(task.status)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("""
            font-size: 16px; font-weight: bold; color: #001F3F;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFD700, stop:1 #FFA500);
            padding: 12px; border-radius: 20px; border: 2px solid #001F3F;
        """)
        layout.addWidget(status_label)

        # انیمیشن hover ساده
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        # shadow اصلی را نگه می‌داریم اما opacity برای hover

    def enterEvent(self, event):
        anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.8)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0.8)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData("application/x-task-id", str(self.task.id).encode())
            drag.setMimeData(mime)
            pixmap = self.grab()
            drag.setPixmap(pixmap)
            drag.exec_(Qt.MoveAction)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog = EditTaskDialog(self.task, self.task_manager, self)
            if dialog.exec():
                self.task_manager.update_task(self.task)
                self.parent().parent().update_views()
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("background-color: #001F3F; color: #FFD700; border: 1px solid #FFD700;")
        delete_action = menu.addAction("حذف وظیفه")
        action = menu.exec(event.globalPos())
        if action == delete_action:
            reply = QMessageBox.question(
                self, "تأیید حذف",
                "آیا از حذف این وظیفه اطمینان دارید؟ این عمل قابل بازگشت نیست.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.task_manager.delete_task(self.task.id)
                self.parent().parent().update_views()

class DraggableListWidget(QListWidget):
    def __init__(self, quadrant: str, task_manager: TaskManager):
        super().__init__()
        self.quadrant = quadrant
        self.task_manager = task_manager
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-task-id"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat("application/x-task-id"):
            task_id_str = bytes(mime.data("application/x-task-id")).decode()
            task_id = uuid.UUID(task_id_str)
            for task in self.task_manager.get_all_tasks():  # بهبود با cache در آینده
                if task.id == task_id:
                    task.quadrant = self.quadrant
                    self.task_manager.update_task(task)
                    break
            event.acceptProposedAction()
            signals.tasks_changed.emit()

class QuadrantWidget(QWidget):
    def __init__(self, key: str, label_text: str, task_manager: TaskManager):
        super().__init__()
        self.key = key
        self.label_text = label_text
        self.task_manager = task_manager

        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 60, 120, 240), stop:1 rgba(0, 40, 80, 240));
                border-radius: 35px;
                border: 4px solid #FFD700;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(15)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        title_label = QLabel(label_text)
        title_label.setStyleSheet("font-size: 34px; font-weight: bold; color: #FFD700;")
        title_label.setFont(QFont("Segoe UI", 34, QFont.Bold))
        header.addWidget(title_label)
        header.addStretch()
        self.count_label = QLabel("0 وظیفه")
        self.count_label.setStyleSheet("font-size: 24px; color: #FFFFFF; background-color: rgba(0,0,0,150); padding: 12px; border-radius: 20px;")
        header.addWidget(self.count_label)
        layout.addLayout(header)

        self.list_widget = DraggableListWidget(key, task_manager)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll)

        signals.tasks_changed.connect(self.update_views)
        self.update_views()

    def update_views(self):
        self.list_widget.clear()
        tasks = self.task_manager.get_tasks_by_quadrant(self.key)
        for task in tasks:
            item = QListWidgetItem(self.list_widget)
            widget = TaskWidget(task, self.task_manager, self.list_widget)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.setItemWidget(item, widget)
        self.count_label.setText(f"{len(tasks)} وظیفه")

class AddTaskDialog(QDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.setWindowTitle("افزودن وظیفه جدید")
        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        self.quadrant_combo = QComboBox()
        self.quadrant_combo.addItems(["Q1", "Q2", "Q3", "Q4"])

        layout.addRow("عنوان:", self.title_edit)
        layout.addRow("توضیحات:", self.desc_edit)
        layout.addRow("ربع:", self.quadrant_combo)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("افزودن")
        cancel_btn = QPushButton("لغو")
        ok_btn.clicked.connect(self.validate_and_accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)

    def validate_and_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان وظیفه الزامی است.")
            return
        task = Task(title, self.desc_edit.text(), self.quadrant_combo.currentText())
        self.task_manager.add_task(task)
        self.accept()

class EditTaskDialog(AddTaskDialog):
    def __init__(self, task: Task, task_manager: TaskManager, parent=None):
        super().__init__(task_manager, parent)
        self.task = task
        self.setWindowTitle("ویرایش وظیفه")
        self.title_edit.setText(task.title)
        self.desc_edit.setText(task.description)
        self.quadrant_combo.setCurrentText(task.quadrant)

    def validate_and_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "خطا", "عنوان وظیفه الزامی است.")
            return
        self.task.title = title
        self.task.description = self.desc_edit.text()
        self.task.quadrant = self.quadrant_combo.currentText()
        self.task_manager.update_task(self.task)
        self.accept()

class ChangePasswordDialog(QDialog):
    def __init__(self, task_manager: TaskManager, parent=None):
        super().__init__(parent)
        self.task_manager = task_manager
        self.setWindowTitle("تغییر رمز عبور")
        layout = QFormLayout(self)

        self.old_pass = QLineEdit()
        self.old_pass.setEchoMode(QLineEdit.Password)
        self.new_pass = QLineEdit()
        self.new_pass.setEchoMode(QLineEdit.Password)
        self.confirm_pass = QLineEdit()
        self.confirm_pass.setEchoMode(QLineEdit.Password)

        layout.addRow("رمز عبور فعلی:", self.old_pass)
        layout.addRow("رمز عبور جدید:", self.new_pass)
        layout.addRow("تکرار رمز عبور جدید:", self.confirm_pass)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("تغییر")
        cancel_btn = QPushButton("لغو")
        ok_btn.clicked.connect(self.validate_and_change)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addRow(buttons)

    def validate_and_change(self):
        old = self.old_pass.text()
        new = self.new_pass.text()
        confirm = self.confirm_pass.text()
        if not old or not new or not confirm:
            QMessageBox.warning(self, "خطا", "تمام فیلدها الزامی هستند.")
            return
        if new != confirm:
            QMessageBox.warning(self, "خطا", "رمزهای جدید مطابقت ندارند.")
            return
        try:
            self.task_manager.change_password(old, new)
            QMessageBox.information(self, "موفقیت", "رمز عبور با موفقیت تغییر یافت.")
            self.accept()
        except:
            QMessageBox.critical(self, "خطا", "رمز عبور فعلی اشتباه است.")

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ورود / ثبت‌نام")
        layout = QFormLayout(self)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        layout.addRow("نام کاربری:", self.username_edit)
        layout.addRow("رمز عبور:", self.password_edit)

        buttons = QHBoxLayout()
        login_btn = QPushButton("ورود / ثبت‌نام")
        login_btn.clicked.connect(self.try_login)
        buttons.addWidget(login_btn)
        layout.addRow(buttons)

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

        # اگر فایل‌ها وجود نداشته باشند، کاربر جدید است و ثبت‌نام موفق
        if not db_path.exists() or not salt_path.exists():
            try:
                # ایجاد کاربر جدید
                task_manager = TaskManager(username, password)
                task_manager.close()
                QMessageBox.information(self, "موفقیت", "کاربر جدید با موفقیت ایجاد شد.")
                self.username = username
                self.password = password
                self.accept()
                return
            except Exception as e:
                QMessageBox.critical(self, "خطا", "خطا در ایجاد کاربر جدید.")
                return

        # ورود موجود
        try:
            task_manager = TaskManager(username, password)
            task_manager.close()  # تست اتصال
            self.username = username
            self.password = password
            self.accept()
        except Exception:
            QMessageBox.critical(self, "خطا", "نام کاربری یا رمز عبور اشتباه است.")

class BackgroundWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.background_pixmap = None
        background_paths = ["bg1.jpg", "bg2.jpg", "bg3.jpg", "bg4.jpg", "bg5.jpg", "bg.webp", "bg.jpg", "bg.png"]
        for path_str in background_paths:
            path = Path(path_str)
            if path.exists():
                self.background_pixmap = QPixmap(str(path))
                if not self.background_pixmap.isNull():
                    break
        if not self.background_pixmap:
            self.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0A1E50, stop:1 #000A28);")

    def paintEvent(self, event):
        if self.background_pixmap:
            painter = QPainter(self)
            scaled = self.background_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)
        else:
            super().paintEvent(event)

class MainWindow(QMainWindow):
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"EisenFlow – خوش آمدید {username}")
        self.resize(1600, 900)
        self.task_manager = TaskManager(username, password)

        background = BackgroundWidget()
        self.setCentralWidget(background)
        self.grid = QGridLayout(background)
        self.grid.setSpacing(40)
        self.grid.setContentsMargins(40, 40, 40, 40)

        quadrants = [
            ("Q1", "فوری و مهم"),
            ("Q2", "مهم اما غیرفوری"),
            ("Q3", "فوری اما غیرمهم"),
            ("Q4", "غیرفوری و غیرمهم"),
        ]

        for i, (key, label) in enumerate(quadrants):
            quadrant_widget = QuadrantWidget(key, label, self.task_manager)
            row = i // 2
            col = i % 2
            self.grid.addWidget(quadrant_widget, row, col)
            self.grid.setRowStretch(row, 1)
            self.grid.setColumnStretch(col, 1)

        add_btn = QPushButton("افزودن وظیفه جدید")
        add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFD700, stop:1 #FFA500);
                color: #001F3F; font-size: 20px; padding: 18px; border-radius: 25px;
                font-weight: bold; min-width: 250px; border: 3px solid #001F3F;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #FFA500, stop:1 #FF8C00); }
        """)
        add_btn.clicked.connect(self.open_add_dialog)

        change_pass_btn = QPushButton("تغییر رمز عبور")
        change_pass_btn.setStyleSheet(add_btn.styleSheet())
        change_pass_btn.clicked.connect(self.open_change_password)

        self.grid.addWidget(add_btn, 2, 0, Qt.AlignCenter)
        self.grid.addWidget(change_pass_btn, 2, 1, Qt.AlignCenter)

    def open_add_dialog(self):
        dialog = AddTaskDialog(self.task_manager, self)
        dialog.exec()

    def open_change_password(self):
        dialog = ChangePasswordDialog(self.task_manager, self)
        if dialog.exec():
            QMessageBox.information(self, "موفقیت", "رمز عبور تغییر یافت. برنامه برای اعمال تغییرات بسته خواهد شد.")
            self.close()  # نیاز به ورود مجدد

    def closeEvent(self, event):
        self.task_manager.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 12))

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