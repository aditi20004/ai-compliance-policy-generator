import datetime
import hashlib
import re
from pathlib import Path

from fpdf import FPDF
from jinja2 import Environment, FileSystemLoader

from app.config import GENERATED_DIR, TEMPLATES_DIR

TEMPLATE_TYPES = {
    "ai_acceptable_use": "ai_acceptable_use.j2",
    "data_classification": "data_classification.j2",
    "incident_response": "incident_response.j2",
    "remediation_action_plan": "remediation_action_plan.j2",
    "vendor_risk_assessment": "vendor_risk_assessment.j2",
    "ai_ethics_framework": "ai_ethics_framework.j2",
    "employee_ai_training": "employee_ai_training.j2",
    "ai_risk_register": "ai_risk_register.j2",
    "privacy_policy": "privacy_policy.j2",
    "board_ai_briefing": "board_ai_briefing.j2",
    "ai_transparency_statement": "ai_transparency_statement.j2",
    "ai_data_retention": "ai_data_retention.j2",
    "ai_procurement": "ai_procurement.j2",
    "shadow_ai_playbook": "shadow_ai_playbook.j2",
    "bias_audit_procedure": "bias_audit_procedure.j2",
    "statutory_tort_defence": "statutory_tort_defence.j2",
    "tranche2_readiness": "tranche2_readiness.j2",
    "essential_eight_ai": "essential_eight_ai.j2",
    "copyright_ip_policy": "copyright_ip_policy.j2",
    "ai_supply_chain_audit": "ai_supply_chain_audit.j2",
}

# Centralised template labels — single source of truth for all UI pages
TEMPLATE_LABELS = {
    "ai_acceptable_use": "AI Acceptable Use Policy",
    "privacy_policy": "Privacy Policy (APP-Compliant)",
    "data_classification": "Data Classification for AI",
    "incident_response": "AI Incident Response Plan",
    "employee_ai_training": "Employee AI Training Guide",
    "ai_risk_register": "AI Risk Register",
    "board_ai_briefing": "Board AI Risk Briefing",
    "ai_ethics_framework": "AI Ethics & Fairness Framework",
    "vendor_risk_assessment": "AI Vendor Risk Assessment",
    "ai_procurement": "AI Procurement & Tool Approval Policy",
    "ai_supply_chain_audit": "AI Supply Chain Audit Template",
    "shadow_ai_playbook": "Shadow AI Detection & Response Playbook",
    "bias_audit_procedure": "AI Bias & Fairness Audit Procedure",
    "ai_data_retention": "AI Data Retention & Destruction Policy",
    "essential_eight_ai": "Essential Eight Controls for AI",
    "ai_transparency_statement": "AI Transparency Statement",
    "copyright_ip_policy": "AI Copyright & IP Policy",
    "statutory_tort_defence": "Statutory Tort Defence Checklist",
    "tranche2_readiness": "POLA Act Tranche 2 Readiness Plan",
    "remediation_action_plan": "Remediation Action Plan",
    "compliance_report": "Compliance Report",
}

# Policy categories for the Generate page
TEMPLATE_CATEGORIES = {
    "Core Governance": [
        "ai_acceptable_use",
        "privacy_policy",
        "data_classification",
        "incident_response",
        "employee_ai_training",
    ],
    "Risk & Oversight": [
        "ai_risk_register",
        "board_ai_briefing",
        "ai_ethics_framework",
        "bias_audit_procedure",
        "essential_eight_ai",
    ],
    "Vendor & Supply Chain": [
        "vendor_risk_assessment",
        "ai_procurement",
        "ai_supply_chain_audit",
    ],
    "Specialist Policies": [
        "shadow_ai_playbook",
        "ai_data_retention",
        "ai_transparency_statement",
        "copyright_ip_policy",
        "statutory_tort_defence",
        "tranche2_readiness",
    ],
}


def recommend_templates(org_data: dict) -> dict[str, list[str]]:
    """Return recommended and optional template keys based on org profile.

    Returns {"recommended": [...], "optional": [...]} from the generatable
    templates (excludes remediation_action_plan and compliance_report which
    are generated from the Compliance page).
    """
    recommended = set()
    optional = set()

    # Core governance — always recommended
    for t in TEMPLATE_CATEGORIES["Core Governance"]:
        recommended.add(t)

    # Risk & Oversight
    recommended.add("ai_risk_register")
    recommended.add("board_ai_briefing")
    if org_data.get("automated_decisions") or org_data.get("customer_facing_ai"):
        recommended.add("ai_ethics_framework")
    else:
        optional.add("ai_ethics_framework")
    if org_data.get("automated_decisions") or org_data.get("ai_profiling_or_eligibility"):
        recommended.add("bias_audit_procedure")
    else:
        optional.add("bias_audit_procedure")
    if not org_data.get("essential_eight_applied"):
        recommended.add("essential_eight_ai")
    else:
        optional.add("essential_eight_ai")

    # Vendor & Supply Chain
    has_overseas = any(
        o for o in (org_data.get("ai_tools_overseas") or [])
        if o != "None — all data stays in Australia"
    )
    if org_data.get("ai_tools_in_use") or has_overseas:
        recommended.add("vendor_risk_assessment")
        recommended.add("ai_procurement")
    else:
        optional.add("vendor_risk_assessment")
        optional.add("ai_procurement")
    if has_overseas:
        recommended.add("ai_supply_chain_audit")
    else:
        optional.add("ai_supply_chain_audit")

    # Specialist Policies
    if not org_data.get("shadow_ai_controls"):
        recommended.add("shadow_ai_playbook")
    else:
        optional.add("shadow_ai_playbook")
    if not org_data.get("has_data_retention_policy"):
        recommended.add("ai_data_retention")
    else:
        optional.add("ai_data_retention")
    if org_data.get("customer_facing_ai"):
        recommended.add("ai_transparency_statement")
    else:
        optional.add("ai_transparency_statement")
    if org_data.get("ai_in_marketing") or org_data.get("customer_facing_ai"):
        recommended.add("copyright_ip_policy")
    else:
        optional.add("copyright_ip_policy")
    # Statutory tort applies to everyone under POLA Act
    recommended.add("statutory_tort_defence")
    if org_data.get("automated_decisions"):
        recommended.add("tranche2_readiness")
    else:
        optional.add("tranche2_readiness")

    return {
        "recommended": sorted(recommended, key=lambda t: _template_sort_key(t)),
        "optional": sorted(optional, key=lambda t: _template_sort_key(t)),
    }


