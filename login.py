from __future__ import annotations

import os
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from typing import Dict, Optional

from PIL import Image, ImageTk

from database import connect_db, initialize_mysql_schema, is_mysql

from patient_registration import PatientRegistrationFeature
from manage_medicine import MedicineManagementFeature
from medicine_reminders import MedicineRemindersFeature
from medication_schedule import MedicationScheduleFeature
from medication_history import MedicationHistoryFeature
from doctor_appointment_records import DoctorAppointmentRecordsFeature

try:
    import tkinter as tk
    from tkinter import messagebox, ttk
except ImportError:  # pragma: no cover
    tk = None
    messagebox = None
    ttk = None

try:
    from admindashboard import build_demo_data
except ImportError:  # pragma: no cover
    build_demo_data = None


def _add_brand_background(root):
    image_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "MedRemind.jpg",
        "MedRemind Care.png",
    )
    background = tk.PhotoImage(master=root, file=image_path)
    canvas = tk.Canvas(root, bg="#d8f0f3", highlightthickness=0, bd=0)
    canvas.place(relwidth=1, relheight=1)
    image_item = canvas.create_image(0, 0, image=background, anchor="center")
    canvas.background_image = background
    canvas.bind(
        "<Configure>",
        lambda event: canvas.coords(image_item, event.width // 2, event.height // 2),
    )
    return canvas


def _load_brand_logo(master, size: int):
    image_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "MedRemind.jpg",
        "MedRemind Care- LOGO.jpg.jpg",
    )
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(image, master=master)


