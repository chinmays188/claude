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
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from state import DB_PATH, ROOT

load_dotenv(ROOT / "config" / ".env", override=True)

MODEL = "claude-sonnet-5"
MASTER_RESUME_PATH = ROOT / "resume" / "master_resume.json"
OUTPUT_DIR = ROOT / "resume" / "tailored"

# The prompt asks the LLM to keep experience/passion-project bullets to
# roughly 110-120 chars so they render on one line, but that instruction is
# not reliably followed (observed a 226-char bullet left untouched in one
# run). BULLET_CHAR_LIMIT is enforced afterward in code — any bullet still
# over this is sent back for a targeted re-tighten rather than trusting the
# model to have complied the first time.
BULLET_CHAR_LIMIT = 130

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
You may NOT add a bullet that doesn't already exist in the master resume — "added" below refers
only to including an existing master-resume bullet that a prior tailoring pass might have cut,
never to fabricating new content.

In each bullet, wrap the 1-3 most impactful phrases in **double asterisks** for bold emphasis —
prioritize metrics/numbers (e.g. **₹88Cr**, **42%**) and skills relevant to the job description.
Do not bold entire bullets or more than ~30% of a bullet's text.

Keep every experience/passion-project bullet to roughly 110-120 characters (including any
**bold** markup) so it renders on a single line — tighten wording, drop redundant qualifiers,
but never cut a metric, number, or the core claim of the bullet. Career summary bullets are the
one exception and may run longer / wrap to two lines.

For every bullet in the master resume's career_summary, experience[].bullets, and
passion_projects, report in the diff what you did to it and why — whether you kept it verbatim,
reworded/tightened it, only reordered or bolded parts of it, or left it out entirely. Always
include a one-sentence reason tied to this specific job description.

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
  "passion_projects": [<selected/reordered passion_projects bullet texts with **bold** spans, keep all but reorder by relevance>],
  "diff": [
    {{"original_text": "<exact original bullet text from the master resume, WITHOUT any **bold** markup>",
      "new_text": "<the bullet text exactly as it appears in career_summary/experience/passion_projects above,
        WITH its **bold** markup intact if it has any — null only if this bullet was left out entirely>",
      "section": "career_summary|experience|passion_projects",
      "reason": "<one sentence tied to this job — why kept as-is / what changed and why / why left out>"}}
  ]
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


def tailor_resume(client, jd_text, master_resume, max_retries=2):
    """Includes the per-bullet diff in the same response as the tailored
    content, so the output is larger than a plain tailoring call. Thinking
    is explicitly disabled — with it on, claude-sonnet-5 was observed
    consuming the entire max_tokens budget on thinking and returning zero
    output tokens (stop_reason 'max_tokens', empty content) for this prompt.
    Retries once more on an empty/truncated response as a fallback."""
    prompt = TAILOR_PROMPT.format(jd_text=jd_text[:4000], resume_json=json.dumps(master_resume))
    last_error = None
    for attempt in range(max_retries + 1):
        response = client.messages.create(
            model=MODEL,
            max_tokens=12000,
            thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}],
        )
        text_block = next((b.text for b in response.content if hasattr(b, "text")), None)
        if text_block is None:
            last_error = "empty response (no text block)"
            continue
        try:
            return json.loads(strip_code_fence(text_block.strip()))
        except json.JSONDecodeError as e:
            last_error = f"unparseable response: {e}"
            continue
    raise RuntimeError(f"tailor_resume failed after {max_retries + 1} attempts: {last_error}")


_TIGHTEN_PROMPT = """Tighten this resume bullet to at most {limit} characters (including any
**bold** markup), while keeping every metric/number and the core claim intact. Do not invent
new facts. Return ONLY the tightened bullet text, nothing else — no quotes, no explanation.

Bullet: {bullet}
"""


def _tighten_bullet(client, bullet_text):
    prompt = _TIGHTEN_PROMPT.format(limit=BULLET_CHAR_LIMIT, bullet=bullet_text)
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": prompt}],
    )
    text_block = next((b.text for b in response.content if hasattr(b, "text")), None)
    if text_block is None:
        return bullet_text  # give up gracefully — an over-length bullet beats losing content
    return text_block.strip().strip('"')


