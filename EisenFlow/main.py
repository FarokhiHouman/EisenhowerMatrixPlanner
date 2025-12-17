import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QListWidget, QListWidgetItem, QFrame, QHBoxLayout,
    QGraphicsOpacityEffect, QStackedWidget
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPalette, QColor, QDrag
from PySide6.QtCore import QMimeData

class TaskWidget(QFrame):
    def __init__(self, title: str, description: str = "", quadrant: str = "", status: str = "To Do"):
        super().__init__()
        self.title = title
        self.description = description
        self.quadrant = quadrant
        self.status = status

        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setMinimumSize(QSize(200, 100))
        self.setMaximumWidth(300)
        self.setStyleSheet(self.get_style_for_quadrant(quadrant))

        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("font-size: 12px; color: #555;")
            layout.addWidget(desc_label)

        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignRight)
        status_label.setStyleSheet("font-size: 10px; color: #777; font-style: italic;")
        layout.addWidget(status_label)

        self.setAcceptDrops(True)

    def get_style_for_quadrant(self, quadrant):
        colors = {
            "Q1": "background-color: #ffcccc; border: 2px solid #ff4444;",
            "Q2": "background-color: #ccffcc; border: 2px solid #44ff44;",
            "Q3": "background-color: #ffffcc; border: 2px solid #ffff44;",
            "Q4": "background-color: #e6e6e6; border: 2px solid #aaaaaa;",
        }
        return colors.get(quadrant, "background-color: #f0f0f0; border: 1px solid #ccc;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, 'drag_start_position'):
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(f"{self.title}|{self.description}|{self.quadrant}|{self.status}")
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction | Qt.CopyAction)


class DropListWidget(QListWidget):
    def __init__(self, allowed_status=None, parent=None):
        super().__init__(parent)
        self.allowed_status = allowed_status
        self.setAcceptDrops(True)
        self.setStyleSheet("background-color: #f8f8f8; border: 1px dashed #aaa; min-height: 200px;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        text = event.mimeData().text()
        title, desc, quad, old_status = text.split("|", 3)  # ایمن‌تر برای split

        # وضعیت جدید بر اساس ستون مقصد تعیین می‌شود
        new_status = self.allowed_status if self.allowed_status else old_status

        task = TaskWidget(title, desc, quad, new_status)
        item = QListWidgetItem(self)
        item.setSizeHint(task.sizeHint())
        self.setItemWidget(item, task)

        # حذف کارت از منبع فقط اگر MoveAction باشد و source یک QListWidget معتبر باشد
        if event.dropAction() == Qt.MoveAction:
            source = event.source()
            if isinstance(source, QListWidget):
                for i in reversed(range(source.count())):
                    source_item = source.item(i)
                    if source_item is None:
                        continue
                    source_widget = source.itemWidget(source_item)
                    if source_widget and hasattr(source_widget, 'title') and hasattr(source_widget, 'description'):
                        if source_widget.title == title and source_widget.description == desc:
                            source.takeItem(i)
                            break

        event.acceptProposedAction()

        # به‌روزرسانی پیش‌نمایش در Overview Mode (اگر لازم باشد)
        if hasattr(self, 'viewport') and self.parent() and hasattr(self.parent(), 'parent'):
            main_window = self.window()
            if isinstance(main_window, QMainWindow) and hasattr(main_window, 'update_quadrant_preview'):
                main_window.update_quadrant_preview(quad)
class QuadrantWidget(QWidget):
    def __init__(self, key: str, label_text: str):
        super().__init__()
        self.key = key
        self.label_text = label_text

        self.setStyleSheet("background-color: #ffffff; border: 2px solid #ccc; border-radius: 10px;")
        self.layout = QVBoxLayout(self)

        self.title_label = QLabel(label_text)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(self.title_label)

        self.count_label = QLabel("0 وظیفه")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.count_label)

        self.preview_stack = QStackedWidget()
        self.overview_list = DropListWidget()
        self.overview_list.setMaximumHeight(300)
        self.overview_list.setFlow(QListWidget.LeftToRight)
        self.overview_list.setWrapping(True)

        self.kanban_widget = QWidget()
        self.kanban_layout = QHBoxLayout(self.kanban_widget)
        self.kanban_lists = {}
        for col in ["To Do", "Doing", "Done"]:
            container = QWidget()
            vlay = QVBoxLayout(container)
            lbl = QLabel(col)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            vlay.addWidget(lbl)
            list_w = DropListWidget(col)
            self.kanban_lists[col] = list_w
            vlay.addWidget(list_w)
            self.kanban_layout.addWidget(container)

        self.preview_stack.addWidget(self.overview_list)
        self.preview_stack.addWidget(self.kanban_widget)
        self.layout.addWidget(self.preview_stack)

        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)


class AddTaskDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("افزودن وظیفه جدید")
        layout = QFormLayout(self)

        self.title_edit = QLineEdit()
        self.desc_edit = QLineEdit()
        self.urgency_combo = QComboBox()
        self.urgency_combo.addItems(["فوری", "غیرفوری"])
        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["مهم", "غیرمهم"])

        layout.addRow("عنوان:", self.title_edit)
        layout.addRow("توضیح:", self.desc_edit)
        layout.addRow("فوریت:", self.urgency_combo)
        layout.addRow("اهمیت:", self.importance_combo)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("اضافه کن")
        cancel_btn = QPushButton("انصراف")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)

        layout.addRow(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EisenFlow - Focus Mode")
        self.resize(1400, 800)
        self.current_quadrant = None

        central = QWidget()
        self.setCentralWidget(central)
        self.grid = QGridLayout(central)
        self.grid.setSpacing(20)

        self.quad_widgets = {}
        quadrants = [("Q1", "مهم و فوری"), ("Q2", "مهم اما غیرفوری"),
                     ("Q3", "فوری اما غیرمهم"), ("Q4", "غیرمهم و غیرفوری")]

        for i, (key, label) in enumerate(quadrants):
            q_widget = QuadrantWidget(key, label)
            q_widget.mousePressEvent = lambda e, k=key: self.enter_focus_mode(k)
            q_widget.setCursor(Qt.PointingHandCursor)
            self.quad_widgets[key] = q_widget
            row = 0 if i < 2 else 1
            col = i % 2
            self.grid.addWidget(q_widget, row, col)

        self.add_btn = QPushButton("افزودن وظیفه جدید")
        self.add_btn.clicked.connect(self.add_new_task)
        self.exit_focus_btn = QPushButton("خروج از Focus Mode")
        self.exit_focus_btn.clicked.connect(self.exit_focus_mode)
        self.exit_focus_btn.setVisible(False)

        status_bar = self.statusBar()
        status_bar.addPermanentWidget(self.add_btn)
        status_bar.addPermanentWidget(self.exit_focus_btn)

    def get_quadrant_color(self, quad):
        colors = {"Q1": "#ffaaaa", "Q2": "#aaffaa", "Q3": "#ffffaa", "Q4": "#dddddd"}
        return colors.get(quad, "#f0f0f0")

    def enter_focus_mode(self, quadrant_key):
        if self.current_quadrant == quadrant_key:
            return

        self.current_quadrant = quadrant_key
        self.exit_focus_btn.setVisible(True)

        central = self.centralWidget()
        central.setStyleSheet(f"background-color: {self.get_quadrant_color(quadrant_key)};")

        for key, q_widget in self.quad_widgets.items():
            if key == quadrant_key:
                self.animate_opacity(q_widget.opacity_effect, 1.0)
                q_widget.preview_stack.setCurrentWidget(q_widget.kanban_widget)
            else:
                self.animate_opacity(q_widget.opacity_effect, 0.3)
                q_widget.preview_stack.setCurrentWidget(q_widget.overview_list)
                self.update_quadrant_preview(key)

        for i in range(2):
            for j in range(2):
                idx = i * 2 + j
                key = list(self.quad_widgets.keys())[idx]
                if key == quadrant_key:
                    self.grid.setRowStretch(i, 5)
                    self.grid.setColumnStretch(j, 5)
                else:
                    self.grid.setRowStretch(i, 1)
                    self.grid.setColumnStretch(j, 1)

    def exit_focus_mode(self):
        if not self.current_quadrant:
            return

        self.current_quadrant = None
        self.exit_focus_btn.setVisible(False)
        central = self.centralWidget()
        central.setStyleSheet("background-color: #ffffff;")

        for key, q_widget in self.quad_widgets.items():
            self.animate_opacity(q_widget.opacity_effect, 1.0)
            q_widget.preview_stack.setCurrentWidget(q_widget.overview_list)
            self.update_quadrant_preview(key)

        for i in range(2):
            self.grid.setRowStretch(i, 1)
            self.grid.setColumnStretch(i, 1)

    def animate_opacity(self, effect, target):
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(400)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(target)
        anim.start()

    def update_quadrant_preview(self, quadrant):
        q_widget = self.quad_widgets[quadrant]
        overview_list = q_widget.overview_list
        overview_list.clear()
        count = 0
        for col in ["To Do", "Doing", "Done"]:
            kanban_list = q_widget.kanban_lists[col]
            for i in range(kanban_list.count()):
                if count >= 3:
                    break
                item_widget = kanban_list.itemWidget(kanban_list.item(i))
                if item_widget:
                    new_task = TaskWidget(item_widget.title, item_widget.description, quadrant, col)
                    new_item = QListWidgetItem(overview_list)
                    new_item.setSizeHint(new_task.sizeHint())
                    overview_list.setItemWidget(new_item, new_task)
                    count += 1
        q_widget.count_label.setText(f"{count} وظیفه")

    def add_new_task(self):
        dialog = AddTaskDialog()
        if dialog.exec() == QDialog.Accepted:
            title = dialog.title_edit.text().strip()
            if not title:
                QMessageBox.warning(self, "خطا", "عنوان وظیفه نمی‌تواند خالی باشد.")
                return
            desc = dialog.desc_edit.text().strip()
            urgency = "فوری" if dialog.urgency_combo.currentText() == "فوری" else "غیرفوری"
            importance = "مهم" if dialog.importance_combo.currentText() == "مهم" else "غیرمهم"

            quadrant = "Q1" if importance == "مهم" and urgency == "فوری" else \
                       "Q2" if importance == "مهم" else \
                       "Q3" if urgency == "فوری" else "Q4"

            task = TaskWidget(title, desc, quadrant, "To Do")
            q_widget = self.quad_widgets[quadrant]
            to_do_list = q_widget.kanban_lists["To Do"]
            item = QListWidgetItem(to_do_list)
            item.setSizeHint(task.sizeHint())
            to_do_list.setItemWidget(item, task)

            self.update_quadrant_preview(quadrant)
            if self.current_quadrant == quadrant:
                self.centralWidget().setStyleSheet(f"background-color: {self.get_quadrant_color(quadrant)};")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.current_quadrant:
            self.exit_focus_mode()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(70, 70, 70))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())