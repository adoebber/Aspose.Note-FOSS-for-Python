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


def _page_body_text(page) -> str:
    from aspose.note import RichText

    ignored = {"2 февраля 2021 г.", "16:34", "19:01"}
    texts = [rich_text.Text for rich_text in page.GetChildNodes(RichText)]
    body_texts = [text for text in texts if text not in ignored and text]
    return body_texts[-1] if body_texts else ""


def _non_empty_outline_texts(page) -> list[str]:
    from aspose.note import Outline, RichText

    result: list[str] = []
    for outline in page.GetChildNodes(Outline):
        texts = [rich_text.Text for rich_text in outline.GetChildNodes(RichText) if rich_text.Text]
        if texts:
            result.append(texts[-1])
    return result


def _table_grid(page) -> list[list[str]]:
    from aspose.note import RichText, Table, TableCell, TableRow

    tables = page.GetChildNodes(Table)
    if not tables:
        return []

    grid: list[list[str]] = []
    for row in tables[0].GetChildNodes(TableRow):
        values: list[str] = []
        for cell in row.GetChildNodes(TableCell):
            texts = [rich_text.Text for rich_text in cell.GetChildNodes(RichText) if rich_text.Text]
            values.append(texts[-1] if texts else "")
        grid.append(values)
    return grid


class TestAsposeNoteHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("SimpleHistory.one")
        if p is None:
            raise unittest.SkipTest("SimpleHistory.one not found")
        cls.path = p

    def test_parser_keeps_default_and_history_roots_separate(self) -> None:
        from aspose.note._internal.onestore.parser import parse_onestore_file

        parsed = parse_onestore_file(self.path)
        content_space = parsed.object_spaces[1]

        default_root = content_space.get_latest_root(1)
        self.assertIsNotNone(default_root)
        if default_root is None:
            raise AssertionError("expected default root")
        self.assertEqual(content_space.objects[default_root].jcid_name, "PageManifestNode")

        context_root_kinds = {
            revision.objects[revision.root_roles[1]].jcid_name
            for revision in content_space.revisions
            if revision.context_id is not None and 1 in revision.root_roles and revision.root_roles[1] in revision.objects
        }
        self.assertIn("VersionHistoryContent", context_root_kinds)

    def test_get_page_history_returns_all_revisions_in_order(self) -> None:
        from aspose.note import Document, LoadOptions, Page

        doc = Document(self.path, LoadOptions(LoadHistory=True))
        page = doc.GetChildNodes(Page)[0]

        history = doc.GetPageHistory(page)

        self.assertEqual([_page_body_text(item) for item in history], ["", "First text", "Second text", "Third text"])

    def test_parser_materializes_incremental_current_roots(self) -> None:
        from aspose.note._internal.onestore.parser import parse_onestore_file

        for fixture_name in ("SimpleTable.one", "TagSizes.one", "3ImagesWithDifferentAlignment.one"):
            fixture_path = _fixture_path(fixture_name)
            if fixture_path is None:
                raise unittest.SkipTest(f"{fixture_name} not found")

            parsed = parse_onestore_file(fixture_path)
            content_space = max(parsed.object_spaces, key=lambda item: len(item.revisions))

            default_root = content_space.get_latest_root(1)
            self.assertIsNotNone(default_root, fixture_name)
            if default_root is None:
                raise AssertionError(f"expected default root for {fixture_name}")
            self.assertIn(default_root, content_space.objects, fixture_name)
            self.assertEqual(content_space.objects[default_root].jcid_name, "PageManifestNode", fixture_name)

    def test_incremental_history_reconstructs_simple_table_versions(self) -> None:
        from aspose.note import Document, LoadOptions, Page

        fixture_path = _fixture_path("SimpleTable.one")
        if fixture_path is None:
            raise unittest.SkipTest("SimpleTable.one not found")

        doc = Document(fixture_path, LoadOptions(LoadHistory=True))
        page = doc.GetChildNodes(Page)[0]
        history = doc.GetPageHistory(page)
        texts = [_page_body_text(item) for item in history]

        self.assertEqual(_page_body_text(page), "0")
        self.assertEqual(texts, ["", "fdf", "0"])

    def test_simple_table_published_history_matches_ui_structure(self) -> None:
        from aspose.note import Document, LoadOptions, Page

        fixture_path = _fixture_path("SimpleTable.one")
        if fixture_path is None:
            raise unittest.SkipTest("SimpleTable.one not found")

        doc = Document(fixture_path, LoadOptions(LoadHistory=True))
        current_page = doc.GetChildNodes(Page)[0]
        history = doc.GetPageHistory(current_page)

        self.assertEqual(len(history), 3)
        self.assertEqual(
            _table_grid(current_page),
            [["1", "2", "3"], ["6", "5", "4"], ["7", "8", "9"], ["b", "a", "0"]],
        )

        previous_page = history[1]
        self.assertEqual(_page_body_text(previous_page), "fdf")
        self.assertEqual(_non_empty_outline_texts(previous_page), ["▪", "fdf"])

        oldest_page = history[0]
        self.assertEqual(_page_body_text(oldest_page), "")
        self.assertEqual(_non_empty_outline_texts(oldest_page), [])

    def test_incremental_history_reconstructs_image_alignment_versions(self) -> None:
        from aspose.note import Document, LoadOptions, Page

        fixture_path = _fixture_path("3ImagesWithDifferentAlignment.one")
        if fixture_path is None:
            raise unittest.SkipTest("3ImagesWithDifferentAlignment.one not found")

        doc = Document(fixture_path, LoadOptions(LoadHistory=True))
        page = doc.GetChildNodes(Page)[0]
        history = doc.GetPageHistory(page)
        texts = [_page_body_text(item) for item in history]

        self.assertEqual(_page_body_text(page), "Image in the outline with left alignment")
        self.assertEqual(texts[:3], ["", "fdf", "0"])
        self.assertTrue(all(text == "tt" for text in texts[3:-1]))
        self.assertEqual(texts[-1], "Image in the outline with left alignment")
