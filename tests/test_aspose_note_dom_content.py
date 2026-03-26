from __future__ import annotations

import hashlib
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


class TestAsposeNoteImages(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("3ImagesWithDifferentAlignment.one")
        if p is None:
            raise unittest.SkipTest("3ImagesWithDifferentAlignment.one not found")
        cls.path = p

    def test_images_exposed_and_have_bytes(self) -> None:
        from aspose.note import Document, Image

        doc = Document(self.path)
        images = doc.GetChildNodes(Image)
        self.assertEqual(len(images), 3)
        self.assertTrue(all(isinstance(img.Bytes, (bytes, bytearray)) for img in images))
        self.assertTrue(all(len(img.Bytes) > 1024 for img in images))

    def test_images_are_identical_by_hash(self) -> None:
        from aspose.note import Document, Image

        doc = Document(self.path)
        images = doc.GetChildNodes(Image)
        self.assertEqual(len(images), 3)

        digests = [hashlib.sha256(bytes(img.Bytes)).digest() for img in images]
        self.assertEqual(len(set(digests)), 1)

    def test_images_preserve_outline_alignment(self) -> None:
        from aspose.note import Document, HorizontalAlignment, Image

        doc = Document(self.path)
        images = doc.GetChildNodes(Image)

        self.assertEqual(
            [image.Alignment for image in images],
            [
                HorizontalAlignment.Right,
                HorizontalAlignment.Center,
                HorizontalAlignment.Left,
            ],
        )

    def test_images_expose_dotnet_compatibility_metadata(self) -> None:
        from aspose.note import Document, Image

        image = Document(self.path).GetChildNodes(Image)[0]

        self.assertEqual(image.OriginalWidth, image.Width)
        self.assertEqual(image.OriginalHeight, image.Height)
        self.assertFalse(hasattr(image, "HorizontalAlignment"))

    def test_image_uses_alignment_without_legacy_alias(self) -> None:
        from aspose.note import HorizontalAlignment, Image

        image = Image(Bytes=b"img", Width=10.0, Height=20.0, Alignment=HorizontalAlignment.Center)

        self.assertEqual(image.Alignment, HorizontalAlignment.Center)
        self.assertFalse(hasattr(image, "HorizontalAlignment"))

    def test_image_read_only_metadata_stays_mutable_via_tags_collection(self) -> None:
        from aspose.note import Image, NoteTag

        image = Image(
            FileName="image.png",
            FilePath="C:/tmp/image.png",
            Format="png",
            Bytes=b"img",
            Width=10.0,
            Height=20.0,
            OriginalWidth=10.0,
            OriginalHeight=20.0,
            Tags=[NoteTag.CreateYellowStar("Важно")],
        )

        with self.assertRaises(AttributeError):
            image.FileName = "renamed.png"

        with self.assertRaises(AttributeError):
            image.Bytes = b"other"

        image.Tags.append(NoteTag.CreateQuestionMark("Вопрос"))
        self.assertEqual([tag.Label for tag in image.Tags], ["Важно", "Вопрос"])


class TestAsposeNoteTables(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("SimpleTable.one")
        if p is None:
            raise unittest.SkipTest("SimpleTable.one not found")
        cls.path = p

    def test_tables_exposed_with_rows_and_cells(self) -> None:
        from aspose.note import Document, Table, TableRow, TableCell

        doc = Document(self.path)
        tables = doc.GetChildNodes(Table)
        self.assertGreaterEqual(len(tables), 1)

        rows = doc.GetChildNodes(TableRow)
        cells = doc.GetChildNodes(TableCell)
        self.assertGreater(len(rows), 0)
        self.assertGreater(len(cells), 0)

        # Basic structural sanity: each TableRow should have at least 1 cell.
        for row in rows[:10]:
            self.assertGreaterEqual(len(list(row)), 1)

    def test_table_collections_are_read_only_properties(self) -> None:
        from aspose.note import NoteTag, Table, TableColumn

        table = Table(Tags=[NoteTag.CreateYellowStar("Важно")], Columns=[TableColumn(Width=70)])

        with self.assertRaises(AttributeError):
            table.Tags = []

        with self.assertRaises(AttributeError):
            table.Columns = []

        table.Tags.append(NoteTag.CreateQuestionMark("Вопрос"))
        table.Columns.append(TableColumn(Width=120))

        self.assertEqual([tag.Label for tag in table.Tags], ["Важно", "Вопрос"])
        self.assertEqual([column.Width for column in table.Columns], [70, 120])


class TestAsposeNoteAttachments(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        p = _fixture_path("OnePageWithFile.one") or _fixture_path("AttachedFileWithTag.one")
        if p is None:
            raise unittest.SkipTest("No attachment fixtures found")
        cls.path = p

    def test_attached_files_exposed_and_have_bytes(self) -> None:
        from aspose.note import AttachedFile, Document

        doc = Document(self.path)
        atts = doc.GetChildNodes(AttachedFile)
        self.assertGreaterEqual(len(atts), 1)

        # Filename should be present.
        self.assertTrue(any((a.FileName or "").strip() for a in atts))

        # Bytes are best-effort in current implementation (may be empty for some fixtures).
        self.assertTrue(all(isinstance(a.Bytes, (bytes, bytearray)) for a in atts))

    def test_attached_file_metadata_is_read_only(self) -> None:
        from aspose.note import AttachedFile, NoteTag

        attached = AttachedFile(FileName="doc.bin", Bytes=b"abc", Tags=[NoteTag.CreateYellowStar("Важно")])

        with self.assertRaises(AttributeError):
            attached.FileName = "other.bin"

        with self.assertRaises(AttributeError):
            attached.Bytes = b"xyz"

        attached.Tags.append(NoteTag.CreateQuestionMark("Вопрос"))
        self.assertEqual([tag.Label for tag in attached.Tags], ["Важно", "Вопрос"])
