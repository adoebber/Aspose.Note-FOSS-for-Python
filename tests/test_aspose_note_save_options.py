from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

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
                self.font_calls: list[tuple[str, float]] = []
                self.fill_colors: list[tuple[float, float, float]] = []
                self.stroke_colors: list[tuple[float, float, float]] = []
                self.rect_calls: list[tuple[float, float, float, float, int, int]] = []
                self.line_calls: list[tuple[float, float, float, float]] = []
                self.link_calls: list[tuple[str, tuple[float, float, float, float], int]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                self.font_calls.append((name, size))

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append(text)

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                self.fill_colors.append((r, g, b))

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                self.stroke_colors.append((r, g, b))

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                self.rect_calls.append((x, y, width, height, stroke, fill))

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                self.line_calls.append((x1, y1, x2, y2))

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                self.link_calls.append((url, rect, relative))

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

    def test_pdf_writer_applies_rich_text_run_styles(self) -> None:
        from aspose.note import Document, Page, PdfSaveOptions, RichText, SaveFormat, TextRun, TextStyle
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.drawn_strings: list[str] = []
                self.font_calls: list[tuple[str, float]] = []
                self.fill_colors: list[tuple[float, float, float]] = []
                self.stroke_colors: list[tuple[float, float, float]] = []
                self.rect_calls: list[tuple[float, float, float, float, int, int]] = []
                self.line_calls: list[tuple[float, float, float, float]] = []
                self.link_calls: list[tuple[str, tuple[float, float, float, float], int]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                self.font_calls.append((name, size))

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append(text)

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                self.fill_colors.append((r, g, b))

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                self.stroke_colors.append((r, g, b))

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                self.rect_calls.append((x, y, width, height, stroke, fill))

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                self.line_calls.append((x1, y1, x2, y2))

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                self.link_calls.append((url, rect, relative))

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        styled = RichText(Text="Bold Blue")
        styled.Runs = [
            TextRun(
                Text="Bold",
                Style=TextStyle(Bold=True, FontColor=0x0000FF, HighlightColor=0xFFFF00, Underline=True),
                Start=0,
                End=4,
            ),
            TextRun(
                Text=" Blue",
                Style=TextStyle(Italic=True, FontName="Times New Roman", FontSize=14.0),
                Start=4,
                End=9,
            ),
        ]

        doc = Document()
        page = Page()
        page.AppendChildLast(styled)
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        canvas = FakeCanvas.instances[0]
        self.assertEqual(canvas.drawn_strings.count("Bold"), 1)
        self.assertEqual(canvas.drawn_strings.count(" Blue"), 1)
        self.assertTrue(any(size == 14 and "Italic" in name for name, size in canvas.font_calls))
        self.assertTrue(any(size == 11.0 and "Bold" in name for name, size in canvas.font_calls))
        self.assertIn((1.0, 0.0, 0.0), canvas.fill_colors)
        self.assertIn((0.0, 1.0, 1.0), canvas.fill_colors)
        self.assertTrue(canvas.rect_calls)
        self.assertTrue(canvas.line_calls)

    def test_pdf_writer_preserves_spaces_and_inline_metadata(self) -> None:
        from aspose.note import Document, Page, PdfSaveOptions, RichText, SaveFormat, Title
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.drawn_strings: list[tuple[int, int, str]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append((x, y, text))

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                return None

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                return None

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                return None

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        doc = Document()
        page = Page()
        title = Title()
        title.TitleText = title.AppendChildLast(RichText(Text="One hyperlink"))
        title.TitleDate = title.AppendChildLast(RichText(Text="2025-01-01"))
        title.TitleTime = title.AppendChildLast(RichText(Text="13:12"))
        page.Title = title
        page.AppendChildLast(title)
        page.AppendChildLast(RichText(Text="This is hyperlink."))
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        canvas = FakeCanvas.instances[0]
        texts = [text for _, _, text in canvas.drawn_strings]
        self.assertIn("One hyperlink", texts)
        self.assertIn("This is hyperlink.", texts)

        date_call = next(item for item in canvas.drawn_strings if item[2] == "2025-01-01")
        time_call = next(item for item in canvas.drawn_strings if item[2] == "13:12")
        self.assertEqual(date_call[1], time_call[1])
        self.assertGreater(time_call[0], date_call[0])

    def test_pdf_writer_skips_internal_hyperlink_markup(self) -> None:
        from aspose.note import Document, PdfSaveOptions, SaveFormat
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

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                return None

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                return None

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                return None

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        doc = Document(self.path)
        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        rendered_text = "".join(FakeCanvas.instances[0].drawn_strings)
        self.assertNotIn("HYPERLINK", rendered_text)
        self.assertNotIn("\ufddf", rendered_text)

    def test_pdf_writer_creates_clickable_hyperlinks(self) -> None:
        from aspose.note import Document, PdfSaveOptions, SaveFormat
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.drawn_strings: list[str] = []
                self.link_calls: list[tuple[str, tuple[float, float, float, float], int]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append(text)

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                return None

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                return None

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                self.link_calls.append((url, rect, relative))

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        doc = Document(self.path)
        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        canvas = FakeCanvas.instances[0]
        self.assertTrue(canvas.link_calls)
        self.assertTrue(any(url == "https://www.google.com" for url, _, _ in canvas.link_calls))

    def test_pdf_writer_applies_default_hyperlink_style(self) -> None:
        from aspose.note import Document, PdfSaveOptions, SaveFormat
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.drawn_strings: list[str] = []
                self.fill_colors: list[tuple[float, float, float]] = []
                self.line_calls: list[tuple[float, float, float, float]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                self.drawn_strings.append(text)

            def setFillColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                self.fill_colors.append((r, g, b))

            def setStrokeColorRGB(self, r: float, g: float, b: float) -> None:  # noqa: N802
                return None

            def rect(self, x: float, y: float, width: float, height: float, stroke: int = 0, fill: int = 0) -> None:
                return None

            def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
                self.line_calls.append((x1, y1, x2, y2))

            def stringWidth(self, text: str, font_name: str, font_size: float) -> float:  # noqa: N802
                return len(text) * font_size * 0.55

            def drawImage(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, N802
                return None

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                return None

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        doc = Document(self.path)
        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions(SaveFormat.Pdf))

        canvas = FakeCanvas.instances[0]
        self.assertIn("hyperlink", canvas.drawn_strings)
        self.assertIn((0.0, 0.2, 0.65), canvas.fill_colors)
        self.assertTrue(canvas.line_calls)

    def test_pdf_writer_uses_base14_fonts_by_default(self) -> None:
        from aspose.note.saving.pdf_writer import _register_font_variant

        self.assertEqual(_register_font_variant("sans", False, False), "Helvetica")
        self.assertEqual(_register_font_variant("serif", False, True), "Times-Italic")

    def test_pdf_writer_uses_unicode_font_for_cyrillic(self) -> None:
        from aspose.note.saving.pdf_writer import _REGISTERED_FONT_NAMES, _font_name_for_style

        style = SimpleNamespace(FontName=None, Bold=False, Italic=False)
        _REGISTERED_FONT_NAMES.clear()
        self.addCleanup(_REGISTERED_FONT_NAMES.clear)

        with patch("aspose.note.saving.pdf_writer._find_font_file", return_value=("DejaVuSans", Path("/tmp/DejaVuSans.ttf"))), patch(
            "reportlab.pdfbase.pdfmetrics.getRegisteredFontNames", return_value=[]
        ), patch("reportlab.pdfbase.pdfmetrics.registerFont") as register_font, patch("reportlab.pdfbase.ttfonts.TTFont") as ttfont:
            font_name = _font_name_for_style(style, "Arial", text="Привет")

        self.assertEqual(font_name, "DejaVuSans")
        ttfont.assert_called_once()
        self.assertEqual(ttfont.call_args.args[0], "DejaVuSans")
        self.assertTrue(str(ttfont.call_args.args[1]).endswith("DejaVuSans.ttf"))
        register_font.assert_called_once()


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
