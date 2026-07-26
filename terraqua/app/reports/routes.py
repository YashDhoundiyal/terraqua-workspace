import csv
import io
from app.utils import utcnow

from flask import Blueprint, Response, send_file
from flask_login import login_required, current_user

from app.decorators import role_required
from app.models import ROLE_ADMIN, ROLE_MANAGER
from app.queries import visible_tasks, visible_projects, visible_clients, weekly_summary_for, kpis_for

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _csv_response(filename, header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/tasks.csv")
@login_required
def export_tasks_csv():
    tasks = visible_tasks(current_user).all()
    rows = [
        [t.id, t.title, t.project.name if t.project else "",
         (t.assignee.full_name if t.assignee else ""), t.status, t.priority,
         t.due_date.isoformat() if t.due_date else "", "Yes" if t.is_overdue else "No"]
        for t in tasks
    ]
    return _csv_response(
        "tasks_export.csv",
        ["ID", "Title", "Project", "Assigned To", "Status", "Priority", "Due Date", "Overdue"],
        rows,
    )


@reports_bp.route("/export/projects.csv")
@login_required
def export_projects_csv():
    projects = visible_projects(current_user).all()
    rows = [
        [p.id, p.name, p.status, p.priority, p.manager.full_name if p.manager else "",
         p.start_date.isoformat() if p.start_date else "", p.end_date.isoformat() if p.end_date else "",
         p.progress, p.budget, p.spent]
        for p in projects
    ]
    return _csv_response(
        "projects_export.csv",
        ["ID", "Name", "Status", "Priority", "Manager", "Start Date", "End Date", "Progress %", "Budget", "Spent"],
        rows,
    )


@reports_bp.route("/export/clients.csv")
@login_required
@role_required(ROLE_ADMIN, ROLE_MANAGER)
def export_clients_csv():
    clients = visible_clients(current_user).all()
    rows = [
        [c.id, c.name, c.company, c.email, c.phone, c.status, c.deal_value,
         c.owner.full_name if c.owner else "", c.last_contact.isoformat() if c.last_contact else ""]
        for c in clients
    ]
    return _csv_response(
        "clients_export.csv",
        ["ID", "Name", "Company", "Email", "Phone", "Status", "Deal Value", "Owner", "Last Contact"],
        rows,
    )


@reports_bp.route("/export/weekly-summary.pdf")
@login_required
def export_weekly_summary_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    summary = weekly_summary_for(current_user)
    kpis = kpis_for(current_user)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TQTitle", parent=styles["Title"], textColor=colors.HexColor("#0B2E36"))
    heading_style = ParagraphStyle("TQHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0E7C86"))

    elements = [
        Paragraph("TerrAqua Workspace &mdash; Weekly Summary", title_style),
        Paragraph(
            f"Generated for {current_user.full_name} ({current_user.role.title()}) "
            f"on {utcnow().strftime('%B %d, %Y')}",
            styles["Normal"],
        ),
        Spacer(1, 16),
        Paragraph("Key Performance Indicators", heading_style),
        Spacer(1, 6),
    ]

    def table_style(header_color):
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DEE0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3EE")]),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])

    kpi_rows = [["Metric", "Value"]] + [[k["label"], str(k["value"])] for k in kpis]
    kpi_table = Table(kpi_rows, colWidths=[3.2 * inch, 2.2 * inch])
    kpi_table.setStyle(table_style("#0B2E36"))
    elements += [kpi_table, Spacer(1, 20), Paragraph("This Week", heading_style), Spacer(1, 6)]

    week_rows = [
        ["Tasks completed this week", summary["completed_this_week"]],
        ["New tasks created this week", summary["new_tasks_this_week"]],
        ["Upcoming deadlines (7 days)", summary["upcoming_deadlines"]],
    ]
    if "new_clients_this_week" in summary:
        week_rows.append(["New CRM leads this week", summary["new_clients_this_week"]])

    week_table = Table([["Metric", "Value"]] + [[r[0], str(r[1])] for r in week_rows],
                        colWidths=[3.2 * inch, 2.2 * inch])
    week_table.setStyle(table_style("#C1652F"))
    elements.append(week_table)

    doc.build(elements)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name="terraqua_weekly_summary.pdf")
