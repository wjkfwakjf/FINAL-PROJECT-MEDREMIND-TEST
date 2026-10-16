# MedRemind Care

## Project structure

```
MedRemind-Care/
├── web_app.py              Flask website (routes)
├── wsgi.py                 Server entry point for hosting (adds a tkinter stand-in on servers)
├── database.py             SQLite / MySQL connection helper
├── login.py                Accounts + desktop app window
├── patient_registration.py, manage_medicine.py, medicine_reminders.py,
│   medication_schedule.py, medication_history.py,
│   doctor_appointment_records.py, admindashboard.py, appointments.py   (desktop app features)
├── templates/              HTML pages (base.html, landing.html, login.html, ...)
├── static/
│   ├── css/                core.css, components.css, polish.css, signup.css
│   ├── js/                 app.js, admin.js, catalog.js, consultations.js, signup.js
│   └── brand/              medremind-care-logo.jpg
├── tests/test_website.py   Smoke test (python tests/test_website.py)
├── docs/DEPLOY.md          Step-by-step Railway guide
├── requirements.txt, Procfile, railway.json, .gitignore
```

The Python files stay at the top level because the desktop app and the website import each other by name.

## Client website

The website uses local `medremind.db` by default. To host it on Railway with MySQL:

1. Create a Railway project with a MySQL service and a Python website service.
2. Add a reference from the website service to the MySQL service so Railway provides `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and `MYSQLDATABASE`. The app detects these automatically. Alternatively, configure `MEDREMIND_DATABASE_URL` with a MySQL connection URL.
3. Set `MEDREMIND_SECRET_KEY` to a long random secret, `MEDREMIND_ADMIN_SIGNUP_KEY` to a separate private value, and `MEDREMIND_COOKIE_SECURE=1` in the website service's variables. Public admin signup is disabled until its key is set and requires the key to create an administrator account. Do not commit database credentials or any of these secrets.
4. The included `railway.json` and `Procfile` already set the start command (`waitress-serve --listen=0.0.0.0:$PORT wsgi:app`) and a health check at `/healthz`. Railway provides the public URL after deployment (Settings -> Networking -> Generate Domain).

This MySQL setup creates only the shared `users` and `consultations` tables. To let the desktop admin see website accounts and consultation requests, configure the same MySQL variables on that computer before launching MedRemind Care. Patient, medicine, appointment, and medication-history records remain in the desktop app's local SQLite database and are not synchronized.

For local development, install dependencies and run `.\.venv\Scripts\python.exe web_app.py`, then open `http://127.0.0.1:5000` in Chrome. Clients can create an account, browse the medicine catalog, and submit consultation requests. Public use requires deploying the app to a hosting provider and using the public HTTPS URL supplied/configured there; the localhost address is only accessible on your computer.

Admins can review website client accounts and consultation requests at `/admin` after signing in at `/admin-login`. While the dashboard is open, it checks for new consultations every eight seconds and displays an on-page alert. Admins can optionally enable browser notifications with the dashboard's **Enable browser alerts** button. The notification endpoint is admin-protected; full request details remain in the dashboard. With Railway configured, website accounts and consultations live in Railway MySQL. The desktop patient's, medicines', and appointments' records remain in local SQLite and are not shared with Railway.

In the desktop admin app configured for the same MySQL service, open **Client Consultations**, select a request, and choose **Review / Edit Selected** (or double-click the request) to update its status and send a reply. The reply is saved in MySQL and appears in the client's **Your consultation requests** list on the website.

The admin **Registered accounts** list can reset a client password if needed. The replacement is stored as a one-way password hash; existing passwords are never displayed. Share any replacement password with the client privately and ask them to change it after signing in.

### Admin signup

Admin accounts can be created from the website at `/admin-signup` or by choosing **Admin Sign Up** on the desktop welcome screen. The desktop screen has separate **Client/User Sign Up** and **Admin Sign Up** choices. For Railway-hosted MySQL, the website admin-signup form requires `MEDREMIND_ADMIN_SIGNUP_KEY`; local SQLite development does not require this key. Website admins can sign in at `/admin-login` and review account registrations and medicine consultations on the protected `/admin` dashboard. Admin accounts cannot use client-only website features.

### Patient IDs

In the desktop app's **Patient Registration** section, **Renumber Patients from 1** compacts existing patient IDs in ascending order. The operation also updates IDs linked from medicines, appointments, and medication history. The auto-increment high-water mark is retained so future registrations do not reuse old IDs.

## Admin dashboard

The desktop dashboard opens first and shows live patient and medicine totals, today's medication adherence based on recorded doses, and the next five appointments. It refreshes when the dashboard is opened, after patient or medication updates, and every 30 seconds. The navigation buttons are equal-width and wrap into additional rows when the window is narrower.

Install dependencies from the project folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the website server:

```powershell
.\.venv\Scripts\python.exe web_app.py
```

Open `http://127.0.0.1:5000` in a browser. To let other devices on the same network connect, set `MEDREMIND_HOST=0.0.0.0` before starting the server and use the server computer's LAN address; configure the firewall and use HTTPS for any public deployment. Set a persistent `MEDREMIND_SECRET_KEY` for deployments so browser sessions remain secure across server restarts. The built-in Flask server is for local development, not production hosting. Existing SQLite data is not copied to MySQL automatically; make a secure backup and intentionally migrate only data you want to move.
