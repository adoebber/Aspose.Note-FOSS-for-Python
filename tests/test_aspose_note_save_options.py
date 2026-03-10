from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import reportlab  # noqa: F401

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _fixture_path(name: str) -> Path | None:
    p = ROOT / "testfiles" / name
    return p if p.exists() else None


class TestAsposeNoteSaveOptions(unittest.TestCase):
    def test_pdf_save_options_roundtrip(self) -> None:
        from aspose.note import PdfSaveOptions, SaveFormat

        opts = PdfSaveOptions(SaveFormat.Pdf)
        self.assertEqual(opts.SaveFormat, SaveFormat.Pdf)


@unittest.skipUnless(HAS_REPORTLAB, "reportlab not installed")
class TestAsposeNoteSaveWithOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_save_pdf_with_pdfsaveoptions(self) -> None:
        from aspose.note import Document, PdfSaveOptions, SaveFormat

        doc = Document(self.path)
        buf = io.BytesIO()
        doc.Save(buf, PdfSaveOptions(SaveFormat.Pdf))
        #doc.Save("out.pdf", PdfSaveOptions(SaveFormat.Pdf))
        self.assertTrue(buf.getvalue().startswith(b"%PDF"))

    def test_pdf_writer_does_not_duplicate_rich_text(self) -> None:
        from aspose.note import Document, Page, PdfSaveOptions, RichText, SaveFormat, Title
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.drawn_strings: list[str] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append(text)

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        doc = Document()
        page = Page()
        title = Title()
        title.TitleText = title.AppendChildLast(RichText(Text="Title text"))
        title.TitleDate = title.AppendChildLast(RichText(Text="2025-01-01"))
        title.TitleTime = title.AppendChildLast(RichText(Text="10:00"))
        page.Title = title
        page.AppendChildLast(title)
        page.AppendChildLast(RichText(Text="Body text"))
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        self.assertEqual(len(FakeCanvas.instances), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("Title text"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("2025-01-01"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("10:00"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("Body text"), 1)


class TestAsposeNoteSaveUnsupportedFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_save_one_raises(self) -> None:
        from aspose.note import Document, SaveFormat, UnsupportedSaveFormatException

        doc = Document(self.path)
        with self.assertRaises(UnsupportedSaveFormatException):
            doc.Save(io.BytesIO(), SaveFormat.One)
