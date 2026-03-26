from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _fixture_path(name: str) -> Path | None:
    p = ROOT / "testfiles" / name
    return p if p.exists() else None


class TestAsposeNoteStubs(unittest.TestCase):
    def test_license_and_metered_are_callable(self) -> None:
        from aspose.note import License, Metered

        lic = License()
        lic.SetLicense("dummy.lic")

        m = Metered()
        m.SetMeteredKey("pub", "priv")

    def test_abstract_compatibility_bases_reject_direct_instantiation(self) -> None:
        import aspose.note as note
        from aspose.note import Document, DocumentVisitor, Node, NoteTag, ParagraphStyle

        class CountingVisitor(DocumentVisitor):
            pass

        with self.assertRaises(TypeError):
            Node()

        with self.assertRaises(TypeError):
            DocumentVisitor()

        self.assertFalse(hasattr(note, "CompositeNode"))
        with self.assertRaises(TypeError):
            NoteTag()
        self.assertIsInstance(ParagraphStyle(), ParagraphStyle)
        self.assertIsInstance(Document(), Document)
        self.assertIsInstance(CountingVisitor(), CountingVisitor)


class TestAsposeNoteLoadOptions(unittest.TestCase):
    def test_encrypted_load_raises_incorrect_password(self) -> None:
        from aspose.note import Document, IncorrectPasswordException, LoadOptions

        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")

        with self.assertRaises(IncorrectPasswordException):
            Document(p, LoadOptions(DocumentPassword="pass"))


class TestAsposeNoteCompatibilitySurface(unittest.TestCase):
    def test_document_does_not_expose_non_dotnet_count_method(self) -> None:
        from aspose.note import Document, Page

        doc = Document()
        doc.AppendChildLast(Page())

        self.assertFalse(hasattr(doc, "Count"))
        self.assertEqual(len(list(doc)), 1)

    def test_parent_node_is_read_only_to_callers(self) -> None:
        from aspose.note import Document, Page

        doc = Document()
        page = Page()
        doc.AppendChildLast(page)

        self.assertIs(page.ParentNode, doc)

        with self.assertRaises(AttributeError):
            setattr(page, "ParentNode", None)

    def test_note_tag_read_only_members_match_dotnet_shape(self) -> None:
        from aspose.note import NoteTag, TagStatus

        tag = NoteTag.CreateQuestionMark("Question")

        self.assertEqual(tag.Status, TagStatus.Open)
        self.assertIsNone(tag.CompletedTime)

        with self.assertRaises(AttributeError):
            setattr(tag, "Status", TagStatus.Disabled)

        with self.assertRaises(AttributeError):
            setattr(tag, "CompletedTime", datetime(2024, 1, 3, tzinfo=timezone.utc))

    def test_note_tag_creation_time_uses_datetime_values(self) -> None:
        from aspose.note import NoteTag, TagStatus

        created_time = datetime(2024, 5, 6, 7, 8, tzinfo=timezone.utc)
        tag = NoteTag.CreateYellowStar("Created")
        tag.CreationTime = created_time

        self.assertEqual(tag.CreationTime, created_time)
        self.assertEqual(tag.Status, TagStatus.Open)

        updated_time = datetime(2024, 5, 7, 8, 9, tzinfo=timezone.utc)
        tag.CreationTime = updated_time

        self.assertEqual(tag.CreationTime, updated_time)

    def test_title_hides_composite_child_mutators(self) -> None:
        from aspose.note import RichText, Title

        title = Title(TitleText=RichText(Text="Title"))

        self.assertIs(next(iter(title)), title.TitleText)
        for member in ("FirstChild", "LastChild", "AppendChildFirst", "AppendChildLast", "InsertChild", "RemoveChild"):
            self.assertFalse(hasattr(title, member), member)

    def test_unsupported_file_format_exception_exposes_read_only_enum(self) -> None:
        from aspose.note import FileFormat, UnsupportedFileFormatException

        error = UnsupportedFileFormatException(file_format="bogus-guid")
        self.assertIs(error.FileFormat, FileFormat.Unknown)

        with self.assertRaises(AttributeError):
            setattr(error, "FileFormat", FileFormat.OneNote2007)

    def test_page_history_constructor_accepts_only_current_page(self) -> None:
        from aspose.note import Page, PageHistory

        current = Page()
        history = PageHistory(current)

        self.assertIs(history.Current, current)

        with self.assertRaises(TypeError):
            PageHistory(current, [Page()])
