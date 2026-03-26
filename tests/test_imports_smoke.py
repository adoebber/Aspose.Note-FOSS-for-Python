import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class TestImportsSmoke(unittest.TestCase):
    def test_imports_smoke(self) -> None:
        import aspose.note
        import aspose.note.saving  # noqa: F401
        from aspose.note import Document, Outline, Page, ParagraphStyle, RichText  # noqa: F401
        from aspose.note.saving import PdfSaveOptions, SaveOptions  # noqa: F401

        self.assertFalse(hasattr(aspose.note, "SaveOptions"))
        self.assertFalse(hasattr(aspose.note, "PdfSaveOptions"))
