import json
import os
import re
import sqlite3
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle, HRFlowable,
)

from state import DB_PATH, ROOT

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"
MASTER_RESUME_PATH = ROOT / "resume" / "master_resume.json"
OUTPUT_DIR = ROOT / "resume" / "tailored"

# Base14 fonts (Helvetica) lack ₹ and other non-Latin-1 glyphs the resume
# content may use. macOS's system Helvetica.ttc covers ₹ (Arial Unicode.ttf,
# despite the name, predates the 2010 ₹ Unicode addition and does not).
# Registering regular and bold as separate faces (subfontIndex 0/1 in the
# .ttc) plus registerFontFamily is required for Paragraph's <b> tag to
# actually switch faces — registering one face under both names silently
# renders "bold" as unstyled regular text.
# Falls back to Base14 Helvetica elsewhere — missing glyphs render as a
# fallback box there, not a crash.
_UNICODE_FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"
if Path(_UNICODE_FONT_PATH).exists():
    pdfmetrics.registerFont(TTFont("ResumeFont", _UNICODE_FONT_PATH, subfontIndex=0))
    pdfmetrics.registerFont(TTFont("ResumeFont-Bold", _UNICODE_FONT_PATH, subfontIndex=1))
    pdfmetrics.registerFontFamily(
        "ResumeFont", normal="ResumeFont", bold="ResumeFont-Bold",
        italic="ResumeFont", boldItalic="ResumeFont-Bold",
    )
    _BASE_FONT, _BOLD_FONT = "ResumeFont", "ResumeFont-Bold"
else:
    _BASE_FONT, _BOLD_FONT = "Helvetica", "Helvetica-Bold"

TAILOR_PROMPT = """You are tailoring a resume to a job description. You may REORDER bullets,
select which optional bullets to include, and adjust emphasis/wording for keyword alignment.
You must NEVER invent new facts, metrics, or experience not present in the source bullets.

In each bullet, wrap the 1-3 most impactful phrases in **double asterisks** for bold emphasis —
prioritize metrics/numbers (e.g. **₹88Cr**, **42%**) and skills relevant to the job description.
Do not bold entire bullets or more than ~30% of a bullet's text.

Job description:
{jd_text}

Master resume (JSON, bullets tagged by skill/domain/impact_area):
{resume_json}

Return ONLY a JSON object with this shape:
{{
  "career_summary": [<selected/reordered summary bullet texts with **bold** spans, max 3>],
  "experience": [
    {{"company": "...", "title": "...", "start_date": "...", "end_date": "...",
      "bullets": [<selected/reordered bullet texts with **bold** spans, keep all bullets but reorder by relevance>]}}
  ],
  "skills": {{
    "functional": [<most relevant skills from master resume's skills.functional, ordered by relevance, keep all that are relevant>],
    "interpersonal": [<most relevant skills from master resume's skills.interpersonal>],
    "technical": [<most relevant skills from master resume's skills.technical>]
  }},
  "passion_projects": [<selected/reordered passion_projects bullet texts with **bold** spans, keep all but reorder by relevance>]
}}
"""


def load_master_resume():
    with open(MASTER_RESUME_PATH) as f:
        return json.load(f)


def strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def tailor_resume(client, jd_text, master_resume):
    prompt = TAILOR_PROMPT.format(jd_text=jd_text[:4000], resume_json=json.dumps(master_resume))
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = next(b.text for b in response.content if hasattr(b, "text")).strip()
    return json.loads(strip_code_fence(text))


_HEADER_GRAY = HexColor("#808080")
_ROLE_ROW_GRAY = HexColor("#E8E8E8")

_STYLES = getSampleStyleSheet()
for _s in _STYLES.byName.values():
    _s.fontName = _BASE_FONT
