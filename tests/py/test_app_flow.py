import os
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta

from database import connect_db, test_connection
from login import LoginPage


class LoginFlowTests(unittest.TestCase):
    def test_valid_login_returns_account(self):
        page = LoginPage()
        account = page.authenticate("admin", "admin123")
        self.assertIsNotNone(account)
        self.assertEqual(account["role"], "Administrator")

    def test_invalid_login_returns_none(self):
        page = LoginPage()
        self.assertIsNone(page.authenticate("admin", "wrongpass"))

    def test_signup_creates_account_with_hashed_password(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "users.db")
            page = LoginPage(db_path=database_path)

            account = page.create_account(
                "New Client",
                "new_caregiver",
                "secure-pass-123",
                "secure-pass-123",
            )
            authenticated = page.authenticate("NEW_CAREGIVER", "secure-pass-123")
            self.assertEqual(account["role"], "Caregiver")
            self.assertEqual(authenticated["role"], "Caregiver")
            self.assertEqual(authenticated["full_name"], "New Client")
            self.assertIsNone(page.authenticate("new_caregiver", "wrong-password"))

            conn = sqlite3.connect(database_path)
            try:
                password_hash = conn.execute(
                    "SELECT password_hash FROM users WHERE username = ?",
                    ("new_caregiver",),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertNotEqual(password_hash, "secure-pass-123")

    def test_client_role_can_be_created_without_changing_existing_roles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "legacy-users.db")
            page = LoginPage(db_path=database_path)
            page.create_account(
                "Existing Caregiver",
                "existing_caregiver",
                "secure-pass-123",
                "secure-pass-123",
            )
            page.create_account(
                "New Client",
                "new_client",
                "secure-pass-123",
                "secure-pass-123",
                role="Client",
            )

            self.assertEqual(
                page.authenticate("existing_caregiver", "secure-pass-123")["role"],
                "Caregiver",
            )
            self.assertEqual(
                page.authenticate("new_client", "secure-pass-123")["role"],
                "Client",
            )

            conn = sqlite3.connect(database_path)
            try:
                roles = dict(
                    conn.execute("SELECT username, role FROM users").fetchall()
                )
            finally:
                conn.close()

            self.assertEqual(roles["existing_caregiver"], "Caregiver")
            self.assertEqual(roles["new_client"], "Client")

    def test_signup_rejects_mismatched_passwords(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = LoginPage(db_path=os.path.join(temp_dir, "users.db"))
            with self.assertRaisesRegex(ValueError, "Passwords do not match"):
                page.create_account("New Caregiver", "new_caregiver", "secure-pass-123", "different")

    def test_admin_signup_creates_admin_account_without_setup_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = LoginPage(db_path=os.path.join(temp_dir, "admin-signup.db"))
            account = page.create_admin_account(
                "New Admin",
                "new_admin",
                "secure-admin-123",
                "secure-admin-123",
            )
            self.assertEqual(account["role"], "Administrator")
            self.assertEqual(
                page.authenticate("new_admin", "secure-admin-123")["role"],
                "Administrator",
            )

    def test_admin_can_reset_client_password_without_storing_plaintext(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "reset-password.db")
            page = LoginPage(db_path=database_path)
            page.create_account(
                "Client User",
                "client_user",
                "old-password-123",
                "old-password-123",
                role="Client",
            )

            page.reset_client_password(
                "CLIENT_USER",
                "new-password-456",
                "new-password-456",
            )

            self.assertIsNone(page.authenticate("client_user", "old-password-123"))
            self.assertEqual(
                page.authenticate("client_user", "new-password-456")["role"],
                "Client",
            )
            conn = sqlite3.connect(database_path)
            try:
                password_salt, password_hash = conn.execute(
                    """
                    SELECT password_salt, password_hash
                    FROM users WHERE username = ?
                    """,
                    ("client_user",),
                ).fetchone()
            finally:
                conn.close()
            self.assertNotIn("new-password-456", password_hash)
            self.assertNotIn("new-password-456", password_salt)

    def test_client_password_reset_validates_input_and_client_role(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            page = LoginPage(db_path=os.path.join(temp_dir, "reset-password.db"))
            page.create_account(
                "Staff User",
                "staff_user",
                "staff-password-123",
                "staff-password-123",
            )

            with self.assertRaisesRegex(ValueError, "at least 8 characters"):
                page.reset_client_password("client_user", "short", "short")
            with self.assertRaisesRegex(ValueError, "Passwords do not match"):
                page.reset_client_password("client_user", "new-password-123", "different")
            with self.assertRaisesRegex(ValueError, "Client account not found"):
                page.reset_client_password(
                    "staff_user",
                    "new-password-123",
                    "new-password-123",
                )

    def test_admin_can_view_signup_list_without_password_fields(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "signups.db")
            LoginPage(db_path=database_path).create_account(
                "Test Client",
                "test_caregiver",
                "secure-pass-123",
                "secure-pass-123",
            )
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = database_path
            app.account = {"username": "admin", "role": "Administrator"}

            accounts = app.get_registered_accounts()
            self.assertEqual(len(accounts), 1)
            self.assertEqual(accounts[0]["full_name"], "Test Client")
            self.assertEqual(accounts[0]["username"], "test_caregiver")
            self.assertEqual(accounts[0]["role"], "Caregiver")
            self.assertIn("created_at", accounts[0].keys())
            self.assertNotIn("password_hash", accounts[0].keys())
            self.assertNotIn("password_salt", accounts[0].keys())

    def test_non_admin_cannot_view_signup_list(self):
        from login import MedRemindCareApp

        app = MedRemindCareApp.__new__(MedRemindCareApp)
        app.db_path = os.path.join(tempfile.gettempdir(), "unused-signups.db")
        app.account = {"username": "caregiver", "role": "Caregiver"}
        with self.assertRaises(PermissionError):
            app.get_registered_accounts()

    def test_admin_can_update_consultation_status_and_reply(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "consultations.db")
            LoginPage(db_path=database_path).create_account(
                "Web Client",
                "web_client",
                "secure-pass-123",
                "secure-pass-123",
                role="Client",
            )
            admin = MedRemindCareApp.__new__(MedRemindCareApp)
            admin.db_path = database_path
            admin.account = {"username": "admin", "role": "Administrator"}
            admin._build_database()
            conn = sqlite3.connect(database_path)
            try:
                conn.execute(
                    """
                    INSERT INTO consultations (client_username, medicine_name, question)
                    VALUES (?, ?, ?)
                    """,
                    ("web_client", "Paracetamol", "How should I ask about this?"),
                )
                conn.commit()
            finally:
                conn.close()

            admin.update_consultation(1, "Responded", "Please contact your clinician.")
            consultation = admin.get_consultations()[0]
            self.assertEqual(consultation["status"], "Responded")
            self.assertEqual(
                consultation["admin_reply"],
                "Please contact your clinician.",
            )
            with self.assertRaisesRegex(ValueError, "valid consultation status"):
                admin.update_consultation(1, "Unknown", "Reply")
            with self.assertRaisesRegex(ValueError, "under 2,000 characters"):
                admin.update_consultation(1, "Responded", "x" * 2001)

    def test_non_admin_cannot_update_consultation(self):
        from login import MedRemindCareApp

        admin = MedRemindCareApp.__new__(MedRemindCareApp)
        admin.account = {"username": "client", "role": "Client"}
        with self.assertRaises(PermissionError):
            admin.update_consultation(1, "Responded", "Reply")

    def test_dashboard_has_in_app_feature_navigation(self):
        from login import MedRemindCareApp

        navigation_items = {
            title: key for key, title, _ in MedRemindCareApp.feature_pages
        }
        self.assertEqual(
            navigation_items,
            {
                "Patient Registration": "patients",
                "Manage Medicine": "medicines",
                "Medicine Reminders": "reminders",
                "Medication Schedule": "schedule",
                "Medication History": "history",
                "Doctor/Appointment Records": "records",
            },
        )

    def test_dashboard_navigation_adapts_column_count_to_window_width(self):
        from login import MedRemindCareApp

        self.assertEqual(MedRemindCareApp._navigation_column_count(1180, 9), 9)
        self.assertEqual(MedRemindCareApp._navigation_column_count(980, 9), 8)
        self.assertEqual(MedRemindCareApp._navigation_column_count(300, 9), 2)
        self.assertEqual(MedRemindCareApp._navigation_column_count(300, 0), 0)

    def test_dashboard_greeting_uses_signed_in_name_with_username_fallback(self):
        from login import MedRemindCareApp

        app = MedRemindCareApp.__new__(MedRemindCareApp)
        app.account = {
            "username": "adrian",
            "full_name": "Adrian",
            "role": "Caregiver",
        }
        self.assertEqual(app._dashboard_user_name(), "Adrian")

        app.account = {"username": "admin", "role": "Administrator"}
        self.assertEqual(app._dashboard_user_name(), "admin")

    def test_brand_background_image_asset_is_available(self):
        assets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "MedRemind.jpg")
        self.assertTrue(os.path.isfile(os.path.join(assets_path, "MedRemind Care.png")))
        logo_path = os.path.join(assets_path, "MedRemind Care- LOGO.jpg.jpg")
        self.assertTrue(os.path.isfile(logo_path))

        from PIL import Image

        with Image.open(logo_path) as logo:
            self.assertEqual(logo.format, "JPEG")

    def test_dashboard_features_are_split_into_modules(self):
        from doctor_appointment_records import DoctorAppointmentRecordsFeature
        from login import MedRemindCareApp
        from manage_medicine import MedicineManagementFeature
        from medication_history import MedicationHistoryFeature
        from medication_schedule import MedicationScheduleFeature
        from medicine_reminders import MedicineRemindersFeature
        from patient_registration import PatientRegistrationFeature

        expected_owners = {
            "_create_tab_patient": PatientRegistrationFeature,
            "register_patient": PatientRegistrationFeature,
            "_create_tab_medicine": MedicineManagementFeature,
            "add_medicine": MedicineManagementFeature,
            "_create_tab_reminders": MedicineRemindersFeature,
            "update_medicine_status": MedicineRemindersFeature,
            "_create_tab_schedule": MedicationScheduleFeature,
            "save_schedule": MedicationScheduleFeature,
            "_create_tab_history": MedicationHistoryFeature,
            "_create_tab_records": DoctorAppointmentRecordsFeature,
            "save_record": DoctorAppointmentRecordsFeature,
        }
        for method_name, feature_class in expected_owners.items():
            with self.subTest(method=method_name):
                self.assertIs(
                    getattr(MedRemindCareApp, method_name),
                    getattr(feature_class, method_name),
                )

    def test_medicine_catalog_has_requested_medicines_and_strength_examples(self):
        from login import MedRemindCareApp

        expected = {
            "Paracetamol": "Biogesic, Tempra, Calpol",
            "Ibuprofen": "Advil, Alaxan",
            "Mefenamic Acid": "Ponstan",
            "Cetirizine": "Alizer, Zyrtec",
            "Loratadine": "Claritin",
            "Dextromethorphan": "Robitussin",
            "Ambroxol": "Expel",
            "Amlodipine": "Norvasc",
            "Losartan": "Cozaar",
            "Atorvastatin": "Lipitor",
            "Omeprazole": "Losec, Prilosec",
            "Loperamide": "Imodium",
            "Aluminum Hydroxide + Magnesium Hydroxide": "Kremil-S",
        }
        for medicine, brands in expected.items():
            with self.subTest(medicine=medicine):
                details = MedRemindCareApp.MEDICINE_CATALOG[medicine]
                self.assertEqual(details["brands"], brands)
                self.assertTrue(details["strengths"])

    def test_removed_demo_patients_do_not_appear_in_sample_dashboards(self):
        from admindashboard import build_demo_data as build_admin_demo
        from appointments import build_demo_data as build_appointment_demo

        for dashboard in (build_admin_demo(), build_appointment_demo()):
            render = getattr(dashboard, "render_summary", None) or dashboard.render_dashboard
            rendered = render()
            self.assertNotIn("Aisha Yusuf", rendered)
            self.assertNotIn("Daniel Okafor", rendered)

    def test_database_starts_without_sample_patients(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "empty.db")
            app._build_database()
            self.assertEqual(app.get_patients(), [])

    def test_patient_id_sequence_is_preserved_after_manual_id_edit_and_restart(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "patient-ids.db")
            app._build_database()

            conn = app._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO patients (id, full_name, age, contact)
                    VALUES (6, 'Test Patient', 25, '5550000')
                    """
                )
                conn.execute("UPDATE patients SET id = 1 WHERE id = 6")
                conn.commit()
            finally:
                conn.close()

            restarted_app = MedRemindCareApp.__new__(MedRemindCareApp)
            restarted_app.db_path = app.db_path
            restarted_app._build_database()
            conn = restarted_app._connect()
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO patients (full_name, age, contact)
                    VALUES ('Next Patient', 30, '5550001')
                    """
                )
                conn.commit()
                self.assertEqual(cursor.lastrowid, 7)
            finally:
                conn.close()

    def test_editing_patient_id_preserves_id_after_refresh_and_updates_linked_records(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "patient-id-update.db")
            app._build_database()

            conn = app._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO patients (id, full_name, age, contact)
                    VALUES (6, 'Test Patient', 25, '5550000')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO medicines
                        (patient_id, medicine_name, dosage, reminder_time)
                    VALUES (6, 'Test Medicine', '1 tablet', '08:00')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO appointments
                        (patient_id, doctor_name, appointment_date, reason)
                    VALUES (6, 'Test Doctor', '2026-10-08', 'Follow-up')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO medication_history
                        (medicine_id, patient_id, patient_name, medicine_name, dosage,
                         status, dose_date)
                    VALUES (1, 6, 'Test Patient', 'Test Medicine', '1 tablet',
                            'taken', '2026-10-08')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            saved_id = app._save_patient_record(
                6,
                1,
                "Test Patient",
                25,
                "5550000",
                "General care",
            )
            self.assertEqual(saved_id, 1)
            self.assertEqual([patient["id"] for patient in app.get_patients()], [1])

            conn = app._connect()
            try:
                for table in ("medicines", "appointments", "medication_history"):
                    with self.subTest(table=table):
                        self.assertEqual(
                            conn.execute(
                                f"SELECT patient_id FROM {table}"
                            ).fetchone()["patient_id"],
                            1,
                        )
            finally:
                conn.close()

            restarted_app = MedRemindCareApp.__new__(MedRemindCareApp)
            restarted_app.db_path = app.db_path
            restarted_app._build_database()
            self.assertEqual([patient["id"] for patient in restarted_app.get_patients()], [1])
            self.assertEqual(
                restarted_app._save_patient_record(
                    None,
                    None,
                    "Next Patient",
                    30,
                    "5550001",
                    "General care",
                ),
                7,
            )

    def test_editing_patient_id_to_existing_id_is_rejected_without_relinking(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "duplicate-patient-id.db")
            app._build_database()
            conn = app._connect()
            try:
                conn.execute(
                    "INSERT INTO patients (id, full_name) VALUES (1, 'First Patient')"
                )
                conn.execute(
                    "INSERT INTO patients (id, full_name) VALUES (2, 'Second Patient')"
                )
                conn.execute(
                    """
                    INSERT INTO medicines
                        (patient_id, medicine_name, dosage)
                    VALUES (2, 'Test Medicine', '1 tablet')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            with self.assertRaisesRegex(ValueError, "already in use"):
                app._save_patient_record(
                    2,
                    1,
                    "Second Patient",
                    30,
                    "5550001",
                    "General care",
                )

            conn = app._connect()
            try:
                self.assertEqual(
                    conn.execute(
                        "SELECT patient_id FROM medicines"
                    ).fetchone()["patient_id"],
                    2,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT full_name FROM patients WHERE id = 2"
                    ).fetchone()["full_name"],
                    "Second Patient",
                )
            finally:
                conn.close()

    def test_renumbering_patients_compacts_ids_and_preserves_linked_records(self):
        from login import MedRemindCareApp
        from patient_registration import PatientRegistrationFeature

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "renumber-patients.db")
            app._build_database()

            conn = app._connect()
            try:
                conn.execute(
                    "INSERT INTO patients (id, full_name) VALUES (3, 'First Patient')"
                )
                conn.execute(
                    "INSERT INTO patients (id, full_name) VALUES (6, 'Second Patient')"
                )
                conn.execute(
                    """
                    INSERT INTO medicines
                        (patient_id, medicine_name, dosage)
                    VALUES (3, 'First Medicine', '1 tablet')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO medicines
                        (patient_id, medicine_name, dosage)
                    VALUES (6, 'Second Medicine', '1 tablet')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO appointments (patient_id, doctor_name)
                    VALUES (3, 'First Doctor')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO medication_history
                        (medicine_id, patient_id, patient_name, medicine_name,
                         dosage, status, dose_date)
                    VALUES (1, 3, 'First Patient', 'First Medicine',
                            '1 tablet', 'taken', '2026-10-08')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            mappings = PatientRegistrationFeature._renumber_patient_ids(app)
            self.assertEqual(mappings, {3: 1, 6: 2})
            self.assertEqual(
                [patient["id"] for patient in app.get_patients()],
                [1, 2],
            )

            conn = app._connect()
            try:
                self.assertEqual(
                    [
                        row["patient_id"]
                        for row in conn.execute(
                            "SELECT patient_id FROM medicines ORDER BY id"
                        )
                    ],
                    [1, 2],
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT patient_id FROM appointments"
                    ).fetchone()["patient_id"],
                    1,
                )
                self.assertEqual(
                    conn.execute(
                        "SELECT patient_id FROM medication_history"
                    ).fetchone()["patient_id"],
                    1,
                )
            finally:
                conn.close()

            restarted_app = MedRemindCareApp.__new__(MedRemindCareApp)
            restarted_app.db_path = app.db_path
            restarted_app._build_database()
            self.assertEqual(
                [patient["id"] for patient in restarted_app.get_patients()],
                [1, 2],
            )
            self.assertEqual(
                restarted_app._save_patient_record(
                    None,
                    None,
                    "Next Patient",
                    30,
                    "5550001",
                    "General care",
                ),
                7,
            )

    def test_application_and_database_helper_share_sqlite_file(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "shared.db")
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = database_path
            app._build_database()
            conn = connect_db(database_path)
            try:
                conn.execute(
                    "INSERT INTO patients (full_name, age, contact) VALUES (?, ?, ?)",
                    ("SQLite Test Patient", 25, "5550000"),
                )
                conn.commit()
            finally:
                conn.close()

            self.assertEqual(app.get_patients()[0]["full_name"], "SQLite Test Patient")
            self.assertIn(("patients",), test_connection(database_path))

    def test_dashboard_metrics_and_upcoming_appointments_use_patient_records(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "dashboard.db")
            app._build_database()

            today = date.today().isoformat()
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            conn = app._connect()
            try:
                conn.execute(
                    "INSERT INTO patients (full_name) VALUES (?)",
                    ("Dashboard Patient",),
                )
                conn.executemany(
                    """
                    INSERT INTO medicines (patient_id, medicine_name, dosage)
                    VALUES (1, ?, '1 tablet')
                    """,
                    [("Taken Medicine",), ("Missed Medicine",), ("Pending Medicine",)],
                )
                conn.executemany(
                    """
                    INSERT INTO medication_history
                        (medicine_id, patient_id, patient_name, medicine_name,
                         dosage, status, dose_date)
                    VALUES (?, 1, 'Dashboard Patient', ?, '1 tablet', ?, ?)
                    """,
                    [
                        (1, "Taken Medicine", "taken", today),
                        (2, "Missed Medicine", "missed", today),
                    ],
                )
                conn.executemany(
                    """
                    INSERT INTO appointments (patient_id, doctor_name, appointment_date, reason)
                    VALUES (1, ?, ?, ?)
                    """,
                    [
                        ("Past Doctor", yesterday, "Past visit"),
                        ("Future Doctor", tomorrow, "Follow-up"),
                    ],
                )
                conn.commit()
            finally:
                conn.close()

            metrics = app.get_dashboard_metrics()
            self.assertEqual(metrics["patient_count"], 1)
            self.assertEqual(metrics["medicine_count"], 3)
            self.assertEqual(metrics["taken_count"], 1)
            self.assertEqual(metrics["missed_count"], 1)
            self.assertEqual(metrics["pending_count"], 1)

            appointments = app.get_upcoming_appointments()
            self.assertEqual(len(appointments), 1)
            self.assertEqual(appointments[0]["doctor_name"], "Future Doctor")
            self.assertEqual(appointments[0]["patient_name"], "Dashboard Patient")

    def test_taken_medicine_returns_as_pending_on_next_day(self):
        from login import MedRemindCareApp

        with tempfile.TemporaryDirectory() as temp_dir:
            app = MedRemindCareApp.__new__(MedRemindCareApp)
            app.db_path = os.path.join(temp_dir, "medremind-test.db")
            app._build_database()

            conn = app._connect()
            try:
                conn.execute(
                    "INSERT INTO patients (full_name) VALUES (?)",
                    ("Test Patient",),
                )
                conn.execute(
                    """
                    INSERT INTO medicines
                        (patient_id, medicine_name, dosage, reminder_time, status)
                    VALUES (1, 'Test Medicine', '1 tablet', '08:00', 'pending')
                    """
                )
                conn.commit()
            finally:
                conn.close()

            self.assertEqual(len(app.get_pending_reminders()), 1)
            conn = app._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO medication_history
                        (medicine_id, patient_id, patient_name, medicine_name, dosage,
                         reminder_time, status, dose_date)
                    VALUES (1, 1, 'Test Patient', 'Test Medicine', '1 tablet',
                            '08:00', 'taken', ?)
                    """,
                    (datetime.now().date().isoformat(),),
                )
                conn.commit()
            finally:
                conn.close()

            self.assertEqual(len(app.get_pending_reminders()), 0)
            conn = app._connect()
            try:
                conn.execute(
                    "UPDATE medication_history SET dose_date = ? WHERE medicine_id = 1",
                    (date(2000, 1, 1).isoformat(),),
                )
                conn.commit()
            finally:
                conn.close()

            self.assertEqual(len(app.get_pending_reminders()), 1)


if __name__ == "__main__":
    unittest.main()
