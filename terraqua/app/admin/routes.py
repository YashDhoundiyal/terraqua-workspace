from app.utils import utcnow

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Project, Task, Client, ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE
from app.queries import (
    kpis_for, alerts_for, weekly_summary_for, visible_projects, visible_tasks,
    visible_clients, team_members, update_task_status, notify,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def restrict_to_admin():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role != ROLE_ADMIN:
        abort(403)


@admin_bp.route("/dashboard")
def dashboard():
    recent_tasks = visible_tasks(current_user).order_by(Task.created_at.desc()).limit(6).all()
    recent_projects = visible_projects(current_user).order_by(Project.created_at.desc()).limit(5).all()
    return render_template(
        "admin/dashboard.html",
        kpis=kpis_for(current_user),
        alerts=alerts_for(current_user),
        summary=weekly_summary_for(current_user),
        recent_tasks=recent_tasks,
        recent_projects=recent_projects,
    )


@admin_bp.route("/projects", methods=["GET", "POST"])
def projects():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Project name is required.", "danger")
            return redirect(url_for("admin.projects"))
        p = Project(
            name=name,
            description=request.form.get("description", "").strip(),
            status=request.form.get("status", "planning"),
            priority=request.form.get("priority", "medium"),
            budget=float(request.form.get("budget") or 0),
            manager_id=request.form.get("manager_id") or None,
            start_date=utcnow().date(),
        )
        db.session.add(p)
        db.session.commit()
        if p.manager_id:
            notify(p.manager_id, "New project assigned", f'You were assigned as manager for "{p.name}".', "info")
        flash(f'Project "{p.name}" created.', "success")
        return redirect(url_for("admin.projects"))

    q = Project.query
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    if status:
        q = q.filter(Project.status == status)
    if search:
        q = q.filter(Project.name.ilike(f"%{search}%"))
    projects_list = q.order_by(Project.created_at.desc()).all()
    managers = User.query.filter_by(role=ROLE_MANAGER).order_by(User.full_name).all()
    return render_template("admin/projects.html", projects=projects_list, managers=managers,
                            status=status, search=search)


@admin_bp.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(username=username).first():
            flash("That username is already taken.", "danger")
            return redirect(url_for("admin.users"))
        u = User(
            username=username,
            email=email,
            full_name=request.form.get("full_name", "").strip(),
            role=request.form.get("role", ROLE_EMPLOYEE),
            department=request.form.get("department", "General"),
        )
        u.set_password(request.form.get("password") or "changeme123")
        db.session.add(u)
        db.session.commit()
        flash(f'User "{u.full_name}" created.', "success")
        return redirect(url_for("admin.users"))

    users_list = User.query.order_by(User.role, User.full_name).all()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
def toggle_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("You can't deactivate your own account.", "warning")
    else:
        user.is_active_user = not user.is_active_user
        db.session.commit()
        flash(f'{user.full_name} is now {"active" if user.is_active_user else "inactive"}.', "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/crm", methods=["GET", "POST"])
def crm():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Client name is required.", "danger")
            return redirect(url_for("admin.crm"))
        c = Client(
            name=name,
            company=request.form.get("company", "").strip(),
            email=request.form.get("email", "").strip(),
            phone=request.form.get("phone", "").strip(),
            status=request.form.get("status", "lead"),
            deal_value=float(request.form.get("deal_value") or 0),
            assigned_to=request.form.get("assigned_to") or None,
        )
        db.session.add(c)
        db.session.commit()
        if c.assigned_to:
            notify(c.assigned_to, "New CRM lead assigned", f'"{c.name}" ({c.company}) was assigned to you.', "info")
        flash(f'Client "{c.name}" added.', "success")
        return redirect(url_for("admin.crm"))

    q = Client.query
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    if status:
        q = q.filter(Client.status == status)
    if search:
        q = q.filter(Client.name.ilike(f"%{search}%"))
    clients_list = q.order_by(Client.created_at.desc()).all()
    owners = User.query.filter(User.role.in_([ROLE_ADMIN, ROLE_MANAGER])).order_by(User.full_name).all()
    return render_template("admin/crm.html", clients=clients_list, owners=owners, status=status, search=search)


@admin_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def task_status(task_id):
    new_status = request.form.get("status")
    task = update_task_status(task_id, new_status, current_user)
    if not task:
        flash("Could not update that task.", "danger")
    else:
        flash(f'"{task.title}" marked as {new_status.replace("_", " ")}.', "success")
    return redirect(request.referrer or url_for("admin.dashboard"))
