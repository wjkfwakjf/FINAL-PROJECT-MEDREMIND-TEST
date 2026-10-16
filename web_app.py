from __future__ import annotations

import hmac
import os
import secrets
import sqlite3
from functools import wraps
from typing import Callable, TypeVar

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from werkzeug.middleware.proxy_fix import ProxyFix

from database import connect_db, is_mysql
from login import LoginPage
from manage_medicine import MedicineManagementFeature

ViewFunction = TypeVar("ViewFunction", bound=Callable)


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    # Railway terminates HTTPS in front of the app; trust its forwarded headers.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config.update(
        SECRET_KEY=os.environ.get("MEDREMIND_SECRET_KEY") or secrets.token_hex(32),
        DATABASE_PATH=db_path,
        MYSQL_DATABASE=is_mysql(db_path),
        ADMIN_SIGNUP_KEY=os.environ.get("MEDREMIND_ADMIN_SIGNUP_KEY", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("MEDREMIND_COOKIE_SECURE") == "1",
    )

    login_page = LoginPage(db_path=app.config["DATABASE_PATH"])
    if not app.config["MYSQL_DATABASE"]:
        conn = connect_db(app.config["DATABASE_PATH"])
        try:
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
            conn.commit()
        finally:
            conn.close()

    @app.before_request
    def protect_forms() -> None:
        csrf_token = session.get("csrf_token")
        if csrf_token is None:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token
        if request.method == "POST":
            submitted_token = request.form.get("csrf_token", "")
            if not hmac.compare_digest(csrf_token, submitted_token):
                abort(400, description="Invalid or missing form security token.")

    @app.context_processor
    def inject_form_token() -> dict[str, str]:
        return {"csrf_token": session.get("csrf_token", "")}

    def client_required(view: ViewFunction) -> ViewFunction:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != "Client":
                flash("Please sign in with a client account to continue.", "error")
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    def admin_required(view: ViewFunction) -> ViewFunction:
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != "Administrator":
                flash("Please sign in with an admin account to continue.", "error")
                return redirect(url_for("admin_login"))
            return view(*args, **kwargs)

        return wrapped  # type: ignore[return-value]

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/")
    def home():
        if session.get("role") == "Client":
            return redirect(url_for("catalog"))
        if session.get("role") == "Administrator":
            return redirect(url_for("admin_dashboard"))
        return render_template("landing.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            try:
                login_page.create_account(
                    request.form.get("full_name", ""),
                    request.form.get("username", ""),
                    request.form.get("password", ""),
                    request.form.get("confirm_password", ""),
                    role="Client",
                )
            except ValueError as exc:
                flash(str(exc), "error")
                return render_template("signup.html"), 400
            session.clear()
            session["username"] = request.form.get("username", "").strip().lower()
            session["role"] = "Client"
            flash("Your client account is ready.", "success")
            return redirect(url_for("catalog"))
        return render_template("signup.html")

    @app.route("/admin-signup", methods=["GET", "POST"])
    def admin_signup():
        admin_signup_key_required = app.config["MYSQL_DATABASE"]
        if admin_signup_key_required and not app.config["ADMIN_SIGNUP_KEY"]:
            abort(
                503,
                description="Admin signup is disabled until MEDREMIND_ADMIN_SIGNUP_KEY is configured.",
            )
        if request.method == "POST":
            if admin_signup_key_required and not hmac.compare_digest(
                request.form.get("admin_signup_key", ""),
                app.config["ADMIN_SIGNUP_KEY"],
            ):
                flash("Invalid admin signup key.", "error")
                return (
                    render_template(
                        "admin_signup.html",
                        admin_signup_key_required=admin_signup_key_required,
                    ),
                    403,
                )
            try:
                login_page.create_account(
                    request.form.get("full_name", ""),
                    request.form.get("username", ""),
                    request.form.get("password", ""),
                    request.form.get("confirm_password", ""),
                    role="Administrator",
                )
            except ValueError as exc:
                flash(str(exc), "error")
                return (
                    render_template(
                        "admin_signup.html",
                        admin_signup_key_required=admin_signup_key_required,
                    ),
                    400,
                )
            session.clear()
            return redirect(url_for("admin_signup_complete"))

        return render_template(
            "admin_signup.html",
            admin_signup_key_required=admin_signup_key_required,
        )

    @app.get("/admin-signup/complete")
    def admin_signup_complete():
        return render_template("admin_signup_complete.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            account = login_page.authenticate(
                request.form.get("username", ""),
                request.form.get("password", ""),
            )
            if account is None or account.get("role") != "Client":
                flash("Invalid client username or password.", "error")
                return render_template("login.html"), 401
            session.clear()
            session["username"] = account["username"]
            session["role"] = account["role"]
            flash("Welcome back.", "success")
            return redirect(url_for("catalog"))
        return render_template("login.html")

    @app.route("/admin-login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            account = login_page.authenticate(
                request.form.get("username", ""),
                request.form.get("password", ""),
            )
            if (
                account is None
                or account.get("role") != "Administrator"
                or "full_name" not in account
            ):
                flash("Invalid admin username or password.", "error")
                return render_template("admin_login.html"), 401
            session.clear()
            session["username"] = account["username"]
            session["role"] = account["role"]
            flash("Welcome to the admin dashboard.", "success")
            return redirect(url_for("admin_dashboard"))
        return render_template("admin_login.html")

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        conn = connect_db(app.config["DATABASE_PATH"])
        try:
            accounts = conn.execute(
                """
                SELECT full_name, username, role, created_at
                FROM users
                ORDER BY created_at DESC, LOWER(username)
                """
            ).fetchall()
            consultations = conn.execute(
                """
                SELECT c.id, u.full_name, c.client_username, c.medicine_name,
                       c.question, c.status, c.admin_reply, c.created_at
                FROM consultations c
                JOIN users u ON u.username = c.client_username
                ORDER BY c.created_at DESC, c.id DESC
                """
            ).fetchall()
            client_count = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'Client'"
            ).fetchone()[0]
            pending_count = conn.execute(
                "SELECT COUNT(*) FROM consultations WHERE lower(trim(status)) = 'pending'"
            ).fetchone()[0]
            latest_consultation_id = conn.execute(
                "SELECT COALESCE(MAX(id), 0) FROM consultations"
            ).fetchone()[0]
        finally:
            conn.close()
        return render_template(
            "admin_dashboard.html",
            accounts=accounts,
            consultations=consultations,
            client_count=client_count,
            pending_count=pending_count,
            latest_consultation_id=latest_consultation_id,
        )

    @app.post("/admin/accounts/<username>/reset-password")
    @admin_required
    def admin_reset_client_password(username: str):
        try:
            login_page.reset_client_password(
                username,
                request.form.get("password", ""),
                request.form.get("confirm_password", ""),
            )
        except ValueError as exc:
            flash(str(exc), "error")
        else:
            flash(
                f"Password reset for @{username}. Share the new password with them securely.",
                "success",
            )
        return redirect(url_for("admin_dashboard") + "#accounts")

    @app.get("/admin/notifications")
    @admin_required
    def admin_notifications():
        after_id_value = request.args.get("after_id", "")
        if not after_id_value.isdecimal():
            abort(400, description="after_id must be a non-negative integer.")
        after_id = int(after_id_value)
        conn = connect_db(app.config["DATABASE_PATH"])
        try:
            rows = conn.execute(
                """
                SELECT c.id, u.full_name, c.client_username, c.medicine_name,
                       c.created_at
                FROM consultations c
                JOIN users u ON u.username = c.client_username
                WHERE c.id > ?
                ORDER BY c.id ASC
                LIMIT 50
                """,
                (after_id,),
            ).fetchall()
        finally:
            conn.close()
        return jsonify(
            notifications=[
                {
                    "id": row["id"],
                    "full_name": row["full_name"],
                    "username": row["client_username"],
                    "medicine_name": row["medicine_name"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
        )

    @app.post("/logout")
    def logout():
        if session.get("role") not in {"Client", "Administrator"}:
            flash("Please sign in before signing out.", "error")
            return redirect(url_for("login"))
        was_admin = session.get("role") == "Administrator"
        session.clear()
        flash("You have signed out.", "success")
        return redirect(url_for("admin_login" if was_admin else "login"))

    @app.get("/medicines")
    @client_required
    def catalog():
        conn = connect_db(app.config["DATABASE_PATH"])
        try:
            counts = conn.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN lower(trim(status)) = 'pending' THEN 1 ELSE 0 END)
                FROM consultations
                WHERE client_username = ?
                """,
                (session["username"],),
            ).fetchone()
            # Index access works for both SQLite rows and the MySQL wrapper
            # (unpacking a MySQL row would return column names, not values).
            consultation_count = int(counts[0] or 0)
            pending_count = int(counts[1] or 0)
        finally:
            conn.close()
        return render_template(
            "catalog.html",
            medicines=MedicineManagementFeature.MEDICINE_CATALOG,
            consultation_count=consultation_count,
            pending_count=pending_count or 0,
        )

    @app.route("/consultations", methods=["GET", "POST"])
    @client_required
    def consultations():
        if request.method == "POST":
            medicine_name = request.form.get("medicine_name", "").strip()
            question = request.form.get("question", "").strip()
            if medicine_name not in MedicineManagementFeature.MEDICINE_CATALOG:
                flash("Choose a medicine from the catalog.", "error")
            elif not question:
                flash("Enter a question about the medicine.", "error")
            elif len(question) > 2000:
                flash("Keep your question under 2,000 characters.", "error")
            else:
                conn = connect_db(app.config["DATABASE_PATH"])
                try:
                    conn.execute(
                        """
                        INSERT INTO consultations (client_username, medicine_name, question)
                        VALUES (?, ?, ?)
                        """,
                        (session["username"], medicine_name, question),
                    )
                    conn.commit()
                except sqlite3.Error:
                    app.logger.exception("Could not save client medicine consultation.")
                    raise
                finally:
                    conn.close()
                flash("Your consultation request was sent to the admin.", "success")
                return redirect(url_for("consultations"))

        conn = connect_db(app.config["DATABASE_PATH"])
        try:
            own_consultations = conn.execute(
                """
                SELECT medicine_name, question, status, created_at, admin_reply
                FROM consultations
                WHERE client_username = ?
                ORDER BY created_at DESC, id DESC
                """,
                (session["username"],),
            ).fetchall()
        finally:
            conn.close()
        return render_template(
            "consultations.html",
            medicines=MedicineManagementFeature.MEDICINE_CATALOG,
            own_consultations=own_consultations,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.environ.get("MEDREMIND_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("MEDREMIND_PORT", "5000")))
    app.run(host=host, port=port, debug=False)
