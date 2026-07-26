from tests.conftest import login


# ---- Authentication -----------------------------------------------------------
def test_login_page_loads(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"TerrAqua Workspace" in resp.data


def test_admin_login_redirects_to_admin_dashboard(client):
    resp = login(client, "admin", "admin123")
    assert resp.status_code == 200
    assert b"Admin Dashboard" in resp.data


def test_manager_login_redirects_to_manager_dashboard(client):
    resp = login(client, "manager1", "manager123")
    assert b"Manager Dashboard" in resp.data


def test_employee_login_redirects_to_employee_dashboard(client):
    resp = login(client, "employee1", "employee123")
    assert b"My Dashboard" in resp.data


def test_invalid_login_shows_error(client):
    resp = login(client, "admin", "wrongpassword")
    assert b"Invalid username or password" in resp.data


def test_unauthenticated_user_is_redirected_to_login(client):
    resp = client.get("/admin/dashboard", follow_redirects=True)
    assert b"TerrAqua Workspace" in resp.data


# ---- Role-based access control -------------------------------------------------
def test_employee_cannot_access_admin_dashboard(client):
    login(client, "employee1", "employee123")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_employee_cannot_access_manager_dashboard(client):
    login(client, "employee1", "employee123")
    resp = client.get("/manager/dashboard")
    assert resp.status_code == 403


def test_manager_cannot_access_admin_dashboard(client):
    login(client, "manager1", "manager123")
    resp = client.get("/admin/dashboard")
    assert resp.status_code == 403


def test_admin_cannot_access_manager_dashboard(client):
    # dashboards are strictly single-role by design
    login(client, "admin", "admin123")
    resp = client.get("/manager/dashboard")
    assert resp.status_code == 403


def test_employee_cannot_export_clients_csv(client):
    login(client, "employee1", "employee123")
    resp = client.get("/reports/export/clients.csv")
    assert resp.status_code == 403


# ---- JSON API -------------------------------------------------------------------
def test_api_requires_login(client):
    resp = client.get("/api/kpis")
    assert resp.status_code in (302, 401)


def test_api_kpis_returns_json(client):
    login(client, "admin", "admin123")
    resp = client.get("/api/kpis")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 6
    assert "label" in data[0] and "value" in data[0]


def test_api_chart_task_status(client):
    login(client, "manager1", "manager123")
    resp = client.get("/api/charts/task-status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "doughnut"
    assert len(data["labels"]) == 4


def test_api_chart_completion_trend(client):
    login(client, "employee1", "employee123")
    resp = client.get("/api/charts/completion-trend")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["type"] == "line"
    assert len(data["labels"]) == 8


def test_notifications_endpoint_shape(client):
    login(client, "employee1", "employee123")
    resp = client.get("/api/notifications")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "unread_count" in data and "items" in data


def test_mark_all_notifications_read(client):
    login(client, "employee2", "employee123")
    before = client.get("/api/notifications").get_json()
    client.post("/api/notifications/read-all")
    after = client.get("/api/notifications").get_json()
    assert after["unread_count"] == 0
    assert before["unread_count"] >= after["unread_count"]


def test_calendar_events_endpoint(client):
    login(client, "admin", "admin123")
    resp = client.get("/api/calendar-events")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


# ---- Reports ----------------------------------------------------------------------
def test_csv_export_tasks(client):
    login(client, "employee1", "employee123")
    resp = client.get("/reports/export/tasks.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.mimetype
    assert b"Title" in resp.data


def test_csv_export_projects(client):
    login(client, "manager2", "manager123")
    resp = client.get("/reports/export/projects.csv")
    assert resp.status_code == 200
    assert b"Budget" in resp.data


def test_pdf_weekly_summary_export(client):
    login(client, "manager1", "manager123")
    resp = client.get("/reports/export/weekly-summary.pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"


# ---- Page rendering smoke tests (catches template/Jinja errors) ---------------------
def test_admin_projects_page_loads(client):
    login(client, "admin", "admin123")
    resp = client.get("/admin/projects")
    assert resp.status_code == 200
    assert b"Riverbank" in resp.data


def test_admin_users_page_loads(client):
    login(client, "admin", "admin123")
    resp = client.get("/admin/users")
    assert resp.status_code == 200
    assert b"Ananya Kapoor" in resp.data


def test_admin_crm_page_loads(client):
    login(client, "admin", "admin123")
    resp = client.get("/admin/crm")
    assert resp.status_code == 200
    assert b"Kaveri" in resp.data


def test_manager_tasks_page_loads(client):
    login(client, "manager2", "manager123")
    resp = client.get("/manager/tasks")
    assert resp.status_code == 200


def test_manager_crm_page_loads(client):
    login(client, "manager1", "manager123")
    resp = client.get("/manager/crm")
    assert resp.status_code == 200


def test_employee_tasks_page_loads(client):
    login(client, "employee3", "employee123")
    resp = client.get("/employee/tasks")
    assert resp.status_code == 200


def test_project_and_task_filters_do_not_error(client):
    login(client, "admin", "admin123")
    resp = client.get("/admin/projects?status=active&q=river")
    assert resp.status_code == 200


# ---- Write path: manager creates a task within their own project ---------------------
def test_manager_can_create_task_in_own_project(client, app):
    login(client, "manager1", "manager123")
    with app.app_context():
        from app.models import Project, User
        mgr = User.query.filter_by(username="manager1").first()
        project = Project.query.filter_by(manager_id=mgr.id).first()
        project_id = project.id

    resp = client.post(
        "/manager/tasks",
        data={"title": "Pytest-created task", "project_id": str(project_id), "priority": "medium"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Pytest-created task" in resp.data


def test_task_status_update_scoped_to_owner(client, app):
    login(client, "employee1", "employee123")
    with app.app_context():
        from app.models import Task, User
        emp = User.query.filter_by(username="employee1").first()
        other_task = Task.query.filter(Task.assigned_to != emp.id).first()
        other_task_id = other_task.id
        original_status = other_task.status

    resp = client.post(f"/employee/tasks/{other_task_id}/status", data={"status": "done"}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        from app.models import Task
        from app.extensions import db
        refreshed = db.session.get(Task, other_task_id)
        assert refreshed.status == original_status  # unchanged — employee1 isn't authorized to touch it
