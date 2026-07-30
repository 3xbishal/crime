# Crime Map - cPanel Production Deployment Guide

## Prerequisites

- cPanel hosting with **Passenger (mod_passenger)** enabled
- Python 3.8+ available on the server
- MySQL/MariaDB database (recommended) or SQLite
- SSH access to your cPanel account (or at least File Manager access)

---

## Step 1: Upload Files

1. Zip the project folder (exclude `venv/`, `db.sqlite3`, `__pycache__/`, `.git/`).
2. Upload and extract the zip in your cPanel file manager, e.g. to:
   ```
   /home/username/crime/
   ```

---

## Step 2: Create Python Application in cPanel

1. Log into cPanel → **Setup Python App** (or **Python** → **Setup Python App**)
2. Create a new app:
   - **Python version**: 3.8+ (use the latest available)
   - **Application root**: `/home/username/crime`
   - **Application URL**: Choose your domain/subdomain (e.g., `crime.yourdomain.com` or leave blank for root)
   - **Application startup file**: `passenger_wsgi.py`
   - **Application entry point**: `application`
3. Click **Create**.

---

## Step 3: Install Dependencies

After creating the app, cPanel opens a virtual environment. Run:

```bash
cd /home/username/crime
pip install -r requirements.txt
```

If you need additional packages (e.g., `mysqlclient` for MySQL):

```bash
pip install mysqlclient
```

---

## Step 4: Configure Environment Variables

In cPanel, go to **Python** → **Setup Python App** → your app → **Environment variables**.

Add the following (adjust values to match your setup):

| Variable | Value |
|---|---|
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | `your-very-long-secret-key-here` |
| `DJANGO_ALLOWED_HOSTS` | `yourdomain.com,www.yourdomain.com,127.0.0.1` |
| `DJANGO_DB_ENGINE` | `django.db.backends.mysql` |
| `DJANGO_DB_NAME` | `your_database_name` |
| `DJANGO_DB_USER` | `your_database_user` |
| `DJANGO_DB_PASSWORD` | `your_database_password` |
| `DJANGO_DB_HOST` | `localhost` |
| `DJANGO_DB_PORT` | `3306` |
| `GOOGLE_MAPS_API_KEY` | `your_actual_google_maps_api_key` |

Generate a secret key with:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Step 5: Set Up the Database

### Option A: Use cPanel MySQL Database Wizard

1. cPanel → **MySQL Databases** → Create a new database.
2. Create a database user and add it to the database with **All Privileges**.
3. Note the database name, username, and password.

### Option B: Use SQLite (simpler, less performant)

Skip the database creation. The app will fall back to SQLite automatically if no MySQL environment variables are set.

---

## Step 6: Run Migrations

In cPanel terminal or SSH:

```bash
cd /home/username/crime
source /home/username/virtualenv/your-app/3.x/bin/activate
python manage.py migrate
```

---

## Step 7: Create a Superuser (Admin)

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin account. This account must have `is_staff=True` to access the custom admin panel.

---

## Step 8: Set File Permissions

```bash
cd /home/username/crime
chmod 755 manage.py
chmod -R 755 static/
chmod -R 755 media/
chmod -R 755 templates/
chmod -R 755 crime_map/
mkdir -p logs
chmod 755 logs/
```

---

## Step 9: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

This gathers static files into `staticfiles/` for production serving.

---

## Step 10: Restart the Application

In cPanel → **Setup Python App** → **Restart** button.

---

## Step 11: Test the Site

Visit your application URL. You should see the Crime Map dashboard.

- **Visitor site**: `/`
- **Admin panel**: `/admin-panel/`
- **Map**: `/map/`
- **Predict**: `/predict/`

---

## Step 12: Optional - Enable Django Built-in Admin

If you want to use Django's built-in admin instead of (or in addition to) the custom panel:

1. In `crime_map/admin.py`, uncomment the standard admin registrations.
2. Ensure `django.contrib.admin` is in `INSTALLED_APPS` (it already is).
3. Run migrations if needed.

---

## Troubleshooting

### 500 Internal Server Error
- Check cPanel error logs: cPanel → **Errors** or **Logs** → **error_log**
- Check Django logs in `/home/username/crime/logs/django.log`
- Verify the Python virtual environment is activated.
- Verify `passenger_wsgi.py` path is correct in cPanel settings.

### Static Files Not Loading
- Ensure `collectstatic` has been run.
- Verify `STATIC_ROOT = BASE_DIR / "staticfiles"` in `settings.py`.
- Check file permissions on `staticfiles/` directory.

### Media Files Not Accessible
- Ensure `media/` directory exists and has write permissions (755 or 775).
- If using MySQL, uploaded CSVs go to `media/csv_uploads/`.

### Database Connection Error
- Verify MySQL credentials in environment variables.
- Ensure the MySQL user has ALL PRIVILEGES on the database.
- If using a remote DB, whitelist the cPanel server IP.

### CSRF / Cookie Issues
- Ensure `SECURE_COOKIE_*` settings are correct for your HTTPS setup.
- If using HTTP (not recommended), set `SESSION_COOKIE_SECURE = False` and `CSRF_COOKIE_SECURE = False`.

---

## Security Checklist

- [ ] `DJANGO_SECRET_KEY` is set to a strong, unique value
- [ ] `DJANGO_DEBUG` is set to `False`
- [ ] `ALLOWED_HOSTS` includes only your actual domains
- [ ] HTTPS is enabled (SSL certificate installed)
- [ ] Admin panel is protected with strong passwords
- [ ] MySQL database has a strong password
- [ ] File permissions are set correctly
- [ ] `.gitignore` prevents secrets from being committed

---

## Backup

Regularly back up:
- The database (via cPanel → **Backup** or phpMyAdmin)
- The `media/` directory (uploaded CSV files)
- The `staticfiles/` directory
- The `passenger_wsgi.py` and `settings.py` (for environment config)

---

## Notes

- The app uses **Passenger** (mod_passenger) on cPanel. Do NOT run `python manage.py runserver` in production.
- Static files are served directly by Apache/PHP-FPM after `collectstatic`.
- Media files are served from the `media/` directory. For high-traffic sites, consider using a CDN.
- For better performance, consider enabling **Redis** or **Memcached** via cPanel and updating `CACHES` in `settings.py`.