def _template_sort_key(template_type: str) -> tuple[int, str]:
    """Sort templates by category order, then alphabetically within category."""
    order = 0
    for idx, (_, templates) in enumerate(TEMPLATE_CATEGORIES.items()):
        if template_type in templates:
            order = idx
            break
    return (order, template_type)

# SECURITY NOTE: autoescape is intentionally disabled because templates output
# Markdown/plain text (rendered to PDF), NOT browser-served HTML. Enabling
# autoescape would corrupt Markdown formatting characters (&, *, _, etc.).
# User input is safe here because the output pipeline is:
#   Jinja2 → Markdown string → fpdf2 PDF  (never rendered as HTML in a browser)
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def build_template_context(questionnaire_data: dict) -> dict:
    ctx = {
        **questionnaire_data,
        "effective_date": datetime.date.today().isoformat(),
        "version": "1.0",
    }
    # Ensure list fields are never None (templates use `in` checks and `for` loops)
    for key in ("data_types_processed", "automated_decision_types", "ai_tools_in_use", "ai_tools_overseas"):
        if ctx.get(key) is None:
            ctx[key] = []
    # Board briefing template needs policy_types; default to empty list
    if "policy_types" not in ctx:
        ctx["policy_types"] = []
    return ctx


def render_policy_text(template_type: str, context: dict) -> str:
    if template_type not in TEMPLATE_TYPES:
        raise ValueError(f"Unknown template type: {template_type}")
    template = jinja_env.get_template(TEMPLATE_TYPES[template_type])
    return template.render(context)


def save_policy_markdown(template_type: str, content: str, org_id: int) -> tuple[str, str]:
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"{template_type}_{org_id}_{timestamp}.md"
    file_path = GENERATED_DIR / filename
    try:
        file_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Failed to write policy file {filename}: {exc}") from exc
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return str(file_path), content_hash


FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "company_logo.png"


class PolicyPDF(FPDF):
    def __init__(self, title_text="Policy Document", org_name="", doc_date=""):
        super().__init__()
        self.title_text = title_text
        self.org_name = org_name
        self.doc_date = doc_date
        self._has_cover = False
        self._use_fallback_font = False
        # Register Unicode font (with existence check for all variants)
        _font_files = {
            "": FONTS_DIR / "DejaVuSans.ttf",
            "B": FONTS_DIR / "DejaVuSans-Bold.ttf",
            "I": FONTS_DIR / "DejaVuSans-Oblique.ttf",
            "BI": FONTS_DIR / "DejaVuSans-BoldOblique.ttf",
        }
        if all(f.exists() for f in _font_files.values()):
            for style, fpath in _font_files.items():
                self.add_font("DejaVu", style, str(fpath))
        else:
            # Fallback to built-in Helvetica (no add_font needed for built-ins)
            self._use_fallback_font = True

    def set_font(self, family="", style="", size=0):
        if self._use_fallback_font and family == "DejaVu":
            family = "Helvetica"
        super().set_font(family, style, size)

    def add_cover_page(self):
        """Add a branded cover page with logo, title, org name, and date."""
        self._has_cover = True
        self.add_page()

        # Blue gradient banner at top
        self.set_fill_color(26, 60, 110)
        self.rect(0, 0, 210, 100, "F")

        # Logo on cover
        if LOGO_PATH.exists():
            import contextlib

            with contextlib.suppress(Exception):
                self.image(str(LOGO_PATH), x=80, y=18, h=20)

        # Title text on the blue banner
        self.set_xy(10, 50)
        self.set_font("DejaVu", "B", 24)
        self.set_text_color(255, 255, 255)
        self.multi_cell(190, 12, self.title_text, align="C")

        # Subtitle
        self.set_x(10)
        self.set_font("DejaVu", "", 12)
        self.set_text_color(200, 215, 240)
        self.multi_cell(190, 8, "AI Governance & Compliance Document", align="C")

        # Organisation details block below the banner
        self.set_xy(10, 115)
        self.set_font("DejaVu", "", 11)
        self.set_text_color(80, 80, 80)

        details = [
            ("Prepared For", self.org_name or "Organisation"),
            ("Date", self.doc_date or datetime.date.today().isoformat()),
            ("Classification", "Confidential — Internal Use Only"),
            ("Framework", "AI6 Essential Practices"),
        ]

        for label, value in details:
            self.set_x(40)
            self.set_font("DejaVu", "B", 10)
            self.set_text_color(26, 60, 110)
            self.cell(40, 8, label, align="R")
            self.set_font("DejaVu", "", 10)
            self.set_text_color(51, 51, 51)
            self.cell(5, 8, "")
            self.cell(0, 8, value)
            self.ln(10)

        # Regulatory badges at bottom
        self.set_y(185)
        self.set_draw_color(26, 60, 110)
        self.set_line_width(0.3)
        self.line(30, self.get_y(), 180, self.get_y())
        self.ln(6)

        self.set_x(10)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(100, 100, 100)
        self.multi_cell(
            190,
            5,
            (
                "Aligned with: Privacy Act 1988 (Cth) | POLA Act 2024 | "
                "AI Ethics Principles | OAIC AI Guidance (Oct 2024) | "
                "AI6 Essential Practices | Australian Consumer Law"
            ),
            align="C",
        )

        self.ln(4)
        self.set_x(10)
        self.set_font("DejaVu", "I", 7)
        self.set_text_color(150, 150, 150)
        self.multi_cell(190, 4, ("Generated by AI Compliance Policy Generator for Australian SMEs"), align="C")

    def header(self):
        # No header on cover page
        if self._has_cover and self.page_no() == 1:
            return
        # Running header on pages 2+
        self.set_font("DejaVu", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, f"{self.org_name}  |  {self.title_text}", align="L")
        self.ln(2)
        self.set_draw_color(220, 220, 220)
        self.set_line_width(0.2)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(95, 10, f"{self.org_name} — Confidential", align="L")
        self.cell(95, 10, f"Page {self.page_no()}/{self.pages_count}", align="R")


