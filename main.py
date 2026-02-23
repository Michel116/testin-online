import hashlib
import os
import sqlite3
import sys
import traceback
import unicodedata
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk

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
    # Нормализуем Unicode-строки (например, вставка из разных источников),
    # чтобы одинаково выглядящие пароли не считались разными.
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


class OnlineApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_user = None
        self.selected_chat_user = None

        self.title("Online — мессенджер")
        self.geometry("1100x700")
        self.minsize(900, 560)
        self.configure(bg="#f4f6f8")

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._configure_styles()

        self.auth_frame = None
        self.main_frame = None
        self.show_auth_frame()

    def _configure_styles(self):
        self.style.configure("Sidebar.TFrame", background="#17212b")
        self.style.configure("Main.TFrame", background="#0e1621")
        self.style.configure("Auth.TFrame", background="#f4f6f8")
        self.style.configure("AuthCard.TFrame", background="#ffffff")
        self.style.configure("Card.TFrame", background="#242f3d")
        self.style.configure("TLabel", background="#0e1621", foreground="#e6ebf0", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#f5f7fa", background="#17212b")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 11), foreground="#8f9bad", background="#17212b")
        self.style.configure("Accent.TButton", background="#2aabee", foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.style.map("Accent.TButton", background=[("active", "#229ed9")])

    def clear_window(self):
        for child in self.winfo_children():
            child.destroy()

    def show_auth_frame(self):
        self.clear_window()
        self.auth_frame = ttk.Frame(self, style="Auth.TFrame")
        self.auth_frame.pack(fill="both", expand=True)

        center = ttk.Frame(self.auth_frame, style="AuthCard.TFrame", padding=30)
        center.place(relx=0.5, rely=0.5, anchor="center", width=470, height=610)

        logo_canvas = tk.Canvas(center, width=96, height=96, bg="#ffffff", highlightthickness=0)
        logo_canvas.pack(pady=(0, 12))
        logo_canvas.create_oval(4, 4, 92, 92, fill="#2aabee", outline="")
        logo_canvas.create_polygon(32, 51, 68, 34, 61, 65, 49, 58, 42, 63, fill="#ffffff", outline="")

        tk.Label(center, text="Войти в Online", bg="#ffffff", fg="#111111", font=("Segoe UI", 28, "bold")).pack(pady=(0, 8))
        tk.Label(
            center,
            text="Введите логин и пароль для входа в приложение Online.",
            bg="#ffffff",
            fg="#6f7f8f",
            font=("Segoe UI", 12),
            wraplength=360,
            justify="center",
        ).pack(pady=(0, 20))

        self.auth_mode = tk.StringVar(value="login")
        switch_row = tk.Frame(center, bg="#ffffff")
        switch_row.pack(fill="x", pady=(0, 16))

        tk.Radiobutton(
            switch_row,
            text="Вход",
            variable=self.auth_mode,
            value="login",
            command=self._update_auth_ui,
            bg="#ffffff",
            fg="#34495e",
            selectcolor="#d8edf9",
            activebackground="#ffffff",
            activeforeground="#111111",
            font=("Segoe UI", 11),
        ).pack(side="left", padx=(0, 20))
        tk.Radiobutton(
            switch_row,
            text="Регистрация",
            variable=self.auth_mode,
            value="register",
            command=self._update_auth_ui,
            bg="#ffffff",
            fg="#34495e",
            selectcolor="#d8edf9",
            activebackground="#ffffff",
            activeforeground="#111111",
            font=("Segoe UI", 11),
        ).pack(side="left")

        tk.Label(center, text="Логин", bg="#ffffff", fg="#637a91", anchor="w", font=("Segoe UI", 10)).pack(fill="x", pady=(8, 4))
        self.login_entry = tk.Entry(center, bg="#f5f7fa", fg="#111111", relief="flat", insertbackground="#111111", font=("Segoe UI", 12))
        self.login_entry.pack(fill="x", ipady=11)

        tk.Label(center, text="Пароль", bg="#ffffff", fg="#637a91", anchor="w", font=("Segoe UI", 10)).pack(fill="x", pady=(12, 4))
        self.password_entry = tk.Entry(center, show="*", bg="#f5f7fa", fg="#111111", relief="flat", insertbackground="#111111", font=("Segoe UI", 12))
        self.password_entry.pack(fill="x", ipady=11)

        self.repeat_password_label = tk.Label(center, text="Повторите пароль", bg="#ffffff", fg="#637a91", anchor="w", font=("Segoe UI", 10))
        self.repeat_password_entry = tk.Entry(center, show="*", bg="#f5f7fa", fg="#111111", relief="flat", insertbackground="#111111", font=("Segoe UI", 12))

        self.auth_button = ttk.Button(center, text="Войти", style="Accent.TButton", command=self._handle_auth)
        self.auth_button.pack(fill="x", pady=(26, 12), ipady=10)

        hint = "Авторизация в текущей версии работает по логину и паролю."
        tk.Label(center, text=hint, bg="#ffffff", fg="#8c9baa", wraplength=360, justify="center", font=("Segoe UI", 9)).pack(fill="x", pady=(2, 0))

        self._update_auth_ui()

    def _update_auth_ui(self):
        is_register = self.auth_mode.get() == "register"
        if is_register:
            self.repeat_password_label.pack(fill="x", pady=(12, 4))
            self.repeat_password_entry.pack(fill="x", ipady=8)
            self.auth_button.config(text="Создать аккаунт")
        else:
            self.repeat_password_label.pack_forget()
            self.repeat_password_entry.pack_forget()
            self.auth_button.config(text="Войти")

    def _handle_auth(self):
        login = self.login_entry.get().strip()
        password = normalize_secret(self.password_entry.get())

        if len(login) < 3:
            messagebox.showerror("Ошибка", "Логин должен быть не короче 3 символов.")
            return
        if len(password) < 4:
            messagebox.showerror("Ошибка", "Пароль должен быть не короче 4 символов.")
            return

        if self.auth_mode.get() == "register":
            repeat = normalize_secret(self.repeat_password_entry.get())
            if password != repeat:
                messagebox.showerror("Ошибка", "Пароли не совпадают.")
                return
            user_id = self.db.create_user(login, password)
            if user_id is None:
                messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует.")
                return
            self.current_user = {"id": user_id, "login": login}
            self.show_main_frame()
            return

        user = self.db.authenticate(login, password)
        if user is None:
            messagebox.showerror("Ошибка", "Неверный логин или пароль.")
            return

        self.current_user = dict(user)
        self.show_main_frame()

    def show_main_frame(self):
        self.clear_window()
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=320)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        chat_area = ttk.Frame(root, style="Main.TFrame")
        chat_area.pack(side="left", fill="both", expand=True)

        ttk.Label(sidebar, text="Online", style="Header.TLabel").pack(anchor="w", padx=16, pady=(18, 0))
        ttk.Label(sidebar, text=f"Вы вошли как @{self.current_user['login']}", style="SubHeader.TLabel").pack(anchor="w", padx=16, pady=(2, 14))

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(sidebar, textvariable=self.search_var, bg="#242f3d", fg="#ffffff", relief="flat", insertbackground="#ffffff", font=("Segoe UI", 10))
        search_entry.pack(fill="x", padx=16, ipady=7)
        search_entry.bind("<KeyRelease>", lambda _e: self.load_dialogs())

        list_container = tk.Frame(sidebar, bg="#17212b")
        list_container.pack(fill="both", expand=True, padx=12, pady=12)

        self.dialog_listbox = tk.Listbox(
            list_container,
            bg="#17212b",
            fg="#e6ebf0",
            selectbackground="#2b5278",
            selectforeground="#ffffff",
            activestyle="none",
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 11),
        )
        self.dialog_listbox.pack(fill="both", expand=True)
        self.dialog_listbox.bind("<<ListboxSelect>>", self._on_dialog_selected)

        footer = tk.Frame(sidebar, bg="#17212b")
        footer.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(footer, text="Выйти", style="Accent.TButton", command=self.show_auth_frame).pack(fill="x")

        top_bar = tk.Frame(chat_area, bg="#182533", height=64)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        self.chat_title = tk.Label(top_bar, text="Выберите диалог слева", bg="#182533", fg="#ffffff", font=("Segoe UI", 13, "bold"))
        self.chat_title.pack(anchor="w", padx=18, pady=18)

        body = tk.Frame(chat_area, bg="#0e1621")
        body.pack(fill="both", expand=True)

        self.messages_text = tk.Text(
            body,
            state="disabled",
            wrap="word",
            bg="#0e1621",
            fg="#dce3ea",
            insertbackground="#ffffff",
            relief="flat",
            padx=20,
            pady=16,
            font=("Segoe UI", 10),
        )
        self.messages_text.pack(fill="both", expand=True)

        input_frame = tk.Frame(chat_area, bg="#17212b")
        input_frame.pack(fill="x")

        self.message_var = tk.StringVar()
        self.message_entry = tk.Entry(input_frame, textvariable=self.message_var, bg="#242f3d", fg="#ffffff", relief="flat", insertbackground="#ffffff", font=("Segoe UI", 11))
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(14, 8), pady=12, ipady=8)
        self.message_entry.bind("<Return>", lambda _e: self.send_message())

        ttk.Button(input_frame, text="Отправить", style="Accent.TButton", command=self.send_message).pack(side="left", padx=(0, 14), pady=12)

        self.dialog_users = []
        self.load_dialogs()

    def load_dialogs(self):
        query = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        rows = self.db.get_dialogs(self.current_user["id"]) if query == "" else self.db.find_users(self.current_user["id"], query)
        self.dialog_users = [dict(r) for r in rows]

        self.dialog_listbox.delete(0, tk.END)
        for row in self.dialog_users:
            self.dialog_listbox.insert(tk.END, f"@{row['login']}")

    def _on_dialog_selected(self, _event=None):
        selected = self.dialog_listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        self.selected_chat_user = self.dialog_users[idx]
        self.chat_title.config(text=f"@{self.selected_chat_user['login']}")
        self.render_messages()

    def render_messages(self):
        if not self.selected_chat_user:
            return

        messages = self.db.get_messages(self.current_user["id"], self.selected_chat_user["id"])
        self.messages_text.config(state="normal")
        self.messages_text.delete("1.0", tk.END)

        if not messages:
            self.messages_text.insert(tk.END, "Начните общение — отправьте первое сообщение.\n")

        for msg in messages:
            is_me = msg["sender_id"] == self.current_user["id"]
            owner = "Вы" if is_me else f"@{self.selected_chat_user['login']}"
            stamp = msg["created_at"].replace("T", " ")
            bubble_tag = "bubble_me" if is_me else "bubble_other"
            self.messages_text.insert(tk.END, f"{owner} • {stamp}\n", "meta")
            self.messages_text.insert(tk.END, f"{msg['text']}\n\n", bubble_tag)

        self.messages_text.tag_config("meta", foreground="#7e8ea4", font=("Segoe UI", 9, "italic"))
        self.messages_text.tag_config("bubble_me", background="#2b5278", foreground="#ffffff", lmargin1=8, lmargin2=8, spacing1=2, spacing3=8)
        self.messages_text.tag_config("bubble_other", background="#223242", foreground="#dce3ea", lmargin1=8, lmargin2=8, spacing1=2, spacing3=8)
        self.messages_text.config(state="disabled")
        self.messages_text.see(tk.END)

    def send_message(self):
        if not self.selected_chat_user:
            messagebox.showwarning("Внимание", "Сначала выберите пользователя для диалога.")
            return

        text = self.message_var.get().strip()
        if not text:
            return

        self.db.save_message(self.current_user["id"], self.selected_chat_user["id"], text)
        self.message_var.set("")
        self.render_messages()
        self.load_dialogs()


def main():
    app = OnlineApp()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        ERROR_LOG.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            messagebox.showerror(
                "Критическая ошибка",
                f"Приложение завершилось с ошибкой.\nЛог: {ERROR_LOG}",
            )
        except Exception:
            pass
        sys.exit(1)
