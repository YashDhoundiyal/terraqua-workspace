from datetime import date

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils import utcnow

from app.extensions import db

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_EMPLOYEE, index=True)
    department = db.Column(db.String(80), default="General")
    avatar_color = db.Column(db.String(20), default="#0E7C86")
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    managed_projects = db.relationship(
        "Project", backref="manager", foreign_keys="Project.manager_id"
    )
    tasks = db.relationship(
        "Task", backref="assignee", foreign_keys="Task.assigned_to",
        cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", backref="user", foreign_keys="Notification.user_id",
        order_by="Notification.created_at.desc()", cascade="all, delete-orphan"
    )
    clients = db.relationship(
        "Client", backref="owner", foreign_keys="Client.assigned_to"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def initials(self):
        parts = [p for p in self.full_name.split() if p]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][0].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="planning", index=True)  # planning, active, on_hold, completed
    priority = db.Column(db.String(10), default="medium")  # low, medium, high
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float, default=0)
    spent = db.Column(db.Float, default=0)
    progress = db.Column(db.Integer, default=0)  # 0-100
    manager_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow)

    tasks = db.relationship("Task", backref="project", cascade="all, delete-orphan")
    documents = db.relationship("Document", backref="project", cascade="all, delete-orphan")
    events = db.relationship("CalendarEvent", backref="project", cascade="all, delete-orphan")

    @property
    def is_over_budget(self):
        return self.spent > self.budget > 0

    @property
    def task_count(self):
        return len(self.tasks)

    @property
    def done_task_count(self):
        return len([t for t in self.tasks if t.status == "done"])


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(20), default="todo", index=True)  # todo, in_progress, review, done
    priority = db.Column(db.String(10), default="medium")  # low, medium, high
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime)

    @property
    def is_overdue(self):
        return self.status != "done" and self.due_date is not None and self.due_date < date.today()

    def __repr__(self):
        return f"<Task {self.title}>"


class Client(db.Model):
    """CRM record."""
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(150), default="")
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(30), default="")
    status = db.Column(db.String(20), default="lead", index=True)  # lead, qualified, active, inactive
    deal_value = db.Column(db.Float, default=0)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=utcnow)
    last_contact = db.Column(db.Date)


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default="general")
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    size_kb = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=utcnow)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(300), default="")
    category = db.Column(db.String(20), default="info")  # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False, index=True)
    link = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=utcnow)


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime)
    all_day = db.Column(db.Boolean, default=True)
    event_type = db.Column(db.String(20), default="deadline")  # deadline, meeting, reminder
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
