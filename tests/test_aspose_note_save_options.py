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
    def test_save_options_is_abstract_compatibility_base(self) -> None:
        from aspose.note import SaveFormat
        from aspose.note.saving import SaveOptions

        with self.assertRaises(TypeError):
            SaveOptions(SaveFormat.Pdf)

    def test_root_namespace_does_not_export_save_options(self) -> None:
        import aspose.note

        self.assertFalse(hasattr(aspose.note, "SaveOptions"))
        self.assertFalse(hasattr(aspose.note, "PdfSaveOptions"))

    def test_pdf_save_options_roundtrip(self) -> None:
        from aspose.note import SaveFormat
        from aspose.note.saving import PdfSaveOptions

        opts = PdfSaveOptions()
        self.assertEqual(opts.SaveFormat, SaveFormat.Pdf)
        self.assertEqual(opts.PageIndex, 0)
        self.assertIsNone(opts.PageCount)
        self.assertFalse(hasattr(opts, "TagIconDir"))
        self.assertFalse(hasattr(opts, "TagIconSize"))
        self.assertFalse(hasattr(opts, "TagIconGap"))

    def test_save_format_exports_only_pdf(self) -> None:
        from aspose.note import SaveFormat

        self.assertEqual(list(SaveFormat), [SaveFormat.Pdf])

    def test_save_options_expose_common_base_properties(self) -> None:
        from aspose.note import SaveFormat
        from aspose.note.saving import PdfSaveOptions

        opts = PdfSaveOptions(PageIndex=2, PageCount=3, FontsSubsystem="fonts-subsystem")
        self.assertEqual(opts.SaveFormat, SaveFormat.Pdf)
        self.assertEqual(opts.PageIndex, 2)
        self.assertEqual(opts.PageCount, 3)
        self.assertEqual(opts.FontsSubsystem, "fonts-subsystem")

    def test_save_format_is_read_only(self) -> None:
        from aspose.note import SaveFormat
        from aspose.note.saving import PdfSaveOptions

        opts = PdfSaveOptions()

        with self.assertRaises(AttributeError):
            setattr(opts, "SaveFormat", SaveFormat.Pdf)