def enforce_bullet_length(client, tailored, diff_entries):
    """Re-prompts Claude for a shorter version of any experience/passion-
    project bullet still over BULLET_CHAR_LIMIT after the main tailoring
    call — the prompt's length guidance alone isn't reliably followed.
    Career summary is exempt (it's allowed to wrap to two lines).

    Also updates the matching diff entry's new_text so the review email
    reflects the bullet that will actually render, not the pre-tighten
    draft the model originally proposed."""
    def tighten_and_sync(bullet_text):
        if len(bullet_text) <= BULLET_CHAR_LIMIT:
            return bullet_text
        tightened = _tighten_bullet(client, bullet_text)
        old_plain = markdown_bold_to_plain(bullet_text).strip()
        for entry in diff_entries:
            if entry.get("new_text") and markdown_bold_to_plain(entry["new_text"]).strip() == old_plain:
                entry["new_text"] = tightened
                entry["reason"] = entry.get("reason", "") + " (auto-tightened to fit one line)"
        return tightened

    for role in tailored.get("experience", []):
        role["bullets"] = [tighten_and_sync(b) for b in role["bullets"]]
    tailored["passion_projects"] = [
        tighten_and_sync(b) for b in tailored.get("passion_projects", [])
    ]
    return tailored


_HEADER_GRAY = HexColor("#808080")
_ROLE_ROW_GRAY = HexColor("#E8E8E8")

_STYLES = getSampleStyleSheet()
for _s in _STYLES.byName.values():
    _s.fontName = _BASE_FONT
