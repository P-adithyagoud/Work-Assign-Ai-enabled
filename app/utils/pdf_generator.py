from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_pdf_report(project, deterministic, ai_plan):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AI Project Assignment Report", styles["Title"]))
    story.append(Paragraph(project.get("project_name", "Untitled Project"), styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    selected = deterministic.get("selected_team", [])
    table_data = [["Name", "Role", "Score", "Skills", "Role", "Perf", "Exp", "Avail"]]
    for member in selected:
        table_data.append(
            [
                member["name"],
                member["assigned_role"],
                member["final_score"],
                member["skills_match"],
                member["role_match"],
                member["performance_score"],
                member["experience_score"],
                member["availability_score"],
            ]
        )

    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)

    add_section(story, styles, "Technology Stack", ai_plan.get("technology_stack", []))
    add_section(story, styles, "Risks", [f"{item.get('risk')}: {item.get('mitigation')}" for item in ai_plan.get("risks", [])])
    add_section(story, styles, "Recommendations", ai_plan.get("final_recommendations", []))

    doc.build(story)
    buffer.seek(0)
    return buffer


def add_section(story, styles, title, items):
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(title, styles["Heading2"]))
    if not items:
        story.append(Paragraph("No items available.", styles["BodyText"]))
    for item in items:
        story.append(Paragraph(f"- {item}", styles["BodyText"]))

