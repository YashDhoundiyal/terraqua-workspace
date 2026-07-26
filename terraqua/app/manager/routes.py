from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from app.extensions import db
from app.models import User, Project, Task, Client, ROLE_MANAGER, ROLE_EMPLOYEE
from app.queries import (
    kpis_for, alerts_for, weekly_summary_for, visible_projects, visible_tasks,
    visible_clients, team_members, update_task_status, notify,
)

manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


@manager_bp.before_request
def restrict_to_manager():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role != ROLE_MANAGER:
        abort(403)


def _own_project_or_404(project_id):
    project = Project.query.filter_by(id=project_id, manager_id=current_user.id).first()
    if not project:
        abort(404)
    return project


@manager_bp.route("/dashboard")
def dashboard():
    recent_tasks = visible_tasks(current_user).order_by(Task.created_at.desc()).limit(6).all()
    return render_template(
        "manager/dashboard.html",
        kpis=kpis_for(current_user),
        alerts=alerts_for(current_user),
        summary=weekly_summary_for(current_user),
        recent_tasks=recent_tasks,
        projects=visible_projects(current_user).order_by(Project.created_at.desc()).all(),
    )


@manager_bp.route("/projects/<int:project_id>/update", methods=["POST"])
def update_project(project_id):
    project = _own_project_or_404(project_id)
    project.status = request.form.get("status", project.status)
    try:
        project.progress = max(0, min(100, int(request.form.get("progress", project.progress))))
    except ValueError:
        pass
    db.session.commit()
    flash(f'"{project.name}" updated.', "success")
    return redirect(url_for("manager.dashboard"))


@manager_bp.route("/tasks", methods=["GET", "POST"])
def tasks():
    my_projects = visible_projects(current_user).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        project_id = request.form.get("project_id")
        if not title or not project_id:
            flash("Title and project are required.", "danger")
            return redirect(url_for("manager.tasks"))
        # ensure the chosen project actually belongs to this manager
        if not any(str(p.id) == project_id for p in my_projects):
            abort(403)
        t = Task(
            title=title,
            description=request.form.get("description", "").strip(),
            project_id=project_id,
            assigned_to=request.form.get("assigned_to") or None,
            priority=request.form.get("priority", "medium"),
            due_date=request.form.get("due_date") or None,
        )
        db.session.add(t)
        db.session.commit()
        if t.assigned_to:
            notify(t.assigned_to, "New task assigned", f'"{t.title}" was assigned to you.', "info", link="/employee/tasks")
        flash(f'Task "{t.title}" created.', "success")
        return redirect(url_for("manager.tasks"))

    q = visible_tasks(current_user)
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    if status:
        q = q.filter(Task.status == status)
    if search:
        q = q.filter(Task.title.ilike(f"%{search}%"))
    tasks_list = q.order_by(Task.due_date.is_(None), Task.due_date.asc()).all()
    return render_template(
        "manager/tasks.html", tasks=tasks_list, projects=my_projects,
        members=team_members(current_user), status=status, search=search,
    )


@manager_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def task_status(task_id):
    new_status = request.form.get("status")
    task = update_task_status(task_id, new_status, current_user)
    if not task:
        flash("Could not update that task.", "danger")
    else:
        flash(f'"{task.title}" marked as {new_status.replace("_", " ")}.', "success")
    return redirect(request.referrer or url_for("manager.dashboard"))


@manager_bp.route("/crm", methods=["GET", "POST"])
def crm():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Client name is required.", "danger")
            return redirect(url_for("manager.crm"))
        c = Client(
            name=name,
            company=request.form.get("company", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            status=request.form.get("status", "lead"),
            deal_value=float(request.form.get("deal_value") or 0),
            assigned_to=current_user.id,
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Client "{c.name}" added to your pipeline.', "success")
        return redirect(url_for("manager.crm"))

    q = visible_clients(current_user)
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    if status:
        q = q.filter(Client.status == status)
    if search:
        q = q.filter(Client.name.ilike(f"%{search}%"))
    clients_list = q.order_by(Client.created_at.desc()).all()
    return render_template("manager/crm.html", clients=clients_list, status=status, search=search)
