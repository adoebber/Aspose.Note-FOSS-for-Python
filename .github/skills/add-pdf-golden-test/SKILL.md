---
name: add-pdf-golden-test
description: "Use when adding a new PDF golden test case for a new .one fixture, extending tests/_pdf_goldens.py, regenerating tests/goldens/pdf baselines, or preparing PDF golden changes for GitHub Actions."
---

# Add PDF Golden Test

Use this skill when you need to add a new PDF golden test for a new OneNote fixture file.

This repository uses semantic PDF goldens, not raw byte-for-byte PDF comparison.
Each golden case is defined by:
- a source fixture in `testfiles/`
- a checked-in baseline PDF in `tests/goldens/pdf/`
- a checked-in manifest JSON in `tests/goldens/pdf/`
- an entry in `PDF_GOLDEN_CASES` in `tests/_pdf_goldens.py`

## Goal

Add a new `.one` input file to the PDF golden suite so that CI verifies future PDF output against a reviewed baseline.

## Files Involved

- `.github/workflows/ci.yml`
- `tests/_pdf_goldens.py`
- `tests/test_aspose_note_pdf_goldens.py`
- `tools/regenerate_pdf_goldens.py`
- `tests/goldens/pdf/`
- `testfiles/`

## Workflow

### 1. Add or verify the source fixture

Make sure the new source document exists in `testfiles/`.

Requirements:
- The fixture must be committed to the repository.
- The fixture should represent a real regression target, not a trivial duplicate of another file.
- Prefer fixtures that cover a distinct rendering behavior such as formatted text, tables, images, links, lists, or non-Latin text.

### 2. Choose a stable case id

Create a short snake_case case id derived from the fixture meaning, not the internal test intent.

Good examples:
- `formatted_richtext`
- `simple_table`
- `cyrillic_richtext`
- `page_with_attachment_preview`

Avoid:
- temporary names
- numeric suffixes without meaning
- ids tied to implementation details

The case id becomes the filename prefix for:
- `<case_id>.pdf`
- `<case_id>.manifest.json`

### 3. Register the case in `tests/_pdf_goldens.py`

Add a new `PdfGoldenCase` entry to `PDF_GOLDEN_CASES`.

Example:

```python
PDF_GOLDEN_CASES: tuple[PdfGoldenCase, ...] = (
    PdfGoldenCase("formatted_richtext", "FormattedRichText.one"),
    PdfGoldenCase("cyrillic_richtext", "CyrillicRichText.one"),
)
```

Rules:
- `case_id` must be unique.
- `fixture_name` must exactly match the file in `testfiles/`.
- Do not add special-case logic in the test module for one fixture unless absolutely necessary.

### 4. Generate the baseline files

Run the regeneration script for the new case:

```bash
python tools/regenerate_pdf_goldens.py --case cyrillic_richtext
```

If the fixture depends on broader rendering changes and you intentionally changed multiple outputs, regenerate all:

```bash
python tools/regenerate_pdf_goldens.py
```

This creates or updates:
- `tests/goldens/pdf/<case_id>.pdf`
- `tests/goldens/pdf/<case_id>.manifest.json`

### 5. Review the generated baseline

Review both artifacts before committing.

Check the PDF visually:
- text is readable
- expected formatting is present
- links render as expected
- non-Latin text is not corrupted
- layout is reasonable

Check the manifest JSON:
- `page_count` is sensible
- extracted `text` matches the intended content
- `links` contain expected targets
- `image_count` is consistent with the fixture

If the manifest is wrong because the rendering contract should be broader, update the manifest extraction logic in `tests/_pdf_goldens.py` for all cases, not only for one case.

### 6. Run the relevant tests locally

Run the PDF golden suite:

```bash
python -m unittest tests.test_aspose_note_pdf_goldens -v
```

Run the PDF writer unit tests as well:

```bash
python -m unittest tests.test_aspose_note_save_options -v
```

