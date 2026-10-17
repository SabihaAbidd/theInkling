"""Render a saved newspaper edition as a downloadable, linked PDF."""

from __future__ import annotations

from html import escape
from io import BytesIO
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

INK = colors.HexColor("#252a26")
SPINE = colors.HexColor("#203b34")
ACCENT = colors.HexColor("#d26747")
MUTED = colors.HexColor("#747a73")
RULE = colors.HexColor("#c9cec6")
LINK = colors.HexColor("#245c9b")


def render_edition_pdf(
    *,
    title: str,
    edition_date: str,
    editorial: str,
    articles: list[dict],
) -> bytes:
    """Return a complete PDF of an edition snapshot, including source links."""

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.92 * inch,
        bottomMargin=0.65 * inch,
        title=f"{title} — {edition_date}",
        author="The Inkling",
        subject="Personal daily newspaper edition",
    )
    styles = getSampleStyleSheet()
    masthead = ParagraphStyle(
        "InklingMasthead",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=31,
        leading=35,
        textColor=INK,
        alignment=TA_LEFT,
        spaceAfter=5,
    )
    deck = ParagraphStyle(
        "InklingDeck",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=MUTED,
        spaceAfter=17,
    )
    lead_title = ParagraphStyle(
        "InklingLead",
        parent=styles["Heading1"],
        fontName="Times-Bold",
        fontSize=24,
        leading=28,
        textColor=INK,
        spaceBefore=7,
        spaceAfter=8,
        keepWithNext=True,
    )
    story_title = ParagraphStyle(
        "InklingStoryTitle",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=16,
        leading=20,
        textColor=INK,
        spaceBefore=8,
        spaceAfter=5,
        keepWithNext=True,
    )
    body = ParagraphStyle(
        "InklingBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=INK,
        spaceAfter=7,
    )
    byline = ParagraphStyle(
        "InklingByline",
        parent=body,
        fontSize=8,
        leading=11,
        textColor=MUTED,
        spaceAfter=4,
    )
    lead_stamp = ParagraphStyle(
        "InklingStamp",
        parent=byline,
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=ACCENT,
        spaceBefore=9,
        spaceAfter=2,
    )
    original_link = ParagraphStyle(
        "InklingLink",
        parent=body,
        fontSize=8,
        leading=11,
        textColor=LINK,
        wordWrap="CJK",
        spaceAfter=0,
    )

    story = [
        Paragraph(escape(title or "The Inkling"), masthead),
        Paragraph(
            f"YOUR MORNING EDITION&nbsp;&nbsp; / &nbsp;&nbsp;{escape(edition_date)}",
            deck,
        ),
        HRFlowable(width="100%", thickness=1, color=SPINE, spaceAfter=14),
    ]
    if editorial.strip():
        story.extend(
            [
                Paragraph(escape(editorial.strip())[:1000], deck),
                HRFlowable(width="100%", thickness=0.5, color=RULE, spaceAfter=8),
            ]
        )

    for index, article in enumerate(articles):
        article_title = escape(str(article.get("title") or "Untitled story"))[:500]
        source = escape(str(article.get("source") or "Independent source"))[:160]
        summary = escape(
            str(article.get("summary") or "Open the original report for details.")
        )[:2500]
        published = escape(str(article.get("published_at") or ""))[:80]
        metadata = f"{source}  ·  {published}" if published else source
        url = _safe_http_url(str(article.get("url") or ""))
        link = (
            f'<link href="{escape(url, quote=True)}" color="{LINK.hexval()}">'
            "Read the original reporting</link>"
            if url
            else "Original link unavailable"
        )
        section = [
            Paragraph("LEAD STORY" if index == 0 else f"STORY {index + 1}", lead_stamp),
            Paragraph(article_title, lead_title if index == 0 else story_title),
            Paragraph(metadata, byline),
            Paragraph(summary, body),
            Paragraph(link, original_link),
            Spacer(1, 12),
        ]
        story.append(KeepTogether(section))

    if not articles:
        story.append(Paragraph("No stories were saved in this edition.", body))

    def draw_page(canvas, page_doc):
        canvas.saveState()
        page_width, page_height = page_doc.pagesize
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(
            page_doc.leftMargin,
            page_height - 0.68 * inch,
            page_width - page_doc.rightMargin,
            page_height - 0.68 * inch,
        )
        canvas.setFillColor(SPINE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(page_doc.leftMargin, page_height - 0.55 * inch, "THE INKLING")
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            page_width - page_doc.rightMargin,
            0.38 * inch,
            f"{edition_date}  ·  {page_doc.page}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return buffer.getvalue()


def _safe_http_url(value: str) -> str:
    """Only embed ordinary HTTP(S) publisher links in the PDF."""

    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return value
