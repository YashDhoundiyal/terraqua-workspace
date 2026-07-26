"""
Central place for role-scoped data access + analytics used by the
Admin / Manager / Employee dashboards and the /api chart & KPI endpoints.
Keeping this logic in one module means every dashboard sees data that is
consistently scoped to what that role is allowed to see.
"""
from datetime import date, timedelta
from app.utils import utcnow

from app.extensions import db
from app.models import User, Project, Task, Client, Notification, CalendarEvent, ROLE_ADMIN, ROLE_MANAGER

# ---- palette (kept in sync with static/css/style.css tokens) --------------
COLORS = {
    "teal": "#0E7C86",
    "clay": "#C1652F",
    "success": "#2F9E6E",
    "warning": "#D9A441",
    "danger": "#D14343",
    "info": "#3B82A6",
    "slate": "#8A9BA0",
}

TASK_STATUS_COLORS = {"todo": COLORS["slate"], "in_progress": COLORS["info"],
                       "review": COLORS["warning"], "done": COLORS["success"]}
PROJECT_STATUS_COLORS = {"planning": COLORS["slate"], "active": COLORS["teal"],
                          "on_hold": COLORS["warning"], "completed": COLORS["success"]}
PRIORITY_COLORS = {"low": COLORS["success"], "medium": COLORS["warning"], "high": COLORS["danger"]}
CLIENT_STATUS_COLORS = {"lead": COLORS["slate"], "qualified": COLORS["info"],
                         "active": COLORS["teal"], "inactive": COLORS["danger"]}


# ---- scoping ----------------------------------------------------------------
def visible_projects(user):
    if user.role == ROLE_ADMIN:
        return Project.query
    if user.role == ROLE_MANAGER:
        return Project.query.filter_by(manager_id=user.id)
    project_ids = db.session.query(Task.project_id).filter(Task.assigned_to == user.id).distinct()
    return Project.query.filter(Project.id.in_(project_ids))


def visible_tasks(user):
    if user.role == ROLE_ADMIN:
        return Task.query
    if user.role == ROLE_MANAGER:
        project_ids = [p.id for p in Project.query.filter_by(manager_id=user.id).with_entities(Project.id).all()]
        return Task.query.filter(Task.project_id.in_(project_ids))
    return Task.query.filter_by(assigned_to=user.id)


def visible_clients(user):
    if user.role == ROLE_ADMIN:
        return Client.query
    if user.role == ROLE_MANAGER:
        return Client.query.filter_by(assigned_to=user.id)
    return Client.query.filter(db.false())


def team_members(user):
    if user.role == ROLE_ADMIN:
        return User.query.filter(User.role != ROLE_ADMIN).order_by(User.full_name).all()
    if user.role == ROLE_MANAGER:
        project_ids = [p.id for p in Project.query.filter_by(manager_id=user.id).with_entities(Project.id).all()]
        user_ids = db.session.query(Task.assigned_to).filter(Task.project_id.in_(project_ids)).distinct()
        return User.query.filter(User.id.in_(user_ids)).order_by(User.full_name).all()
    return []


def visible_calendar_events(user):
    if user.role == ROLE_ADMIN:
        return CalendarEvent.query
    if user.role == ROLE_MANAGER:
        project_ids = [p.id for p in Project.query.filter_by(manager_id=user.id).with_entities(Project.id).all()]
        return CalendarEvent.query.filter(
            db.or_(CalendarEvent.project_id.in_(project_ids), CalendarEvent.created_by == user.id)
        )
    project_ids = db.session.query(Task.project_id).filter(Task.assigned_to == user.id).distinct()
    return CalendarEvent.query.filter(
        db.or_(CalendarEvent.project_id.in_(project_ids), CalendarEvent.created_by == user.id)
    )


