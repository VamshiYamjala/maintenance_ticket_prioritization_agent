"""
PDF Report Generator for Greenko O&M Maintenance Intelligence.

Generates a professional 5-page enterprise industrial assessment report
using ReportLab and in-memory BytesIO buffers.
"""

from __future__ import annotations

import datetime
import io
import re
import secrets
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Brand Color Palette
CLR_PRIMARY = colors.HexColor("#059669")       # Emerald green
CLR_PRIMARY_DARK = colors.HexColor("#064E3B")  # Dark emerald
CLR_PRIMARY_LIGHT = colors.HexColor("#ECFDF5") # Mint tint
CLR_NAVY = colors.HexColor("#0F2D3A")          # Deep navy
CLR_NAVY_LIGHT = colors.HexColor("#1E3A8A")    # Classic slate navy
CLR_TEXT_MAIN = colors.HexColor("#0F172A")     # Slate dark
CLR_TEXT_MUTED = colors.HexColor("#64748B")    # Medium grey
CLR_TEXT_LIGHT = colors.HexColor("#94A3B8")    # Light grey
CLR_BG_LIGHT = colors.HexColor("#F8FAFC")      # Off-white card bg
CLR_BG_ALT = colors.HexColor("#F1F5F9")        # Table alternate
CLR_BORDER = colors.HexColor("#E2E8F0")        # Border grey

# Severity Semantic Colors
SEV_COLORS = {
    "critical": {
        "text": colors.HexColor("#991B1B"),
        "bg": colors.HexColor("#FEF2F2"),
        "border": colors.HexColor("#FECACA"),
        "bar": colors.HexColor("#DC2626"),
    },
    "high": {
        "text": colors.HexColor("#C2410C"),
        "bg": colors.HexColor("#FFF7ED"),
        "border": colors.HexColor("#FED7AA"),
        "bar": colors.HexColor("#EA580C"),
    },
    "medium": {
        "text": colors.HexColor("#854D0E"),
        "bg": colors.HexColor("#FEFCE8"),
        "border": colors.HexColor("#FEF08A"),
        "bar": colors.HexColor("#CA8A04"),
    },
    "low": {
        "text": colors.HexColor("#166534"),
        "bg": colors.HexColor("#F0FDF4"),
        "border": colors.HexColor("#BBF7D0"),
        "bar": colors.HexColor("#16A34A"),
    },
}


def generate_report_id() -> str:
    """Generate a unique audit-compliant report identifier."""
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    rand_hex = secrets.token_hex(3).upper()
    return f"GKO-RPT-{date_str}-{rand_hex}"


def escape_xml(text: Any) -> str:
    """Escape text for safe XML rendering inside ReportLab Paragraphs."""
    s = str(text if text is not None else "")
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas that automatically records pages and draws running headers,
    footers, and 'Page X of Y' numbering on document save.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []
        self.report_id = "GKO-RPT-OPERATIONAL"

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(total_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, total_pages: int) -> None:
        self.saveState()
        page_w, page_h = self._pagesize

        # Running Top Emerald Accent Bar
        self.setFillColor(CLR_PRIMARY)
        self.rect(0, page_h - 4, page_w, 4, fill=True, stroke=False)

        # Running Top Header
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(CLR_NAVY)
        self.drawString(40, page_h - 24, "GREENKO GROUP O&M | MAINTENANCE INTELLIGENCE")

        self.setFont("Helvetica", 7.5)
        self.setFillColor(CLR_TEXT_MUTED)
        self.drawRightString(page_w - 40, page_h - 24, f"DOC REF: {self.report_id}")

        self.setStrokeColor(CLR_BORDER)
        self.setLineWidth(0.6)
        self.line(40, page_h - 29, page_w - 40, page_h - 29)

        # Running Bottom Footer
        self.setStrokeColor(CLR_BORDER)
        self.setLineWidth(0.6)
        self.line(40, 34, page_w - 40, 34)

        self.setFont("Helvetica", 7)
        self.setFillColor(CLR_TEXT_MUTED)
        self.drawString(40, 22, "CONFIDENTIAL & PROPRIETARY — OPERATIONAL MAINTENANCE ASSESSMENT REPORT")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(page_w - 40, 22, page_str)

        self.restoreState()


