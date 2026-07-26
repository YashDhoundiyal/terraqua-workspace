# TerrAqua Workspace — Dashboard, Analytics, Calendar & Notification Management System

A role-based operations platform for **Admin**, **Manager**, and **Employee** users, built with
Flask + SQLAlchemy + SQLite on the backend and Bootstrap 5 + Chart.js + FullCalendar on the
frontend — implemented per the TerrAqua Workspace project guide.

---

## 1. Tech stack

| Layer          | Technology                                  |
|----------------|----------------------------------------------|
| Backend        | Python, Flask, Flask-Login, SQLAlchemy       |
| Database       | SQLite (file-based, zero setup)              |
| Frontend       | HTML, Bootstrap 5, vanilla JavaScript        |
| Charts         | Chart.js                                     |
| Calendar       | FullCalendar                                 |
| Reports        | Python `csv` module + ReportLab (PDF)        |
| Testing        | Pytest (30 tests)                            |

## 2. Quick start

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed the database with demo data (safe to re-run — it wipes and re-seeds)
export FLASK_APP=run.py           # Windows (PowerShell): $env:FLASK_APP="run.py"
flask seed-db

# 4. Run the app
flask run
# or: python run.py

# 5. Open http://127.0.0.1:5000 and sign in with one of the demo accounts below
```

Run the test suite at any time with:
```bash
pytest -v
```

## 3. Demo credentials

Seeded by `flask seed-db`:

| Role     | Username     | Password      | Notes                                  |
|----------|--------------|---------------|-----------------------------------------|
| Admin    | `admin`      | `admin123`    | Ananya Kapoor — full org visibility     |
| Manager  | `manager1`   | `manager123`  | Rohan Mehta — Infrastructure Projects   |
| Manager  | `manager2`   | `manager123`  | Sanya Pillai — Client Solutions         |
| Employee | `employee1`–`employee6` | `employee123` | Distributed across both teams |

## 4. Where each module lives

| # | Module                       | Implementation |
|---|-------------------------------|-----------------|
| 1 | Authentication (3 roles)      | `app/auth/routes.py`, `app/decorators.py` (`role_required`), per-blueprint `before_request` guards |
| 2 | Admin Dashboard                | `app/admin/routes.py` + `app/templates/admin/dashboard.html` |
| 3 | Manager Dashboard               | `app/manager/routes.py` + `app/templates/manager/dashboard.html` |
| 4 | Employee Dashboard               | `app/employee/routes.py` + `app/templates/employee/dashboard.html` |
| 5 | KPI Cards (6–8 per role)        | `app/queries.py::kpis_for()` |
| 6 | Analytics Charts (6 chart types) | `app/queries.py::chart_payload()`, served via `app/api/routes.py`, rendered by `static/js/charts.js` |
| 7 | Calendar                        | `app/api/routes.py::calendar_events()` merges explicit events + task due dates + project deadlines; rendered by `static/js/calendar.js` (FullCalendar) |
| 8 | Notification System              | `Notification` model, `app/api/routes.py`, bell dropdown in `base.html` + `static/js/notifications.js` (polls every 30s) |
| 9 | Alerts                          | `app/queries.py::alerts_for()` — overdue tasks, due-soon tasks, over-budget & ending-soon projects |
| 10 | Weekly Summary                 | `app/queries.py::weekly_summary_for()` |
| 11 | Reports (CSV/PDF)               | `app/reports/routes.py` — CSV for tasks/projects/clients, PDF weekly summary via ReportLab |
| 12 | Filters & Search                | Server-side query-string filtering on every list page (status + free-text search) |
| 13 | Database Integration             | `app/models.py` — 7 tables, real foreign keys, seeded via `app/seed.py` |
| 14 | Testing & Validation             | `tests/` — 30 Pytest tests covering auth, RBAC, APIs, exports, and write paths |
| 15 | Documentation                   | This README + inline docstrings/comments |

## 5. Role scoping model

Access control is enforced in two layers:

1. **Blueprint guards** — `admin_bp`, `manager_bp`, and `employee_bp` each register a
   `before_request` hook that immediately 403s any signed-in user of the wrong role (and
   redirects anonymous users to `/auth/login`). Dashboards are intentionally kept fully
   separate rather than one dashboard with conditional sections.
2. **Query scoping** — `app/queries.py` centralizes *what data* each role can see:
   - **Admin** sees everything.
   - **Manager** sees only projects they manage, tasks within those projects, their team
     (distinct assignees across those projects), and CRM clients assigned to themselves.
   - **Employee** sees only tasks assigned to them, and the (read-only) projects those
     tasks belong to. Employees do not have CRM access.

   Every dashboard, list page, chart, CSV export, and calendar feed is built on these same
   helper functions, so a change to the scoping rules only has to happen in one place.

## 6. Design notes

The visual system uses a deliberate "Terra + Aqua" palette (deep teal `#0E7C86` for the
"aqua" side, terracotta clay `#C1652F` for "terra") instead of Bootstrap's default blue,
with Manrope for headings, Inter for body text, and IBM Plex Mono for KPI figures and table
numerics — reinforcing the "instrumented / measured" feel of an environmental-monitoring
operations tool.

## 7. Known limitations / possible next steps

- CRUD is intentionally scoped to what the brief needed: tasks/projects/clients/users
  support **create**, **read**, **status/progress update**; full edit-all-fields and delete
  flows were left out to keep the codebase focused on the dashboard/analytics modules.
- The `Document` model exists (for schema completeness — the brief mentions documents as
  data to integrate) and is seeded with sample rows, but there's no dedicated
  upload/management page, since it isn't one of the 15 listed modules.
- Notifications are polled every 30 seconds rather than pushed via WebSockets — simpler to
  run with just `flask run`, at the cost of near-real-time delivery.
- SQLite is intentionally used for zero-setup local grading/demo; swapping
  `SQLALCHEMY_DATABASE_URI` in `config.py` is all that's needed to point at Postgres/MySQL
  later.

## 8. Project structure

```
terraqua/
├── app/
│   ├── __init__.py            # application factory
│   ├── models.py               # SQLAlchemy models
│   ├── queries.py               # role-scoped KPIs, charts, alerts, weekly summary
│   ├── decorators.py            # @role_required
│   ├── seed.py                  # demo data + `flask seed-db`
│   ├── auth/                    # login / logout
│   ├── admin/                   # admin dashboard, projects, users, CRM
│   ├── manager/                 # manager dashboard, tasks, CRM
│   ├── employee/                # employee dashboard, tasks
│   ├── api/                     # JSON endpoints: kpis, charts, calendar, notifications
│   ├── reports/                 # CSV + PDF exports
│   ├── templates/                # Jinja templates (base shell + per-role pages)
│   └── static/{css,js}/          # design system CSS, Chart.js/FullCalendar/notifications JS
├── tests/                       # Pytest suite (30 tests)
├── requirements.txt
├── run.py
└── config.py
```