If you changed the PDF writer, also run the full CI-equivalent suite or at least the modules that exercise PDF generation.

### 7. Understand what a failure means

The golden test in `tests/test_aspose_note_pdf_goldens.py` does this for each case:
- loads the `.one` fixture
- generates a fresh PDF
- writes the generated PDF to `tests/out/pdf_golden_failures/`
- extracts a semantic manifest from the generated PDF
- compares it to the checked-in manifest

If the manifest differs, the test fails and prints:
- the generated PDF path
- the generated manifest path
- a unified diff of expected vs actual manifest

If visual diff tools are available, it also produces:
- baseline page PNGs
- generated page PNGs
- per-page diff PNGs

These are diagnostics only. Pass/fail is based on manifest comparison.

### 8. Commit the right files

When adding a new golden case, commit all of the following together:
- the new fixture in `testfiles/`
- the updated `tests/_pdf_goldens.py`
- the generated `tests/goldens/pdf/<case_id>.pdf`
- the generated `tests/goldens/pdf/<case_id>.manifest.json`
- any related test or writer changes if the new case required them

Do not commit files from `tests/out/`.

## GitHub Actions Requirements

The GitHub Actions workflow expects:
- fixtures to exist in `testfiles/`
- goldens to exist in `tests/goldens/pdf/`
- deterministic font behavior via `ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=0`
- dependencies installed via `.[pdf,test-pdf]`

This means a new case will work in CI only if:
1. the fixture is committed
2. the case is registered in `PDF_GOLDEN_CASES`
3. the baseline PDF is committed
4. the baseline manifest is committed

CI does not generate missing goldens for you.
CI only verifies that generated output matches the checked-in baseline.

## When To Regenerate One Case vs All Cases

Regenerate one case when:
- you added one new fixture
- only one fixture changed intentionally
- you are iterating on a single scenario

Regenerate all cases when:
- you changed PDF font strategy
- you changed text extraction-relevant rendering
- you changed hyperlink emission
- you changed image rendering behavior
- you changed layout rules broadly enough to affect many baselines

## Review Checklist

- The fixture exists in `testfiles/`.
- The case id is unique and stable.
- `PDF_GOLDEN_CASES` includes the new case.
- The baseline PDF was regenerated.
- The baseline manifest was regenerated.
- `tests.test_aspose_note_pdf_goldens` passes.
- `tests.test_aspose_note_save_options` passes.
- No files from `tests/out/` are staged.

## Common Mistakes

### Missing fixture

Symptom:
- the test skips or the regeneration script exits with a missing fixture error

Fix:
- add the `.one` file to `testfiles/`

### Missing committed goldens

Symptom:
- CI fails with “Missing golden PDF” or “Missing golden manifest”

Fix:
- run the regeneration script locally and commit the generated files

### Wrong expectation about comparison mode

Symptom:
- someone expects exact binary PDF equality

Fix:
- explain that this repository compares semantic manifest data, not raw PDF bytes

### Non-Latin text looks corrupted

Symptom:
- Cyrillic or other non-Latin text renders as boxes or extracts incorrectly

Fix:
- verify PDF font fallback behavior in `src/aspose/note/saving/pdf_writer.py`
- regenerate the affected goldens after the rendering fix

### Updating the baseline for an accidental regression

Symptom:
- tests fail and the baseline is regenerated immediately without review

Fix:
- review the generated PDF and manifest first
- only regenerate when the output change is intentional and correct

## Recommended Command Sequence

```bash
python tools/regenerate_pdf_goldens.py --case <case_id>
python -m unittest tests.test_aspose_note_save_options -v
python -m unittest tests.test_aspose_note_pdf_goldens -v
```

## Definition of Done

A new PDF golden test is complete when:
- the new fixture is in version control
- the new case is registered
- the baseline PDF and manifest are in version control
- local tests pass
- GitHub Actions can verify the new case without generating anything at runtime