_NAME_STYLE = ParagraphStyle(
    "NameStyle", parent=_STYLES["Title"], fontName=_BOLD_FONT, fontSize=17, leading=20,
    alignment=TA_CENTER, spaceAfter=2,
)
_HEADLINE_STYLE = ParagraphStyle(
    "HeadlineStyle", parent=_STYLES["Normal"], fontName=_BOLD_FONT, fontSize=10,
    alignment=TA_CENTER, spaceAfter=8,
)
_CONTACT_STYLE = ParagraphStyle(
    "ContactStyle", parent=_STYLES["Normal"], fontSize=9.5, alignment=TA_CENTER, spaceAfter=4,
)
_SECTION_HEADING_STYLE = ParagraphStyle(
    "SectionHeading", parent=_STYLES["Normal"], fontName=_BOLD_FONT, fontSize=11.5,
    textColor=white, leftIndent=4,
)
_ROLE_TITLE_STYLE = ParagraphStyle(
    "RoleTitleStyle", parent=_STYLES["Normal"], fontName=_BOLD_FONT, fontSize=10.5,
)
_ROLE_DATE_STYLE = ParagraphStyle(
    "RoleDateStyle", parent=_STYLES["Normal"], fontName=_BOLD_FONT, fontSize=10.5, alignment=2,  # right
)
_BODY_STYLE = ParagraphStyle("BodyStyle", parent=_STYLES["Normal"], fontSize=10, leading=13)
_BULLET_STYLE = ParagraphStyle("BulletStyle", parent=_BODY_STYLE, leftIndent=12)

_BOLD_MARKDOWN_RE = re.compile(r"\*\*(.+?)\*\*")


def markdown_bold_to_reportlab(text):
    """Convert **bold** spans from the tailoring prompt's output into
    reportlab's inline <b> tag, and escape any literal & so Paragraph's
    XML-like parser doesn't choke on ampersands in job/company text."""
    text = (text or "").replace("&", "&amp;")
    return _BOLD_MARKDOWN_RE.sub(r"<b>\1</b>", text)