def _get_canvas_maker(report_id: str):
    class ConfiguredNumberedCanvas(NumberedCanvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.report_id = report_id
    return ConfiguredNumberedCanvas


def _build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()

    styles: dict[str, ParagraphStyle] = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=CLR_NAVY,
            spaceAfter=3,
        ),
        "DocSub": ParagraphStyle(
            "DocSub",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=CLR_TEXT_MUTED,
            spaceAfter=10,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            textColor=CLR_NAVY,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "SubSectionHeading": ParagraphStyle(
            "SubSectionHeading",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=CLR_NAVY,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=CLR_TEXT_MAIN,
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=CLR_TEXT_MAIN,
        ),
        "BodySmall": ParagraphStyle(
            "BodySmall",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10.5,
            textColor=CLR_TEXT_MUTED,
        ),
        "NoticeText": ParagraphStyle(
            "NoticeText",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=11,
            textColor=CLR_TEXT_MAIN,
        ),
        "MetaLabel": ParagraphStyle(
            "MetaLabel",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=10,
            textColor=CLR_TEXT_MUTED,
        ),
        "MetaVal": ParagraphStyle(
            "MetaVal",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=CLR_TEXT_MAIN,
        ),
        "CardScore": ParagraphStyle(
            "CardScore",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            textColor=CLR_PRIMARY,
            alignment=1,
        ),
        "CardScoreLabel": ParagraphStyle(
            "CardScoreLabel",
            parent=sample["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=CLR_TEXT_MUTED,
            alignment=1,
        ),
        "MonoText": ParagraphStyle(
            "MonoText",
            parent=sample["Normal"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=CLR_NAVY,
        ),
        "MonoSmall": ParagraphStyle(
            "MonoSmall",
            parent=sample["Normal"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=CLR_TEXT_MAIN,
        ),
    }
    return styles


def generate_maintenance_report_pdf(
    ticket_result: dict[str, Any],
    report_id: str | None = None,
) -> bytes:
    """
    Generate an official 5-page enterprise maintenance assessment PDF report.

    Args:
        ticket_result: Full dictionary returned by TicketTriageAgent.run(...)
                       or submitted by the frontend client.
        report_id: Optional unique report identifier. If omitted, one is generated.

    Returns:
        bytes: Binary content of the generated PDF document.
    """
    rep_id = report_id or generate_report_id()
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Extract & sanitize fields with safe defaults
    ticket_id = str(ticket_result.get("ticket_id") or "ADHOC-01")
    asset_type = str(ticket_result.get("asset_type") or "solar").strip().lower()
    category = str(ticket_result.get("category") or "general_maintenance")
    severity = str(ticket_result.get("severity") or "medium").strip().lower()
    ml_severity = str(ticket_result.get("ml_severity") or severity).strip().lower()
    guardrail_escalated = bool(ticket_result.get("guardrail_escalated", False))
    priority_score = float(ticket_result.get("priority_score", 50.0))
    priority_formula = str(
        ticket_result.get("priority_formula")
        or "priority_score = 100 * (0.45 * severity + 0.20 * asset + 0.20 * gen_loss + 0.10 * safety + 0.05 * dup)"
    )
    prio_components = ticket_result.get("priority_components") or {}
    owner_team = str(ticket_result.get("owner_team") or "Plant O&M Central Team")
    sla_hours = int(ticket_result.get("sla_hours") or 24)
    sla_label = str(ticket_result.get("sla_label") or f"Respond within {sla_hours} hours")
    escalation_tier = str(ticket_result.get("escalation_tier") or "Tier-1 Shift Operations")
    confidence = ticket_result.get("confidence") or {}
    cat_conf = float(confidence.get("category", 0.0))
    sev_conf = float(confidence.get("severity", 0.0))
    top2_margin = float(confidence.get("top2_category_margin", 0.0))
    needs_human_review = bool(ticket_result.get("needs_human_review", False))
    review_reasons = ticket_result.get("review_reasons") or []
    equipment_ids = ticket_result.get("equipment_ids") or []
    site_hints = ticket_result.get("site_hints") or []
    probable_causes = ticket_result.get("probable_causes") or []
    next_actions = ticket_result.get("next_actions") or []
    top_terms = ticket_result.get("top_contributing_terms") or []
    cat_probs = ticket_result.get("category_probabilities") or {}
    dup_info = ticket_result.get("duplicate_info") or {}
    dup_count = int(dup_info.get("duplicate_count", 0))
    explanation = str(ticket_result.get("explanation") or "Automated maintenance triage assessment completed.")
    agent_trace = ticket_result.get("agent_trace") or []

    # Original description extraction from result or trace
    raw_description = str(ticket_result.get("raw_description") or ticket_result.get("description") or "")
    clean_text = ""
    for step in agent_trace:
        if step.get("tool") == "normalize_and_extract":
            out = step.get("output") or {}
            clean_text = out.get("clean_text") or ""
            if not raw_description:
                raw_description = clean_text

    if not raw_description:
        raw_description = "Maintenance ticket observation recorded for automated assessment."

    # Setup Document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=38,
        bottomMargin=42,
    )

    styles = _build_styles()
    usable_w = 515.0  # 595 - 80
    story: list[Any] = []

    sev_cfg = SEV_COLORS.get(severity, SEV_COLORS["medium"])

    # =========================================================================
    # PAGE 1: COVER & EXECUTIVE SUMMARY
    # =========================================================================
    # Brand Top Banner
    brand_table_data = [
        [
            Paragraph("<b>GREENKO O&amp;M</b><br/><font size='7' color='#059669'>RENEWABLE ASSET INTELLIGENCE &amp; TRIAGE</font>", styles["DocTitle"]),
            Paragraph(
                f"<font color='#64748B'><b>REPORT REF:</b> {escape_xml(rep_id)}<br/>"
                f"<b>TIMESTAMP:</b> {escape_xml(now_utc)}<br/>"
                f"<b>STATUS:</b> <font color='{sev_cfg['text'].hexval()}'><b>{escape_xml(severity.upper())} PRIORITY</b></font></font>",
                styles["BodySmall"],
            ),
        ]
    ]
    brand_table = Table(brand_table_data, colWidths=[315, 200])
    brand_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(brand_table)

    story.append(HRFlowable(width="100%", thickness=1.5, color=CLR_PRIMARY, spaceBefore=4, spaceAfter=8))

    story.append(Paragraph("AI Maintenance Ticket Assessment Report", styles["DocTitle"]))
    story.append(Paragraph(
        "Autonomous Multi-Factor Maintenance Prioritization, Safety Verification &amp; Operational Dispatch Brief",
        styles["DocSub"],
    ))

    # Document Metadata Grid (6 cells, 2 rows)
    eq_str = ", ".join(equipment_ids) if equipment_ids else "None extracted"
    site_str = ", ".join(site_hints) if site_hints else "None extracted"

    meta_grid_data = [
        [
            Paragraph("REPORT IDENTIFIER", styles["MetaLabel"]),
            Paragraph("TICKET IDENTIFIER", styles["MetaLabel"]),
            Paragraph("PRIMARY ASSET TYPE", styles["MetaLabel"]),
        ],
        [
            Paragraph(f"<b>{escape_xml(rep_id)}</b>", styles["MetaVal"]),
            Paragraph(f"<b>{escape_xml(ticket_id)}</b>", styles["MetaVal"]),
            Paragraph(f"<b>{escape_xml(asset_type.upper())}</b>", styles["MetaVal"]),
        ],
        [
            Paragraph("EQUIPMENT IDENTIFIER(S)", styles["MetaLabel"]),
            Paragraph("SITE / BAY LOCATION", styles["MetaLabel"]),
            Paragraph("ASSESSMENT DATE (UTC)", styles["MetaLabel"]),
        ],
        [
            Paragraph(f"<b>{escape_xml(eq_str)}</b>", styles["MetaVal"]),
            Paragraph(f"<b>{escape_xml(site_str)}</b>", styles["MetaVal"]),
            Paragraph(f"<b>{escape_xml(now_utc)}</b>", styles["MetaVal"]),
        ],
    ]
    meta_table = Table(meta_grid_data, colWidths=[171, 171, 173])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Summary Text
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    story.append(Paragraph(escape_xml(explanation), styles["Body"]))
    story.append(Spacer(1, 10))

    # Highlighted Assessment Executive Card
    score_display = f"{priority_score:.1f}"
    review_status_html = (
        f"<font color='#C2410C'><b>HUMAN REVIEW REQUIRED</b></font>"
        if needs_human_review
        else "<font color='#166534'><b>VERIFIED (AUTONOMOUS)</b></font>"
    )
    guardrail_status_html = (
        f"<font color='#991B1B'><b>ESCALATED BY SAFETY GUARDRAIL</b></font>"
        if guardrail_escalated
        else "<font color='#166534'><b>CLEARED (NO ESCALATION)</b></font>"
    )

    exec_card_data = [
        [
            # Left: Big Priority Score Box
            [
                Paragraph("COMPOSITE PRIORITY", styles["CardScoreLabel"]),
                Paragraph(score_display, styles["CardScore"]),
                Paragraph("<b>OUT OF 100</b>", styles["CardScoreLabel"]),
                Paragraph(f"<font size='7' color='{sev_cfg['bar'].hexval()}'><b>{severity.upper()} TIER</b></font>", styles["CardScoreLabel"]),
            ],
            # Right: Key Metrics Table
            Table([
                [
                    Paragraph("FAULT CATEGORY", styles["MetaLabel"]),
                    Paragraph(f"<b>{escape_xml(category.replace('_', ' ').upper())}</b>", styles["MetaVal"]),
                ],
                [
                    Paragraph("SEVERITY RATING", styles["MetaLabel"]),
                    Paragraph(f"<font color='{sev_cfg['text'].hexval()}'><b>{escape_xml(severity.upper())}</b> (ML: {escape_xml(ml_severity)})</font>", styles["MetaVal"]),
                ],
                [
                    Paragraph("ASSIGNED TEAM", styles["MetaLabel"]),
                    Paragraph(f"<b>{escape_xml(owner_team)}</b>", styles["MetaVal"]),
                ],
                [
                    Paragraph("RESPONSE SLA", styles["MetaLabel"]),
                    Paragraph(f"<b>{escape_xml(sla_label)}</b> ({sla_hours}h max)", styles["MetaVal"]),
                ],
                [
                    Paragraph("SAFETY GUARDRAIL", styles["MetaLabel"]),
                    Paragraph(guardrail_status_html, styles["MetaVal"]),
                ],
                [
                    Paragraph("CONFIDENCE GATE", styles["MetaLabel"]),
                    Paragraph(review_status_html, styles["MetaVal"]),
                ],
            ], colWidths=[120, 245]),
        ]
    ]

    exec_table = Table(exec_card_data, colWidths=[130, 385])
    exec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), CLR_PRIMARY_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 1, CLR_PRIMARY),
        ("INNERGRID", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(exec_table)
    story.append(Spacer(1, 14))

    # Executive Operational Disclaimer Box
    disclaimer_text = (
        "<b>OPERATIONAL ADVISORY NOTICE:</b> This assessment is generated by an automated AI decision-support "
        "system combining NLP classification models, deterministic safety rules, and local O&amp;M runbooks. "
        "All classifications, predicted severities, and recommended inspection actions serve as advisory support "
        "and do NOT replace direct physical walkdown inspections, licensed engineering assessments, or authorized "
        "plant Lock-Out/Tag-Out (LOTO) and Permit-to-Work (PTW) statutory safety procedures."
    )
    disclaimer_table = Table([[Paragraph(disclaimer_text, styles["NoticeText"])]], colWidths=[usable_w])
    disclaimer_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(disclaimer_table)

    # =========================================================================
    # PAGE 2: TICKET DETAILS AND AI ANALYSIS
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("Page 2: Ticket Details &amp; AI Analysis", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CLR_PRIMARY, spaceBefore=2, spaceAfter=8))

    # Section A: Original Maintenance Ticket
    story.append(Paragraph("Section A: Original Maintenance Ticket", styles["SubSectionHeading"]))
    tkt_detail_data = [
        [
            Paragraph("RAW TICKET DESCRIPTION", styles["MetaLabel"]),
            Paragraph(escape_xml(raw_description), styles["Body"]),
        ],
        [
            Paragraph("NORMALIZED CLEAN TEXT", styles["MetaLabel"]),
            Paragraph(escape_xml(clean_text or raw_description), styles["MonoSmall"]),
        ],
        [
            Paragraph("EXTRACTED ENTITIES", styles["MetaLabel"]),
            Paragraph(
                f"Equipment IDs: <b>{escape_xml(eq_str)}</b> &nbsp;|&nbsp; Site Hints: <b>{escape_xml(site_str)}</b>",
                styles["BodySmall"],
            ),
        ],
    ]
    tkt_detail_table = Table(tkt_detail_data, colWidths=[140, 375])
    tkt_detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(tkt_detail_table)
    story.append(Spacer(1, 10))

    # Section B: AI Classification Results
    story.append(Paragraph("Section B: AI Classification &amp; Confidence Breakdown", styles["SubSectionHeading"]))

    cls_summary_data = [
        [
            Paragraph("CLASSIFICATION METRIC", styles["MetaLabel"]),
            Paragraph("PREDICTED VALUE", styles["MetaLabel"]),
            Paragraph("CONFIDENCE / THRESHOLD", styles["MetaLabel"]),
            Paragraph("STATUS", styles["MetaLabel"]),
        ],
        [
            Paragraph("Fault Category", styles["BodyBold"]),
            Paragraph(escape_xml(category.replace("_", " ").title()), styles["Body"]),
            Paragraph(f"{cat_conf * 100:.1f}% (Gate: &ge; 45%)", styles["BodySmall"]),
            Paragraph("<b>PASSED</b>" if cat_conf >= 0.45 else "<font color='#C2410C'>LOW CONF</font>", styles["BodySmall"]),
        ],
        [
            Paragraph("Category Top-2 Margin", styles["BodyBold"]),
            Paragraph(f"{top2_margin * 100:.1f}% separation", styles["Body"]),
            Paragraph("Margin Gate: &ge; 12%", styles["BodySmall"]),
            Paragraph("<b>PASSED</b>" if top2_margin >= 0.12 else "<font color='#C2410C'>CLOSE MARGIN</font>", styles["BodySmall"]),
        ],
        [
            Paragraph("ML Raw Severity", styles["BodyBold"]),
            Paragraph(escape_xml(ml_severity.upper()), styles["Body"]),
            Paragraph(f"{sev_conf * 100:.1f}% (Gate: &ge; 40%)", styles["BodySmall"]),
            Paragraph("<b>PASSED</b>" if sev_conf >= 0.40 else "<font color='#C2410C'>LOW CONF</font>", styles["BodySmall"]),
        ],
        [
            Paragraph("Final Post-Guardrail Severity", styles["BodyBold"]),
            Paragraph(f"<font color='{sev_cfg['text'].hexval()}'><b>{escape_xml(severity.upper())}</b></font>", styles["Body"]),
            Paragraph("Deterministic Rule Gate", styles["BodySmall"]),
            Paragraph("<font color='#991B1B'><b>ESCALATED</b></font>" if guardrail_escalated else "<b>NOMINAL</b>", styles["BodySmall"]),
        ],
    ]
    cls_table = Table(cls_summary_data, colWidths=[140, 135, 140, 100])
    cls_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cls_table)
    story.append(Spacer(1, 8))

    # Top Features Table
    clean_top_terms = [t for t in top_terms if not str(t.get("term", "")).startswith("asset_type_")][:5]
    if clean_top_terms:
        story.append(Paragraph("<b>Top Influential Token Features (Explainability Weights):</b>", styles["BodySmall"]))
        term_row_headers = [Paragraph(f"<b>{escape_xml(t.get('term'))}</b><br/><font color='#059669'>+{t.get('weight', 0):.3f}</font>", styles["BodySmall"]) for t in clean_top_terms]
        while len(term_row_headers) < 5:
            term_row_headers.append(Paragraph("<font color='#94A3B8'>—</font>", styles["BodySmall"]))
        terms_table = Table([term_row_headers], colWidths=[103] * 5)
        terms_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(terms_table)
        story.append(Spacer(1, 10))

    # Section C: Safety Assessment
    story.append(Paragraph("Section C: Safety Assessment &amp; Deterministic Overrides", styles["SubSectionHeading"]))

    # Extract fired rules from agent_trace Step 3
    fired_rules: list[dict[str, Any]] = []
    for step in agent_trace:
        if step.get("tool") == "safety_guardrail":
            fired_rules = (step.get("output") or {}).get("fired_rules") or []

    if fired_rules:
        safety_rows = [
            [
                Paragraph("RULE ID", styles["MetaLabel"]),
                Paragraph("TRIGGER KEYWORDS", styles["MetaLabel"]),
                Paragraph("ESCALATED TO", styles["MetaLabel"]),
                Paragraph("SAFETY JUSTIFICATION", styles["MetaLabel"]),
            ]
        ]
        for r in fired_rules:
            safety_rows.append([
                Paragraph(f"<b>{escape_xml(r.get('rule_id'))}</b>", styles["BodyBold"]),
                Paragraph(escape_xml(r.get("matched_keywords")), styles["MonoSmall"]),
                Paragraph(f"<font color='#991B1B'><b>{escape_xml(str(r.get('escalated_to')).upper())}</b></font>", styles["BodySmall"]),
                Paragraph(escape_xml(r.get("reason")), styles["BodySmall"]),
            ])
        safety_table = Table(safety_rows, colWidths=[110, 115, 90, 200])
        safety_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FEF2F2")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFF7ED")),
            ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#FECACA")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FED7AA")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(safety_table)
    else:
        no_safety_box = Table(
            [[Paragraph(
                "<b>SAFETY CLEARANCE CONFIRMED:</b> No deterministic hazard or safety override keywords were detected. "
                "The severity rating was maintained strictly at the machine learning model prediction without artificial elevation.",
                styles["NoticeText"],
            )]],
            colWidths=[usable_w],
        )
        no_safety_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(no_safety_box)

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "<i>Architectural Note: Deterministic safety guardrails in Greenko O&amp;M enforce a strict escalate-only policy. "
        "They can never downgrade an ML severity prediction, guaranteeing that physical plant and personnel safety "
        "is never compromised by probabilistic model variance.</i>",
        styles["BodySmall"],
    ))

    # =========================================================================
    # PAGE 3: PRIORITY AND OPERATIONAL ROUTING
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("Page 3: Priority &amp; Operational Routing", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CLR_PRIMARY, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("Section A: Transparent Priority Scoring Calculation", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "Priority in Greenko O&amp;M is computed deterministically using a multi-factor transparent formula "
        "combining severity tier, asset criticality, power generation loss risk, safety flags, and repeat fault count:",
        styles["Body"],
    ))
    story.append(Spacer(1, 4))

    # Formula Display Box
    formula_box = Table([[Paragraph(
        "<b>PRIORITY FORMULA:</b><br/>"
        "<font face='Courier' size='7.5' color='#0F2D3A'>"
        "priority_score = 100 &times; [<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;0.45 &times; severity_weight<br/>"
        "&nbsp;&nbsp;+ 0.20 &times; asset_criticality<br/>"
        "&nbsp;&nbsp;+ 0.20 &times; generation_loss_risk<br/>"
        "&nbsp;&nbsp;+ 0.10 &times; safety_flag<br/>"
        "&nbsp;&nbsp;+ 0.05 &times; min(duplicate_count, 3) / 3<br/>"
        "]</font>",
        styles["Body"],
    )]], colWidths=[usable_w])
    formula_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(formula_box)
    story.append(Spacer(1, 8))

    # Priority Component Breakdown Table
    sev_w = float(prio_components.get("severity_weight", 0.75))
    crit_w = float(prio_components.get("asset_criticality", 0.85))
    loss_w = float(prio_components.get("generation_loss_risk", 0.85))
    safe_w = float(prio_components.get("safety_flag", 1.0))
    dup_f = float(prio_components.get("duplicate_factor", 0.0))

    comp_table_data = [
        [
            Paragraph("FACTOR COMPONENT", styles["MetaLabel"]),
            Paragraph("WEIGHT", styles["MetaLabel"]),
            Paragraph("RAW VALUE", styles["MetaLabel"]),
            Paragraph("WEIGHTED CONTRIBUTION", styles["MetaLabel"]),
            Paragraph("OPERATIONAL SIGNIFICANCE", styles["MetaLabel"]),
        ],
        [
            Paragraph("Severity Weight", styles["BodyBold"]),
            Paragraph("45%", styles["Body"]),
            Paragraph(f"{sev_w:.2f}", styles["Body"]),
            Paragraph(f"<b>+{100 * 0.45 * sev_w:.2f} pts</b>", styles["BodyBold"]),
            Paragraph("Baseline fault criticality from ML / safety override", styles["BodySmall"]),
        ],
        [
            Paragraph("Asset Criticality", styles["BodyBold"]),
            Paragraph("20%", styles["Body"]),
            Paragraph(f"{crit_w:.2f}", styles["Body"]),
            Paragraph(f"<b>+{100 * 0.20 * crit_w:.2f} pts</b>", styles["BodyBold"]),
            Paragraph("Equipment hierarchy importance in generation train", styles["BodySmall"]),
        ],
        [
            Paragraph("Generation Loss Risk", styles["BodyBold"]),
            Paragraph("20%", styles["Body"]),
            Paragraph(f"{loss_w:.2f}", styles["Body"]),
            Paragraph(f"<b>+{100 * 0.20 * loss_w:.2f} pts</b>", styles["BodyBold"]),
            Paragraph("Immediate MWh curtailment / revenue loss risk", styles["BodySmall"]),
        ],
        [
            Paragraph("Safety Override Flag", styles["BodyBold"]),
            Paragraph("10%", styles["Body"]),
            Paragraph(f"{safe_w:.1f}", styles["Body"]),
            Paragraph(f"<b>+{100 * 0.10 * safe_w:.2f} pts</b>", styles["BodyBold"]),
            Paragraph("Personnel safety, EHS, or arc/fire hazard escalation", styles["BodySmall"]),
        ],
        [
            Paragraph("Duplicate Repeat Factor", styles["BodyBold"]),
            Paragraph("5%", styles["Body"]),
            Paragraph(f"{dup_f:.2f} (count: {dup_count})", styles["Body"]),
            Paragraph(f"<b>+{100 * 0.05 * dup_f:.2f} pts</b>", styles["BodyBold"]),
            Paragraph("Repeat nuisance tripping / unaddressed defect boost", styles["BodySmall"]),
        ],
        [
            Paragraph("<b>TOTAL COMPOSITE SCORE</b>", styles["BodyBold"]),
            Paragraph("<b>100%</b>", styles["BodyBold"]),
            Paragraph("<b>—</b>", styles["BodyBold"]),
            Paragraph(f"<font color='{sev_cfg['bar'].hexval()}'><b>{priority_score:.1f} / 100</b></font>", styles["BodyBold"]),
            Paragraph(f"<b>Normalized Rank: {severity.upper()} Priority</b>", styles["BodyBold"]),
        ],
    ]
    comp_table = Table(comp_table_data, colWidths=[120, 50, 75, 120, 150])
    comp_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_BG_ALT),
        ("BACKGROUND", (0, -1), (-1, -1), CLR_PRIMARY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 12))

    # Section B: Operational Assignment
    story.append(Paragraph("Section B: Operational Assignment &amp; SLA Standards", styles["SubSectionHeading"]))

    sla_standards_data = [
        [
            Paragraph("SEVERITY", styles["MetaLabel"]),
            Paragraph("TARGET SLA", styles["MetaLabel"]),
            Paragraph("DISPATCH WINDOW", styles["MetaLabel"]),
            Paragraph("ORGANIZATIONAL ASSIGNMENT", styles["MetaLabel"]),
            Paragraph("CURRENT TICKET STATUS", styles["MetaLabel"]),
        ],
        [
            Paragraph("<font color='#991B1B'><b>CRITICAL</b></font>", styles["BodySmall"]),
            Paragraph("1 Hour", styles["BodySmall"]),
            Paragraph("Immediate emergency dispatch", styles["BodySmall"]),
            Paragraph("Central Grid &amp; Plant Emergency Team", styles["BodySmall"]),
            Paragraph("<b>SELECTED</b>" if severity == "critical" else "—", styles["BodySmall"]),
        ],
        [
            Paragraph("<font color='#C2410C'><b>HIGH</b></font>", styles["BodySmall"]),
            Paragraph("4 Hours", styles["BodySmall"]),
            Paragraph("Same-shift engineering dispatch", styles["BodySmall"]),
            Paragraph(escape_xml(owner_team), styles["BodySmall"]),
            Paragraph("<b>SELECTED</b>" if severity == "high" else "—", styles["BodySmall"]),
        ],
        [
            Paragraph("<font color='#854D0E'><b>MEDIUM</b></font>", styles["BodySmall"]),
            Paragraph("24 Hours", styles["BodySmall"]),
            Paragraph("Next-day scheduled inspection", styles["BodySmall"]),
            Paragraph("Asset Scheduled Maintenance Team", styles["BodySmall"]),
            Paragraph("<b>SELECTED</b>" if severity == "medium" else "—", styles["BodySmall"]),
        ],
        [
            Paragraph("<font color='#166534'><b>LOW</b></font>", styles["BodySmall"]),
            Paragraph("72 Hours", styles["BodySmall"]),
            Paragraph("Standard routine backlog window", styles["BodySmall"]),
            Paragraph("Routine Operations Walkdown Team", styles["BodySmall"]),
            Paragraph("<b>SELECTED</b>" if severity == "low" else "—", styles["BodySmall"]),
        ],
    ]
    sla_table = Table(sla_standards_data, colWidths=[75, 70, 130, 160, 80])
    sla_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sla_table)
    story.append(Spacer(1, 8))

    # Duplicate status notes
    dup_status_text = (
        f"<b>Duplicate Detection Audit:</b> Token Jaccard similarity analysis identified "
        f"<b>{dup_count}</b> matching recent ticket(s). "
        + ("Repeated fault condition flagged; priority factor elevated." if dup_count > 0 else "No duplicate defect patterns detected in current rolling window.")
    )
    story.append(Paragraph(dup_status_text, styles["BodySmall"]))

    # =========================================================================
    # PAGE 4: RUNBOOK AND MAINTENANCE RECOMMENDATIONS
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("Page 4: Runbook &amp; Maintenance Recommendations", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CLR_PRIMARY, spaceBefore=2, spaceAfter=8))

    runbook_id = str(ticket_result.get("runbook_id") or "RB-STANDARD-01")
    for step in agent_trace:
        if step.get("tool") == "lookup_runbook":
            runbook_id = (step.get("output") or {}).get("runbook_id") or runbook_id

    # Runbook SOP Banner
    rb_header_data = [
        [
            Paragraph("RETRIEVED RUNBOOK SOP", styles["MetaLabel"]),
            Paragraph("TARGET ASSET &amp; FAULT", styles["MetaLabel"]),
            Paragraph("KNOWLEDGE BASE RETRIEVAL METHOD", styles["MetaLabel"]),
        ],
        [
            Paragraph(f"<b>{escape_xml(runbook_id)}</b>", styles["BodyBold"]),
            Paragraph(f"<b>{escape_xml(asset_type.upper())} &bull; {escape_xml(category.replace('_', ' ').upper())}</b>", styles["BodyBold"]),
            Paragraph("TF-IDF Cosine Similarity over local SOP repository", styles["BodySmall"]),
        ],
    ]
    rb_header_table = Table(rb_header_data, colWidths=[130, 205, 180])
    rb_header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(rb_header_table)
    story.append(Spacer(1, 10))

    # Probable Root Causes Section
    story.append(Paragraph("Candidate Probable Causes (Investigation Hypotheses)", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "<i>The following hypotheses were retrieved from historical O&amp;M fault trees. "
        "They represent candidate inspection focal points, not confirmed diagnoses:</i>",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 4))

    cause_rows = []
    for idx, c in enumerate(probable_causes, 1):
        cause_rows.append([
            Paragraph(f"<b>CAUSE {idx}</b>", styles["MetaLabel"]),
            Paragraph(escape_xml(c), styles["Body"]),
        ])
    if not cause_rows:
        cause_rows.append([Paragraph("CAUSE 1", styles["MetaLabel"]), Paragraph("Inspect equipment logs and telemetry trends.", styles["Body"])])

    cause_table = Table(cause_rows, colWidths=[70, 445])
    cause_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), CLR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cause_table)
    story.append(Spacer(1, 10))

    # Recommended Inspection Steps Section
    story.append(Paragraph("Recommended Troubleshooting &amp; Inspection Steps", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "<i>Execute the following operational procedures sequentially under valid Permit-to-Work (PTW):</i>",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 4))

    action_rows = []
    for idx, a in enumerate(next_actions, 1):
        action_rows.append([
            Paragraph(f"<b>STEP {idx}</b>", styles["MetaLabel"]),
            Paragraph(escape_xml(a), styles["Body"]),
        ])
    if not action_rows:
        action_rows.append([Paragraph("STEP 1", styles["MetaLabel"]), Paragraph("Dispatch technician for visual and electrical walkdown.", styles["Body"])])

    action_table = Table(action_rows, colWidths=[70, 445])
    action_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), CLR_PRIMARY_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_PRIMARY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(action_table)
    story.append(Spacer(1, 14))

    # Runbook Safety Notice
    rb_notice = (
        "<b>RUNBOOK USAGE SAFETY DIRECTIVE:</b> The troubleshooting recommendations above are derived from the "
        "Greenko Plant Standard Operating Procedure repository. Personnel must verify that all equipment has been "
        "properly isolated, tagged out (LOTO), and grounded before opening enclosures, accessing high-voltage "
        "switchgear, or performing physical maintenance. Do not bypass safety interlocks under any circumstances."
    )
    rb_notice_table = Table([[Paragraph(rb_notice, styles["NoticeText"])]], colWidths=[usable_w])
    rb_notice_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rb_notice_table)

    # =========================================================================
    # PAGE 5: AI AGENT EXECUTION TRACE & FINAL DISCLAIMER
    # =========================================================================
    story.append(PageBreak())

    story.append(Paragraph("Page 5: AI Agent Execution Trace &amp; Audit Trail", styles["SectionHeading"]))
    story.append(HRFlowable(width="100%", thickness=1, color=CLR_PRIMARY, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("9-Step Autonomous Agent Workflow Trace", styles["SubSectionHeading"]))
    story.append(Paragraph(
        "Complete deterministic audit trail of the 9 sequential tools executed by the Greenko Triage Agent:",
        styles["BodySmall"],
    ))
    story.append(Spacer(1, 4))

    # Trace Table
    trace_rows = [
        [
            Paragraph("STEP", styles["MetaLabel"]),
            Paragraph("TOOL EXECUTED", styles["MetaLabel"]),
            Paragraph("STATUS", styles["MetaLabel"]),
            Paragraph("EXECUTION SUMMARY / KEY PAYLOAD", styles["MetaLabel"]),
        ]
    ]

    for step in agent_trace:
        step_num = step.get("step", 0)
        tool_name = step.get("tool", "unknown_tool")
        out = step.get("output") or {}

        status_text = "<b>EXECUTED</b>"
        if tool_name == "safety_guardrail" and out.get("escalated"):
            status_text = "<font color='#991B1B'><b>ESCALATED</b></font>"
        elif tool_name == "confidence_gate" and out.get("needs_human_review"):
            status_text = "<font color='#C2410C'><b>FLAGGED</b></font>"

        # Format concise payload summary
        if tool_name == "normalize_and_extract":
            eq = out.get("equipment_ids") or []
            summary = f"Cleaned text. Equipment: {escape_xml(', '.join(eq) or 'None')}. Site: {escape_xml(', '.join(out.get('site_hints') or []) or 'None')}."
        elif tool_name == "classify_ticket":
            summary = f"Category: {escape_xml(out.get('category'))} ({out.get('category_confidence', 0)*100:.1f}%). ML Severity: {escape_xml(out.get('ml_severity'))} ({out.get('severity_confidence', 0)*100:.1f}%)."
        elif tool_name == "safety_guardrail":
            if out.get("escalated"):
                rules = out.get("fired_rules") or []
                r_ids = ", ".join(r.get("rule_id", "") for r in rules)
                summary = f"ESCALATED to {escape_xml(out.get('final_severity'))}. Fired: {escape_xml(r_ids)}."
            else:
                summary = f"Cleared. Final Severity: {escape_xml(out.get('final_severity'))} (no hazard override triggered)."
        elif tool_name == "lookup_runbook":
            summary = f"Matched SOP: {escape_xml(out.get('runbook_id'))} via TF-IDF cosine similarity. Owner: {escape_xml(out.get('owner_team'))}."
        elif tool_name == "check_duplicates":
            summary = f"Duplicate count: {out.get('duplicate_count', 0)}. Is repeat fault: {out.get('is_repeat_fault', False)}."
        elif tool_name == "compute_priority":
            summary = f"Priority score: {out.get('priority_score', 0):.1f}/100 based on 5 weighted factors."
        elif tool_name == "route_ticket":
            summary = f"Assigned: {escape_xml(out.get('owner_team'))}. SLA: {escape_xml(out.get('sla_label'))}. Tier: {escape_xml(out.get('escalation_tier'))}."
        elif tool_name == "confidence_gate":
            reasons = out.get("reasons") or []
            if out.get("needs_human_review"):
                summary = f"Human review flagged. Reasons: {escape_xml('; '.join(reasons))}."
            else:
                summary = "Confidence gate passed. All metrics within autonomous thresholds."
        elif tool_name == "explanation_layer":
            summary = f"Summary generated via {escape_xml(out.get('explanation_source', 'template'))} layer."
        else:
            summary = escape_xml(str(out)[:80])

        trace_rows.append([
            Paragraph(f"<b>{step_num}</b>", styles["BodyBold"]),
            Paragraph(f"<code>{escape_xml(tool_name)}</code>", styles["MonoSmall"]),
            Paragraph(status_text, styles["BodySmall"]),
            Paragraph(summary, styles["BodySmall"]),
        ])

    trace_table = Table(trace_rows, colWidths=[35, 125, 75, 280])
    trace_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(trace_table)
    story.append(Spacer(1, 10))

    # Human Review & Operational Limitations
    review_desc = (
        "<b>CONFIDENCE GATE DECISION:</b> "
        + (f"<font color='#C2410C'><b>HUMAN REVIEW REQUIRED</b> &mdash; Reasons: {escape_xml('; '.join(review_reasons))}</font>"
           if needs_human_review
           else "<font color='#166534'><b>AUTONOMOUS TRIAGE APPROVED</b> &mdash; Classification and severity confidences exceed all operational safety thresholds.</font>")
    )
    story.append(Paragraph(review_desc, styles["BodySmall"]))
    story.append(Spacer(1, 6))

    limitations_text = (
        "<b>SYSTEM LIMITATIONS NOTICE:</b> This system is trained on renewable energy domain data (Solar, Wind, Hydro, Grid). "
        "Out-of-domain descriptions, ambiguous multi-asset reports, or novel telemetry codes should be routed to senior plant "
        "engineering for manual review. The model does not monitor real-time SCADA live streams directly; it triages submitted "
        "operator observations."
    )
    story.append(Paragraph(limitations_text, styles["BodySmall"]))
    story.append(Spacer(1, 10))

    # Formal Closing Statement & Engineering Sign-off Box
    final_disclaimer_text = (
        "<b>FINAL AUDIT STATEMENT:</b> This document is an AI-assisted maintenance decision-support report. "
        "All classifications, severity predictions, and recommended actions must be reviewed and authorized "
        "by qualified personnel before operational decisions or physical maintenance actions are executed. "
        "This software does not independently inspect equipment or execute physical operations."
    )
    story.append(Paragraph(final_disclaimer_text, styles["NoticeText"]))
    story.append(Spacer(1, 8))

    # Sign-off Grid
    signoff_data = [
        [
            Paragraph("ASSESSMENT GENERATION", styles["MetaLabel"]),
            Paragraph("OPERATIONAL VERIFICATION", styles["MetaLabel"]),
            Paragraph("PLANT MANAGEMENT APPROVAL", styles["MetaLabel"]),
        ],
        [
            Paragraph("System: Greenko AI Triage Agent<br/>Engine: TF-IDF + Logistic Regression<br/>Version: v1.0.0 Enterprise", styles["BodySmall"]),
            Paragraph("Verified By: ________________________<br/>Role: O&amp;M Shift Lead<br/>Date: ____________________________", styles["BodySmall"]),
            Paragraph("Approved By: ________________________<br/>Role: Plant Operations Manager<br/>Date: ____________________________", styles["BodySmall"]),
        ],
    ]
    signoff_table = Table(signoff_data, colWidths=[171, 171, 173])
    signoff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CLR_BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.75, CLR_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, CLR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(signoff_table)

    # Build the PDF using our custom NumberedCanvas
    canvas_maker = _get_canvas_maker(rep_id)
    doc.build(story, canvasmaker=canvas_maker)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