# ---- KPI cards ----------------------------------------------------------------
def kpis_for(user):
    tasks = visible_tasks(user)
    projects = visible_projects(user)
    today = date.today()

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(Task.status == "done").count()
    overdue_tasks = tasks.filter(Task.status != "done", Task.due_date.isnot(None), Task.due_date < today).count()
    total_projects = projects.count()
    active_projects = projects.filter(Project.status == "active").count()

    cards = []

    if user.role == ROLE_ADMIN:
        headcount = User.query.filter(User.role != ROLE_ADMIN).count()
        pipeline_value = sum(c.deal_value or 0 for c in Client.query.filter(Client.status != "inactive").all())
        total_budget = sum(p.budget or 0 for p in Project.query.all())
        cards = [
            {"label": "Total Projects", "value": total_projects, "icon": "bi-kanban", "tone": "teal"},
            {"label": "Active Projects", "value": active_projects, "icon": "bi-lightning-charge", "tone": "info"},
            {"label": "Total Tasks", "value": total_tasks, "icon": "bi-list-check", "tone": "slate"},
            {"label": "Completed Tasks", "value": completed_tasks, "icon": "bi-check-circle", "tone": "success"},
            {"label": "Overdue Tasks", "value": overdue_tasks, "icon": "bi-exclamation-triangle", "tone": "danger"},
            {"label": "Team Members", "value": headcount, "icon": "bi-people", "tone": "teal"},
            {"label": "CRM Pipeline", "value": f"₹{pipeline_value:,.0f}", "icon": "bi-graph-up-arrow", "tone": "clay"},
            {"label": "Total Budget", "value": f"₹{total_budget:,.0f}", "icon": "bi-wallet2", "tone": "warning"},
        ]
    elif user.role == ROLE_MANAGER:
        members = team_members(user)
        pipeline_value = sum(c.deal_value or 0 for c in visible_clients(user).all())
        cards = [
            {"label": "My Projects", "value": total_projects, "icon": "bi-kanban", "tone": "teal"},
            {"label": "Active Projects", "value": active_projects, "icon": "bi-lightning-charge", "tone": "info"},
            {"label": "Team Tasks", "value": total_tasks, "icon": "bi-list-check", "tone": "slate"},
            {"label": "Completed Tasks", "value": completed_tasks, "icon": "bi-check-circle", "tone": "success"},
            {"label": "Overdue Tasks", "value": overdue_tasks, "icon": "bi-exclamation-triangle", "tone": "danger"},
            {"label": "Team Members", "value": len(members), "icon": "bi-people", "tone": "teal"},
            {"label": "My CRM Pipeline", "value": f"₹{pipeline_value:,.0f}", "icon": "bi-graph-up-arrow", "tone": "clay"},
        ]
    else:  # employee
        in_progress = tasks.filter(Task.status == "in_progress").count()
        due_this_week = tasks.filter(
            Task.status != "done", Task.due_date.isnot(None),
            Task.due_date >= today, Task.due_date <= today + timedelta(days=7)
        ).count()
        rate = round((completed_tasks / total_tasks) * 100) if total_tasks else 0
        cards = [
            {"label": "My Tasks", "value": total_tasks, "icon": "bi-list-check", "tone": "teal"},
            {"label": "In Progress", "value": in_progress, "icon": "bi-arrow-repeat", "tone": "info"},
            {"label": "Completed", "value": completed_tasks, "icon": "bi-check-circle", "tone": "success"},
            {"label": "Overdue", "value": overdue_tasks, "icon": "bi-exclamation-triangle", "tone": "danger"},
            {"label": "Due This Week", "value": due_this_week, "icon": "bi-calendar-week", "tone": "warning"},
            {"label": "My Projects", "value": total_projects, "icon": "bi-kanban", "tone": "clay"},
            {"label": "Completion Rate", "value": f"{rate}%", "icon": "bi-speedometer2", "tone": "slate"},
        ]
    return cards


# ---- charts ----------------------------------------------------------------
def chart_payload(kind, user):
    tasks = visible_tasks(user)

    if kind == "task-status":
        counts = {s: tasks.filter(Task.status == s).count() for s in ["todo", "in_progress", "review", "done"]}
        labels = ["To Do", "In Progress", "Review", "Done"]
        return {
            "type": "doughnut",
            "labels": labels,
            "datasets": [{"data": list(counts.values()),
                          "backgroundColor": [TASK_STATUS_COLORS[k] for k in counts]}],
        }

    if kind == "project-status":
        projects = visible_projects(user)
        statuses = ["planning", "active", "on_hold", "completed"]
        counts = {s: projects.filter(Project.status == s).count() for s in statuses}
        return {
            "type": "bar",
            "labels": ["Planning", "Active", "On Hold", "Completed"],
            "datasets": [{"label": "Projects", "data": list(counts.values()),
                          "backgroundColor": [PROJECT_STATUS_COLORS[k] for k in statuses]}],
        }

    if kind == "completion-trend":
        today = date.today()
        labels, data = [], []
        for i in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            week_end = week_start + timedelta(days=6)
            count = tasks.filter(
                Task.status == "done", Task.completed_at.isnot(None),
                db.func.date(Task.completed_at) >= week_start,
                db.func.date(Task.completed_at) <= week_end,
            ).count()
            labels.append(week_start.strftime("%b %d"))
            data.append(count)
        return {
            "type": "line",
            "labels": labels,
            "datasets": [{"label": "Tasks completed", "data": data,
                          "borderColor": COLORS["teal"], "backgroundColor": COLORS["teal"] + "33",
                          "fill": True, "tension": 0.35}],
        }

    if kind == "team-workload":
        members = team_members(user)[:10]
        labels = [m.full_name for m in members]
        data = [visible_tasks(user).filter(Task.assigned_to == m.id).count() for m in members]
        return {
            "type": "bar",
            "labels": labels,
            "datasets": [{"label": "Assigned tasks", "data": data, "backgroundColor": COLORS["info"]}],
        }

    if kind == "crm-pipeline":
        clients = visible_clients(user)
        statuses = ["lead", "qualified", "active", "inactive"]
        counts = {s: clients.filter(Client.status == s).count() for s in statuses}
        return {
            "type": "bar",
            "labels": ["Lead", "Qualified", "Active", "Inactive"],
            "datasets": [{"label": "Clients", "data": list(counts.values()),
                          "backgroundColor": [CLIENT_STATUS_COLORS[k] for k in statuses]}],
        }

    if kind == "priority-breakdown":
        priorities = ["low", "medium", "high"]
        counts = {p: tasks.filter(Task.priority == p).count() for p in priorities}
        return {
            "type": "doughnut",
            "labels": ["Low", "Medium", "High"],
            "datasets": [{"data": list(counts.values()),
                          "backgroundColor": [PRIORITY_COLORS[k] for k in priorities]}],
        }

    return {"type": "bar", "labels": [], "datasets": []}


