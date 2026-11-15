"""One-page PDF receipts. The payment row is the source of the numbers."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def build_receipt(
    *,
    branch_name: str,
    receipt_no: str,
    student_name: str,
    admission_no: str,
    invoice_no: str,
    amount: str,
    method: str,
    paid_on: str,
    status: str,
) -> bytes:
    """Render a receipt. A voided payment still prints, with its status on the page."""
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=f"Receipt {receipt_no}")
    styles = getSampleStyleSheet()
    story = [
        Paragraph(branch_name, styles["Title"]),
        Paragraph(f"Receipt {receipt_no}", styles["Heading2"]),
        Spacer(1, 12),
        Paragraph(f"Student: {student_name} ({admission_no})", styles["Normal"]),
        Paragraph(f"Invoice: {invoice_no}", styles["Normal"]),
        Paragraph(f"Amount: {amount}", styles["Normal"]),
        Paragraph(f"Method: {method}", styles["Normal"]),
        Paragraph(f"Paid on: {paid_on}", styles["Normal"]),
        Paragraph(f"Status: {status}", styles["Normal"]),
    ]
    document.build(story)
    return buffer.getvalue()
