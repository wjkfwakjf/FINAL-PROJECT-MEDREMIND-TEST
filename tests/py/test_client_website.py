import os
import re
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from database import connect_db, is_mysql
from login import LoginPage, MedRemindCareApp
from web_app import create_app


class ClientWebsiteTests(unittest.TestCase):
    def test_railway_mysql_environment_selects_mysql_connection(self):
        railway_variables = {
            "MYSQLHOST": "mysql.internal",
            "MYSQLPORT": "3306",
            "MYSQLUSER": "medremind",
            "MYSQLPASSWORD": "secret",
            "MYSQLDATABASE": "medremind",
        }
        with patch.dict(os.environ, railway_variables, clear=True):
            self.assertTrue(is_mysql())
            with patch("database.mysql.connector.connect") as connect:
                connection = connect_db()
                connect.assert_called_once_with(
                    host="mysql.internal",
                    port=3306,
                    user="medremind",
                    password="secret",
                    database="medremind",
                )
                connection.close()

    def test_mysql_connection_url_decodes_credentials_and_database(self):
        with patch.dict(
            os.environ,
            {"MEDREMIND_DATABASE_URL": "mysql://user:p%40ss@mysql.internal:3307/care%20db"},
            clear=True,
        ):
            with patch("database.mysql.connector.connect") as connect:
                connection = connect_db()
                connect.assert_called_once_with(
                    host="mysql.internal",
                    port=3307,
                    user="user",
                    password="p@ss",
                    database="care db",
                )
                connection.close()

    def test_incomplete_railway_mysql_environment_fails_instead_of_using_sqlite(self):
        with patch.dict(os.environ, {"MYSQLUSER": "medremind"}, clear=True):
            with self.assertRaisesRegex(ValueError, "MYSQLHOST"):
                is_mysql()

    def test_desktop_admin_uses_shared_store_for_accounts_and_consultations(self):
        admin = MedRemindCareApp.__new__(MedRemindCareApp)
        admin.account = {"username": "admin", "role": "Administrator"}
        admin.db_path = self.database_path
        admin._use_shared_database = True
        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = []

        with patch("login.connect_db", return_value=connection) as connect:
            self.assertEqual(admin.get_registered_accounts(), [])
            connect.assert_called_once_with()

        with patch("login.connect_db", return_value=connection) as connect:
            self.assertEqual(admin.get_consultations(), [])
            connect.assert_called_once_with()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "website.db")
        self.app = create_app(self.database_path)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _csrf_token(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode("ascii")

    def test_client_signup_creates_client_and_opens_medicine_catalog(self):
        token = self._csrf_token("/signup")
        response = self.client.post(
            "/signup",
            data={
                "csrf_token": token,
                "full_name": "Web Client",
                "username": "web_client",
                "password": "secure-pass-123",
                "confirm_password": "secure-pass-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        catalog = self.client.get(response.location)
        self.assertEqual(catalog.status_code, 200)
        self.assertIn(b"Paracetamol", catalog.data)
        self.assertIn(b"YOUR MEDREMIND CARE SPACE", catalog.data)
        self.assertIn(b'id="medicine-search"', catalog.data)
        self.assertIn(b"Ask about a medicine", catalog.data)
        self.assertIn(b"0 pending", catalog.data)

        account = LoginPage(db_path=self.database_path).authenticate(
            "web_client", "secure-pass-123"
        )
        self.assertEqual(account["role"], "Client")
        admin = MedRemindCareApp.__new__(MedRemindCareApp)
        admin.db_path = self.database_path
        admin.account = {"username": "admin", "role": "Administrator"}
        self.assertEqual(admin.get_registered_accounts()[0]["role"], "Client")

    def test_signup_page_loads_separate_css_and_javascript_assets(self):
        response = self.client.get("/signup")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/static/css/signup.css", response.data)
        self.assertIn(b"/static/js/signup.js", response.data)
        css_response = self.client.get("/static/css/signup.css")
        js_response = self.client.get("/static/js/signup.js")
        self.assertEqual(css_response.status_code, 200)
        self.assertEqual(js_response.status_code, 200)
        css_response.close()
        js_response.close()

    def test_client_can_submit_consultation_visible_to_desktop_admin(self):
        login = LoginPage(db_path=self.database_path)
        login.create_account(
            "Web Client",
            "web_client",
            "secure-pass-123",
            "secure-pass-123",
            role="Client",
        )
        token = self._csrf_token("/login")
        self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "web_client",
                "password": "secure-pass-123",
            },
        )
        token = self._csrf_token("/consultations")
        response = self.client.post(
            "/consultations",
            data={
                "csrf_token": token,
                "medicine_name": "Paracetamol",
                "question": "Can I take this with my current prescription?",
            },
        )
        self.assertEqual(response.status_code, 302)

        admin = MedRemindCareApp.__new__(MedRemindCareApp)
        admin.db_path = self.database_path
        admin.account = {"username": "admin", "role": "Administrator"}
        consultations = admin.get_consultations()
        self.assertEqual(len(consultations), 1)
        self.assertEqual(consultations[0]["client_username"], "web_client")
        self.assertEqual(consultations[0]["medicine_name"], "Paracetamol")

        admin.update_consultation(
            consultations[0]["id"],
            "Responded",
            "Please ask your healthcare professional for personalized advice.",
        )
        client_page = self.client.get("/consultations")
        self.assertIn(b"Reply from the care team", client_page.data)
        self.assertIn(b"Please ask your healthcare professional", client_page.data)

    def test_consultation_page_has_guided_form_and_question_counter(self):
        LoginPage(db_path=self.database_path).create_account(
            "Web Client",
            "web_client",
            "secure-pass-123",
            "secure-pass-123",
            role="Client",
        )
        token = self._csrf_token("/login")
        self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "web_client",
                "password": "secure-pass-123",
            },
        )

        response = self.client.get("/consultations")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"How a consultation works", response.data)
        self.assertIn(b'id="question-count"', response.data)
        self.assertIn(b'id="consultation-form"', response.data)
        self.assertIn(b"For your safety", response.data)

    def test_guest_cannot_browse_catalog_or_submit_without_csrf(self):
        self.assertEqual(self.client.get("/medicines").status_code, 302)
        self.assertEqual(self.client.post("/signup").status_code, 400)

    def test_guest_homepage_shows_project_overview_and_product_features(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Care, in", response.data)
        self.assertIn(b"better rhythm.", response.data)
        for section_id in (
            b"introduction",
            b"problem",
            b"objectives",
            b"scope",
            b"limitations",
            b"interface-preview",
            b"dashboard-preview",
            b"system-features",
            b"expected-benefits",
            b"methodology",
            b"conclusion",
            b"flowchart",
            b"database-erd",
        ):
            with self.subTest(section=section_id):
                self.assertIn(b'id="' + section_id + b'"', response.data)
                self.assertIn(b'href="#' + section_id + b'"', response.data)
        for heading in (
            b"Statement of the Problem",
            b"Specific Objectives",
            b"Scope of the Study",
            b"Limitation of the Study",
            b"Current Interface Preview",
            b"Dashboard Preview",
            b"System Features",
            b"Expected Benefits",
            b"Development Methodology",
            b"Conclusion",
            b"Flowchart",
            b"Database ERD",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, response.data)
        self.assertIn(b"users", response.data)
        self.assertIn(b"medication_history", response.data)
        self.assertIn(b"/static/brand/medremind-care-logo.jpg", response.data)
        logo_response = self.client.get("/static/brand/medremind-care-logo.jpg")
        self.assertEqual(logo_response.status_code, 200)
        self.assertTrue(logo_response.mimetype.startswith("image/"))
        logo_response.close()
        self.assertIn(b'href="/login"', response.data)
        self.assertIn(b'href="/admin-login"', response.data)

    def test_client_login_page_prominently_shows_medremind_care_brand(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MedRemind", response.data)
        self.assertIn(b"<b>Care</b>", response.data)
        self.assertIn(b"Client sign in", response.data)
        self.assertIn(b"/static/brand/medremind-care-logo.jpg", response.data)

    def test_website_rejects_admin_account_login(self):
        token = self._csrf_token("/login")
        response = self.client.post(
            "/login",
            data={"csrf_token": token, "username": "admin", "password": "admin123"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_admin_can_sign_in_and_review_accounts_and_consultations(self):
        login_page = LoginPage(db_path=self.database_path)
        login_page.create_account(
            "Web Admin",
            "web_admin",
            "secure-admin-123",
            "secure-admin-123",
            role="Administrator",
        )
        login_page.create_account(
            "Website Client",
            "website_client",
            "secure-client-123",
            "secure-client-123",
            role="Client",
        )
        conn = connect_db(self.database_path)
        try:
            conn.execute(
                """
                INSERT INTO consultations (client_username, medicine_name, question)
                VALUES (?, ?, ?)
                """,
                (
                    "website_client",
                    "Paracetamol",
                    "Is this medicine suitable for me?",
                ),
            )
            conn.commit()
        finally:
            conn.close()

        token = self._csrf_token("/admin-login")
        response = self.client.post(
            "/admin-login",
            data={
                "csrf_token": token,
                "username": "web_admin",
                "password": "secure-admin-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get(response.location)
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Website Client", dashboard.data)
        self.assertIn(b"Is this medicine suitable for me?", dashboard.data)
        self.assertIn(b"CLIENT ACCOUNTS", dashboard.data)
        self.assertIn(b"NEEDS ATTENTION", dashboard.data)
        self.assertIn(b'id="consultation-search"', dashboard.data)
        self.assertIn(b'data-status="pending"', dashboard.data)
        self.assertIn(b'id="account-search"', dashboard.data)

        self.assertEqual(self.client.get("/medicines").status_code, 302)
        self.assertEqual(self.client.get("/").location, "/admin")

        token = self._csrf_token("/admin")
        logout = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(logout.location, "/admin-login")
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_admin_dashboard_can_poll_for_new_consultation_notifications(self):
        login = LoginPage(db_path=self.database_path)
        login.create_account(
            "Web Admin",
            "web_admin",
            "secure-admin-123",
            "secure-admin-123",
            role="Administrator",
        )
        login.create_account(
            "Website Client",
            "website_client",
            "secure-client-123",
            "secure-client-123",
            role="Client",
        )
        with self.client.session_transaction() as session:
            session["username"] = "web_admin"
            session["role"] = "Administrator"

        dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"data-notifications-url=\"/admin/notifications\"", dashboard.data)

        conn = connect_db(self.database_path)
        try:
            conn.execute(
                """
                INSERT INTO consultations (client_username, medicine_name, question)
                VALUES (?, ?, ?)
                """,
                ("website_client", "Paracetamol", "Can I ask about this medicine?"),
            )
            conn.commit()
        finally:
            conn.close()

        response = self.client.get("/admin/notifications?after_id=0")
        self.assertEqual(response.status_code, 200)
        notification = response.get_json()["notifications"][0]
        self.assertEqual(notification["id"], 1)
        self.assertEqual(notification["full_name"], "Website Client")
        self.assertEqual(notification["username"], "website_client")
        self.assertEqual(notification["medicine_name"], "Paracetamol")
        self.assertTrue(notification["created_at"])
        self.assertEqual(
            self.client.get("/admin/notifications?after_id=1").get_json(),
            {"notifications": []},
        )

    def test_admin_can_reset_client_password_from_registered_accounts(self):
        login = LoginPage(db_path=self.database_path)
        login.create_account(
            "Web Admin",
            "web_admin",
            "secure-admin-123",
            "secure-admin-123",
            role="Administrator",
        )
        login.create_account(
            "Website Client",
            "website_client",
            "secure-client-123",
            "secure-client-123",
            role="Client",
        )
        token = self._csrf_token("/admin-login")
        self.client.post(
            "/admin-login",
            data={
                "csrf_token": token,
                "username": "web_admin",
                "password": "secure-admin-123",
            },
        )

        dashboard = self.client.get("/admin")
        self.assertIn(b"Reset password", dashboard.data)
        token = re.search(
            rb'name="csrf_token" value="([^"]+)"', dashboard.data
        ).group(1).decode("ascii")
        response = self.client.post(
            "/admin/accounts/website_client/reset-password",
            data={
                "csrf_token": token,
                "password": "new-client-pass-456",
                "confirm_password": "new-client-pass-456",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith("#accounts"))
        self.assertIsNone(login.authenticate("website_client", "secure-client-123"))
        self.assertEqual(
            login.authenticate("website_client", "new-client-pass-456")["role"],
            "Client",
        )

    def test_only_admin_can_reset_client_password(self):
        login = LoginPage(db_path=self.database_path)
        login.create_account(
            "Website Client",
            "website_client",
            "secure-client-123",
            "secure-client-123",
            role="Client",
        )
        token = self._csrf_token("/signup")
        response = self.client.post(
            "/admin/accounts/website_client/reset-password",
            data={
                "csrf_token": token,
                "password": "new-client-pass-456",
                "confirm_password": "new-client-pass-456",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/admin-login")
        self.assertIsNotNone(login.authenticate("website_client", "secure-client-123"))

    def test_consultation_notifications_require_admin_and_valid_cursor(self):
        self.assertEqual(
            self.client.get("/admin/notifications?after_id=0").status_code,
            302,
        )

        LoginPage(db_path=self.database_path).create_account(
            "Web Admin",
            "web_admin",
            "secure-admin-123",
            "secure-admin-123",
            role="Administrator",
        )
        with self.client.session_transaction() as session:
            session["username"] = "web_admin"
            session["role"] = "Administrator"

        self.assertEqual(self.client.get("/admin/notifications").status_code, 400)

    def test_admin_signin_rejects_builtin_desktop_credentials(self):
        token = self._csrf_token("/admin-login")
        response = self.client.post(
            "/admin-login",
            data={
                "csrf_token": token,
                "username": "admin",
                "password": "admin123",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/admin").status_code, 302)

    def test_client_cannot_access_admin_dashboard(self):
        LoginPage(db_path=self.database_path).create_account(
            "Website Client",
            "website_client",
            "secure-client-123",
            "secure-client-123",
            role="Client",
        )
        token = self._csrf_token("/login")
        self.client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "website_client",
                "password": "secure-client-123",
            },
        )
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/admin-login")

    def test_admin_signup_page_does_not_require_invite_code(self):
        response = self.client.get("/admin-signup")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Create admin account", response.data)
        self.assertNotIn(b"Admin signup key", response.data)

    def test_mysql_admin_signup_requires_configured_key(self):
        self.app.config["MYSQL_DATABASE"] = True
        response = self.client.get("/admin-signup")
        self.assertEqual(response.status_code, 503)

    def test_mysql_admin_signup_requires_matching_key(self):
        self.app.config["MYSQL_DATABASE"] = True
        self.app.config["ADMIN_SIGNUP_KEY"] = "invite-key"
        response = self.client.get("/admin-signup")
        self.assertIn(b"Admin signup key", response.data)
        token = re.search(rb'name="csrf_token" value="([^"]+)"', response.data).group(1)

        denied = self.client.post(
            "/admin-signup",
            data={
                "csrf_token": token.decode("ascii"),
                "admin_signup_key": "wrong-key",
                "full_name": "Web Admin",
                "username": "web_admin",
                "password": "secure-pass-123",
                "confirm_password": "secure-pass-123",
            },
        )
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(b"invite code", response.data.lower())

    def test_admin_signup_creates_desktop_admin_without_invite_code(self):
        token = self._csrf_token("/admin-signup")
        response = self.client.post(
            "/admin-signup",
            data={
                "csrf_token": token,
                "full_name": "Web Admin",
                "username": "web_admin",
                "password": "secure-admin-123",
                "confirm_password": "secure-admin-123",
            },
        )
        self.assertEqual(response.status_code, 302)
        complete = self.client.get(response.location)
        self.assertEqual(complete.status_code, 200)

        account = LoginPage(db_path=self.database_path).authenticate(
            "web_admin", "secure-admin-123"
        )
        self.assertEqual(account["role"], "Administrator")
        desktop_admin = MedRemindCareApp.__new__(MedRemindCareApp)
        desktop_admin.db_path = self.database_path
        desktop_admin.account = {"username": "admin", "role": "Administrator"}
        self.assertEqual(
            desktop_admin.get_registered_accounts()[0]["role"],
            "Administrator",
        )
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_admin_signup_still_validates_credentials(self):
        token = self._csrf_token("/admin-signup")
        response = self.client.post(
            "/admin-signup",
            data={
                "csrf_token": token,
                "full_name": "Incomplete Admin",
                "username": "incomplete_admin",
                "password": "secure-admin-123",
                "confirm_password": "different-password",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(
            LoginPage(db_path=self.database_path).authenticate(
                "incomplete_admin", "secure-admin-123"
            )
        )

    def test_only_admin_can_read_consultations(self):
        admin = MedRemindCareApp.__new__(MedRemindCareApp)
        admin.db_path = self.database_path
        admin.account = {"username": "client", "role": "Client"}
        with self.assertRaises(PermissionError):
            admin.get_consultations()


if __name__ == "__main__":
    unittest.main()