_NAME_STYLE = ParagraphStyle(
    "NameStyle", parent=_STYLES["Title"], fontName=_BOLD_FONT, fontSize=17, leading=20,
    alignment=TA_CENTER, spaceAfter=2,
)
_LINK_COLOR = HexColor("#0000EE")
_HEADLINE_STYLE = ParagraphStyle(
    "HeadlineStyle", parent=_STYLES["Normal"], fontName=_BOLD_FONT, fontSize=10,
    alignment=TA_CENTER, spaceAfter=8, linkUnderline=True, textColor=HexColor("#000000"),
)
_CONTACT_STYLE = ParagraphStyle(
    "ContactStyle", parent=_STYLES["Normal"], fontSize=9.5, alignment=TA_CENTER, spaceAfter=4,
    linkUnderline=True,
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

_BOLD_MARKDOWN_RE = re.compile(r"\*\*(.+?)\*\*")

_MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def format_resume_date(value):
    """Master resume stores dates as 'YYYY-MM' or the literal 'present';
    the rendered PDF must show 'Month YYYY' / 'Present' to match
    master_resume.pdf's own formatting."""
    if not value or value.strip().lower() == "present":
        return "Present"
    m = re.match(r"^(\d{4})-(\d{2})$", value.strip())
    if not m:
        return value
    year, month = m.group(1), int(m.group(2))
    return f"{_MONTH_NAMES[month - 1]} {year}"


def markdown_bold_to_reportlab(text):
    """Convert **bold** spans from the tailoring prompt's output into
    reportlab's inline <b> tag, and escape any literal & so Paragraph's
    XML-like parser doesn't choke on ampersands in job/company text."""
    text = (text or "").replace("&", "&amp;")
    return _BOLD_MARKDOWN_RE.sub(r"<b>\1</b>", text)


def markdown_bold_to_plain(text):
    """Strip **bold** markup for plain-text contexts (the diff review
    email), where the XML-style <b> tag reportlab uses would just show up
    as literal text."""
    return _BOLD_MARKDOWN_RE.sub(r"\1", text or "")


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
        fontSize=body_size, leading=body_size * 1.3, leftIndent=6,
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


def _section_heading(text, section_style, content_width):
    table = Table([[Paragraph(text, section_style)]], colWidths=[content_width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _HEADER_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _role_header_row(role, role_title_style, role_date_style, col_widths):
    date_range = f"({format_resume_date(role['start_date'])} - {format_resume_date(role['end_date'])})"
    table = Table(
        [[
            Paragraph(markdown_bold_to_reportlab(f"{role['title']}, {role['company']}"), role_title_style),
            Paragraph(date_range, role_date_style),
        ]],
        colWidths=col_widths,
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _ROLE_ROW_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _build_story(master_resume, tailored, scale, spacer_scale, content_width):
    bullet_style, body_style, section_style, role_title_style, role_date_style = _build_styles(scale)
    contact = master_resume["contact"]
    role_col_widths = [content_width - 2 * inch, 2 * inch]

    def sp(base_pt):
        return Spacer(1, max(2, base_pt * spacer_scale))

    headline_parts = [master_resume["headline"]]
    if contact.get("portfolio_url"):
        headline_parts.append(f'<link href="{contact["portfolio_url"]}">Portfolio</link>')
    if contact.get("github_url"):
        headline_parts.append(f'<link href="{contact["github_url"]}">GitHub</link>')
    headline_line = " || ".join(headline_parts)

    footer_parts = [contact["email"]]
    if contact.get("linkedin_url"):
        footer_parts.append(f'<link href="{contact["linkedin_url"]}">Linked In</link>')
    footer_parts.append(f"Ph:{contact['phone']}")
    footer_parts.append(contact["location"])
    footer_line = " || ".join(footer_parts)

    story = [
        Paragraph(master_resume["name"], _NAME_STYLE),
        Paragraph(headline_line, _HEADLINE_STYLE),
        sp(4),
        _section_heading("Career Summary", section_style, content_width),
        sp(4),
        *[Paragraph(markdown_bold_to_reportlab(b), bullet_style) for b in tailored["career_summary"]],
        sp(8),
        _section_heading("Professional Experience", section_style, content_width),
    ]

    for role in tailored["experience"]:
        story.append(sp(6))
        story.append(_role_header_row(role, role_title_style, role_date_style, role_col_widths))
        story.append(sp(3))
        story.extend(Paragraph(markdown_bold_to_reportlab(b), bullet_style) for b in role["bullets"])

    story.append(sp(8))
    story.append(_section_heading("Education", section_style, content_width))
    story.append(sp(4))
    for edu in master_resume["education"]:
        story.append(Paragraph(
            f"{edu['degree']}, {edu['institution']} ({edu['years']}) — {edu['detail']}", body_style,
        ))

    story.append(sp(8))
    story.append(_section_heading("Skills", section_style, content_width))
    story.append(sp(4))
    skills = tailored["skills"]
    for label, key in (("Functional", "functional"), ("Interpersonal", "interpersonal"), ("Technical", "technical")):
        if skills.get(key):
            story.append(Paragraph(f"<b>{label}</b>: {', '.join(skills[key])}", body_style))

    if tailored.get("passion_projects"):
        story.append(sp(8))
        story.append(_section_heading("Passion Projects", section_style, content_width))
        story.append(sp(4))
        story.extend(Paragraph(markdown_bold_to_reportlab(b), bullet_style) for b in tailored["passion_projects"])

    story.append(sp(10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor("#999999")))
    story.append(sp(4))
    story.append(Paragraph(footer_line, _CONTACT_STYLE))
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

    # Side margins match master_resume.pdf's own layout (~0.17in each side,
    # measured from its text bounding boxes) rather than reportlab's wider
    # defaults, which left noticeably more whitespace than the master resume.
    side_margin = 0.17 * inch

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
                leftMargin=side_margin, rightMargin=side_margin,
            )
            content_width = letter[0] - 2 * side_margin
            story = _build_story(master_resume, content, scale, spacer_scale, content_width)
            doc.build(story)
            if doc.page <= 1:
                return
        content = _shrink_tailored_content(content)

    # Exhausted every shrink/trim step — leave the smallest-font, most-trimmed
    # render in place rather than raise; a slightly-over-budget PDF still
    # ships, and this should be rare given the trims above.


def _classify_diff_entry(entry):
    """Determine the real change type by comparing plain-text (markup
    stripped) original vs new — more reliable than trusting the LLM's own
    self-reported classification, which was observed calling bold-only or
    reorder-only changes "edited" even when the wording was identical."""
    new_text = entry.get("new_text")
    if new_text is None:
        return "removed"
    original_plain = entry["original_text"].strip()
    new_plain = markdown_bold_to_plain(new_text).strip()
    if original_plain == new_plain:
        return "reordered_or_emphasized"
    return "reworded"


def format_diff_summary(job, diff_entries):
    """Human-readable per-bullet diff for email review — grouped by change
    type so reworded/reordered/removed/kept are each easy to scan, with the
    reason always visible next to the bullet it applies to."""
    lines = [f"{job['title']} @ {job['company']}", f"  {job['job_url']}", ""]
    groups = {"reworded": [], "reordered_or_emphasized": [], "removed": []}
    for entry in diff_entries:
        groups[_classify_diff_entry(entry)].append(entry)

    if groups["reworded"]:
        lines.append("REWORDED:")
        for e in groups["reworded"]:
            lines.append(f"  Original: {e['original_text']}")
            lines.append(f"  Edited to: {markdown_bold_to_plain(e['new_text'])}")
            lines.append(f"  Reason: {e.get('reason', '')}")
            lines.append("")
        lines.append("")
    if groups["removed"]:
        lines.append("REMOVED:")
        for e in groups["removed"]:
            lines.append(f"  - {e['original_text']}")
            lines.append(f"    Reason: {e.get('reason', '')}")
        lines.append("")
    if groups["reordered_or_emphasized"]:
        lines.append("REORDERED / RE-EMPHASIZED (same wording, kept as-is otherwise):")
        for e in groups["reordered_or_emphasized"]:
            lines.append(f"  - {e['original_text']}")
            lines.append(f"    Reason: {e.get('reason', '')}")
        lines.append("")

    return "\n".join(lines)


def generate_diffs():
    """Phase 1: for every 'scored' job, call Claude to produce a tailored
    draft + per-bullet diff, but do NOT render a PDF yet. Moves the job to
    'tailor_pending_review' so a human can review the diff (emailed
    separately) before any PDF is built — approval happens via
    approve_and_render(), not automatically."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set — add it to config/.env")

    client = anthropic.Anthropic(api_key=api_key)
    master_resume = load_master_resume()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs WHERE status = 'scored'").fetchall()

    pending = []
    for row in rows:
        job = dict(row)
        tailored = tailor_resume(client, job["jd_text"] or "", master_resume)
        diff_entries = tailored.pop("diff", [])
        tailored = enforce_bullet_length(client, tailored, diff_entries)
        conn.execute(
            "UPDATE jobs SET status = 'tailor_pending_review', tailoring_diff = ? WHERE id = ?",
            (json.dumps({"tailored": tailored, "diff": diff_entries}), job["id"]),
        )
        conn.commit()
        pending.append((job, diff_entries))

    conn.close()
    return pending


def approve_and_render(job_id):
    """Phase 2: render the PDF for a single job whose diff has already been
    reviewed (status 'tailor_pending_review'), using the tailored content
    generated and stored during generate_diffs(). Moves the job to
    'tailored' so contacts/outreach/digest can proceed for it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM jobs WHERE id = ? AND status = 'tailor_pending_review'", (job_id,)
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Job {job_id} not found or not in 'tailor_pending_review' status")

    job = dict(row)
    stored = json.loads(job["tailoring_diff"])
    master_resume = load_master_resume()

    output_path = OUTPUT_DIR / f"{job['id']}_{job['company']}.pdf".replace("/", "_")
    render_pdf(master_resume, stored["tailored"], output_path)
    conn.execute("UPDATE jobs SET status = 'tailored' WHERE id = ?", (job["id"],))
    conn.commit()
    conn.close()
    return str(output_path)


def approve_and_render_all():
    conn = sqlite3.connect(DB_PATH)
    ids = [r[0] for r in conn.execute(
        "SELECT id FROM jobs WHERE status = 'tailor_pending_review'"
    ).fetchall()]
    conn.close()
    return [(job_id, approve_and_render(job_id)) for job_id in ids]


def run_tailoring():
    """Runs the diff-generation phase and emails the diffs for review.
    Does NOT render any PDFs — approval is a separate manual step via
    `python3 tailoring.py --approve <job_id>` or `--approve-all`."""
    pending = generate_diffs()
    if pending:
        send_diff_review_email(pending)
    return pending


def send_diff_review_email(pending):
    import smtplib
    from email.message import EmailMessage
    from state import load_config

    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    if not gmail_address or not gmail_app_password:
        print("  GMAIL not configured — diffs generated but review email not sent")
        return

    config = load_config()
    body = "\n---\n\n".join(format_diff_summary(job, diff) for job, diff in pending)
    body = (
        f"{len(pending)} resume(s) tailored and awaiting your review before PDFs are built.\n"
        f"Approve with: python3 tailoring.py --approve <job_id>  (or --approve-all)\n\n---\n\n"
    ) + body

    msg = EmailMessage()
    msg["Subject"] = f"[Resume Review] {len(pending)} tailored resume(s) awaiting approval"
    msg["From"] = gmail_address
    msg["To"] = config["digest_email_to"]
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(msg)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--approve", metavar="JOB_ID", default=None,
                         help="Approve and render one job's PDF by job_id")
    parser.add_argument("--approve-all", action="store_true",
                         help="Approve and render all jobs currently pending review")
    args = parser.parse_args()

    if args.approve_all:
        results = approve_and_render_all()
        print(f"Approved and rendered {len(results)} resumes.")
    elif args.approve:
        path = approve_and_render(args.approve)
        print(f"Approved and rendered: {path}")
    else:
        pending = run_tailoring()
        print(f"Generated {len(pending)} diff(s) for review — check your email, then approve with --approve <job_id> or --approve-all.")
