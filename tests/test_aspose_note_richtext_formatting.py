from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _fixture_path(name: str) -> Path | None:
    p = ROOT / "testfiles" / name
    return p if p.exists() else None


class TestAsposeNoteRichTextFormatting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_richtext_runs_preserved(self) -> None:
        from aspose.note import Document, RichText

        doc = Document(self.path)
        rts = doc.GetChildNodes(RichText)
        self.assertGreater(len(rts), 0)

        # At least one RichText node should carry extracted formatting runs.
        self.assertTrue(any(len(rt.TextRuns) > 0 for rt in rts))

    def test_richtext_has_some_non_default_style(self) -> None:
        from aspose.note import Document, RichText

        doc = Document(self.path)
        rts = doc.GetChildNodes(RichText)

        # Look for any run with a meaningful style attribute.
        def is_styled(rt: RichText) -> bool:
            for run in rt.TextRuns:
                s = run.Style
                if (
                    s.IsBold
                    or s.IsItalic
                    or s.IsUnderline
                    or s.IsStrikethrough
                    or s.IsSuperscript
                    or s.IsSubscript
                    or (s.FontName is not None)
                    or (s.FontSize is not None)
                    or (s.FontColor is not None)
                    or (s.Highlight is not None)
                    or (s.HyperlinkAddress is not None)
                ):
                    return True
            return False

        if not any(rt.TextRuns for rt in rts):
            raise unittest.SkipTest("No RichText nodes with runs extracted")

        self.assertTrue(any(is_styled(rt) for rt in rts))

    def test_textstyle_uses_dotnet_property_names_only(self) -> None:
        from aspose.note import TextStyle

        style = TextStyle.Default
        style.IsBold = True
        style.IsItalic = True
        style.IsUnderline = True
        style.IsStrikethrough = True
        style.IsSuperscript = True
        style.IsSubscript = True
        style.Highlight = 123
        style.Language = 1031

        self.assertFalse(hasattr(style, "Bold"))
        self.assertFalse(hasattr(style, "Italic"))
        self.assertFalse(hasattr(style, "Underline"))
        self.assertFalse(hasattr(style, "Strikethrough"))
        self.assertFalse(hasattr(style, "Superscript"))
        self.assertFalse(hasattr(style, "Subscript"))
        self.assertFalse(hasattr(style, "HighlightColor"))
        self.assertFalse(hasattr(style, "HorizontalAlignment"))
        self.assertFalse(hasattr(style, "LanguageId"))
        self.assertEqual(style.Highlight, 123)
        self.assertEqual(style.Language, 1031)

    def test_textstyle_rejects_legacy_keyword_aliases(self) -> None:
        from aspose.note import TextStyle

        for kwargs in (
            {"Bold": True},
            {"Italic": True},
            {"Underline": True},
            {"Strikethrough": True},
            {"Superscript": True},
            {"Subscript": True},
            {"HighlightColor": 123},
            {"LanguageId": 1031},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(TypeError):
                    TextStyle(**kwargs)

    def test_richtext_stores_alignment_on_richtext(self) -> None:
        from aspose.note import HorizontalAlignment, ParagraphStyle, RichText

        with self.assertRaises(TypeError):
            ParagraphStyle(Alignment=HorizontalAlignment.Center)

        paragraph_style = ParagraphStyle()
        rich_text = RichText(Text="Aligned", ParagraphStyle=paragraph_style, Alignment=HorizontalAlignment.Center)

        self.assertEqual(rich_text.Alignment, HorizontalAlignment.Center)
        self.assertFalse(hasattr(rich_text.ParagraphStyle, "Alignment"))

    def test_paragraphstyle_exposes_default_text_properties(self) -> None:
        from aspose.note import ParagraphStyle

        style = ParagraphStyle.Default
        style.FontName = "Courier New"
        style.FontSize = 20.0
        style.FontColor = 0x112233
        style.Highlight = 0xAABBCC
        style.IsBold = True
        style.IsItalic = True
        style.IsUnderline = True
        style.IsStrikethrough = True
        style.IsSuperscript = True
        style.IsSubscript = True

        self.assertEqual(style.FontName, "Courier New")
        self.assertEqual(style.FontSize, 20.0)
        self.assertEqual(style.FontColor, 0x112233)
        self.assertEqual(style.Highlight, 0xAABBCC)
        self.assertEqual(style.FontStyle, 15)
        self.assertFalse(hasattr(style, "Alignment"))
        self.assertFalse(hasattr(style, "Language"))

    def test_richtext_uses_paragraphstyle_as_default_text_style(self) -> None:
        from aspose.note import ParagraphStyle, RichText

        paragraph_style = ParagraphStyle(FontName="Courier New", FontSize=20.0, IsBold=True, Highlight=0xFFFF00)
        rich_text = RichText(Text="Paragraph defaults", ParagraphStyle=paragraph_style)

        self.assertEqual(len(rich_text.TextRuns), 1)
        run_style = rich_text.TextRuns[0].Style
        self.assertEqual(run_style.FontName, "Courier New")
        self.assertEqual(run_style.FontSize, 20.0)
        self.assertTrue(run_style.IsBold)
        self.assertEqual(run_style.Highlight, 0xFFFF00)

    def test_richtext_append_without_explicit_style_uses_paragraphstyle_defaults(self) -> None:
        from aspose.note import ParagraphStyle, RichText

        rich_text = RichText(ParagraphStyle=ParagraphStyle(FontName="Courier New", FontSize=18.0, IsItalic=True))
        rich_text.Append("First")
        rich_text.Append("Second")

        self.assertEqual([run.Text for run in rich_text.TextRuns], ["First", "Second"])
        for run in rich_text.TextRuns:
            self.assertEqual(run.Style.FontName, "Courier New")
            self.assertEqual(run.Style.FontSize, 18.0)
            self.assertTrue(run.Style.IsItalic)

    def test_richtext_rejects_legacy_keyword_aliases(self) -> None:
        from aspose.note import RichText, TextRun

        with self.assertRaises(TypeError):
            RichText(Runs=[TextRun(Text="segment")])

        with self.assertRaises(TypeError):
            RichText(FontSize=14.0)

    def test_textrun_does_not_expose_run_boundaries(self) -> None:
        from aspose.note import TextRun

        run = TextRun(Text="segment")

        self.assertFalse(hasattr(run, "Start"))
        self.assertFalse(hasattr(run, "End"))

    def test_richtext_collection_properties_are_read_only(self) -> None:
        from aspose.note import NoteTag, RichText, TextRun

        rich_text = RichText(TextRuns=[TextRun(Text="segment")], Tags=[NoteTag.CreateYellowStar("Важно")])

        with self.assertRaises(AttributeError):
            setattr(rich_text, "TextRuns", [TextRun(Text="other")])

        with self.assertRaises(AttributeError):
            setattr(rich_text, "Tags", [])

        rich_text.TextRuns.append(TextRun(Text=" tail"))
        rich_text.Tags.append(NoteTag.CreateQuestionMark("Вопрос"))

        self.assertEqual(rich_text.Text, "segment tail")
        self.assertEqual([tag.Label for tag in rich_text.Tags], ["Важно", "Вопрос"])

    def test_formatted_richtext_run_boundaries_align_with_visible_text(self) -> None:
        from aspose.note import Document, RichText

        doc = Document(self.path)
        target = next(
            rt for rt in doc.GetChildNodes(RichText) if "hyperlink. This text is not a hyperlink." in rt.Text
        )

        visible_runs = [(run.Text, run.Style) for run in target.TextRuns if run.Text and "HYPERLINK" not in run.Text]
        texts = [text for text, _ in visible_runs]

        self.assertIn("This", texts)
        self.assertIn("text", texts)
        self.assertIn("is ", texts)
        self.assertIn("not", texts)
        self.assertIn("hyperlink", texts)

        style_by_text = {text: style for text, style in visible_runs}
        self.assertEqual(style_by_text["This"].Highlight, 65535)
        self.assertTrue(style_by_text["text"].IsBold)
        self.assertEqual(style_by_text["is "].Highlight, 16776960)
        self.assertTrue(style_by_text["not"].IsItalic)
        self.assertTrue(style_by_text["hyperlink"].IsUnderline)