@unittest.skipUnless(HAS_REPORTLAB, "reportlab not installed")
class TestAsposeNoteSaveWithOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_save_pdf_with_pdfsaveoptions(self) -> None:
        from aspose.note import Document
        from aspose.note.saving import PdfSaveOptions

        doc = Document(self.path)
        buf = io.BytesIO()
        doc.Save(buf, PdfSaveOptions())
        self.assertTrue(buf.getvalue().startswith(b"%PDF"))

    def test_save_pdf_infers_format_from_path_extension(self) -> None:
        from aspose.note import Document

        doc = Document(self.path)
        output = Path("tests/out/pdf_export/inferred_extension_save.pdf")
        output.parent.mkdir(parents=True, exist_ok=True)
        self.addCleanup(output.unlink, missing_ok=True)

        doc.Save(output)

        self.assertTrue(output.read_bytes().startswith(b"%PDF"))

    def test_pdf_writer_renders_note_tags(self) -> None:
        from aspose.note import Document, NoteTag, Page, RichText
        from aspose.note.saving import PdfSaveOptions
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

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        tagged = RichText(Text="Tagged body")
        tagged.Tags.extend(
            [
            NoteTag.CreateYellowStar("Важно"),
            NoteTag.CreateQuestionMark("Вопрос"),
            NoteTag.CreateMusicalNote("Послушать музыку"),
            ]
        )

        doc = Document()
        page = Page()
        page.AppendChildLast(tagged)
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions())

        canvas = FakeCanvas.instances[0]
        self.assertIn("Tagged body", canvas.drawn_strings)
        self.assertTrue(canvas.rect_calls)
        self.assertTrue(canvas.line_calls)

    def test_pdf_writer_renders_tags_in_visual_reverse_order(self) -> None:
        from aspose.note import Document, NoteTag, Page, RichText
        from aspose.note.saving import PdfSaveOptions
        from aspose.note.saving import pdf_writer

        class FakeCanvas:
            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                return None

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

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        tagged = RichText(Text="Tagged body")
        tagged.Tags.extend(
            [
            NoteTag.CreateYellowStar("Важно"),
            NoteTag.CreateQuestionMark("Вопрос"),
            NoteTag.CreateMusicalNote("Послушать музыку"),
            ]
        )

        doc = Document()
        page = Page()
        page.AppendChildLast(tagged)
        doc.AppendChildLast(page)

        rendered_shapes: list[int | None] = []

        def _capture_tag(pdf, tag, x: float, baseline_y: float, options):
            rendered_shapes.append(getattr(tag, "Icon", None))
            return 10.0

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas), patch.object(pdf_writer, "_render_note_tag", side_effect=_capture_tag):
            pdf_writer.write_pdf(doc, PdfSaveOptions())

        self.assertEqual(rendered_shapes, [121, 15, 13])

    def test_question_tag_uses_distinct_color(self) -> None:
        from aspose.note.saving.pdf_writer import _tag_color

        self.assertEqual(_tag_color(15), (0.64, 0.32, 0.82))
        self.assertNotEqual(_tag_color(15), _tag_color(13))

    def test_pdf_writer_does_not_duplicate_rich_text(self) -> None:
        from aspose.note import Document, Page, RichText, Title
        from aspose.note.saving import PdfSaveOptions
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
        title.TitleText = RichText(Text="Title text")
        title.TitleDate = RichText(Text="2025-01-01")
        title.TitleTime = RichText(Text="10:00")
        page.Title = title
        page.AppendChildLast(title)
        page.AppendChildLast(RichText(Text="Body text"))
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions())

        self.assertEqual(len(FakeCanvas.instances), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("Title text"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("2025-01-01"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("10:00"), 1)
        self.assertEqual(FakeCanvas.instances[0].drawn_strings.count("Body text"), 1)

    def test_pdf_writer_applies_rich_text_run_styles(self) -> None:
        from aspose.note import Document, Page, RichText, TextRun, TextStyle
        from aspose.note.saving import PdfSaveOptions
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

        styled = RichText(
            TextRuns=[
            TextRun(
                Text="Bold",
                Style=TextStyle(IsBold=True, FontColor=0x0000FF, Highlight=0xFFFF00, IsUnderline=True),
            ),
            TextRun(
                Text=" Blue",
                Style=TextStyle(IsItalic=True, FontName="Times New Roman", FontSize=14.0),
            ),
            ]
        )

        doc = Document()
        page = Page()
        page.AppendChildLast(styled)
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions())

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
        from aspose.note import Document, Page, RichText, Title
        from aspose.note.saving import PdfSaveOptions
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
        title.TitleText = RichText(Text="One hyperlink")
        title.TitleDate = RichText(Text="2025-01-01")
        title.TitleTime = RichText(Text="13:12")
        page.Title = title
        page.AppendChildLast(title)
        page.AppendChildLast(RichText(Text="This is hyperlink."))
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas):
            write_pdf(doc, PdfSaveOptions())

        canvas = FakeCanvas.instances[0]
        texts = [text for _, _, text in canvas.drawn_strings]
        self.assertIn("One hyperlink", texts)
        self.assertIn("This is hyperlink.", texts)

        date_call = next(item for item in canvas.drawn_strings if item[2] == "2025-01-01")
        time_call = next(item for item in canvas.drawn_strings if item[2] == "13:12")
        self.assertEqual(date_call[1], time_call[1])
        self.assertGreater(time_call[0], date_call[0])

    def test_pdf_writer_converts_image_size_from_centimeters_to_points(self) -> None:
        from aspose.note import Document, Image, Page
        from aspose.note.saving import PdfSaveOptions
        from aspose.note.saving.pdf_writer import write_pdf

        class FakeCanvas:
            instances: list["FakeCanvas"] = []

            def __init__(self, buffer: io.BytesIO) -> None:
                self._buffer = buffer
                self._pagesize = (595, 842)
                self.image_calls: list[tuple[object, float, float, float, float, bool, str]] = []
                FakeCanvas.instances.append(self)

            def setFont(self, name: str, size: int) -> None:  # noqa: N802
                return None

            def drawString(self, x: int, y: int, text: str) -> None:  # noqa: N802
                return None

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

            def drawImage(self, image, x: float, y: float, width: float, height: float, preserveAspectRatio: bool, mask: str) -> None:  # noqa: N802
                self.image_calls.append((image, x, y, width, height, preserveAspectRatio, mask))

            def linkURL(self, url: str, rect: tuple[float, float, float, float], relative: int = 0) -> None:  # noqa: N802
                return None

            def showPage(self) -> None:  # noqa: N802
                return None

            def save(self) -> None:
                self._buffer.write(b"%PDF-fake")

        class FakeImageReader:
            def __init__(self, source) -> None:
                self.source = source

            def getSize(self) -> tuple[int, int]:  # noqa: N802
                return (1024, 768)

        doc = Document()
        page = Page()
        page.AppendChildLast(Image(Bytes=b"image-bytes", Width=10.0, Height=5.0))
        doc.AppendChildLast(page)

        with patch("reportlab.pdfgen.canvas.Canvas", FakeCanvas), patch("reportlab.lib.utils.ImageReader", FakeImageReader):
            write_pdf(doc, PdfSaveOptions())

        canvas = FakeCanvas.instances[0]
        self.assertEqual(len(canvas.image_calls), 1)
        _, x, y, width, height, preserve_aspect_ratio, mask = canvas.image_calls[0]
        self.assertEqual(x, 40)
        self.assertAlmostEqual(y, 842 - 40 - (5.0 * 28.35), places=2)
        self.assertAlmostEqual(width, 10.0 * 28.35, places=2)
        self.assertAlmostEqual(height, 5.0 * 28.35, places=2)
        self.assertTrue(preserve_aspect_ratio)
        self.assertEqual(mask, "auto")

    def test_pdf_writer_skips_internal_hyperlink_markup(self) -> None:
        from aspose.note import Document
        from aspose.note.saving import PdfSaveOptions
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
            write_pdf(doc, PdfSaveOptions())

        rendered_text = "".join(FakeCanvas.instances[0].drawn_strings)
        self.assertNotIn("HYPERLINK", rendered_text)
        self.assertNotIn("\ufddf", rendered_text)

    def test_pdf_writer_creates_clickable_hyperlinks(self) -> None:
        from aspose.note import Document
        from aspose.note.saving import PdfSaveOptions
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
            write_pdf(doc, PdfSaveOptions())

        canvas = FakeCanvas.instances[0]
        self.assertTrue(canvas.link_calls)
        self.assertTrue(any(url == "https://www.google.com" for url, _, _ in canvas.link_calls))

    def test_pdf_writer_applies_default_hyperlink_style(self) -> None:
        from aspose.note import Document
        from aspose.note.saving import PdfSaveOptions
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
            write_pdf(doc, PdfSaveOptions())

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

        style = SimpleNamespace(FontName=None, IsBold=False, IsItalic=False)
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

    def test_save_non_pdf_path_raises(self) -> None:
        from aspose.note import Document, UnsupportedSaveFormatException

        doc = Document(self.path)
        with self.assertRaises(UnsupportedSaveFormatException):
            doc.Save("unsupported-output.one")
