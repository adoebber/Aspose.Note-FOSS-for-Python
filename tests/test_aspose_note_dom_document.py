from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

from aspose.note.enums import SaveFormat

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _fixture_path(name: str) -> Path | None:
    p = ROOT / "testfiles" / name
    return p if p.exists() else None


class TestAsposeNoteDocumentBasics(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p
        cls.data = p.read_bytes()

    def test_construct_from_path(self) -> None:
        from aspose.note import Document

        doc = Document(self.path)
        self.assertFalse(hasattr(doc, "Count"))
        self.assertGreater(len(list(doc)), 0)
        self.assertIsNotNone(doc.FirstChild)
        self.assertIsNotNone(doc.LastChild)

    def test_construct_from_stream(self) -> None:
        from aspose.note import Document

        doc = Document(io.BytesIO(self.data))
        self.assertGreater(len(list(doc)), 0)

    def test_document_file_format_enum(self) -> None:
        from aspose.note import Document, FileFormat

        doc = Document(self.path)
        self.assertIsInstance(doc.FileFormat, FileFormat)

    def test_get_child_nodes_page_and_title(self) -> None:
        from aspose.note import Document, Page, Title

        doc = Document(self.path)
        pages = doc.GetChildNodes(Page)
        self.assertGreaterEqual(len(pages), 1)

        titles = doc.GetChildNodes(Title)
        # Each page should have a Title node.
        self.assertGreaterEqual(len(titles), len(pages))

        # Page.Title property should match first Title in its children.
        page0 = pages[0]
        self.assertIsNotNone(page0.Title)
        self.assertIs(page0.FirstChild, page0.Title)


class TestAsposeNoteRichTextOperations(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_richtext_replace_changes_text(self) -> None:
        from aspose.note import Document, RichText

        doc = Document(self.path)
        rts = doc.GetChildNodes(RichText)
        self.assertGreater(len(rts), 0)

        # Pick a non-empty node with a replaceable substring.
        target = None
        for rt in rts:
            if rt.Text and " " in rt.Text:
                target = rt
                break
        if target is None:
            raise unittest.SkipTest("No RichText nodes with replaceable content found")

        before = target.Text
        returned = target.Replace(" ", "  ")
        after = target.Text
        self.assertIs(returned, target)
        self.assertNotEqual(before, after)
        doc.Save("FormattedRichText.pdf", SaveFormat.Pdf)

    def test_richtext_supports_dotnet_text_runs_alias(self) -> None:
        from aspose.note import Document, RichText

        doc = Document(self.path)
        rich_text = next(rt for rt in doc.GetChildNodes(RichText) if rt.TextRuns)

        self.assertFalse(hasattr(rich_text, "Runs"))
        self.assertGreater(len(rich_text.TextRuns), 0)
        self.assertEqual(rich_text.Length, len(rich_text.Text))


class TestAsposeNotePageClone(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("FormattedRichText.one")
        if p is None:
            raise unittest.SkipTest("FormattedRichText.one not found")
        cls.path = p

    def test_page_clone_duplicates_content_tree(self) -> None:
        from aspose.note import Document, Page, RichText

        page = Document(self.path).GetChildNodes(Page)[0]
        cloned = page.Clone()

        self.assertIsNot(cloned, page)
        self.assertEqual(len(list(cloned)), len(list(page)))
        self.assertEqual(len(cloned.GetChildNodes(RichText)), len(page.GetChildNodes(RichText)))
        self.assertIsNone(cloned.ParentNode)

    def test_page_clone_accepts_clone_history_keyword(self) -> None:
        from aspose.note import Document, Page

        page = Document(self.path).GetChildNodes(Page)[0]
        cloned = page.Clone(cloneHistory=True)

        self.assertIsNot(cloned, page)


class TestAsposeNoteVisitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("SimpleTable.one")
        if p is None:
            raise unittest.SkipTest("SimpleTable.one not found")
        cls.path = p

    def test_accept_visits_document_and_pages(self) -> None:
        from aspose.note import Document, DocumentVisitor, Page

        class CountingVisitor(DocumentVisitor):
            def __init__(self) -> None:
                self.pages = 0
                self.doc_start = 0

            def VisitDocumentStart(self, document):  # noqa: N802
                self.doc_start += 1

            def VisitPageStart(self, page: Page):  # noqa: N802
                self.pages += 1

        doc = Document(self.path)
        v = CountingVisitor()
        doc.Accept(v)

        self.assertEqual(v.doc_start, 1)
        self.assertGreaterEqual(v.pages, 1)


class TestAsposeNoteSubpages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("Issue1Subpages.one")
        if p is None:
            raise unittest.SkipTest("Issue1Subpages.one not found")
        cls.path = p

    def test_document_keeps_subpages_from_multiple_page_spaces(self) -> None:
        from aspose.note import Document, Outline, OutlineElement, Page, RichText

        doc = Document(self.path)
        pages = doc.GetChildNodes(Page)

        self.assertEqual(len(list(doc)), 2)
        self.assertEqual(len(pages), 2)
        self.assertEqual(
            [page.Title.TitleText.Text if page.Title and page.Title.TitleText else None for page in pages],
            ["Page1", "Subpage2"],
        )
        self.assertEqual([page.Level for page in pages], [1, 2])

        page_texts: list[list[str]] = []
        for page in pages:
            texts: list[str] = []
            for outline in page.GetChildNodes(Outline):
                for outline_element in outline.GetChildNodes(OutlineElement):
                    texts.extend(rich_text.Text for rich_text in outline_element.GetChildNodes(RichText) if rich_text.Text)
            page_texts.append(texts)

        self.assertEqual(page_texts, [["Content1"], ["Content2"]])


class TestAsposeNoteSinglePageMetadataFallback(unittest.TestCase):
    def test_single_page_fixtures_do_not_create_synthetic_titles(self) -> None:
        from aspose.note import Document, Page

        for fixture_name in ("SimpleTable.one", "3ImagesWithDifferentAlignment.one"):
            path = _fixture_path(fixture_name)
            if path is None:
                raise unittest.SkipTest(f"{fixture_name} not found")

            doc = Document(path)
            pages = doc.GetChildNodes(Page)

            self.assertEqual(len(pages), 1)
            self.assertIsNone(pages[0].Title, fixture_name)
            self.assertEqual(pages[0].Level, 1, fixture_name)