def section_heading(text):
    """Full-width gray band behind bold white section-header text, matching
    the master resume's shaded section dividers."""
    table = Table(
        [[Paragraph(text, _SECTION_HEADING_STYLE)]],
        colWidths=[7 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _HEADER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def role_header_row(role):
    """Title/company left, date range right, on one shaded row — matches the
    master resume's role-header bands."""
    table = Table(
        [[
            Paragraph(markdown_bold_to_reportlab(f"{role['title']}, {role['company']}"), _ROLE_TITLE_STYLE),
            Paragraph(f"({role['start_date']} - {role['end_date']})", _ROLE_DATE_STYLE),
        ]],
        colWidths=[5 * inch, 2 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _ROLE_ROW_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _build_styles(scale):
    """Font/leading/spacing styles at a given shrink scale (1.0 = defaults).
    Used to re-render smaller when the first pass overflows one page."""
    body_size = 10 * scale
    bullet_style = ParagraphStyle(
        "BulletStyle", parent=_STYLES["Normal"], fontName=_BASE_FONT,
        fontSize=body_size, leading=body_size * 1.3, leftIndent=12,
    )
    body_style = ParagraphStyle(
        "BodyStyle2", parent=_STYLES["Normal"], fontName=_BASE_FONT,
        fontSize=body_size, leading=body_size * 1.3,
    )
    section_style = ParagraphStyle(
        "SectionHeading2", parent=_SECTION_HEADING_STYLE, fontSize=11.5 * scale,
    )
    role_title_style = ParagraphStyle("RoleTitleStyle2", parent=_ROLE_TITLE_STYLE, fontSize=10.5 * scale)
    role_date_style = ParagraphStyle("RoleDateStyle2", parent=_ROLE_DATE_STYLE, fontSize=10.5 * scale)
    return bullet_style, body_style, section_style, role_title_style, role_date_style


def _section_heading(text, section_style):
    table = Table([[Paragraph(text, section_style)]], colWidths=[7 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _HEADER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _role_header_row(role, role_title_style, role_date_style):
    table = Table(
        [[
            Paragraph(markdown_bold_to_reportlab(f"{role['title']}, {role['company']}"), role_title_style),
            Paragraph(f"({role['start_date']} - {role['end_date']})", role_date_style),
        ]],
        colWidths=[5 * inch, 2 * inch],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _ROLE_ROW_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _build_story(master_resume, tailored, scale, spacer_scale):
    bullet_style, body_style, section_style, role_title_style, role_date_style = _build_styles(scale)
    contact = master_resume["contact"]

    def sp(base_pt):
        return Spacer(1, max(2, base_pt * spacer_scale))

    story = [
        Paragraph(master_resume["name"], _NAME_STYLE),
        Paragraph(master_resume["headline"], _HEADLINE_STYLE),
        Paragraph(f"{contact['email']} | {contact['phone']} | {contact['location']}", _CONTACT_STYLE),
        sp(4),
        _section_heading("Career Summary", section_style),
        sp(4),
        ListFlowable(
            [ListItem(Paragraph(markdown_bold_to_reportlab(b), bullet_style))
             for b in tailored["career_summary"]],
            bulletType="bullet",
        ),
        sp(8),
        _section_heading("Professional Experience", section_style),
    ]

    for role in tailored["experience"]:
        story.append(sp(6))
        story.append(_role_header_row(role, role_title_style, role_date_style))
        story.append(sp(3))
        story.append(ListFlowable(
            [ListItem(Paragraph(markdown_bold_to_reportlab(b), bullet_style)) for b in role["bullets"]],
            bulletType="bullet",
        ))

    story.append(sp(8))
    story.append(_section_heading("Education", section_style))
    story.append(sp(4))
    for edu in master_resume["education"]:
        story.append(Paragraph(
            f"{edu['degree']}, {edu['institution']} ({edu['years']}) — {edu['detail']}", body_style,
        ))

    story.append(sp(8))
    story.append(_section_heading("Skills", section_style))
    story.append(sp(4))
    skills = tailored["skills"]
    for label, key in (("Functional", "functional"), ("Interpersonal", "interpersonal"), ("Technical", "technical")):
        if skills.get(key):
            story.append(Paragraph(f"<b>{label}</b>: {', '.join(skills[key])}", body_style))

    if tailored.get("passion_projects"):
        story.append(sp(8))
        story.append(_section_heading("Passion Projects", section_style))
        story.append(sp(4))
        story.append(ListFlowable(
            [ListItem(Paragraph(markdown_bold_to_reportlab(b), bullet_style))
             for b in tailored["passion_projects"]],
            bulletType="bullet",
        ))

    story.append(sp(10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#999999")))
    story.append(sp(4))
    story.append(Paragraph(
        f"{contact['email']} | Ph:{contact['phone']} | {contact['location']}", _CONTACT_STYLE,
    ))
    return story


def _shrink_tailored_content(tailored):
    """Drop the lowest-priority content when even the smallest font/margin
    pass still overflows one page: career_summary down to 2 bullets, then
    drop passion_projects entirely (both are the most dispensable sections —
    experience bullets and skills are the substance a recruiter needs)."""
    shrunk = json.loads(json.dumps(tailored))  # deep copy
    if len(shrunk.get("career_summary", [])) > 2:
        shrunk["career_summary"] = shrunk["career_summary"][:2]
    elif shrunk.get("passion_projects"):
        shrunk["passion_projects"] = []
    return shrunk


def render_pdf(master_resume, tailored, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Progressively shrink font/spacing, then trim content, until the resume
    # fits strictly on one page — the candidate's master resume is a one-pager
    # and every tailored version must match that constraint.
    attempts = [
        (1.0, 1.0, 0.5 * inch, 0.5 * inch),
        (0.93, 0.85, 0.4 * inch, 0.4 * inch),
        (0.87, 0.7, 0.35 * inch, 0.35 * inch),
    ]
    content = tailored
    for content_pass in range(3):  # original content, then up to 2 content-trim passes
        for scale, spacer_scale, top_margin, bottom_margin in attempts:
            doc = SimpleDocTemplate(
                str(output_path), pagesize=letter,
                topMargin=top_margin, bottomMargin=bottom_margin,
                leftMargin=0.75 * inch, rightMargin=0.75 * inch,
            )
            story = _build_story(master_resume, content, scale, spacer_scale)
            doc.build(story)
            if doc.page <= 1:
                return
        content = _shrink_tailored_content(content)

    # Exhausted every shrink/trim step — leave the smallest-font, most-trimmed
    # render in place rather than raise; a slightly-over-budget PDF still
    # ships, and this should be rare given the trims above.


def run_tailoring():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to config/.env")

    client = anthropic.Anthropic(api_key=api_key)
    master_resume = load_master_resume()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs WHERE status = 'scored'").fetchall()

    tailored_jobs = []
    for row in rows:
        job = dict(row)
        tailored = tailor_resume(client, job["jd_text"] or "", master_resume)
        output_path = OUTPUT_DIR / f"{job['id']}_{job['company']}.pdf".replace("/", "_")
        render_pdf(master_resume, tailored, output_path)
        conn.execute("UPDATE jobs SET status = 'tailored' WHERE id = ?", (job["id"],))
        conn.commit()
        tailored_jobs.append((job["id"], str(output_path)))

    conn.close()
    return tailored_jobs


if __name__ == "__main__":
    results = run_tailoring()
    print(f"Tailored {len(results)} resumes.")
