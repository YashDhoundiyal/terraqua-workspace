from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user

from app.models import Task, ROLE_EMPLOYEE
from app.queries import kpis_for, alerts_for, weekly_summary_for, visible_tasks, visible_projects, update_task_status

employee_bp = Blueprint("employee", __name__, url_prefix="/employee")


@employee_bp.before_request
def restrict_to_employee():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if current_user.role != ROLE_EMPLOYEE:
        abort(403)


@employee_bp.route("/dashboard")
def dashboard():
    recent_tasks = visible_tasks(current_user).order_by(Task.due_date.is_(None), Task.due_date.asc()).limit(6).all()
    return render_template(
        "employee/dashboard.html",
        kpis=kpis_for(current_user),
        alerts=alerts_for(current_user),
        summary=weekly_summary_for(current_user),
        recent_tasks=recent_tasks,
        projects=visible_projects(current_user).all(),
    )


@employee_bp.route("/tasks")
def tasks():
    q = visible_tasks(current_user)
    status = request.args.get("status", "")
    search = request.args.get("q", "")
    if status:
        q = q.filter(Task.status == status)
    if search:
        q = q.filter(Task.title.ilike(f"%{search}%"))
    tasks_list = q.order_by(Task.due_date.is_(None), Task.due_date.asc()).all()
    return render_template("employee/tasks.html", tasks=tasks_list, status=status, search=search)


@employee_bp.route("/tasks/<int:task_id>/status", methods=["POST"])
def task_status(task_id):
    new_status = request.form.get("status")
    task = update_task_status(task_id, new_status, current_user)
    if not task:
        flash("Could not update that task.", "danger")
    else:
        flash(f'"{task.title}" marked as {new_status.replace("_", " ")}.', "success")
    return redirect(request.referrer or url_for("employee.dashboard"))
