import random
from datetime import date, timedelta
from app.utils import utcnow

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import (
    User, Project, Task, Client, Document, Notification, CalendarEvent,
    ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE,
)


def run_seed():
    db.drop_all()
    db.create_all()

    today = date.today()

    admin = User(username="admin", email="admin@terraqua.io", full_name="Ananya Kapoor",
                 role=ROLE_ADMIN, department="Operations", avatar_color="#0B2E36")
    admin.set_password("admin123")

    mgr1 = User(username="manager1", email="rohan.mehta@terraqua.io", full_name="Rohan Mehta",
                role=ROLE_MANAGER, department="Infrastructure Projects", avatar_color="#0E7C86")
    mgr1.set_password("manager123")

    mgr2 = User(username="manager2", email="sanya.pillai@terraqua.io", full_name="Sanya Pillai",
                role=ROLE_MANAGER, department="Client Solutions", avatar_color="#3B82A6")
    mgr2.set_password("manager123")

    employees_data = [
        ("employee1", "Aditi Sharma"), ("employee2", "Karan Verma"), ("employee3", "Neha Joshi"),
        ("employee4", "Vikram Rao"), ("employee5", "Ishaan Gupta"), ("employee6", "Meera Nair"),
    ]
    employees = []
    palette = ["#C1652F", "#2F9E6E", "#D9A441", "#8A9BA0", "#3B82A6", "#0E7C86"]
    for i, (uname, fname) in enumerate(employees_data):
        dept = "Infrastructure Projects" if i < 3 else "Client Solutions"
        e = User(username=uname, email=f"{uname}@terraqua.io", full_name=fname,
                 role=ROLE_EMPLOYEE, department=dept, avatar_color=palette[i % len(palette)])
        e.set_password("employee123")
        employees.append(e)

    db.session.add_all([admin, mgr1, mgr2, *employees])
    db.session.commit()

    team1 = employees[:3]  # under mgr1
    team2 = employees[3:]  # under mgr2

    projects_data = [
        dict(name="Riverbank Flood Monitoring Rollout", manager=mgr1, status="active", priority="high",
             budget=850000, spent=620000, progress=65, start_offset=-70, end_offset=25,
             description="Deploy IoT water-level sensors and dashboards along the river basin."),
        dict(name="Groundwater Sensor Network Expansion", manager=mgr1, status="planning", priority="medium",
             budget=420000, spent=40000, progress=10, start_offset=-10, end_offset=90,
             description="Extend the groundwater monitoring network to 12 new districts."),
        dict(name="Legacy Pump Station Retrofit", manager=mgr1, status="completed", priority="medium",
             budget=300000, spent=295000, progress=100, start_offset=-150, end_offset=-20,
             description="Retrofit ageing pump stations with remote telemetry."),
        dict(name="Municipal Water Quality Dashboard", manager=mgr2, status="active", priority="high",
             budget=500000, spent=512000, progress=80, start_offset=-55, end_offset=6,
             description="Real-time water quality analytics dashboard for municipal clients."),
        dict(name="Coastal Erosion Client Portal", manager=mgr2, status="on_hold", priority="low",
             budget=150000, spent=60000, progress=30, start_offset=-40, end_offset=60,
             description="Client-facing portal tracking coastal erosion sensor data."),
        dict(name="Agri Irrigation Analytics Pilot", manager=mgr2, status="active", priority="medium",
             budget=275000, spent=180000, progress=55, start_offset=-30, end_offset=40,
             description="Pilot analytics suite for smart irrigation scheduling."),
    ]

    projects = []
    for pd in projects_data:
        p = Project(
            name=pd["name"], description=pd["description"], status=pd["status"], priority=pd["priority"],
            budget=pd["budget"], spent=pd["spent"], progress=pd["progress"],
            manager_id=pd["manager"].id,
            start_date=today + timedelta(days=pd["start_offset"]),
            end_date=today + timedelta(days=pd["end_offset"]),
        )
        db.session.add(p)
        projects.append(p)
    db.session.commit()

    # ---- Tasks --------------------------------------------------------------
    task_titles = [
        "Draft requirements checklist", "Calibrate sensor batch", "Review vendor SOW",
        "Prepare stakeholder update", "Fix dashboard rendering bug", "Set up staging environment",
        "Write API integration tests", "Design KPI card layout", "Migrate legacy readings",
        "Audit access permissions", "Update onboarding docs", "Configure alert thresholds",
        "Reconcile budget spreadsheet", "Prepare training session", "Optimize chart queries",
        "Validate sensor calibration report", "Coordinate field deployment", "Clean up telemetry data",
        "Prepare client demo", "Resolve login bug", "Draft weekly status email", "Tag release build",
    ]
    statuses = ["todo", "in_progress", "review", "done"]
    priorities = ["low", "medium", "high"]

    def assignees_for(project):
        return team1 if project.manager_id == mgr1.id else team2

    task_count = 0
    for project in projects:
        for _ in range(random.randint(5, 8)):
            assignee = random.choice(assignees_for(project))
            status = random.choices(statuses, weights=[3, 3, 2, 5])[0]
            due_date = today + timedelta(days=random.randint(-10, 25))
            created_offset = random.randint(3, 60)
            created_at = utcnow() - timedelta(days=created_offset)
            completed_at = None
            if status == "done":
                completed_at = created_at + timedelta(days=random.randint(1, max(created_offset - 1, 1)))
            db.session.add(Task(
                title=random.choice(task_titles), project_id=project.id, assigned_to=assignee.id,
                status=status, priority=random.choice(priorities), due_date=due_date,
                created_at=created_at, completed_at=completed_at,
                description="Auto-generated demo task for TerrAqua Workspace.",
            ))
            task_count += 1
    db.session.commit()

    # Guarantee visible alert data for both manager teams (overdue + due-soon)
    for proj in (projects[0], projects[3]):
        sample = Task.query.filter_by(project_id=proj.id).order_by(Task.id).limit(2).all()
        if len(sample) >= 2:
            sample[0].status, sample[0].due_date = "in_progress", today - timedelta(days=random.randint(1, 4))
            sample[1].status, sample[1].due_date = "todo", today + timedelta(days=random.choice([1, 2]))
    db.session.commit()

    # Guarantee non-zero "this week" figures for the weekly summary demo
    recent = Task.query.order_by(Task.id.desc()).limit(4).all()
    if len(recent) >= 4:
        recent[0].created_at = utcnow() - timedelta(days=1)
        recent[1].created_at = utcnow() - timedelta(days=2)
        recent[2].status, recent[2].created_at = "done", utcnow() - timedelta(days=20)
        recent[2].completed_at = utcnow() - timedelta(hours=5)
        recent[3].status, recent[3].completed_at = "done", utcnow() - timedelta(days=1)
    db.session.commit()

    # ---- Clients (CRM) --------------------------------------------------------
    clients_data = [
        ("Kaveri Municipal Corp", "Kaveri Water Board", "active", 620000, mgr1),
        ("Nilgiri District Council", "Nilgiri Admin", "qualified", 340000, mgr1),
        ("BlueDrop Utilities", "BlueDrop Pvt Ltd", "lead", 180000, mgr1),
        ("Coastal Line Authority", "CLA", "active", 410000, mgr2),
        ("GreenFields AgriTech", "GreenFields", "qualified", 260000, mgr2),
        ("Sahyadri Irrigation Board", "Sahyadri Board", "lead", 150000, mgr2),
        ("Metro Water Works", "MWW", "inactive", 90000, mgr2),
        ("Delta Basin Trust", "Delta Basin", "active", 500000, mgr1),
        ("Prakriti Analytics Co-op", "Prakriti", "lead", 120000, mgr2),
        ("EastRiver Municipal Body", "EastRiver Corp", "qualified", 275000, mgr1),
    ]
    for name, company, status, value, owner in clients_data:
        db.session.add(Client(
            name=name, company=company, status=status, deal_value=value, assigned_to=owner.id,
            email=f"contact@{company.lower().replace(' ', '')}.example.com",
            phone=f"+91 9{random.randint(100000000, 999999999)}",
            notes="Demo CRM record for TerrAqua Workspace.",
            created_at=utcnow() - timedelta(days=random.choice([1, 2, 4, 10, 20, 45, 60])),
            last_contact=today - timedelta(days=random.randint(0, 20)),
        ))
    db.session.commit()

    # ---- Calendar events --------------------------------------------------------
    events_data = [
        ("Sprint Planning", "meeting", 2, mgr1, projects[0]),
        ("Client Review Call", "meeting", 4, mgr2, projects[3]),
        ("Budget Review", "reminder", 6, admin, None),
        ("Field Deployment Window", "reminder", 8, mgr1, projects[1]),
        ("Quarterly Ops Review", "meeting", 12, admin, None),
        ("Vendor Sync", "meeting", -2, mgr2, projects[5]),
    ]
    for title, etype, offset, creator, project in events_data:
        start_dt = utcnow() + timedelta(days=offset)
        db.session.add(CalendarEvent(
            title=title, event_type=etype, start=start_dt, end=start_dt + timedelta(hours=1),
            all_day=False, project_id=project.id if project else None, created_by=creator.id,
            description="Auto-generated demo calendar entry.",
        ))
    db.session.commit()

    # ---- Documents (schema completeness) -----------------------------------------
    doc_names = ["requirements.pdf", "architecture-diagram.png", "vendor-contract.pdf",
                 "sensor-calibration-log.csv", "budget-sheet.xlsx"]
    for project in projects:
        for name in random.sample(doc_names, k=2):
            db.session.add(Document(filename=name, project_id=project.id, uploaded_by=project.manager_id,
                                     size_kb=random.randint(80, 4200), category="general"))
    db.session.commit()

    # ---- Notifications -------------------------------------------------------------
    notif_templates = [
        ("Task assigned", "A new task was assigned to you.", "info"),
        ("Deadline approaching", "One of your tasks is due soon.", "warning"),
        ("Task completed", "A teammate marked a task as done.", "success"),
        ("Budget alert", "A project you manage is nearing its budget limit.", "danger"),
        ("New CRM lead", "A new lead was added to the pipeline.", "info"),
    ]
    all_users = [admin, mgr1, mgr2, *employees]
    for u in all_users:
        for _ in range(random.randint(3, 6)):
            title, message, category = random.choice(notif_templates)
            db.session.add(Notification(
                user_id=u.id, title=title, message=message, category=category,
                is_read=random.choice([True, True, False]),
                created_at=utcnow() - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23)),
            ))
    db.session.commit()

    return {
        "users": len(all_users), "projects": len(projects), "tasks": task_count,
        "clients": len(clients_data), "events": len(events_data),
    }


@click.command("seed-db")
@with_appcontext
def seed_cli():
    """Wipe and re-seed the database with demo data."""
    stats = run_seed()
    click.echo(f"Seeded database: {stats}")
