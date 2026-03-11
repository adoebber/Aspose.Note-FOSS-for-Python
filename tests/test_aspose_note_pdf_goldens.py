from __future__ import annotations

import difflib
import io
import unittest

from tests._pdf_goldens import (
    HAS_PYPDF,
    PDF_GOLDEN_CASES,
    create_visual_diff_artifacts,
    ensure_output_dirs,
    failure_manifest_path,
    failure_pdf_path,
    fixture_path,
    golden_manifest_path,
    golden_pdf_path,
    load_manifest,
    manifest_pretty_json,
    visual_diff_available,
    write_manifest,
)

try:
    import reportlab  # noqa: F401

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@unittest.skipUnless(HAS_REPORTLAB and HAS_PYPDF, "reportlab and pypdf are required")
class TestAsposeNotePdfGoldens(unittest.TestCase):
    def test_pdf_goldens_match_manifest(self) -> None:
        from aspose.note import Document, PdfSaveOptions, SaveFormat

        from tests._pdf_goldens import build_pdf_manifest

        ensure_output_dirs()

        for case in PDF_GOLDEN_CASES:
            with self.subTest(case=case.case_id):
                source = fixture_path(case.fixture_name)
                if source is None:
                    raise unittest.SkipTest(f"{case.fixture_name} not found")

                expected_pdf = golden_pdf_path(case.case_id)
                expected_manifest_path = golden_manifest_path(case.case_id)
                self.assertTrue(
                    expected_pdf.exists(),
                    f"Missing golden PDF for {case.case_id}. Run tools/regenerate_pdf_goldens.py.",
                )
                self.assertTrue(
                    expected_manifest_path.exists(),
                    f"Missing golden manifest for {case.case_id}. Run tools/regenerate_pdf_goldens.py.",
                )

                buf = io.BytesIO()
                Document(source).Save(buf, PdfSaveOptions(SaveFormat.Pdf))

                generated_pdf = failure_pdf_path(case.case_id)
                generated_pdf.write_bytes(buf.getvalue())
                actual_manifest = build_pdf_manifest(generated_pdf, fixture_name=case.fixture_name)
                generated_manifest = failure_manifest_path(case.case_id)
                write_manifest(generated_manifest, actual_manifest)

                expected_manifest = load_manifest(expected_manifest_path)
                if actual_manifest != expected_manifest:
                    visual_artifacts: list[str] = []
                    if visual_diff_available():
                        visual_artifacts = [
                            str(path)
                            for path in create_visual_diff_artifacts(case.case_id, expected_pdf, generated_pdf)
                        ]
                    diff = "".join(
                        difflib.unified_diff(
                            manifest_pretty_json(expected_manifest).splitlines(keepends=True),
                            manifest_pretty_json(actual_manifest).splitlines(keepends=True),
                            fromfile=str(expected_manifest_path),
                            tofile=str(generated_manifest),
                        )
                    )
                    self.fail(
                        f"PDF golden mismatch for {case.case_id}.\n"
                        f"Generated PDF: {generated_pdf}\n"
                        f"Generated manifest: {generated_manifest}\n"
                        f"Visual artifacts: {visual_artifacts or 'not available'}\n"
                        f"Manifest diff:\n{diff}"
                    )