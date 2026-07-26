from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Notification
from app.queries import (
    chart_payload, kpis_for, weekly_summary_for,
    visible_tasks, visible_projects, visible_calendar_events,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

EVENT_COLORS = {
    "deadline": "#D14343", "meeting": "#3B82A6", "reminder": "#D9A441",
    "task_due": "#0E7C86", "project_deadline": "#C1652F",
}


@api_bp.route("/kpis")
@login_required
def kpis():
    return jsonify(kpis_for(current_user))


@api_bp.route("/charts/<kind>")
@login_required
def charts(kind):
    return jsonify(chart_payload(kind, current_user))


@api_bp.route("/weekly-summary")
@login_required
def weekly_summary():
    data = dict(weekly_summary_for(current_user))
    data["week_start"] = data["week_start"].isoformat()
    return jsonify(data)


@api_bp.route("/calendar-events")
@login_required
def calendar_events():
    events = []

    for e in visible_calendar_events(current_user).all():
        events.append({
            "id": f"evt-{e.id}",
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat() if e.end else None,
            "allDay": e.all_day,
            "color": EVENT_COLORS.get(e.event_type, "#0E7C86"),
            "extendedProps": {"type": e.event_type, "description": e.description or ""},
        })

    for t in visible_tasks(current_user).all():
        if t.due_date and t.status != "done":
            events.append({
                "id": f"task-{t.id}",
                "title": f"Due: {t.title}",
                "start": t.due_date.isoformat(),
                "allDay": True,
                "color": EVENT_COLORS["task_due"],
                "extendedProps": {"type": "task_due", "description": t.description or ""},
            })

    for p in visible_projects(current_user).all():
        if p.end_date and p.status != "completed":
            events.append({
                "id": f"proj-{p.id}",
                "title": f"Deadline: {p.name}",
                "start": p.end_date.isoformat(),
                "allDay": True,
                "color": EVENT_COLORS["project_deadline"],
                "extendedProps": {"type": "project_deadline", "description": p.description or ""},
            })

    return jsonify(events)


@api_bp.route("/notifications")
@login_required
def notifications():
    items = (Notification.query.filter_by(user_id=current_user.id)
             .order_by(Notification.created_at.desc()).limit(25).all())
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({
        "unread_count": unread,
        "items": [
            {
                "id": n.id, "title": n.title, "message": n.message, "category": n.category,
                "is_read": n.is_read, "link": n.link or "", "created_at": n.created_at.isoformat(),
            }
            for n in items
        ],
    })


@api_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id):
    n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
    if n:
        n.is_read = True
        db.session.commit()
    return jsonify({"ok": bool(n)})


@api_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify({"ok": True})
