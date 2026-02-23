import hashlib
import os
import sqlite3
import sys
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "Online"


def get_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
        data_dir = base / APP_NAME
    else:
        data_dir = Path.home() / f".{APP_NAME.lower()}"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DB_NAME = str(get_data_dir() / "online.db")
ERROR_LOG = get_data_dir() / "online_error.log"


def normalize_secret(value: str) -> str:
    return unicodedata.normalize("NFC", value).rstrip("\r\n")


def hash_password(password: str) -> str:
    normalized = normalize_secret(password)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, db_name: str = DB_NAME):
        self.connection = sqlite3.connect(db_name)
        self.connection.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(sender_id) REFERENCES users(id),
                FOREIGN KEY(receiver_id) REFERENCES users(id)
            )
            """
        )
        self.connection.commit()

    def create_user(self, login: str, password: str):
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (login, password_hash, created_at) VALUES (?, ?, ?)",
                (login, hash_password(password), datetime.now().isoformat(timespec="seconds")),
            )
            self.connection.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def authenticate(self, login: str, password: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE login = ? AND password_hash = ?",
            (login, hash_password(password)),
        )
        return cursor.fetchone()

    def find_users(self, current_user_id: int, query: str = ""):
        cursor = self.connection.cursor()
        like_q = f"%{query}%"
        cursor.execute(
            "SELECT id, login FROM users WHERE id != ? AND login LIKE ? ORDER BY login",
            (current_user_id, like_q),
        )
        return cursor.fetchall()

    def save_message(self, sender_id: int, receiver_id: int, text: str):
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO messages (sender_id, receiver_id, text, created_at) VALUES (?, ?, ?, ?)",
            (sender_id, receiver_id, text, datetime.now().isoformat(timespec="seconds")),
        )
        self.connection.commit()

    def get_messages(self, user_a: int, user_b: int):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT sender_id, receiver_id, text, created_at
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY id
            """,
            (user_a, user_b, user_b, user_a),
        )
        return cursor.fetchall()

    def get_dialogs(self, current_user_id: int):
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT
                u.id AS id,
                u.login AS login,
                MAX(m.id) AS last_message_id
            FROM users u
            LEFT JOIN messages m
                ON (m.sender_id = u.id AND m.receiver_id = ?)
                OR (m.receiver_id = u.id AND m.sender_id = ?)
            WHERE u.id != ?
            GROUP BY u.id, u.login
            ORDER BY COALESCE(last_message_id, 0) DESC, u.login ASC
            """,
            (current_user_id, current_user_id, current_user_id),
        )
        return cursor.fetchall()


class OnlineWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_user = None
        self.dialog_users = []
        self.selected_chat_user = None

        self.setWindowTitle("Online — мессенджер")
        self.resize(1220, 760)
        self.setMinimumSize(980, 640)
        self.setWindowIcon(self._make_icon())
        self.setStyleSheet(self._stylesheet())

        self.root = QWidget()
        self.setCentralWidget(self.root)
        self.root_layout = QVBoxLayout(self.root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)

        self.auth_widget = self._build_auth_ui()
        self.main_widget = self._build_main_ui()
        self.main_widget.hide()

        self.root_layout.addWidget(self.auth_widget)
        self.root_layout.addWidget(self.main_widget)

    def _make_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#2f7cf6"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.setPen(QPen(QColor("#ffffff"), 6))
        painter.drawEllipse(18, 18, 28, 28)
        painter.end()
        return QIcon(pixmap)

    def _stylesheet(self) -> str:
        return """
            QWidget { background: #eaf3ff; color: #1f2a3d; font-family: 'Segoe UI'; font-size: 14px; }
            #AuthCard { background: white; border-radius: 26px; border: 1px solid #dfe7f5; }
            #BrandTitle { color: #2f7cf6; font-size: 46px; font-weight: 800; }
            #AuthTitle { font-size: 34px; font-weight: 700; color: #182335; }
            #Hint { color: #7e8ea8; }
            QLineEdit { background: #f6f9ff; border: 1px solid #d7e2f4; border-radius: 12px; padding: 12px; }
            QLineEdit:focus { border-color: #2f7cf6; background: #ffffff; }
            QPushButton { background: #2f7cf6; color: white; border: none; border-radius: 12px; padding: 12px 14px; font-weight: 700; }
            QPushButton:hover { background: #2368d3; }
            #MainShell { background: #f7fbff; border-radius: 24px; border: 1px solid #d9e6fb; }
            #LeftRail { background: #f8fbff; border-right: 1px solid #e2ebfa; }
            #ChatsPanel { background: #ffffff; border-right: 1px solid #e2ebfa; }
            #ChatArea { background: #eef3fb; }
            #TopBar, #Composer { background: #ffffff; border-bottom: 1px solid #e2ebfa; }
            #Composer { border-top: 1px solid #e2ebfa; border-bottom: none; }
            #ProfilePanel { background: #ffffff; border-left: 1px solid #e2ebfa; }
            #SectionTitle { font-size: 11px; color: #8c9ab1; font-weight: 600; letter-spacing: 1px; }
            QListWidget { background: transparent; border: none; }
            QListWidget::item { padding: 10px; border-radius: 10px; margin: 2px 8px; }
            QListWidget::item:selected { background: #dfeeff; color: #10376a; }
            QTextEdit { background: #edf3fc; border: none; padding: 16px; }
            QRadioButton { color: #4f5f78; }
            #NavButton { background: transparent; color: #5d6f8f; text-align: left; padding: 8px 10px; border-radius: 10px; font-weight: 600; }
            #NavButton:hover { background: #e8f1ff; color: #2f7cf6; }
            #StoryChip { background: #f2f7ff; border: 1px solid #d8e7ff; border-radius: 16px; padding: 8px 10px; color: #44628f; }
            #InfoItem { color: #3c5275; padding: 5px 0; }
        """

    def _build_auth_ui(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(120, 40, 120, 40)

        card = QFrame()
        card.setObjectName("AuthCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 36, 42, 32)
        card_layout.setSpacing(10)

        brand = QLabel("Online")
        brand.setObjectName("BrandTitle")
        brand.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(brand)

        title = QLabel("Вход в Online")
        title.setObjectName("AuthTitle")
        title.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(title)

        subtitle = QLabel("Войдите в аккаунт или зарегистрируйтесь по логину и паролю")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("Hint")
        subtitle.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(subtitle)

        mode_row = QHBoxLayout()
        self.login_mode = QRadioButton("Вход")
        self.register_mode = QRadioButton("Регистрация")
        self.login_mode.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.login_mode)
        mode_group.addButton(self.register_mode)
        self.login_mode.toggled.connect(self._toggle_register_fields)
        mode_row.addWidget(self.login_mode)
        mode_row.addWidget(self.register_mode)
        mode_row.addStretch()
        card_layout.addLayout(mode_row)

        card_layout.addWidget(QLabel("Логин"))
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Введите логин")
        card_layout.addWidget(self.login_input)

        card_layout.addWidget(QLabel("Пароль"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Введите пароль")
        card_layout.addWidget(self.password_input)

        self.repeat_label = QLabel("Повторите пароль")
        self.repeat_input = QLineEdit()
        self.repeat_input.setEchoMode(QLineEdit.Password)
        self.repeat_input.setPlaceholderText("Повторите пароль")
        card_layout.addWidget(self.repeat_label)
        card_layout.addWidget(self.repeat_input)

        self.auth_button = QPushButton("Войти")
        self.auth_button.clicked.connect(self._handle_auth)
        card_layout.addWidget(self.auth_button)

        hint = QLabel("Современный сине-белый интерфейс Online. Для переписки создайте минимум 2 аккаунта.")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignHCenter)
        card_layout.addWidget(hint)

        layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        self._toggle_register_fields()
        return page

    def _build_main_ui(self) -> QWidget:
        container = QFrame()
        container.setObjectName("MainShell")
        root = QVBoxLayout(container)
        root.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter()

        left_rail = QFrame()
        left_rail.setObjectName("LeftRail")
        rail_layout = QVBoxLayout(left_rail)
        rail_layout.setContentsMargins(8, 12, 8, 12)
        rail_layout.setSpacing(4)
        rail_logo = QLabel("Online")
        rail_logo.setStyleSheet("font-size:18px; font-weight:800; color:#2f7cf6;")
        rail_layout.addWidget(rail_logo)
        for txt in ["Все чаты", "Личные", "Группы", "Каналы", "Избранное"]:
            btn = QPushButton(txt)
            btn.setObjectName("NavButton")
            rail_layout.addWidget(btn)
        rail_layout.addStretch()
        settings_btn = QPushButton("Настройки")
        settings_btn.setObjectName("NavButton")
        rail_layout.addWidget(settings_btn)

        chats_panel = QFrame()
        chats_panel.setObjectName("ChatsPanel")
        left_layout = QVBoxLayout(chats_panel)
        left_layout.setContentsMargins(12, 14, 12, 12)
        left_layout.setSpacing(10)

        self.user_label = QLabel("Вы вошли")
        self.user_label.setStyleSheet("font-weight:700; color:#28518d;")
        left_layout.addWidget(self.user_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск")
        self.search_input.textChanged.connect(self.load_dialogs)
        left_layout.addWidget(self.search_input)

        section_story = QLabel("STORY")
        section_story.setObjectName("SectionTitle")
        left_layout.addWidget(section_story)

        stories_row = QHBoxLayout()
        for name in ["Luna", "Mark", "Anna", "Leo"]:
            chip = QLabel(name)
            chip.setObjectName("StoryChip")
            stories_row.addWidget(chip)
        left_layout.addLayout(stories_row)

        section_chats = QLabel("CHATS")
        section_chats.setObjectName("SectionTitle")
        left_layout.addWidget(section_chats)

        self.dialog_list = QListWidget()
        self.dialog_list.itemSelectionChanged.connect(self._on_dialog_selected)
        left_layout.addWidget(self.dialog_list, 1)

        logout_btn = QPushButton("Выйти")
        logout_btn.clicked.connect(self.show_auth_page)
        left_layout.addWidget(logout_btn)

        center = QFrame()
        center.setObjectName("ChatArea")
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        self.chat_title = QLabel("Выберите диалог")
        self.chat_title.setStyleSheet("font-size:18px; font-weight:700; color:#21395f;")
        top_layout.addWidget(self.chat_title)
        top_layout.addStretch()
        top_layout.addWidget(QLabel("🔍  📞  ⋮"))
        center_layout.addWidget(top_bar)

        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)
        center_layout.addWidget(self.messages_view, 1)

        composer = QFrame()
        composer.setObjectName("Composer")
        composer_layout = QHBoxLayout(composer)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Напишите сообщение...")
        self.message_input.returnPressed.connect(self.send_message)
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.send_message)
        composer_layout.addWidget(self.message_input, 1)
        composer_layout.addWidget(send_btn)
        center_layout.addWidget(composer)

        details = QFrame()
        details.setObjectName("ProfilePanel")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(16, 18, 16, 18)

        details_title = QLabel("Профиль")
        details_title.setStyleSheet("font-size:22px; font-weight:800; color:#2f7cf6;")
        details_layout.addWidget(details_title)
        details_layout.addWidget(QLabel("Уведомления"))

        for item in [
            "+7 (999) 123-45-67",
            "@online_user",
            "43 Фото",
            "22 Видео",
            "54 Файла",
            "31 Музыка",
            "87 Голосовых",
        ]:
            row = QLabel(item)
            row.setObjectName("InfoItem")
            details_layout.addWidget(row)

        details_layout.addStretch()

        splitter.addWidget(left_rail)
        splitter.addWidget(chats_panel)
        splitter.addWidget(center)
        splitter.addWidget(details)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        splitter.setStretchFactor(3, 2)

        root.addWidget(splitter)
        return container

    def _toggle_register_fields(self):
        is_register = self.register_mode.isChecked()
        self.repeat_label.setVisible(is_register)
        self.repeat_input.setVisible(is_register)
        self.auth_button.setText("Создать аккаунт" if is_register else "Войти")
        if not is_register:
            self.repeat_input.clear()

    def _handle_auth(self):
        login = self.login_input.text().strip()
        password = normalize_secret(self.password_input.text())

        if len(login) < 3:
            QMessageBox.critical(self, "Ошибка", "Логин должен быть не короче 3 символов.")
            return
        if len(password) < 4:
            QMessageBox.critical(self, "Ошибка", "Пароль должен быть не короче 4 символов.")
            return

        if self.register_mode.isChecked():
            repeat = normalize_secret(self.repeat_input.text())
            if password != repeat:
                QMessageBox.critical(self, "Ошибка", "Пароли не совпадают.")
                return
            user_id = self.db.create_user(login, password)
            if user_id is None:
                QMessageBox.critical(self, "Ошибка", "Пользователь с таким логином уже существует.")
                return
            self.current_user = {"id": user_id, "login": login}
            self.show_main_page()
            return

        user = self.db.authenticate(login, password)
        if user is None:
            QMessageBox.critical(self, "Ошибка", "Неверный логин или пароль.")
            return
        self.current_user = dict(user)
        self.show_main_page()

    def show_auth_page(self):
        self.main_widget.hide()
        self.auth_widget.show()
        self.password_input.clear()
        self.repeat_input.clear()

    def show_main_page(self):
        self.auth_widget.hide()
        self.main_widget.show()
        self.user_label.setText(f"@{self.current_user['login']}")
        self.load_dialogs()

    def load_dialogs(self):
        if not self.current_user:
            return
        query = self.search_input.text().strip()
        rows = self.db.get_dialogs(self.current_user["id"]) if not query else self.db.find_users(self.current_user["id"], query)
        self.dialog_users = [dict(r) for r in rows]

        self.dialog_list.clear()
        for user in self.dialog_users:
            item = QListWidgetItem(f"@{user['login']}")
            self.dialog_list.addItem(item)

    def _on_dialog_selected(self):
        idx = self.dialog_list.currentRow()
        if idx < 0 or idx >= len(self.dialog_users):
            return
        self.selected_chat_user = self.dialog_users[idx]
        self.chat_title.setText(f"@{self.selected_chat_user['login']}")
        self.render_messages()

    def render_messages(self):
        if not self.selected_chat_user:
            return
        messages = self.db.get_messages(self.current_user["id"], self.selected_chat_user["id"])
        html_parts = []
        for msg in messages:
            is_me = msg["sender_id"] == self.current_user["id"]
            align = "right" if is_me else "left"
            bg = "#b025ff" if is_me else "#ffffff"
            fg = "#ffffff" if is_me else "#2c2d45"
            who = "Вы" if is_me else f"@{self.selected_chat_user['login']}"
            stamp = msg["created_at"].replace("T", " ")
            safe_text = msg["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(
                f"""
                <div style='text-align:{align}; margin:8px 0;'>
                    <div style='display:inline-block; max-width:70%; background:{bg}; color:{fg}; border-radius:14px; padding:9px 12px;'>
                        <div style='font-size:11px; opacity:0.75; margin-bottom:3px;'>{who} • {stamp}</div>
                        <div>{safe_text}</div>
                    </div>
                </div>
                """
            )
        if not html_parts:
            html_parts.append("<div style='color:#6f6f8f;'>Начните общение — отправьте первое сообщение.</div>")
        self.messages_view.setHtml("".join(html_parts))
        self.messages_view.verticalScrollBar().setValue(self.messages_view.verticalScrollBar().maximum())

    def send_message(self):
        if not self.selected_chat_user:
            QMessageBox.warning(self, "Внимание", "Сначала выберите пользователя для диалога.")
            return
        text = self.message_input.text().strip()
        if not text:
            return
        self.db.save_message(self.current_user["id"], self.selected_chat_user["id"], text)
        self.message_input.clear()
        self.render_messages()
        self.load_dialogs()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = OnlineWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        ERROR_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        print(f"Критическая ошибка. Лог: {ERROR_LOG}")
        sys.exit(1)