# ---- alerts + weekly summary --------------------------------------------------
def alerts_for(user):
    tasks = visible_tasks(user)
    today = date.today()
    alerts = []

    overdue = tasks.filter(Task.status != "done", Task.due_date.isnot(None), Task.due_date < today).count()
    if overdue:
        alerts.append({"level": "danger", "icon": "bi-exclamation-octagon",
                        "message": f"{overdue} task{'s' if overdue != 1 else ''} overdue and needs attention."})

    due_soon = tasks.filter(
        Task.status != "done", Task.due_date.isnot(None),
        Task.due_date >= today, Task.due_date <= today + timedelta(days=3)
    ).count()
    if due_soon:
        alerts.append({"level": "warning", "icon": "bi-hourglass-split",
                        "message": f"{due_soon} task{'s' if due_soon != 1 else ''} due within 3 days."})

    if user.role in (ROLE_ADMIN, ROLE_MANAGER):
        projects = visible_projects(user).all()
        over_budget = [p for p in projects if p.is_over_budget]
        if over_budget:
            alerts.append({"level": "danger", "icon": "bi-cash-coin",
                            "message": f"{len(over_budget)} project{'s' if len(over_budget) != 1 else ''} over budget: "
                                       + ", ".join(p.name for p in over_budget[:3]) + "."})
        ending_soon = [p for p in projects if p.end_date and today <= p.end_date <= today + timedelta(days=7)
                       and p.status != "completed"]
        if ending_soon:
            alerts.append({"level": "warning", "icon": "bi-flag",
                            "message": f"{len(ending_soon)} project deadline(s) in the next 7 days."})

    return alerts


def notify(user_id, title, message, category="info", link=""):
    n = Notification(user_id=user_id, title=title, message=message, category=category, link=link)
    db.session.add(n)
    db.session.commit()
    return n


def update_task_status(task_id, new_status, user):
    """Update a task's status, but only if it is within `user`'s visible scope."""
    if new_status not in ("todo", "in_progress", "review", "done"):
        return None
    task = visible_tasks(user).filter(Task.id == task_id).first()
    if not task:
        return None
    task.status = new_status
    task.completed_at = utcnow() if new_status == "done" else None
    db.session.commit()

    if new_status == "done" and task.project and task.project.manager_id and task.project.manager_id != user.id:
        notify(task.project.manager_id, "Task completed",
               f'"{task.title}" was marked done by {user.full_name}.', "success", link="/manager/tasks")
    return task


def weekly_summary_for(user):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    tasks = visible_tasks(user)

    completed_this_week = tasks.filter(
        Task.status == "done", Task.completed_at.isnot(None), db.func.date(Task.completed_at) >= week_start
    ).count()
    new_tasks_this_week = tasks.filter(
        db.func.date(Task.created_at) >= week_start
    ).count()
    upcoming_deadlines = tasks.filter(
        Task.status != "done", Task.due_date.isnot(None),
        Task.due_date >= today, Task.due_date <= today + timedelta(days=7)
    ).count()

    summary = {
        "week_start": week_start,
        "completed_this_week": completed_this_week,
        "new_tasks_this_week": new_tasks_this_week,
        "upcoming_deadlines": upcoming_deadlines,
    }

    if user.role in (ROLE_ADMIN, ROLE_MANAGER):
        clients = visible_clients(user)
        summary["new_clients_this_week"] = clients.filter(
            db.func.date(Client.created_at) >= week_start
        ).count()

    return summary
