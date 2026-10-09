"""
Converts report/PROJECT_REPORT.md into a professional, submission-ready PDF
using fpdf2 with complete character sanitization.
"""

from pathlib import Path
import re
import unicodedata
from fpdf import FPDF


def sanitize(text: str) -> str:
    """Sanitize unicode characters for standard PDF fonts."""
    replacements = {
        "\u2013": "-",
        "\u2014": "--",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "\u2192": "->",
        "\u2190": "<-",
        "\u2194": "<->",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u00d7": "x",
        "\u223c": "~",
        "\u2211": "sum",
        "\u221a": "sqrt",
        "\u03bc": "mu",
        "\u03c3": "sigma",
        "\u0394": "Delta",
        "\u2208": "in",
        "\u211d": "R",
        chr(149): "*",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"\$+(.*?)\$+", r"\1", text)
    text = text.replace(r"\mathbf{", "").replace(r"\text{", "").replace("}", "")
    return unicodedata.normalize("NFKD", text).encode("latin-1", "ignore").decode("latin-1")


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("helvetica", "I", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 8, "CSE3010 Computer Vision - Project Report | Soham Singh Mehra", 0, 0, "L")
            self.cell(0, 8, f"Page {self.page_no()}", 0, 1, "R")
            self.set_draw_color(210, 210, 210)
            self.line(10, 16, 200, 16)
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, "Intelligent Traffic Surveillance & Vehicle Analytics - VITyarthi Evaluation", 0, 0, "C")


def build_pdf():
    md_path = Path("report/PROJECT_REPORT.md")
    pdf_path = Path("report/PROJECT_REPORT.pdf")

    if not md_path.is_file():
        print(f"Error: {md_path} not found.")
        return

    content = md_path.read_text(encoding="utf-8")

    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(12, 12, 12)

    lines = content.split("\n")
    in_code_block = False
    code_lines = []

    for line in lines:
        pdf.set_x(12)
        line_clean = sanitize(line.strip())

        # Code block handling
        if line_clean.startswith("```"):
            if in_code_block:
                in_code_block = False
                pdf.set_font("courier", "", 7.0)
                pdf.set_fill_color(245, 245, 248)
                pdf.set_text_color(30, 30, 30)
                code_text = "\n".join(code_lines)
                pdf.multi_cell(0, 3.8, code_text, border=1, fill=True)
                pdf.ln(2)
                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(sanitize(line))
            continue

        # Skip horizontal dividers
        if line_clean == "---":
            pdf.ln(1)
            pdf.set_draw_color(220, 220, 225)
            pdf.line(12, pdf.get_y(), 198, pdf.get_y())
            pdf.ln(3)
            continue

        # Headings
        if line_clean.startswith("# "):
            pdf.set_font("helvetica", "B", 16)
            pdf.set_text_color(20, 45, 85)
            clean_title = sanitize(line_clean[2:].strip())
            pdf.multi_cell(0, 8, clean_title)
            pdf.ln(2)
            continue

        if line_clean.startswith("## "):
            pdf.ln(2)
            pdf.set_font("helvetica", "B", 12.0)
            pdf.set_text_color(30, 65, 125)
            clean_h2 = sanitize(line_clean[3:].strip())
            pdf.multi_cell(0, 6.5, clean_h2)
            pdf.ln(1)
            continue

        if line_clean.startswith("### "):
            pdf.ln(1)
            pdf.set_font("helvetica", "B", 10.0)
            pdf.set_text_color(40, 80, 140)
            clean_h3 = sanitize(line_clean[4:].strip())
            pdf.multi_cell(0, 5.5, clean_h3)
            pdf.ln(1)
            continue

        # Tables (Markdown format)
        if line_clean.startswith("|") and line_clean.endswith("|"):
            if "---" in line_clean:
                continue
            cells = [c.strip() for c in line_clean.strip("|").split("|")]
            pdf.set_font("helvetica", "", 8.0)
            pdf.set_text_color(30, 30, 30)
            col_w = (198 - 12) / max(1, len(cells))
            for cell in cells:
                clean_cell = sanitize(cell.replace("**", "").replace("`", ""))
                pdf.cell(col_w, 5.2, clean_cell[:45], border=1)
            pdf.ln()
            continue

        # Image skip
        if line_clean.startswith("!["):
            continue

        # Bullet points
        if line_clean.startswith("- ") or line_clean.startswith("* "):
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_text_color(35, 35, 35)
            bullet_text = line_clean[2:].strip()
            bullet_text = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_text)
            bullet_text = re.sub(r"`(.*?)`", r"\1", bullet_text)
            bullet_text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", bullet_text)
            pdf.multi_cell(0, 4.4, f"  * {sanitize(bullet_text)}")
            continue

        # Numbered list
        num_match = re.match(r"^(\d+)\.\s+(.*)", line_clean)
        if num_match:
            pdf.set_font("helvetica", "", 8.5)
            pdf.set_text_color(35, 35, 35)
            num_str = num_match.group(1)
            item_text = num_match.group(2)
            item_text = re.sub(r"\*\*(.*?)\*\*", r"\1", item_text)
            item_text = re.sub(r"`(.*?)`", r"\1", item_text)
            item_text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", item_text)
            pdf.multi_cell(0, 4.4, f"  {num_str}. {sanitize(item_text)}")
            continue

        # Regular paragraphs
        if line_clean:
            pdf.set_font("helvetica", "", 9)
            pdf.set_text_color(40, 40, 40)
            clean_para = re.sub(r"\*\*(.*?)\*\*", r"\1", line_clean)
            clean_para = re.sub(r"`(.*?)`", r"\1", clean_para)
            clean_para = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", clean_para)
            pdf.multi_cell(0, 4.6, sanitize(clean_para))
            pdf.ln(1)

    pdf.output(str(pdf_path))
    print(f"Successfully generated: {pdf_path.resolve()} ({pdf_path.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