def _parse_table(lines: list[str], start_idx: int) -> tuple[list[list[str]], int]:
    """Parse a markdown table starting at start_idx. Returns (rows, end_idx)."""
    rows = []
    i = start_idx
    while i < len(lines):
        line = lines[i].strip()
        if not line.startswith("|"):
            break
        # Skip separator row (|---|---|)
        if re.match(r"^\|[\s\-:|]+\|$", line):
            i += 1
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)
        i += 1
    return rows, i


def _clean_md(text: str) -> str:
    """Strip markdown formatting from text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    return text


def _calc_col_widths(rows: list[list[str]], num_cols: int, total_width: float, font_size: float) -> list[float]:
    """Calculate proportional column widths based on content length."""
    min_col_w = 18.0  # minimum column width in mm

    # Find the max content length per column
    max_lens = [0] * num_cols
    for row in rows:
        for j in range(min(len(row), num_cols)):
            cleaned = _clean_md(row[j])
            max_lens[j] = max(max_lens[j], len(cleaned))

    # Convert to proportional widths
    total_chars = sum(max_lens) or 1
    widths = []
    for ml in max_lens:
        w = max(min_col_w, (ml / total_chars) * total_width)
        widths.append(w)

    # Normalize so they sum to total_width
    w_sum = sum(widths) or 1
    widths = [w * total_width / w_sum for w in widths]
    return widths


def _estimate_row_height(cells: list[str], col_widths: list[float], font_size: float, line_h: float) -> float:
    """Estimate the height needed for a row based on text wrapping."""
    char_w = font_size * 0.45
    max_lines = 1
    for j, cell_text in enumerate(cells):
        if j >= len(col_widths):
            break
        text = _clean_md(cell_text)
        # Usable width inside the cell (subtract padding)
        usable = col_widths[j] - 2
        if usable <= 0:
            usable = col_widths[j]
        chars_per_line = max(1, int(usable / char_w))
        num_lines = max(1, -(-len(text) // chars_per_line))  # ceiling division
        max_lines = max(max_lines, num_lines)
    return max_lines * line_h


def _draw_table_row(
    pdf,
    cells: list[str],
    col_widths: list[float],
    row_h: float,
    left_margin: float,
    is_header: bool = False,
    num_cols: int = 0,
    header_cells: list[str] | None = None,
    header_h: float = 0,
    font_size: float = 8,
):
    """Draw a single table row with proper text wrapping inside bordered cells.
    If header_cells is provided and a page break is needed, the header row is re-drawn first."""
    x_start = left_margin
    y_start = pdf.get_y()

    # Check if row fits on current page, if not add a new page
    if y_start + row_h > pdf.h - pdf.b_margin:
        pdf.add_page()
        y_start = pdf.get_y()

        # Re-draw header row on new page (if this is a data row)
        if not is_header and header_cells:
            pdf.set_font("DejaVu", "B", font_size)
            pdf.set_text_color(255, 255, 255)
            pdf.set_draw_color(26, 60, 110)
            _draw_table_row(pdf, header_cells, col_widths, header_h, left_margin, is_header=True, num_cols=num_cols)
            pdf.set_font("DejaVu", "", font_size)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(180, 180, 180)
            y_start = pdf.get_y()

    # Alternate row shading for data rows
    if not is_header:
        # Light grey background on even rows for readability
        pdf.set_fill_color(245, 247, 250)

    # Draw cell borders and content
    for j in range(num_cols):
        cell_text = _clean_md(cells[j]) if j < len(cells) else ""
        cw = col_widths[j]
        x_pos = x_start + sum(col_widths[:j])

        # Fill header or alternate row background
        if is_header:
            pdf.set_fill_color(26, 60, 110)
            pdf.rect(x_pos, y_start, cw, row_h, "F")
        pdf.rect(x_pos, y_start, cw, row_h, "D")

        # Write text inside the cell
        pdf.set_xy(x_pos + 1, y_start + 1)
        align = "C" if is_header else "L"
        pdf.multi_cell(cw - 2, 4, cell_text, align=align)

    # Move to next row
    pdf.set_xy(left_margin, y_start + row_h)


def markdown_to_pdf(md_content: str, output_path: Path) -> None:
    """Convert markdown content to a styled PDF using fpdf2."""
    title_match = re.search(r"^#\s+(.+)$", md_content, re.MULTILINE)
    title_text = _clean_md(title_match.group(1)) if title_match else "Policy Document"

    # Extract org name and date from content metadata
    org_match = re.search(r"\*\*Organisation:\*\*\s*(.+)", md_content)
    date_match = re.search(r"\*\*Effective Date:\*\*\s*(.+)", md_content)
    org_name = (org_match.group(1).strip()[:100] if org_match else "").replace("\x00", "")
    doc_date = (date_match.group(1).strip()[:30] if date_match else "").replace("\x00", "")

    pdf = PolicyPDF(title_text=title_text, org_name=org_name, doc_date=doc_date)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Add branded cover page
    pdf.add_cover_page()

    # Start content on page 2
    pdf.add_page()
    left_margin = pdf.l_margin

    lines = md_content.split("\n")
    i = 0
    table_width = 190.0

    while i < len(lines):
        stripped = lines[i].strip()
        pdf.set_x(left_margin)  # Always reset x to left margin

        # Skip empty lines
        if not stripped:
            pdf.ln(3)
            i += 1
            continue

        # Horizontal rule
        if stripped.startswith("---"):
            y = pdf.get_y()
            pdf.set_draw_color(200, 200, 200)
            pdf.line(10, y, 200, y)
            pdf.ln(5)
            i += 1
            continue

        # Table
        if stripped.startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            rows, end_idx = _parse_table(lines, i)
            if rows:
                num_cols = max(len(r) for r in rows)
                font_size = 7 if num_cols > 4 else 8
                line_h = 4
                col_widths = _calc_col_widths(rows, num_cols, table_width, font_size)

                # Header row
                pdf.set_font("DejaVu", "B", font_size)
                pdf.set_text_color(255, 255, 255)
                pdf.set_draw_color(26, 60, 110)
                header_h = _estimate_row_height(rows[0], col_widths, font_size, line_h)
                header_h = max(header_h, 6)
                _draw_table_row(pdf, rows[0], col_widths, header_h, left_margin, is_header=True, num_cols=num_cols)

                # Data rows (pass header info for repetition on page breaks)
                pdf.set_font("DejaVu", "", font_size)
                pdf.set_text_color(0, 0, 0)
                pdf.set_draw_color(180, 180, 180)
                for row in rows[1:]:
                    row_h = _estimate_row_height(row, col_widths, font_size, line_h)
                    row_h = max(row_h, 6)
                    _draw_table_row(
                        pdf,
                        row,
                        col_widths,
                        row_h,
                        left_margin,
                        is_header=False,
                        num_cols=num_cols,
                        header_cells=rows[0],
                        header_h=header_h,
                        font_size=font_size,
                    )

                pdf.ln(4)
            i = end_idx
            continue

        # Heading 1
        if stripped.startswith("# ") and not stripped.startswith("## "):
            pdf.set_font("DejaVu", "B", 18)
            pdf.set_text_color(26, 60, 110)
            pdf.multi_cell(0, 10, _clean_md(stripped[2:]))
            pdf.set_draw_color(26, 60, 110)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(4)
            i += 1
            continue

        # Heading 2
        if stripped.startswith("## ") and not stripped.startswith("### "):
            pdf.ln(4)
            pdf.set_font("DejaVu", "B", 14)
            pdf.set_text_color(26, 60, 110)
            pdf.multi_cell(0, 8, _clean_md(stripped[3:]))
            pdf.ln(2)
            i += 1
            continue

        # Heading 3
        if stripped.startswith("### "):
            pdf.ln(2)
            pdf.set_font("DejaVu", "B", 11)
            pdf.set_text_color(51, 51, 51)
            pdf.multi_cell(0, 7, _clean_md(stripped[4:]))
            pdf.ln(1)
            i += 1
            continue

        # Checkbox items
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]") or stripped.startswith("- [X]"):
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(0, 0, 0)
            checked = "[x]" in stripped.lower()
            text = re.sub(r"^- \[.\]\s*", "", stripped)
            marker = "[X]" if checked else "[ ]"
            pdf.set_x(left_margin + 8)
            pdf.multi_cell(0, 6, f"{marker} {_clean_md(text)}")
            i += 1
            continue

        # Bullet points
        if stripped.startswith("- ") or stripped.startswith("* "):
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(0, 0, 0)
            text = stripped[2:]
            pdf.set_x(left_margin + 8)
            pdf.multi_cell(0, 6, f"  {_clean_md(text)}")
            i += 1
            continue

        # Numbered items
        num_match = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if num_match:
            pdf.set_font("DejaVu", "", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.set_x(left_margin + 8)
            pdf.multi_cell(0, 6, f"{num_match.group(1)}. {_clean_md(num_match.group(2))}")
            i += 1
            continue

        # Regular text (including bold lines)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 6, _clean_md(stripped))
        i += 1

    try:
        pdf.output(str(output_path))
    except OSError as exc:
        raise RuntimeError(f"Failed to write PDF {output_path.name}: {exc}") from exc


def save_policy_pdf(template_type: str, content: str, org_id: int) -> tuple[str, str]:
    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"{template_type}_{org_id}_{timestamp}.pdf"
    file_path = GENERATED_DIR / filename
    markdown_to_pdf(content, file_path)
    content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return str(file_path), content_hash


def generate_docx(template_type: str, context: dict, org_id: int) -> tuple[str, str]:
    """Generate DOCX from docxtpl if .docx template exists, otherwise fallback."""
    from app.config import BASE_DIR

    docx_template_path = BASE_DIR / "templates" / f"{template_type}.docx"

    if docx_template_path.exists():
        from docxtpl import DocxTemplate

        doc = DocxTemplate(str(docx_template_path))
        doc.render(context)
        timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"{template_type}_{org_id}_{timestamp}.docx"
        file_path = GENERATED_DIR / filename
        doc.save(str(file_path))
        content_bytes = file_path.read_bytes()
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        return str(file_path), content_hash

    # No DOCX template found — fall back to PDF instead of silently returning wrong format
    content = render_policy_text(template_type, context)
    return save_policy_pdf(template_type, content, org_id)


def generate_compliance_report_pdf(org_data: dict, compliance_result: dict, org_id: int) -> tuple[str, str]:
    """Generate a comprehensive branded PDF compliance report from scorecard results."""
    biz = org_data.get("business_name", "Organisation")
    industry = (org_data.get("industry") or "N/A").replace("_", " ").title()
    score = compliance_result["score_percentage"]
    risk = compliance_result["risk_rating"]
    passed = compliance_result["passed"]
    total = compliance_result["total"]
    penalty = compliance_result["penalty_exposure"]
    today = datetime.date.today().isoformat()
    contact = org_data.get("ai_governance_contact") or "To be appointed"

    lines = [
        "# AI Compliance Assessment Report",
        "",
        f"**Organisation:** {biz}",
        f"**Industry:** {industry}",
        f"**Employees:** {org_data.get('employee_count', 'N/A')}",
        f"**Annual Revenue:** {(org_data.get('annual_revenue') or 'N/A').replace('_', ' ').upper()}",
        f"**AI Governance Contact:** {contact}",
        f"**Assessment Date:** {today}",
        "**Report Version:** 1.0",
        "**Classification:** Confidential — For Internal Use Only",
        "",
        "---",
        "",
        "## Document Control",
        "",
        "| Field | Detail |",
        "|---|---|",
        f"| Prepared For | {biz} |",
        f"| Assessment Date | {today} |",
        "| Methodology | AI6 Essential Practices Framework |",
        "| Regulatory Scope | Privacy Act 1988, POLA Act 2024, ACL, AI Ethics Principles |",
        f"| Next Assessment Due | {(datetime.date.today() + datetime.timedelta(days=90)).isoformat()} |",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"{biz} operates in the {industry} sector with {org_data.get('employee_count', 'N/A')} employees "
        f"and currently uses {len(org_data.get('ai_tools_in_use', []))} approved AI tool(s). "
        f"This assessment evaluates the organisation's AI governance posture against the Australian Government's "
        f"AI6 Essential Practices framework and applicable regulatory requirements.",
        "",
        f"The assessment identified a **weighted compliance score of {score}%** with an overall risk rating of "
        f"**{risk}**. Of {total} compliance items assessed, {passed} were satisfied and {total - passed} require "
        f"remediation. The estimated maximum regulatory penalty exposure is **${penalty.get('total_maximum_exposure', 0):,.0f} AUD**.",
        "",
    ]

    # Risk summary paragraph
    if risk == "CRITICAL":
        lines.append(
            f"{biz} has minimal AI governance controls in place. Immediate action is required to reduce "
            "substantial regulatory exposure. The organisation faces significant risk under multiple "
            "Australian regulatory frameworks."
        )
    elif risk == "HIGH":
        lines.append(
            f"{biz} has significant governance gaps that must be addressed urgently. The organisation "
            "should prioritise critical remediation items before the POLA Act December 2026 deadline."
        )
    elif risk == "MEDIUM":
        lines.append(
            f"{biz} has moderate AI governance foundations but key gaps remain. Address critical items "
            "promptly and continue building governance maturity."
        )
    else:
        lines.append(
            f"{biz} demonstrates strong AI governance foundations. Continue monitoring regulatory "
            "developments and maintain current practices."
        )

    lines += [
        "",
        "---",
        "",
        "## 2. Assessment Methodology",
        "",
        "This compliance assessment is based on the following frameworks and regulations:",
        "",
        "- **AI6 Essential Practices** — The Australian Government's six essential practices for safe and responsible AI (Know Your AI, Be Accountable, Manage Risks, Be Transparent, Prioritise Safety & Fairness, Engage & Review)",
        "- **Privacy Act 1988 (Cth)** — Australian Privacy Principles (APPs), Notifiable Data Breaches scheme",
        "- **Privacy and Other Legislation Amendment (POLA) Act 2024** — Automated decision transparency (commences December 2026), statutory tort for serious invasion of privacy",
        "- **Australian Consumer Law (ACL)** — Sections 18, 29, 33 (misleading or deceptive conduct obligations for AI-generated content)",
        "- **OAIC AI Guidance (October 2024)** — Practical guidance on AI and privacy compliance",
        "- **Australia's 8 AI Ethics Principles** — Voluntary but increasingly referenced in regulatory enforcement",
        "",
        "Each compliance item is assigned a severity (Critical, High, Medium, Low) and a weight (1-10) reflecting "
        "regulatory significance. The weighted score accounts for the relative importance of each item.",
        "",
        "---",
        "",
        "## 3. Organisation AI Profile",
        "",
        "### 3.1 Approved AI Tools",
        "",
    ]

    for tool in org_data.get("ai_tools_in_use", []):
        lines.append(f"- {tool}")

    lines.append("")

    overseas = org_data.get("ai_tools_overseas", [])
    has_overseas = bool(overseas) and "None — all data stays in Australia" not in overseas
    if has_overseas:
        lines.append("### 3.2 Cross-Border Data Processing")
        lines.append("")
        lines.append("The following AI tools process data in overseas jurisdictions, triggering APP 8 obligations:")
        lines.append("")
        for tool in overseas:
            lines.append(f"- {tool}")
        lines.append("")

    lines.append("### 3.3 Data Types Processed")
    lines.append("")
    for dtype in org_data.get("data_types_processed", []):
        lines.append(f"- {dtype}")

    lines += [
        "",
        "### 3.4 Key Risk Indicators",
        "",
        "| Risk Factor | Status | Implication |",
        "|---|---|---|",
        f"| Privacy Act Coverage | {'Covered' if org_data.get('revenue_exceeds_threshold') or org_data.get('trades_in_personal_info') else 'Small Business Exemption'} | {'Full APP compliance required' if org_data.get('revenue_exceeds_threshold') else 'Statutory tort still applies'} |",
        f"| Shadow AI Awareness | {'Risk Identified' if org_data.get('shadow_ai_aware') and not org_data.get('shadow_ai_controls') else 'Controlled'} | {'Unapproved AI use without controls' if org_data.get('shadow_ai_aware') and not org_data.get('shadow_ai_controls') else 'Shadow AI managed'} |",
        f"| Customer-Facing AI | {'Yes' if org_data.get('customer_facing_ai') else 'No'} | {'ACL obligations apply' if org_data.get('customer_facing_ai') else 'N/A'} |",
        f"| Automated Decisions | {'Yes' if org_data.get('automated_decisions') else 'No'} | {'POLA Act disclosure required by Dec 2026' if org_data.get('automated_decisions') else 'N/A'} |",
        f"| Vendor DPAs | {'In Place' if org_data.get('vendor_dpa_in_place') else 'NOT in Place'} | {'Contractual protections established' if org_data.get('vendor_dpa_in_place') else 'APP 8 vicarious liability risk'} |",
        f"| PIA Conducted | {'Yes' if org_data.get('pia_conducted') else 'No'} | {'Privacy risks assessed' if org_data.get('pia_conducted') else 'Recommended by OAIC'} |",
        "",
        "---",
        "",
        "## 4. Compliance Score Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Weighted Compliance Score | {score}% |",
        f"| Items Passed | {passed}/{total} |",
        f"| Risk Rating | {risk} |",
        f"| Total Weight Earned | {compliance_result['earned_weight']}/{compliance_result['total_weight']} |",
        f"| Critical Gaps | {len(compliance_result['critical_gaps'])} |",
        f"| High Priority Gaps | {len(compliance_result['high_gaps'])} |",
        "",
        compliance_result["risk_description"],
        "",
        "---",
        "",
        "## 5. Estimated Maximum Penalty Exposure",
        "",
        f"**Total estimated maximum exposure: ${penalty['total_maximum_exposure']:,.0f} AUD**",
        "",
    ]

    penalty_regs = {
        "POLA Act non-compliance (Tier 1)": "POLA Act 2024",
        "Privacy Act interference (Tier 2)": "Privacy Act 1988 s 13G",
        "APP 8 cross-border non-compliance (Tier 2)": "Privacy Act APP 8, s 16C",
        "ACL misleading conduct risk": "ACL s 18, ss 54-56",
        "NDB scheme non-compliance (failure to notify)": "Privacy Act Part IIIC (NDB Scheme)",
        "Note": "N/A",
    }

    estimated_regs = {
        "Statutory tort — estimated damages (any organisation)": "POLA Act 2024 (court-determined damages)",
        "Shadow AI data breach cost — estimated (IBM 2025)": "IBM 2025 Cost of a Data Breach Report (scaled for AU SMEs)",
    }

    # Regulatory penalties table
    reg_items = penalty.get("regulatory_items", {})
    if reg_items:
        lines += [
            "### Regulatory Penalties (Enforceable Fines)",
            "",
            "Maximum statutory penalties based on current compliance posture. Actual penalties depend on "
            "the nature and severity of any breach.",
            "",
            "| Penalty Category | Maximum Amount (AUD) | Regulatory Basis |",
            "|---|---|---|",
        ]
        for item_name, amount in reg_items.items():
            if item_name == "Note":
                lines.append(f"| {item_name} | {amount} | N/A |")
            else:
                reg = penalty_regs.get(item_name, "Various")
                lines.append(f"| {item_name} | ${amount:,.0f} | {reg} |")

    # Estimated business costs table
    est_items = penalty.get("estimated_items", {})
    if est_items:
        lines += [
            "",
            "### Estimated Business Costs (Not Regulatory Fines)",
            "",
            "These are estimated costs based on industry research, not enforceable penalties. "
            "Actual amounts are determined by courts or vary by incident.",
            "",
            "| Cost Category | Estimated Amount (AUD) | Source |",
            "|---|---|---|",
        ]
        for item_name, amount in est_items.items():
            source = estimated_regs.get(item_name, "Various")
            lines.append(f"| {item_name} | ${amount:,.0f} | {source} |")

    # Penalty stacking warning
    stacking_note = penalty.get("stacking_note")
    if stacking_note:
        lines += ["", f"**{stacking_note}**"]

    if penalty["is_privacy_act_covered"]:
        lines.append("")
        lines.append(
            "The organisation is covered by the Privacy Act 1988 (annual revenue exceeds $3M "
            "or trades in personal information). Full Australian Privacy Principles compliance is required."
        )
    else:
        lines.append("")
        lines.append(
            "The small business exemption currently applies. However, the statutory tort for serious "
            "invasion of privacy applies to ALL organisations regardless of revenue. The exemption "
            "is under active review and may be removed under proposed reforms."
        )

    lines += [
        "",
        "---",
        "",
        "## 6. AI6 Essential Practices — Detailed Assessment",
        "",
        "The following sections detail compliance against each of the six AI6 Essential Practices.",
        "",
    ]

    for practice_name, practice_data in compliance_result["by_practice"].items():
        p = practice_data["passed"]
        t = practice_data["total"]
        pct = round((p / t) * 100) if t > 0 else 0
        lines.append(f"### {practice_name}")
        lines.append("")
        lines.append(f"**Score: {p}/{t} passed ({pct}%)**")
        lines.append("")
        lines.append("| # | Compliance Item | Status | Severity | Weight | Regulation |")
        lines.append("|---|---|---|---|---|---|")
        for idx, item in enumerate(practice_data["items"], 1):
            status = "PASS" if item["passed"] else "FAIL"
            sev = item["severity"].upper() if not item["passed"] else "-"
            lines.append(f"| {idx} | {item['name']} | {status} | {sev} | {item['weight']}/10 | {item['regulation']} |")
        lines.append("")

        # Add detailed findings for failed items
        failed = [item for item in practice_data["items"] if not item["passed"]]
        if failed:
            lines.append("**Findings:**")
            lines.append("")
            for item in failed:
                lines.append(
                    f"- **{item['name']}** ({item['severity'].upper()}): {item['description']} "
                    f"Recommendation: {item['recommendation']}"
                )
            lines.append("")

    # Gap analysis
    lines += ["---", "", "## 7. Priority Gap Analysis", ""]

    if compliance_result["critical_gaps"]:
        lines.append("### 7.1 Critical Gaps — Immediate Action Required")
        lines.append("")
        lines.append("These gaps represent the highest regulatory risk and must be addressed within 30 days.")
        lines.append("")
        lines.append("| # | Gap | Regulation | Severity | Recommended Action |")
        lines.append("|---|---|---|---|---|")
        for i, gap in enumerate(compliance_result["critical_gaps"], 1):
            lines.append(f"| {i} | {gap['name']} | {gap['regulation']} | CRITICAL | {gap['recommendation'][:60]}{'...' if len(gap['recommendation']) > 60 else ''} |")
        lines.append("")
        for i, gap in enumerate(compliance_result["critical_gaps"], 1):
            lines.append(f"**{i}. {gap['name']}**")
            lines.append(f"- Regulation: {gap['regulation']}")
            lines.append(f"- Action: {gap['recommendation']}")
            lines.append("- Timeline: Within 30 days")
            lines.append(f"- Owner: {contact}")
            lines.append("")

    if compliance_result["high_gaps"]:
        lines.append("### 7.2 High Priority Gaps")
        lines.append("")
        lines.append("These gaps carry significant risk and should be addressed within 60 days.")
        lines.append("")
        lines.append("| # | Gap | Regulation | Severity | Recommended Action |")
        lines.append("|---|---|---|---|---|")
        for i, gap in enumerate(compliance_result["high_gaps"], 1):
            lines.append(f"| {i} | {gap['name']} | {gap['regulation']} | HIGH | {gap['recommendation'][:60]}{'...' if len(gap['recommendation']) > 60 else ''} |")
        lines.append("")
        for i, gap in enumerate(compliance_result["high_gaps"], 1):
            lines.append(f"**{i}. {gap['name']}**")
            lines.append(f"- Regulation: {gap['regulation']}")
            lines.append(f"- Action: {gap['recommendation']}")
            lines.append("- Timeline: Within 60 days")
            lines.append(f"- Owner: {contact}")
            lines.append("")

    if not compliance_result["critical_gaps"] and not compliance_result["high_gaps"]:
        lines.append("No critical or high-priority gaps identified. Continue monitoring regulatory developments.")
        lines.append("")

    # Medium/low gaps
    medium_gaps = [
        item for item in compliance_result["checklist"] if not item["passed"] and item["severity"] == "medium"
    ]
    low_gaps = [item for item in compliance_result["checklist"] if not item["passed"] and item["severity"] == "low"]
    if medium_gaps or low_gaps:
        lines.append("### 7.3 Medium and Low Priority Items")
        lines.append("")
        for gap in medium_gaps + low_gaps:
            lines.append(f"- **{gap['name']}** ({gap['severity'].upper()}) — {gap['recommendation']}")
        lines.append("")

    # Regulatory timeline
    lines += [
        "---",
        "",
        "## 8. Regulatory Timeline and Key Dates",
        "",
        "| Date | Regulatory Event | Impact on Organisation |",
        "|---|---|---|",
        "| October 2024 | OAIC AI Guidance published | Establishes expectations for AI privacy compliance |",
        "| 2025 | Privacy Act Review - Tranche 2 | May remove small business exemption |",
        "| 10 December 2026 | POLA Act commences | Automated decision disclosure mandatory |",
        "| Ongoing | Statutory tort in effect | Civil liability for serious privacy invasion |",
        "| Ongoing | ACL obligations | Strict liability for misleading AI content |",
        "",
        "---",
        "",
        "## 9. Recommendations Summary",
        "",
        "Based on this assessment, the following actions are recommended in priority order:",
        "",
    ]

    all_gaps = compliance_result["critical_gaps"] + compliance_result["high_gaps"] + medium_gaps + low_gaps
    for i, gap in enumerate(all_gaps[:10], 1):
        lines.append(f"{i}. **{gap['name']}** ({gap['severity'].upper()}) — {gap['recommendation']}")
    lines.append("")

    lines += [
        "---",
        "",
        "## 10. Next Steps",
        "",
        "1. Review this report with senior management and the AI governance contact",
        "2. Generate a Remediation Action Plan for a detailed 30/60/90-day implementation roadmap",
        "3. Address critical gaps within 30 days",
        "4. Schedule a follow-up compliance assessment in 90 days",
        "5. Monitor regulatory developments, particularly POLA Act implementation guidance",
        "",
        "---",
        "",
        "## Appendix A: Glossary",
        "",
        "| Term | Definition |",
        "|---|---|",
        "| AI6 | Australian Government's 6 Essential Practices for safe and responsible AI |",
        "| APP | Australian Privacy Principle (under the Privacy Act 1988) |",
        "| ACL | Australian Consumer Law (Schedule 2, Competition and Consumer Act 2010) |",
        "| DPA | Data Processing Agreement (contractual obligations with AI vendors) |",
        "| NDB | Notifiable Data Breaches scheme (Privacy Act Part IIIC) |",
        "| OAIC | Office of the Australian Information Commissioner |",
        "| PIA | Privacy Impact Assessment |",
        "| POLA Act | Privacy and Other Legislation Amendment Act 2024 |",
        "| Shadow AI | Unapproved AI tools used without organisational oversight |",
        "",
        "---",
        "",
        f"*This report was generated on {today} by the AI Compliance Policy Generator.*",
        "*Assessment methodology: AI6 Essential Practices weighted compliance scoring.*",
        f"*This report is confidential and intended for {biz} internal use only.*",
        f"*Next assessment due: {(datetime.date.today() + datetime.timedelta(days=90)).isoformat()}*",
    ]

    md_content = "\n".join(lines)
    return save_policy_pdf("compliance_report", md_content, org_id)


def build_remediation_context(org_data: dict, compliance_result: dict) -> dict:
    """Map compliance gaps to 30/60/90-day timeline buckets."""
    today = datetime.date.today()
    owner = org_data.get("ai_governance_contact") or "AI Governance Lead (TBD)"

    critical_actions = []  # 30-day
    high_actions = []  # 60-day
    medium_actions = []  # 90-day
    quick_wins = []

    for item in compliance_result["checklist"]:
        if item["passed"]:
            continue

        action = {
            "name": item["name"],
            "description": item["recommendation"],
            "regulation": item["regulation"],
            "severity": item["severity"],
            "owner": owner,
        }

        # Quick wins: low weight or simple governance items
        if item["weight"] <= 4 or item["name"] in (
            "Existing IT security policies foundation",
            "Training frequency meets OAIC recommendation",
        ):
            action["deadline"] = (today + datetime.timedelta(days=14)).isoformat()
            quick_wins.append(action)
        elif item["severity"] == "critical":
            action["deadline"] = (today + datetime.timedelta(days=30)).isoformat()
            critical_actions.append(action)
        elif item["severity"] == "high":
            action["deadline"] = (today + datetime.timedelta(days=60)).isoformat()
            high_actions.append(action)
        else:
            action["deadline"] = (today + datetime.timedelta(days=90)).isoformat()
            medium_actions.append(action)

    return {
        **org_data,
        "effective_date": today.isoformat(),
        "version": "1.0",
        "score_percentage": compliance_result["score_percentage"],
        "risk_rating": compliance_result["risk_rating"],
        "risk_description": compliance_result["risk_description"],
        "passed": compliance_result["passed"],
        "total": compliance_result["total"],
        "critical_actions": critical_actions,
        "high_actions": high_actions,
        "medium_actions": medium_actions,
        "quick_wins": quick_wins,
        "deadline_30": (today + datetime.timedelta(days=30)).isoformat(),
        "deadline_60": (today + datetime.timedelta(days=60)).isoformat(),
        "deadline_90": (today + datetime.timedelta(days=90)).isoformat(),
        "next_assessment_date": (today + datetime.timedelta(days=90)).isoformat(),
        "owner": owner,
    }


def build_board_briefing_context(questionnaire_data: dict, policy_types: set[str]) -> dict:
    """Build context for board AI briefing template with policy status."""
    return {
        **questionnaire_data,
        "effective_date": datetime.date.today().isoformat(),
        "next_review_date": (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
        "version": "1.0",
        "policy_types": list(policy_types),
    }


def generate_policy(
    template_type: str,
    questionnaire_data: dict,
    org_id: int,
    output_format: str = "pdf",
    enhance_with_llm: bool = False,
) -> tuple[str, str]:
    context = build_template_context(questionnaire_data)
    content = render_policy_text(template_type, context)

    if enhance_with_llm:
        try:
            from app.llm_service import generate_policy_clauses

            llm_notes = generate_policy_clauses(template_type, questionnaire_data)
            if llm_notes and not llm_notes.startswith("("):
                content += "\n\n---\n\n## Regulatory Alignment Notes (AI-Generated)\n\n" + llm_notes
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("LLM enhancement failed (using template defaults): %s", exc)

    if output_format == "pdf":
        return save_policy_pdf(template_type, content, org_id)
    elif output_format == "docx":
        return generate_docx(template_type, context, org_id)
    else:
        return save_policy_markdown(template_type, content, org_id)
