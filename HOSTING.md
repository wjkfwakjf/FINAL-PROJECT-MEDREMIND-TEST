# Publish MedRemind Care on Railway (public https address, not localhost)

Files to add to your project folder (next to web_app.py):
  wsgi.py  Procfile  .gitignore  requirements.txt (replace)  templates/landing.html (-> templates/)
Also copy your logo to static/brand/medremind-care-logo.jpg.

1. Put the project on GitHub (private repo is fine). Do NOT upload .venv or medremind.db (see .gitignore).
2. railway.com -> New Project -> Deploy from GitHub repo -> pick the repo.
3. In the same project: New -> Database -> MySQL.
4. Website service -> Variables:
     MYSQLHOST  = ${{MySQL.MYSQLHOST}}
     MYSQLPORT  = ${{MySQL.MYSQLPORT}}
     MYSQLUSER  = ${{MySQL.MYSQLUSER}}
     MYSQLPASSWORD = ${{MySQL.MYSQLPASSWORD}}
     MYSQLDATABASE = ${{MySQL.MYSQLDATABASE}}
     MEDREMIND_SECRET_KEY = <long random text>
     MEDREMIND_ADMIN_SIGNUP_KEY = <private key only you know>
     MEDREMIND_COOKIE_SECURE = 1
5. Settings -> Start command (if not read from Procfile):
     waitress-serve --listen=0.0.0.0:$PORT wsgi:app
6. Settings -> Networking -> Generate Domain (gives your public https link).
7. Own domain: buy one, then Settings -> Networking -> Custom Domain and add the DNS records Railway shows.
8. Open /admin-signup, enter your admin key, create the admin account.
