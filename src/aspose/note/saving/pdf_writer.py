from __future__ import annotations

from io import BytesIO

from .options import PdfSaveOptions


def write_pdf(document, options: PdfSaveOptions) -> bytes:
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab") from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    width, height = pdf._pagesize

    pages = list(document)
    start = max(options.PageIndex, 0)
    selected = pages[start : start + options.PageCount if options.PageCount is not None else None]
    if not selected:
        selected = [None]

    for index, page in enumerate(selected):
        cursor_y = height - 40
        if page is not None:
            title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else document.DisplayName or "OneNote"
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(40, cursor_y, title[:120])
            cursor_y -= 28

            from ..model import Image, RichText, Table, TableCell

            for rich_text in page.GetChildNodes(RichText):
                if page.Title and page.Title.TitleText is rich_text:
                    continue
                text = rich_text.Text.strip()
                if not text:
                    continue
                pdf.setFont("Helvetica", 11)
                for line in text.splitlines() or [text]:
                    if cursor_y < 80:
                        pdf.showPage()
                        cursor_y = height - 40
                        pdf.setFont("Helvetica", 11)
                    pdf.drawString(40, cursor_y, line[:150])
                    cursor_y -= 15

            for table in page.GetChildNodes(Table):
                if cursor_y < 80:
                    pdf.showPage()
                    cursor_y = height - 40
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(40, cursor_y, "Table")
                cursor_y -= 16
                pdf.setFont("Helvetica", 10)
                for row in table:
                    cell_texts: list[str] = []
                    for cell in row:
                        texts = [rt.Text.strip() for rt in cell.GetChildNodes(RichText) if rt.Text.strip()]
                        cell_texts.append(" | ".join(texts))
                    pdf.drawString(50, cursor_y, " || ".join(cell_texts)[:150])
                    cursor_y -= 14

            for image in page.GetChildNodes(Image):
                if not image.Bytes:
                    continue
                if cursor_y < 180:
                    pdf.showPage()
                    cursor_y = height - 40
                try:
                    img = ImageReader(BytesIO(bytes(image.Bytes)))
                    draw_width = min(220, image.Width or 220)
                    draw_height = min(160, image.Height or 160)
                    pdf.drawImage(img, 40, max(40, cursor_y - draw_height), width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
                    cursor_y -= draw_height + 12
                except Exception:
                    pdf.setFont("Helvetica-Oblique", 10)
                    pdf.drawString(40, cursor_y, image.FileName or "[image]")
                    cursor_y -= 14

            if index != len(selected) - 1:
                pdf.showPage()
        else:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(40, cursor_y, document.DisplayName or "Empty document")

    pdf.save()
    return buffer.getvalue()