class _FeaturePage(ttk.Frame):
    def __init__(self, master, title: str, show_dashboard) -> None:
        super().__init__(master, padding=(24, 18), style="FeaturePage.TFrame")
        header = ttk.Frame(self, style="FeaturePage.TFrame")
        header.pack(fill="x", pady=(0, 16))
        ttk.Button(
            header,
            text="← Dashboard",
            command=show_dashboard,
            style="Nav.TButton",
        ).pack(side="left", padx=(0, 14))
        title_area = ttk.Frame(header, style="FeaturePage.TFrame")
        title_area.pack(side="left", fill="x", expand=True)
        ttk.Label(
            title_area,
            text="MEDREMIND CARE WORKSPACE",
            style="PageEyebrow.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            title_area,
            text=title,
            style="PageTitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(0, 14))

    def add(self, frame, text: Optional[str] = None) -> None:
        _ = text
        frame.pack(fill="both", expand=True)


class LoginPage:
    """Sign-up and authentication page for MedRemind Care."""

    VALID_USERS: Dict[str, Dict[str, str]] = {
        "admin": {"password": "admin123", "role": "Administrator"},
        "doctor": {"password": "doctor123", "role": "Doctor"},
        "caregiver": {"password": "care123", "role": "Caregiver"},
    }

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        initialize_mysql_schema(self.db_path)
        conn = connect_db(self.db_path)
        try:
            if not is_mysql(self.db_path):
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        password_salt TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'Caregiver',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            conn.commit()
        finally:
            conn.close()

    def create_account(
        self,
        full_name: str,
        username: str,
        password: str,
        confirm_password: str,
        *,
        role: str = "Caregiver",
    ) -> Dict[str, str]:
        full_name = full_name.strip()
        username = username.strip().lower()
        if role not in {"Caregiver", "Client", "Administrator"}:
            raise ValueError("Invalid account role.")
        if not full_name:
            raise ValueError("Enter your full name.")
        if len(username) < 3 or not all(
            character.isalnum() or character == "_" for character in username
        ):
            raise ValueError("Username must be at least 3 characters and use only letters, numbers, or underscores.")
        if username in self.VALID_USERS:
            raise ValueError("That username is already in use.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if password != confirm_password:
            raise ValueError("Passwords do not match.")

        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 310_000
        )
        conn = connect_db(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO users (username, full_name, password_salt, password_hash, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    username,
                    full_name,
                    salt.hex(),
                    password_hash.hex(),
                    role,
                ),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username is already in use.") from exc
        finally:
            conn.close()

        return {"username": username, "full_name": full_name, "role": role}

    def create_admin_account(
        self,
        full_name: str,
        username: str,
        password: str,
        confirm_password: str,
    ) -> Dict[str, str]:
        return self.create_account(
            full_name,
            username,
            password,
            confirm_password,
            role="Administrator",
        )

    def reset_client_password(
        self,
        username: str,
        password: str,
        confirm_password: str,
    ) -> None:
        username = username.strip().lower()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if password != confirm_password:
            raise ValueError("Passwords do not match.")

        salt = secrets.token_bytes(16)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 310_000
        )
        conn = connect_db(self.db_path)
        try:
            result = conn.execute(
                """
                UPDATE users
                SET password_salt = ?, password_hash = ?
                WHERE username = ? AND role = 'Client'
                """,
                (salt.hex(), password_hash.hex(), username),
            )
            if result.rowcount == 0:
                raise ValueError("Client account not found.")
            conn.commit()
        finally:
            conn.close()

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, str]]:
        username = username.strip().lower()
        conn = connect_db(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            user = conn.execute(
                """
                SELECT username, full_name, password_salt, password_hash, role
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        finally:
            conn.close()

        if user is not None:
            candidate_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(user["password_salt"]),
                310_000,
            )
            if not hmac.compare_digest(candidate_hash.hex(), user["password_hash"]):
                return None
            return {
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
            }

        user = self.VALID_USERS.get(username)
        if not user:
            return None

        if user["password"] != password:
            return None

        return {"username": username, "role": user["role"]}

    def run_console(self) -> bool:
        print("\n=== MedRemind Care ===")
        print("1. Sign up")
        print("2. Sign in")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            try:
                account = self.create_account(
                    input("Full name: "),
                    input("Username: "),
                    input("Password (at least 8 characters): "),
                    input("Confirm password: "),
                )
            except ValueError as exc:
                print(f"Sign-up failed: {exc}")
                return False
            print(f"Account created. Welcome, {account['full_name']}!")
            self.show_dashboard(account)
            return True

        for attempt in range(1, 4):
            username = input("\nUsername: ").strip()
            password = input("Password: ")
            account = self.authenticate(username, password)
            if account is not None:
                print(f"\nWelcome, {account.get('full_name', account['username'])} ({account['role']})!")
                self.show_dashboard(account)
                return True
            print(f"Invalid username or password. Attempts left: {3 - attempt}")

        print("\nToo many failed attempts. Access denied.")
        return False

    def show_dashboard(self, account: Dict[str, str]) -> None:
        print("\nOpening dashboard...")
        if build_demo_data is not None:
            dashboard = build_demo_data()
            print(dashboard.render_summary())
        else:
            print(f"Role: {account['role']}")
            print("Dashboard module is not available yet.")

    def run_gui(self) -> None:
        if tk is None or messagebox is None or ttk is None:
            self.run_console()
            return

        root = tk.Tk()
        root.title("MedRemind Care - Welcome")
        root.geometry("1120x720")
        root.minsize(900, 620)
        root.configure(bg="#eef3f7")
        _add_brand_background(root)

        frame = tk.Frame(
            root,
            padx=34,
            pady=30,
            bg="#fbfdff",
            bd=0,
            highlightthickness=1,
            highlightbackground="#dce6ed",
        )
        frame.place(relx=0.73, rely=0.5, anchor="center", width=430)
        frame.lift()

        frame.brand_logo_image = _load_brand_logo(root, 58)
        tk.Label(
            frame,
            image=frame.brand_logo_image,
            bg="#fbfdff",
            bd=0,
        ).pack(anchor="w", pady=(0, 18))
        title = tk.Label(
            frame,
            text="Welcome to better care.",
            font=("Arial", 22, "bold"),
            bg="#fbfdff",
            fg="#102a3d",
            wraplength=350,
            justify="left",
        )
        title.pack(anchor="w", pady=(0, 4))
        subtitle = tk.Label(
            frame,
            text="Create an account to get started",
            font=("Arial", 10),
            bg="#fbfdff",
            fg="#718391",
        )
        subtitle.pack(anchor="w", pady=(0, 18))

        form = tk.Frame(frame, bg="#fbfdff")
        form.pack(fill="x")
        field_frames = {}

        def add_field(label: str, name: str, secret: bool = False):
            field = tk.Frame(form, bg="#fbfdff")
            field.pack(fill="x", pady=(4, 7))
            tk.Label(
                field,
                text=label,
                anchor="w",
                bg="#fbfdff",
                fg="#314b5c",
                font=("Arial", 9, "bold"),
            ).pack(fill="x", pady=(0, 5))
            entry = tk.Entry(
                field,
                width=38,
                show="*" if secret else "",
                relief="flat",
                bd=0,
                bg="#f5f8fa",
                fg="#102a3d",
                insertbackground="#15566c",
                font=("Arial", 11),
                highlightthickness=1,
                highlightbackground="#dce6ed",
                highlightcolor="#2b8290",
            )
            entry.pack(fill="x", ipady=9, ipadx=10)
            field_frames[name] = field
            return entry

        full_name_entry = add_field("Full name", "full_name")
        username_entry = add_field("Username", "username")
        password_entry = add_field("Password (at least 8 characters)", "password", secret=True)
        confirm_entry = add_field("Confirm password", "confirm_password", secret=True)
        status = tk.Label(
            frame,
            text="",
            bg="#fbfdff",
            fg="#a23c42",
            wraplength=350,
            justify="left",
        )
        status.pack(anchor="w", pady=(7, 0))
        action_button = tk.Button(
            frame,
            text="Create Account",
            width=32,
            bg="#102b40",
            fg="white",
            activebackground="#1b5268",
            activeforeground="white",
            font=("Arial", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
        )
        action_button.pack(fill="x", ipady=8, pady=(15, 7))
        signup_choices = tk.Frame(frame, bg="#fbfdff")
        signup_choices.pack(fill="x", pady=(0, 4))
        switch_button = tk.Button(
            frame,
            text="Already have an account? Sign in",
            relief="flat",
            bg="#fbfdff",
            fg="#245c72",
            activebackground="#fbfdff",
            activeforeground="#143e56",
            font=("Arial", 9, "bold"),
            cursor="hand2",
        )
        switch_button.pack()
        client_signup_button = tk.Button(
            signup_choices,
            text="Client/User Sign Up",
            relief="flat",
            bg="#eaf3f7",
            fg="#245c72",
            activebackground="#dcebf0",
            activeforeground="#143e56",
            font=("Arial", 9, "bold"),
            cursor="hand2",
        )
        client_signup_button.pack(side="left", fill="x", expand=True, padx=(0, 5))
        admin_signup_button = tk.Button(
            signup_choices,
            text="Admin Sign Up",
            relief="flat",
            bg="#fbfdff",
            fg="#718391",
            activebackground="#f1f6f8",
            activeforeground="#245c72",
            font=("Arial", 9, "bold"),
            cursor="hand2",
        )
        admin_signup_button.pack(side="left", fill="x", expand=True, padx=(5, 0))

        is_signup = True

        def open_dashboard(account: Dict[str, str]) -> None:
            if account["role"] == "Client":
                messagebox.showinfo(
                    "Use the client website",
                    "Client accounts use the MedRemind Care website, not the admin desktop app.",
                )
                return
            messagebox.showinfo(
                "Welcome",
                f"Welcome, {account.get('full_name', account['username'])} ({account['role']})!",
            )
            root.destroy()
            app = MedRemindCareApp(account=account, db_path=self.db_path)
            app.run()

        def handle_signup() -> None:
            try:
                account = self.create_account(
                    full_name_entry.get(),
                    username_entry.get(),
                    password_entry.get(),
                    confirm_entry.get(),
                    role="Client",
                )
            except ValueError as exc:
                status.config(text=str(exc))
                return
            open_dashboard(account)

        def handle_admin_signup() -> None:
            try:
                account = self.create_admin_account(
                    full_name_entry.get(),
                    username_entry.get(),
                    password_entry.get(),
                    confirm_entry.get(),
                )
            except ValueError as exc:
                status.config(text=str(exc))
                return
            open_dashboard(account)

        def handle_login() -> None:
            username = username_entry.get()
            password = password_entry.get()
            account = self.authenticate(username, password)

            if account is None:
                status.config(text="Invalid username or password.")
                return

            open_dashboard(account)

        def switch_mode() -> None:
            nonlocal is_signup
            is_signup = not is_signup
            status.config(text="")
            if is_signup:
                set_signup_role("Client")
                subtitle.config(text="Create an account to get started")
                field_frames["full_name"].pack(fill="x", pady=(5, 2), before=field_frames["username"])
                field_frames["confirm_password"].pack(fill="x", pady=(5, 2))
                signup_choices.pack(fill="x", pady=(0, 4), before=switch_button)
                switch_button.config(text="Already have an account? Sign in")
            else:
                subtitle.config(text="Sign in to your account")
                field_frames["full_name"].pack_forget()
                field_frames["confirm_password"].pack_forget()
                signup_choices.pack_forget()
                action_button.config(text="Sign In", command=handle_login)
                switch_button.config(text="New to MedRemind Care? Create an account")

        def set_signup_role(role: str) -> None:
            status.config(text="")
            is_admin = role == "Administrator"
            subtitle.config(
                text="Create an administrator account" if is_admin
                else "Create a client/user account"
            )
            field_frames["full_name"].pack(
                fill="x", pady=(5, 2), before=field_frames["username"]
            )
            field_frames["confirm_password"].pack(fill="x", pady=(5, 2))
            action_button.config(
                text="Create Admin Account" if is_admin else "Create Client Account",
                command=handle_admin_signup if is_admin else handle_signup,
            )
            client_signup_button.config(
                bg="#fbfdff" if is_admin else "#eaf3f7",
                fg="#718391" if is_admin else "#245c72",
            )
            admin_signup_button.config(
                bg="#eaf3f7" if is_admin else "#fbfdff",
                fg="#245c72" if is_admin else "#718391",
            )
            switch_button.config(text="Already have an account? Sign in")

        field_frames["full_name"].pack_forget()
        field_frames["full_name"].pack(fill="x", pady=(5, 2), before=field_frames["username"])
        field_frames["confirm_password"].pack_forget()
        field_frames["confirm_password"].pack(fill="x", pady=(5, 2))
        action_button.config(text="Create Client Account", command=handle_signup)
        switch_button.config(command=switch_mode)
        client_signup_button.config(command=lambda: set_signup_role("Client"))
        admin_signup_button.config(command=lambda: set_signup_role("Administrator"))
        username_entry.focus()
        root.mainloop()

    def run(self) -> None:
        try:
            self.run_gui()
        except tk.TclError as exc:  # pragma: no cover
            print(f"Unable to open the desktop login window: {exc}")
            self.run_console()


class MedRemindCareApp(
    PatientRegistrationFeature,
    MedicineManagementFeature,
    MedicineRemindersFeature,
    MedicationScheduleFeature,
    MedicationHistoryFeature,
    DoctorAppointmentRecordsFeature,
):
    """Tabbed patient and medication management dashboard."""


    tabs = [
        "Patient Registration",
        "Manage Medicine",
        "Medicine Reminders",
        "Medication Schedule",
        "Medication History",
        "Doctor/Appointment Records",
    ]
    feature_pages = (
        ("patients", "Patient Registration", "_create_tab_patient"),
        ("medicines", "Manage Medicine", "_create_tab_medicine"),
        ("reminders", "Medicine Reminders", "_create_tab_reminders"),
        ("schedule", "Medication Schedule", "_create_tab_schedule"),
        ("history", "Medication History", "_create_tab_history"),
        ("records", "Doctor/Appointment Records", "_create_tab_records"),
    )

    def __init__(
        self,
        account: Optional[Dict[str, str]] = None,
        master=None,
        db_path: Optional[str] = None,
    ) -> None:
        self.account = account or {"username": "admin", "role": "Administrator"}
        self.root = master
        if self.root is None and tk is not None:
            try:
                self.root = tk.Tk()
            except Exception:  # pragma: no cover
                self.root = None

        self._use_shared_database = (
            is_mysql(db_path) if db_path is not None else is_mysql()
        )
        if self._use_shared_database:
            initialize_mysql_schema(db_path)
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "medremind.db"
        )
        self._build_database()
        self.selected_patient_id: Optional[int] = None
        self.selected_medicine_id: Optional[int] = None
        self._notified_reminders: set[tuple[int, str]] = set()

        if self.root is not None:
            self.root.title("MedRemind Care Dashboard")
            self.root.geometry("1180x760")
            self.root.minsize(980, 640)
            self._build_ui()

    def _connect(self) -> sqlite3.Connection:
        return connect_db(self.db_path)

    def _connect_account_store(self):
        if not getattr(self, "_use_shared_database", False):
            return self._connect()
        if is_mysql(self.db_path):
            return connect_db(self.db_path)
        return connect_db()

    def _build_database(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    age INTEGER,
                    contact TEXT,
                    condition TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS medicines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    medicine_name TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    reminder_time TEXT,
                    status TEXT DEFAULT 'pending',
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER NOT NULL,
                    doctor_name TEXT,
                    appointment_date TEXT,
                    reason TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS medication_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    medicine_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    patient_name TEXT NOT NULL,
                    medicine_name TEXT NOT NULL,
                    dosage TEXT NOT NULL,
                    reminder_time TEXT,
                    status TEXT NOT NULL,
                    recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    dose_date TEXT NOT NULL DEFAULT CURRENT_DATE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consultations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_username TEXT NOT NULL,
                    medicine_name TEXT NOT NULL,
                    question TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            consultation_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(consultations)")
            }
            if "admin_reply" not in consultation_columns:
                conn.execute(
                    "ALTER TABLE consultations ADD COLUMN admin_reply TEXT NOT NULL DEFAULT ''"
                )
            history_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(medication_history)")
            }
            if "dose_date" not in history_columns:
                conn.execute(
                    "ALTER TABLE medication_history ADD COLUMN dose_date TEXT NOT NULL DEFAULT ''"
                )
                conn.execute(
                    """
                    UPDATE medication_history
                    SET dose_date = COALESCE(date(recorded_at), date('now', 'localtime'))
                    WHERE dose_date = ''
                    """
                )
            conn.execute(
                """
                INSERT INTO medication_history
                    (medicine_id, patient_id, patient_name, medicine_name, dosage, reminder_time,
                     status, dose_date, recorded_at)
                SELECT m.id, m.patient_id, p.full_name, m.medicine_name, m.dosage,
                       m.reminder_time, m.status, date('now', 'localtime'),
                       datetime('now', 'localtime')
                FROM medicines m
                JOIN patients p ON p.id = m.patient_id
                WHERE m.status IN ('taken', 'missed')
                AND NOT EXISTS (
                    SELECT 1 FROM medication_history h
                    WHERE h.medicine_id = m.id
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def get_patients(self):
        conn = self._connect()
        try:
            return conn.execute("SELECT * FROM patients ORDER BY id ASC").fetchall()
        finally:
            conn.close()

    def get_medicines(self):
        conn = self._connect()
        try:
            return conn.execute(
                """
                SELECT m.*, p.full_name AS patient_name,
                    (
                        SELECT h.status
                        FROM medication_history h
                        WHERE h.medicine_id = m.id AND h.dose_date = ?
                        ORDER BY h.id DESC
                        LIMIT 1
                    ) AS today_status
                FROM medicines m
                JOIN patients p ON p.id = m.patient_id
                ORDER BY m.id DESC
                """,
                (datetime.now().date().isoformat(),),
            ).fetchall()
        finally:
            conn.close()

    def get_pending_reminders(self):
        conn = self._connect()
        try:
            return conn.execute(
                """
                SELECT m.*, p.full_name AS patient_name
                FROM medicines m
                JOIN patients p ON p.id = m.patient_id
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM medication_history h
                    WHERE h.medicine_id = m.id AND h.dose_date = ?
                )
                ORDER BY m.reminder_time, m.id DESC
                """,
                (datetime.now().date().isoformat(),),
            ).fetchall()
        finally:
            conn.close()

    def get_appointments(self):
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT a.*, p.full_name AS patient_name FROM appointments a JOIN patients p ON p.id = a.patient_id ORDER BY a.appointment_date DESC"
            ).fetchall()
        finally:
            conn.close()

    def get_dashboard_metrics(self):
        today = datetime.now().date().isoformat()
        conn = self._connect()
        try:
            return conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM patients) AS patient_count,
                    (SELECT COUNT(*) FROM medicines) AS medicine_count,
                    (
                        SELECT COUNT(*)
                        FROM medication_history
                        WHERE dose_date = ? AND lower(status) = 'taken'
                    ) AS taken_count,
                    (
                        SELECT COUNT(*)
                        FROM medication_history
                        WHERE dose_date = ? AND lower(status) = 'missed'
                    ) AS missed_count,
                    (
                        SELECT COUNT(*)
                        FROM medicines m
                        WHERE NOT EXISTS (
                            SELECT 1
                            FROM medication_history h
                            WHERE h.medicine_id = m.id AND h.dose_date = ?
                        )
                    ) AS pending_count
                """,
                (today, today, today),
            ).fetchone()
        finally:
            conn.close()

    def get_upcoming_appointments(self, limit: int = 5):
        today = datetime.now().date().isoformat()
        conn = self._connect()
        try:
            return conn.execute(
                """
                SELECT a.id, a.appointment_date, a.doctor_name, a.reason,
                       p.full_name AS patient_name
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                WHERE DATE(a.appointment_date) >= DATE(?)
                ORDER BY DATE(a.appointment_date), a.id
                LIMIT ?
                """,
                (today, limit),
            ).fetchall()
        finally:
            conn.close()

    def get_registered_accounts(self):
        if self.account.get("role") != "Administrator":
            raise PermissionError("Only administrators can view registered accounts.")

        conn = self._connect_account_store()
        try:
            return conn.execute(
                """
                SELECT full_name, username, role, created_at
                FROM users
                ORDER BY created_at DESC, LOWER(username)
                """
            ).fetchall()
        finally:
            conn.close()

    def get_consultations(self):
        if self.account.get("role") != "Administrator":
            raise PermissionError("Only administrators can view client consultations.")

        conn = self._connect_account_store()
        try:
            return conn.execute(
                """
                SELECT c.id, u.full_name, c.client_username, c.medicine_name,
                       c.question, c.status, c.admin_reply, c.created_at
                FROM consultations c
                JOIN users u ON u.username = c.client_username
                ORDER BY c.created_at DESC, c.id DESC
                """
            ).fetchall()
        finally:
            conn.close()

    def update_consultation(
        self,
        consultation_id: int,
        status: str,
        admin_reply: str,
    ) -> None:
        if self.account.get("role") != "Administrator":
            raise PermissionError("Only administrators can update consultations.")
        if status not in {"Pending", "In Review", "Responded", "Closed"}:
            raise ValueError("Choose a valid consultation status.")
        admin_reply = admin_reply.strip()
        if len(admin_reply) > 2000:
            raise ValueError("Keep the admin reply under 2,000 characters.")

        conn = self._connect_account_store()
        try:
            result = conn.execute(
                """
                UPDATE consultations
                SET status = ?, admin_reply = ?
                WHERE id = ?
                """,
                (status, admin_reply, consultation_id),
            )
            if result.rowcount == 0:
                raise ValueError("Consultation request not found.")
            conn.commit()
        finally:
            conn.close()

    def _build_ui(self) -> None:
        self.root.configure(bg="#edf2f6")
        self.background_canvas = _add_brand_background(self.root)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#edf2f6")
        style.configure("TLabel", background="#ffffff", foreground="#355366")
        style.configure("FeaturePage.TFrame", background="#edf2f6")
        style.configure(
            "PageEyebrow.TLabel",
            background="#edf2f6",
            foreground="#668292",
            font=("Arial", 7, "bold"),
        )
        style.configure(
            "PageTitle.TLabel",
            background="#edf2f6",
            foreground="#102b40",
            font=("Arial", 18, "bold"),
        )
        style.configure("TSeparator", background="#dce6eb")
        style.configure("TLabelframe", background="#ffffff", bordercolor="#dce6eb")
        style.configure(
            "TLabelframe.Label",
            background="#ffffff",
            foreground="#31566c",
            font=("Arial", 10, "bold"),
        )
        style.configure("TNotebook", background="#edf2f6", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(14, 8),
            background="#e3ebf0",
            foreground="#456173",
            font=("Arial", 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#ffffff"), ("active", "#f3f7f9")],
            foreground=[("selected", "#143c54")],
        )
        style.configure(
            "TButton",
            padding=(11, 7),
            background="#ffffff",
            foreground="#24495f",
            bordercolor="#d7e2e8",
            font=("Arial", 9, "bold"),
        )
        style.map(
            "TButton",
            background=[("active", "#eaf3f7"), ("pressed", "#dfebf0")],
            foreground=[("active", "#102f45")],
        )
        style.configure(
            "Nav.TButton",
            padding=(12, 9),
            background="#f6f9fb",
            foreground="#496475",
            bordercolor="#e1e9ee",
            font=("Arial", 9, "bold"),
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#e5f0f4"), ("pressed", "#dcebf0")],
            foreground=[("active", "#12384f")],
        )
        style.configure(
            "NavActive.TButton",
            padding=(12, 9),
            background="#e5f1f5",
            foreground="#12384f",
            bordercolor="#cbdfe7",
            font=("Arial", 9, "bold"),
        )
        style.configure(
            "Action.TButton",
            padding=(12, 10),
            background="#ffffff",
            foreground="#1e5168",
            bordercolor="#dce7ec",
            font=("Arial", 9, "bold"),
        )
        style.map(
            "Action.TButton",
            background=[("active", "#edf6f8")],
            foreground=[("active", "#0e344a")],
        )
        style.configure(
            "TEntry",
            padding=(9, 7),
            fieldbackground="#f8fafb",
            foreground="#19394d",
            insertcolor="#1c6175",
            bordercolor="#d9e4e9",
            lightcolor="#d9e4e9",
            darkcolor="#d9e4e9",
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", "#438796")],
            lightcolor=[("focus", "#438796")],
            darkcolor=[("focus", "#438796")],
        )
        style.configure(
            "TCombobox",
            padding=(8, 6),
            fieldbackground="#f8fafb",
            background="#ffffff",
            foreground="#19394d",
            arrowcolor="#42687b",
            bordercolor="#d9e4e9",
            lightcolor="#d9e4e9",
            darkcolor="#d9e4e9",
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#f8fafb")],
            foreground=[("readonly", "#19394d")],
            bordercolor=[("focus", "#438796")],
        )
        style.configure(
            "Vertical.TScrollbar",
            background="#e5edf1",
            troughcolor="#f6f9fa",
            bordercolor="#f6f9fa",
            arrowcolor="#718a97",
        )
        style.configure(
            "Treeview",
            rowheight=32,
            font=("Arial", 9),
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground="#29485b",
            borderwidth=0,
        )
        style.map("Treeview", background=[("selected", "#dcecf0")], foreground=[("selected", "#102f44")])
        style.configure(
            "Treeview.Heading",
            font=("Arial", 9, "bold"),
            background="#f1f6f8",
            foreground="#607986",
            relief="flat",
            padding=(8, 8),
        )

        header = tk.Frame(self.root, bg="#091c2b", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg="#091c2b")
        brand.pack(side="left", padx=23, pady=12)
        self.brand_logo_image = _load_brand_logo(header, 40)
        tk.Label(
            brand,
            image=self.brand_logo_image,
            bg="#ffffff",
            bd=0,
        ).pack(side="left", padx=(0, 10))
        title = tk.Label(
            brand,
            text="MedRemind Care",
            fg="#f5f8fb",
            bg="#091c2b",
            font=("Arial", 16, "bold"),
        )
        title.pack(side="left")
        account_info = tk.Frame(header, bg="#091c2b")
        account_info.pack(side="right", padx=(8, 20), pady=12)
        signed_in = tk.Label(
            account_info,
            text=self._dashboard_user_name(),
            fg="#f1f6f8",
            bg="#091c2b",
            font=("Arial", 9, "bold"),
        )
        signed_in.pack(anchor="e")
        tk.Label(
            account_info,
            text=self.account["role"].upper(),
            fg="#94b5c1",
            bg="#091c2b",
            font=("Arial", 7, "bold"),
        ).pack(anchor="e", pady=(3, 0))
        ttk.Button(header, text="Log Out", command=self.log_out).pack(
            side="right", padx=(0, 6), pady=17
        )

        navigation_shell = tk.Frame(self.root, bg="#ffffff", height=52, highlightthickness=1, highlightbackground="#dfe7eb")
        navigation_shell.pack(fill="x")
        navigation_shell.pack_propagate(False)
        navigation = tk.Frame(navigation_shell, bg="#ffffff")
        navigation.pack(fill="both", expand=True, padx=18, pady=5)
        destinations = [
            ("dashboard", "Dashboard", ""),
            ("patients", "Patients", ""),
            ("medicines", "Medicines", ""),
            ("reminders", "Reminders", ""),
            ("schedule", "Schedule", ""),
            ("history", "History", ""),
            ("records", "Appointments", ""),
        ]
        if self.account.get("role") == "Administrator":
            destinations.extend(
                [
                    ("signups", "Sign-ups", ""),
                    ("consultations", "Consultations", ""),
                ]
            )
        self.navigation_buttons = []
        self.navigation_keys = []
        self._navigation_columns_used = 0
        for page_key, title_text, _ in destinations:
            command = lambda key=page_key: (
                self.show_dashboard()
                if key == "dashboard"
                else self.show_feature_page(key)
            )
            button = ttk.Button(
                navigation,
                text=title_text,
                command=command,
                width=13,
                style="Nav.TButton",
            )
            self.navigation_buttons.append(button)
            self.navigation_keys.append(page_key)
        navigation.bind("<Configure>", self._layout_navigation)
        self.root.after_idle(self._layout_navigation)

        self.dashboard_view = ttk.Frame(self.root, padding=20)
        self.feature_page_widgets = {}
        self._create_dashboard_view()

        for page_key, title_text, creator_name in self.feature_pages:
            page = _FeaturePage(
                self.root,
                title_text,
                self.show_dashboard,
            )
            self.feature_page_widgets[page_key] = page
            getattr(self, creator_name)(page)

        if self.account.get("role") == "Administrator":
            signups_page = _FeaturePage(
                self.root,
                "Sign-ups",
                self.show_dashboard,
            )
            self.feature_page_widgets["signups"] = signups_page
            self._create_tab_signups(signups_page)
            consultations_page = _FeaturePage(
                self.root,
                "Client Consultations",
                self.show_dashboard,
            )
            self.feature_page_widgets["consultations"] = consultations_page
            self._create_tab_consultations(consultations_page)

        self.refresh_all()
        self.show_dashboard()
        self.root.after(30000, self._poll_dashboard_data)
        self.root.after(15000, self._check_medication_alerts)

    def _create_dashboard_view(self) -> None:
        self.dashboard_view.configure(style="TFrame")
        heading = tk.Frame(self.dashboard_view, bg="#edf2f6")
        heading.pack(fill="x", pady=(0, 14))
        heading.columnconfigure(0, weight=1)
        tk.Label(
            heading,
            text="YOUR CARE WORKSPACE",
            bg="#edf2f6",
            fg="#53768a",
            font=("Arial", 8, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        tk.Label(
            heading,
            text=f"Good to see you, {self._dashboard_user_name()}.",
            bg="#edf2f6",
            fg="#102b40",
            font=("Arial", 22, "bold"),
        ).grid(row=1, column=0, sticky="w")
        tk.Label(
            heading,
            text="Your care records, medication routines, and upcoming visits at a glance.",
            bg="#edf2f6",
            fg="#6d808d",
            font=("Arial", 9),
        ).grid(row=2, column=0, sticky="w", pady=(5, 0))
        date_badge = tk.Frame(
            heading,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#dce6eb",
            padx=14,
            pady=9,
        )
        date_badge.grid(row=0, column=1, rowspan=3, sticky="e")
        tk.Label(
            date_badge,
            text=datetime.now().strftime("%A").upper(),
            bg="#ffffff",
            fg="#6b8290",
            font=("Arial", 7, "bold"),
        ).pack(anchor="e")
        tk.Label(
            date_badge,
            text=datetime.now().strftime("%b %d, %Y"),
            bg="#ffffff",
            fg="#173c53",
            font=("Arial", 10, "bold"),
        ).pack(anchor="e", pady=(3, 0))

        self.dashboard_metric_vars = {
            key: tk.StringVar(master=self.root, value="0")
            for key in ("patients", "medicines", "adherence", "taken", "missed", "pending")
        }
        metric_labels = (
            ("PATIENTS", "patients", "Patient records", "#245a74"),
            ("MEDICINES", "medicines", "Care library", "#377c7a"),
            ("TODAY'S ADHERENCE", "adherence", "Doses marked taken", "#397b69"),
            ("TAKEN TODAY", "taken", "Recorded as taken", "#397b69"),
            ("MISSED TODAY", "missed", "Recorded as missed", "#a35e56"),
            ("PENDING TODAY", "pending", "Awaiting a dose record", "#9a762f"),
        )
        metrics_box = tk.Frame(self.dashboard_view, bg="#edf2f6")
        metrics_box.pack(fill="x", pady=(0, 13))
        for column in range(3):
            metrics_box.columnconfigure(column, weight=1, uniform="dashboard_metric")
        for index, (label, key, description, accent) in enumerate(metric_labels):
            row, column = divmod(index, 3)
            metric = tk.Frame(
                metrics_box,
                bg="#ffffff",
                highlightthickness=1,
                highlightbackground="#e0e8ed",
            )
            metric.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")
            tk.Frame(metric, bg=accent, width=4).pack(side="left", fill="y")
            content = tk.Frame(metric, bg="#ffffff", padx=12, pady=9)
            content.pack(side="left", fill="both", expand=True)
            tk.Label(
                content,
                text=label,
                bg="#ffffff",
                fg="#748893",
                font=("Arial", 7, "bold"),
            ).pack(anchor="w")
            tk.Label(
                content,
                textvariable=self.dashboard_metric_vars[key],
                bg="#ffffff",
                fg="#112e42",
                font=("Arial", 19, "bold"),
            ).pack(anchor="w", pady=(2, 0))
            tk.Label(
                content,
                text=description,
                bg="#ffffff",
                fg="#83939c",
                font=("Arial", 7),
            ).pack(anchor="w", pady=(1, 0))

        quick_access = tk.Frame(self.dashboard_view, bg="#edf2f6")
        quick_access.pack(fill="x", pady=(0, 14))
        quick_access.columnconfigure(0, weight=1)
        tk.Label(
            quick_access,
            text="QUICK ACCESS",
            bg="#edf2f6",
            fg="#53768a",
            font=("Arial", 8, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 7))
        actions = tk.Frame(quick_access, bg="#edf2f6")
        actions.grid(row=1, column=0, sticky="ew")
        action_items = (
            ("patients", "＋  Add patient"),
            ("medicines", "＋  Add medicine"),
            ("schedule", "▦  Medication schedule"),
            ("reminders", "◷  Dose reminders"),
            ("records", "↗  Appointments"),
            ("history", "≡  Dose history"),
        )
        if self.account.get("role") == "Administrator":
            action_items += (
                ("signups", "◎  Registered accounts"),
                ("consultations", "✉  Client questions"),
            )
        for column in range(4):
            actions.columnconfigure(column, weight=1, uniform="dashboard_action")
        for index, (page_key, label) in enumerate(action_items):
            ttk.Button(
                actions,
                text=label,
                style="Action.TButton",
                command=lambda key=page_key: self.show_feature_page(key),
            ).grid(
                row=index // 4,
                column=index % 4,
                padx=4,
                pady=3,
                sticky="ew",
            )

        appointments_box = tk.Frame(
            self.dashboard_view,
            bg="#ffffff",
            highlightthickness=1,
            highlightbackground="#dfe8ed",
        )
        appointments_box.pack(fill="both", expand=True)
        appointment_header = tk.Frame(appointments_box, bg="#ffffff")
        appointment_header.pack(fill="x", padx=13, pady=(10, 7))
        appointment_heading = tk.Frame(appointment_header, bg="#ffffff")
        appointment_heading.pack(side="left")
        tk.Label(
            appointment_heading,
            text="UP NEXT",
            bg="#ffffff",
            fg="#53768a",
            font=("Arial", 7, "bold"),
        ).pack(anchor="w")
        tk.Label(
            appointment_heading,
            text="Upcoming appointments",
            bg="#ffffff",
            fg="#15364b",
            font=("Arial", 12, "bold"),
        ).pack(anchor="w", pady=(2, 0))
        ttk.Button(
            appointment_header,
            text="Refresh",
            command=self._refresh_dashboard_data,
        ).pack(side="right")
        table_frame = tk.Frame(appointments_box, bg="#ffffff")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        appointment_columns = ("Date", "Patient", "Doctor", "Reason")
        self.dashboard_appointments_tree = ttk.Treeview(
            table_frame,
            columns=appointment_columns,
            show="headings",
            height=4,
        )
        for column, width in zip(appointment_columns, (150, 220, 190, 340)):
            self.dashboard_appointments_tree.heading(column, text=column)
            self.dashboard_appointments_tree.column(column, width=width, anchor="w")
        appointment_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.dashboard_appointments_tree.yview,
        )
        self.dashboard_appointments_tree.configure(
            yscrollcommand=appointment_scrollbar.set
        )
        self.dashboard_appointments_tree.pack(side="left", fill="both", expand=True)
        appointment_scrollbar.pack(side="right", fill="y")

    @staticmethod
    def _navigation_column_count(available_width: int, button_count: int) -> int:
        if button_count <= 0:
            return 0
        return max(1, min(button_count, available_width // 120))

    def _layout_navigation(self, event=None) -> None:
        if not self.navigation_buttons:
            return
        available_width = (
            event.width if event is not None else self.navigation_buttons[0].master.winfo_width()
        )
        columns = self._navigation_column_count(
            available_width,
            len(self.navigation_buttons),
        )
        for column in range(max(self._navigation_columns_used, columns)):
            self.navigation_buttons[0].master.grid_columnconfigure(column, weight=0)
        for column in range(columns):
            self.navigation_buttons[0].master.grid_columnconfigure(column, weight=1)
        for index, button in enumerate(self.navigation_buttons):
            button.grid(
                row=index // columns,
                column=index % columns,
                padx=4,
                pady=4,
                sticky="ew",
            )
        self._navigation_columns_used = columns

    def _dashboard_user_name(self) -> str:
        return self.account.get("full_name", "").strip() or self.account["username"]

    def show_dashboard(self) -> None:
        for page in self.feature_page_widgets.values():
            page.pack_forget()
        self._refresh_dashboard_data()
        self.dashboard_view.pack(fill="both", expand=True, padx=24, pady=20)
        self._set_active_navigation("dashboard")

    def _set_active_navigation(self, page_key: str) -> None:
        for key, button in zip(self.navigation_keys, self.navigation_buttons):
            button.configure(
                style="NavActive.TButton" if key == page_key else "Nav.TButton"
            )

    def _refresh_dashboard_data(self) -> None:
        metrics = self.get_dashboard_metrics()
        taken = metrics["taken_count"]
        missed = metrics["missed_count"]
        pending = metrics["pending_count"]
        total = taken + missed + pending
        adherence = (taken / total * 100) if total else 0
        values = {
            "patients": metrics["patient_count"],
            "medicines": metrics["medicine_count"],
            "adherence": f"{adherence:.0f}%",
            "taken": taken,
            "missed": missed,
            "pending": pending,
        }
        for key, value in values.items():
            self.dashboard_metric_vars[key].set(str(value))

        for row in self.dashboard_appointments_tree.get_children():
            self.dashboard_appointments_tree.delete(row)
        appointments = self.get_upcoming_appointments()
        if not appointments:
            self.dashboard_appointments_tree.insert(
                "",
                "end",
                values=("-", "No upcoming appointments", "-", "-"),
            )
            return
        for appointment in appointments:
            self.dashboard_appointments_tree.insert(
                "",
                "end",
                values=(
                    appointment["appointment_date"],
                    appointment["patient_name"],
                    appointment["doctor_name"] or "",
                    appointment["reason"] or "",
                ),
            )

    def _poll_dashboard_data(self) -> None:
        self._refresh_dashboard_data()
        self.root.after(30000, self._poll_dashboard_data)

    def show_feature_page(self, page_key: str) -> None:
        page = self.feature_page_widgets.get(page_key)
        if page is None:
            raise ValueError(f"Unknown dashboard section: {page_key}")
        self.dashboard_view.pack_forget()
        for other_page in self.feature_page_widgets.values():
            other_page.pack_forget()
        page.pack(fill="both", expand=True, padx=42, pady=22)
        self._set_active_navigation(page_key)

    def log_out(self) -> None:
        if not messagebox.askyesno("Log out", "Are you sure you want to log out?"):
            return
        self.root.destroy()
        LoginPage(db_path=self.db_path).run()

    def _create_tab_signups(self, notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Sign-ups")

        signups_box = ttk.LabelFrame(frame, text="Registered Accounts", padding=12)
        signups_box.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(
            signups_box,
            text="New accounts appear here after sign-up. Passwords are never displayed.",
        ).pack(anchor="w", pady=(0, 8))

        columns = ("Full Name", "Username", "Role", "Signed Up")
        self.signup_tree = ttk.Treeview(
            signups_box,
            columns=columns,
            show="headings",
        )
        for column in columns:
            self.signup_tree.heading(column, text=column)
            self.signup_tree.column(column, width=180, anchor="center")
        self.signup_tree.pack(fill="both", expand=True)

        ttk.Button(
            signups_box,
            text="Refresh Sign-ups",
            command=self._refresh_signup_tree,
        ).pack(anchor="e", pady=(10, 0))
        self._refresh_signup_tree()
        self.root.after(30000, self._poll_signup_tree)

    def _refresh_signup_tree(self) -> None:
        for row in self.signup_tree.get_children():
            self.signup_tree.delete(row)
        for account in self.get_registered_accounts():
            self.signup_tree.insert(
                "",
                "end",
                values=(
                    account["full_name"],
                    account["username"],
                    account["role"],
                    account["created_at"],
                ),
            )

    def _poll_signup_tree(self) -> None:
        self._refresh_signup_tree()
        self.root.after(30000, self._poll_signup_tree)

    def _create_tab_consultations(self, page) -> None:
        consultations_box = ttk.LabelFrame(page, text="Client Medicine Consultations", padding=12)
        page.add(consultations_box)
        ttk.Label(
            consultations_box,
            text="Website requests are shared here. Select a request to update its status and write a reply visible to the client.",
        ).pack(anchor="w", pady=(0, 8))

        columns = (
            "ID",
            "Client",
            "Username",
            "Medicine",
            "Question",
            "Status",
            "Admin Reply",
            "Submitted",
        )
        self.consultation_tree = ttk.Treeview(
            consultations_box,
            columns=columns,
            show="headings",
        )
        widths = (55, 150, 130, 150, 300, 100, 260, 150)
        for column, width in zip(columns, widths):
            self.consultation_tree.heading(column, text=column)
            self.consultation_tree.column(column, width=width, anchor="w")
        horizontal_scrollbar = ttk.Scrollbar(
            consultations_box,
            orient="horizontal",
            command=self.consultation_tree.xview,
        )
        scrollbar = ttk.Scrollbar(
            consultations_box,
            orient="vertical",
            command=self.consultation_tree.yview,
        )
        self.consultation_tree.configure(
            xscrollcommand=horizontal_scrollbar.set,
            yscrollcommand=scrollbar.set,
        )
        self.consultation_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        horizontal_scrollbar.pack(side="bottom", fill="x")

        actions = ttk.Frame(consultations_box)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(
            actions,
            text="Review / Edit Selected",
            command=self._edit_selected_consultation,
        ).pack(side="right")
        ttk.Button(
            actions,
            text="Refresh Consultations",
            command=self._refresh_consultation_tree,
        ).pack(side="right", padx=(0, 8))
        self.consultation_tree.bind(
            "<Double-1>",
            self._on_consultation_double_click,
        )
        self._refresh_consultation_tree()
        self.root.after(30000, self._poll_consultation_tree)

    def _on_consultation_double_click(self, event) -> None:
        row = self.consultation_tree.identify_row(event.y)
        if row:
            self.consultation_tree.selection_set(row)
            self._edit_selected_consultation()

    def _refresh_consultation_tree(self) -> None:
        for row in self.consultation_tree.get_children():
            self.consultation_tree.delete(row)
        for consultation in self.get_consultations():
            self.consultation_tree.insert(
                "",
                "end",
                values=(
                    consultation["id"],
                    consultation["full_name"],
                    consultation["client_username"],
                    consultation["medicine_name"],
                    consultation["question"],
                    consultation["status"],
                    consultation["admin_reply"],
                    consultation["created_at"],
                ),
            )

    def _edit_selected_consultation(self) -> None:
        selected = self.consultation_tree.selection()
        if not selected:
            messagebox.showinfo(
                "Select a consultation",
                "Choose a client consultation before reviewing it.",
                parent=self.root,
            )
            return

        values = self.consultation_tree.item(selected[0], "values")
        consultation_id = int(values[0])
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Review consultation #{consultation_id}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.geometry("620x560")
        dialog.minsize(520, 460)

        body = ttk.Frame(dialog, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(
            body,
            text=f"{values[1]} (@{values[2]}) · {values[3]}",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w")
        ttk.Label(body, text="Client question").pack(anchor="w", pady=(18, 5))
        question = tk.Text(body, height=6, wrap="word", state="normal")
        question.insert("1.0", values[4])
        question.configure(state="disabled")
        question.pack(fill="x")

        ttk.Label(body, text="Status").pack(anchor="w", pady=(16, 5))
        status = ttk.Combobox(
            body,
            state="readonly",
            values=("Pending", "In Review", "Responded", "Closed"),
        )
        status.set(values[5] if values[5] in status["values"] else "Pending")
        status.pack(fill="x")

        ttk.Label(body, text="Reply to client (up to 2,000 characters)").pack(
            anchor="w", pady=(16, 5)
        )
        reply = tk.Text(body, height=8, wrap="word")
        reply.insert("1.0", values[6])
        reply.pack(fill="both", expand=True)

        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(16, 0))

        def save_consultation() -> None:
            try:
                self.update_consultation(
                    consultation_id,
                    status.get(),
                    reply.get("1.0", "end-1c"),
                )
            except ValueError as exc:
                messagebox.showerror("Could not save consultation", str(exc), parent=dialog)
                return
            except sqlite3.Error as exc:
                messagebox.showerror(
                    "Could not save consultation",
                    f"The consultation could not be saved: {exc}",
                    parent=dialog,
                )
                return
            dialog.destroy()
            self._refresh_consultation_tree()

        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(
            buttons,
            text="Save and Send Reply",
            command=save_consultation,
        ).pack(side="right", padx=(0, 8))

    def _poll_consultation_tree(self) -> None:
        self._refresh_consultation_tree()
        self.root.after(30000, self._poll_consultation_tree)

    def _populate_patient_combo(self) -> None:
        patients = self.get_patients()
        names = [f"{p['id']} - {p['full_name']}" for p in patients]
        for combo in [self.medicine_patient, self.schedule_patient, self.record_patient]:
            if combo is not None:
                combo["values"] = names
                if names:
                    combo.current(0)

    def refresh_all(self) -> None:
        self._populate_patient_combo()
        self._refresh_patient_tree()
        self._refresh_medicine_tree()
        self._refresh_reminders()
        self._refresh_schedule_tree()
        self._refresh_history_tree()
        self._refresh_record_tree()
        self._refresh_dashboard_data()
    def run(self) -> None:
        if self.root is not None:
            self.root.mainloop()


if __name__ == "__main__":
    LoginPage().run()
