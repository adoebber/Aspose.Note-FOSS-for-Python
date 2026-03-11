from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from types import SimpleNamespace

from .options import PdfSaveOptions


_HYPERLINK_FIELD_RE = re.compile(r'\ufddfHYPERLINK\s+"[^"]*"')
_HYPERLINK_TARGET_RE = re.compile(r'\ufddfHYPERLINK\s+"([^"]+)"')
_LEFT_MARGIN = 40
_TOP_MARGIN = 40
_BOTTOM_MARGIN = 80
_RIGHT_MARGIN = 40
_CONTENT_MARGIN = 28.35
_POINTS_PER_CM = 28.35
_WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")
_SYSTEM_FONT_ENV_VAR = "ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS"
_DEFAULT_HYPERLINK_COLOR = (0.0, 0.2, 0.65)
_COMMON_FONT_DIRS = (
    _WINDOWS_FONT_DIR,
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/share/fonts/truetype/liberation2"),
    Path("/usr/share/fonts/truetype/liberation"),
    Path("/usr/share/fonts/truetype/noto"),
    Path("/usr/share/fonts/opentype/noto"),
    Path("/Library/Fonts"),
    Path("/System/Library/Fonts"),
)
_FONT_VARIANTS = {
    "sans": {
        (False, False): ("Arial", "arial.ttf"),
        (True, False): ("Arial-Bold", "arialbd.ttf"),
        (False, True): ("Arial-Italic", "ariali.ttf"),
        (True, True): ("Arial-BoldItalic", "arialbi.ttf"),
    },
    "serif": {
        (False, False): ("TimesNewRoman", "times.ttf"),
        (True, False): ("TimesNewRoman-Bold", "timesbd.ttf"),
        (False, True): ("TimesNewRoman-Italic", "timesi.ttf"),
        (True, True): ("TimesNewRoman-BoldItalic", "timesbi.ttf"),
    },
    "mono": {
        (False, False): ("CourierNew", "cour.ttf"),
        (True, False): ("CourierNew-Bold", "courbd.ttf"),
        (False, True): ("CourierNew-Italic", "couri.ttf"),
        (True, True): ("CourierNew-BoldItalic", "courbi.ttf"),
    },
}
_UNICODE_FONT_CANDIDATES = {
    "sans": {
        (False, False): (("Arial", "arial.ttf"), ("DejaVuSans", "DejaVuSans.ttf"), ("LiberationSans", "LiberationSans-Regular.ttf"), ("NotoSans", "NotoSans-Regular.ttf"), ("FreeSans", "FreeSans.ttf")),
        (True, False): (("Arial-Bold", "arialbd.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf"), ("LiberationSans-Bold", "LiberationSans-Bold.ttf"), ("NotoSans-Bold", "NotoSans-Bold.ttf"), ("FreeSans-Bold", "FreeSansBold.ttf")),
        (False, True): (("Arial-Italic", "ariali.ttf"), ("DejaVuSans-Oblique", "DejaVuSans-Oblique.ttf"), ("LiberationSans-Italic", "LiberationSans-Italic.ttf"), ("NotoSans-Italic", "NotoSans-Italic.ttf"), ("FreeSans-Oblique", "FreeSansOblique.ttf")),
        (True, True): (("Arial-BoldItalic", "arialbi.ttf"), ("DejaVuSans-BoldOblique", "DejaVuSans-BoldOblique.ttf"), ("LiberationSans-BoldItalic", "LiberationSans-BoldItalic.ttf"), ("NotoSans-BoldItalic", "NotoSans-BoldItalic.ttf"), ("FreeSans-BoldOblique", "FreeSansBoldOblique.ttf")),
    },
    "serif": {
        (False, False): (("TimesNewRoman", "times.ttf"), ("DejaVuSerif", "DejaVuSerif.ttf"), ("LiberationSerif", "LiberationSerif-Regular.ttf"), ("NotoSerif", "NotoSerif-Regular.ttf"), ("FreeSerif", "FreeSerif.ttf")),
        (True, False): (("TimesNewRoman-Bold", "timesbd.ttf"), ("DejaVuSerif-Bold", "DejaVuSerif-Bold.ttf"), ("LiberationSerif-Bold", "LiberationSerif-Bold.ttf"), ("NotoSerif-Bold", "NotoSerif-Bold.ttf"), ("FreeSerif-Bold", "FreeSerifBold.ttf")),
        (False, True): (("TimesNewRoman-Italic", "timesi.ttf"), ("DejaVuSerif-Italic", "DejaVuSerif-Italic.ttf"), ("LiberationSerif-Italic", "LiberationSerif-Italic.ttf"), ("NotoSerif-Italic", "NotoSerif-Italic.ttf"), ("FreeSerif-Italic", "FreeSerifItalic.ttf")),
        (True, True): (("TimesNewRoman-BoldItalic", "timesbi.ttf"), ("DejaVuSerif-BoldItalic", "DejaVuSerif-BoldItalic.ttf"), ("LiberationSerif-BoldItalic", "LiberationSerif-BoldItalic.ttf"), ("NotoSerif-BoldItalic", "NotoSerif-BoldItalic.ttf"), ("FreeSerif-BoldItalic", "FreeSerifBoldItalic.ttf")),
    },
    "mono": {
        (False, False): (("CourierNew", "cour.ttf"), ("DejaVuSansMono", "DejaVuSansMono.ttf"), ("LiberationMono", "LiberationMono-Regular.ttf"), ("NotoSansMono", "NotoSansMono-Regular.ttf"), ("FreeMono", "FreeMono.ttf")),
        (True, False): (("CourierNew-Bold", "courbd.ttf"), ("DejaVuSansMono-Bold", "DejaVuSansMono-Bold.ttf"), ("LiberationMono-Bold", "LiberationMono-Bold.ttf"), ("NotoSansMono-Bold", "NotoSansMono-Bold.ttf"), ("FreeMono-Bold", "FreeMonoBold.ttf")),
        (False, True): (("CourierNew-Italic", "couri.ttf"), ("DejaVuSansMono-Oblique", "DejaVuSansMono-Oblique.ttf"), ("LiberationMono-Italic", "LiberationMono-Italic.ttf"), ("NotoSansMono-Italic", "NotoSansMono-Italic.ttf"), ("FreeMono-Oblique", "FreeMonoOblique.ttf")),
        (True, True): (("CourierNew-BoldItalic", "courbi.ttf"), ("DejaVuSansMono-BoldOblique", "DejaVuSansMono-BoldOblique.ttf"), ("LiberationMono-BoldItalic", "LiberationMono-BoldItalic.ttf"), ("NotoSansMono-BoldItalic", "NotoSansMono-BoldItalic.ttf"), ("FreeMono-BoldOblique", "FreeMonoBoldOblique.ttf")),
    },
}
_BASE14_FONTS = {
    "sans": {
        (False, False): "Helvetica",
        (True, False): "Helvetica-Bold",
        (False, True): "Helvetica-Oblique",
        (True, True): "Helvetica-BoldOblique",
    },
    "serif": {
        (False, False): "Times-Roman",
        (True, False): "Times-Bold",
        (False, True): "Times-Italic",
        (True, True): "Times-BoldItalic",
    },
    "mono": {
        (False, False): "Courier",
        (True, False): "Courier-Bold",
        (False, True): "Courier-Oblique",
        (True, True): "Courier-BoldOblique",
    },
}
_REGISTERED_FONT_NAMES: dict[tuple[str, bool, bool, bool], str] = {}


def _sanitize_text(text: str) -> str:
    return _HYPERLINK_FIELD_RE.sub("", text).replace("\ufddf", "")


def _extract_hyperlink_target(text: str) -> str | None:
    match = _HYPERLINK_TARGET_RE.search(text)
    if match is None:
        return None
    return match.group(1).strip() or None


def _normalize_hyperlink_target(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme:
        return target
    if "@" in target and " " not in target:
        return f"mailto:{target}"
    return f"https://{target}"


def _font_group_for_family(family_name: str) -> str:
    family_source = family_name.lower()
    if "times" in family_source or "serif" in family_source:
        return "serif"
    if any(name in family_source for name in ("courier", "consol", "mono")):
        return "mono"
    return "sans"


def _use_system_fonts() -> bool:
    value = os.environ.get(_SYSTEM_FONT_ENV_VAR, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _text_requires_unicode_font(text: str) -> bool:
    for char in text:
        codepoint = ord(char)
        if 0x0400 <= codepoint <= 0x052F:
            return True
        if 0x2DE0 <= codepoint <= 0x2DFF:
            return True
        if 0xA640 <= codepoint <= 0xA69F:
            return True
    return False


def _find_font_file(group: str, bold: bool, italic: bool) -> tuple[str, Path] | None:
    candidates = _UNICODE_FONT_CANDIDATES[group][(bold, italic)]
    for alias, file_name in candidates:
        for directory in _COMMON_FONT_DIRS:
            font_path = directory / file_name
            if font_path.exists():
                return alias, font_path
    return None


def _register_font_variant(group: str, bold: bool, italic: bool, require_unicode: bool = False) -> str:
    use_system_fonts = _use_system_fonts() or require_unicode
    key = (group, bold, italic, use_system_fonts)
    if key in _REGISTERED_FONT_NAMES:
        return _REGISTERED_FONT_NAMES[key]

    if not use_system_fonts:
        name = _BASE14_FONTS[group][(bold, italic)]
        _REGISTERED_FONT_NAMES[key] = name
        return name

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        name = _BASE14_FONTS[group][(bold, italic)]
        _REGISTERED_FONT_NAMES[key] = name
        return name

    resolved = _find_font_file(group, bold, italic)
    if resolved is not None:
        alias, font_path = resolved
        if alias not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(alias, str(font_path)))
        _REGISTERED_FONT_NAMES[key] = alias
        return alias

    name = _BASE14_FONTS[group][(bold, italic)]
    _REGISTERED_FONT_NAMES[key] = name
    return name


def _font_name_for_style(style, default_font: str, text: str = "", default_bold: bool = False) -> str:
    family_source = getattr(style, "FontName", None) or default_font
    bold = bool(default_bold or getattr(style, "Bold", False))
    italic = bool(getattr(style, "Italic", False))
    return _register_font_variant(_font_group_for_family(family_source), bold, italic, require_unicode=_text_requires_unicode_font(text))


def _rgb_components(color: int | None, default: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> tuple[float, float, float]:
    if color is None:
        return default
    color = max(0, min(int(color), 0xFFFFFF))
    return (color & 0xFF) / 255.0, ((color >> 8) & 0xFF) / 255.0, ((color >> 16) & 0xFF) / 255.0


def _string_width(pdf, text: str, font_name: str, font_size: float) -> float:
    if hasattr(pdf, "stringWidth"):
        return float(pdf.stringWidth(text, font_name, font_size))
    return len(text) * font_size * 0.55


def _set_fill_color(pdf, color: tuple[float, float, float]) -> None:
    if hasattr(pdf, "setFillColorRGB"):
        pdf.setFillColorRGB(*color)


def _set_stroke_color(pdf, color: tuple[float, float, float]) -> None:
    if hasattr(pdf, "setStrokeColorRGB"):
        pdf.setStrokeColorRGB(*color)


def _effective_text_color(style) -> tuple[float, float, float]:
    if getattr(style, "FontColor", None) is not None:
        return _rgb_components(getattr(style, "FontColor"))
    if getattr(style, "IsHyperlink", False) or getattr(style, "HyperlinkAddress", None):
        return _DEFAULT_HYPERLINK_COLOR
    return (0.0, 0.0, 0.0)


def _should_underline(style) -> bool:
    return bool(getattr(style, "Underline", False) or getattr(style, "IsHyperlink", False) or getattr(style, "HyperlinkAddress", None))


def _show_page(pdf, height: float) -> float:
    pdf.showPage()
    _set_fill_color(pdf, (0.0, 0.0, 0.0))
    _set_stroke_color(pdf, (0.0, 0.0, 0.0))
    return height - _TOP_MARGIN


def _fit_prefix_length(pdf, text: str, font_name: str, font_size: float, max_width: float) -> int:
    if not text:
        return 0
    if _string_width(pdf, text, font_name, font_size) <= max_width:
        return len(text)

    low = 1
    high = len(text)
    best = 0
    while low <= high:
        middle = (low + high) // 2
        if _string_width(pdf, text[:middle], font_name, font_size) <= max_width:
            best = middle
            low = middle + 1
        else:
            high = middle - 1

    if best == 0:
        return 1

    break_at = max(text.rfind(" ", 0, best), text.rfind("\t", 0, best))
    if 0 < break_at < len(text):
        return break_at + 1
    return best


def _iter_runs(rich_text):
    runs = list(getattr(rich_text, "Runs", []) or [])
    if runs:
        return runs

    text = getattr(rich_text, "Text", "")
    if not text:
        return []

    fallback_style = SimpleNamespace(
        FontName=None,
        FontSize=getattr(rich_text, "FontSize", None),
        FontColor=None,
        HighlightColor=None,
        Bold=False,
        Italic=False,
        Underline=False,
        Strikethrough=False,
        Superscript=False,
        Subscript=False,
        HyperlinkAddress=None,
    )
    return [SimpleNamespace(Text=text, Style=fallback_style)]


def _draw_segment(pdf, x: float, y: float, text: str, style, default_font: str, default_size: float, default_bold: bool = False) -> float:
    if not text:
        return x

    font_size = max(float(getattr(style, "FontSize", None) or default_size), 1.0)
    font_name = _font_name_for_style(style, default_font, text=text, default_bold=default_bold)
    text_color = _effective_text_color(style)
    highlight = getattr(style, "HighlightColor", None)
    baseline_shift = 0.35 * font_size if getattr(style, "Superscript", False) else (-0.2 * font_size if getattr(style, "Subscript", False) else 0.0)
    width = _string_width(pdf, text, font_name, font_size)

    if highlight is not None and hasattr(pdf, "rect"):
        highlight_color = _rgb_components(highlight)
        _set_fill_color(pdf, highlight_color)
        pdf.rect(x, y - (font_size * 0.25) + baseline_shift, width, font_size * 1.15, stroke=0, fill=1)

    pdf.setFont(font_name, font_size)
    _set_fill_color(pdf, text_color)
    pdf.drawString(x, y + baseline_shift, text)

    if _should_underline(style) and hasattr(pdf, "line"):
        _set_stroke_color(pdf, text_color)
        pdf.line(x, y - (font_size * 0.15) + baseline_shift, x + width, y - (font_size * 0.15) + baseline_shift)
    if getattr(style, "Strikethrough", False) and hasattr(pdf, "line"):
        _set_stroke_color(pdf, text_color)
        pdf.line(x, y + (font_size * 0.3) + baseline_shift, x + width, y + (font_size * 0.3) + baseline_shift)

    return x + width


def _render_runs(pdf, runs, start_x: float, cursor_y: float, page_width: float, page_height: float, default_font: str = "Arial", default_size: float = 11.0, default_bold: bool = False, finish_with_newline: bool = True) -> tuple[float, float]:
    if not runs:
        return start_x, cursor_y

    x = start_x
    base_line_height = default_size * 1.35
    current_line_height = base_line_height
    rendered_any = False
    pending_hyperlink_target: str | None = None

    for run in runs:
        style = run.Style
        font_size = max(float(getattr(style, "FontSize", None) or default_size), 1.0)
        raw_text = getattr(run, "Text", "")
        font_name = _font_name_for_style(style, default_font, text=raw_text, default_bold=default_bold)
        extracted_target = _extract_hyperlink_target(raw_text)
        if extracted_target is not None:
            pending_hyperlink_target = _normalize_hyperlink_target(extracted_target)
        text = _sanitize_text(raw_text)
        run_hyperlink_target = _normalize_hyperlink_target(getattr(style, "HyperlinkAddress", None))
        if run_hyperlink_target is None and getattr(style, "IsHyperlink", False):
            run_hyperlink_target = pending_hyperlink_target
        position = 0

        while position < len(text):
            if cursor_y < _BOTTOM_MARGIN + current_line_height:
                cursor_y = _show_page(pdf, page_height)
                x = start_x
                current_line_height = base_line_height

            newline_at = text.find("\n", position)
            chunk_end = newline_at if newline_at != -1 else len(text)
            chunk = text[position:chunk_end]

            while chunk:
                current_line_height = max(current_line_height, font_size * 1.35)
                available_width = max(page_width - _RIGHT_MARGIN - x, font_size)
                piece_length = _fit_prefix_length(pdf, chunk, font_name, font_size, available_width)
                piece = chunk[:piece_length]
                if x == start_x and piece.isspace():
                    piece = ""
                    piece_length = len(chunk)
                if piece:
                    piece_start_x = x
                    x = _draw_segment(pdf, x, cursor_y, piece, style, default_font, default_size, default_bold=default_bold)
                    if run_hyperlink_target is not None and hasattr(pdf, "linkURL"):
                        pdf.linkURL(
                            run_hyperlink_target,
                            (
                                piece_start_x,
                                cursor_y - (font_size * 0.25),
                                x,
                                cursor_y + (font_size * 0.95),
                            ),
                            relative=0,
                        )
                    rendered_any = True
                chunk = chunk[piece_length:]
                if chunk:
                    cursor_y -= current_line_height
                    x = start_x
                    current_line_height = base_line_height

            if newline_at == -1:
                position = len(text)
            else:
                position = newline_at + 1
                cursor_y -= current_line_height
                x = start_x
                current_line_height = base_line_height

        if text and run_hyperlink_target is not None:
            pending_hyperlink_target = None

    if rendered_any and finish_with_newline:
        cursor_y -= current_line_height
        x = start_x
    return x, cursor_y


def _render_rich_text(pdf, rich_text, cursor_y: float, page_width: float, page_height: float, start_x: float = _LEFT_MARGIN, default_font: str = "Arial", default_size: float = 11.0, default_bold: bool = False) -> float:
    runs = _iter_runs(rich_text)
    if not runs:
        return cursor_y
    _, cursor_y = _render_runs(pdf, runs, start_x, cursor_y, page_width, page_height, default_font=default_font, default_size=default_size, default_bold=default_bold)
    return cursor_y


def _render_inline_rich_texts(pdf, rich_texts, cursor_y: float, page_width: float, page_height: float, start_x: float = _LEFT_MARGIN, gap: float = 18.0, default_font: str = "Arial", default_size: float = 10.0) -> float:
    x = start_x
    rendered = False
    for rich_text in rich_texts:
        runs = _iter_runs(rich_text)
        if not runs:
            continue
        x, cursor_y = _render_runs(pdf, runs, x, cursor_y, page_width, page_height, default_font=default_font, default_size=default_size, finish_with_newline=False)
        x += gap
        rendered = True
    if rendered:
        cursor_y -= default_size * 1.6
    return cursor_y


def _plain_text_from_rich_text(rich_text) -> str:
    return _sanitize_text(getattr(rich_text, "Text", "")).strip()


def _has_ancestor_of_type(node, node_type: type) -> bool:
    current = getattr(node, "ParentNode", None)
    while current is not None:
        if isinstance(current, node_type):
            return True
        current = getattr(current, "ParentNode", None)
    return False


def _outline_x_position(outline) -> float:
    return _CONTENT_MARGIN + max(float(getattr(outline, "X", 0.0) or 0.0), 0.0) * _POINTS_PER_CM


def _outline_y_position(content_origin_y: float, outline) -> float:
    return content_origin_y - max(float(getattr(outline, "Y", 0.0) or 0.0), 0.0) * _POINTS_PER_CM


def write_pdf(document, options: PdfSaveOptions) -> bytes:
    try:
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab") from exc

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    width, height = pdf._pagesize

    pages = list(document)
    start = max(options.PageIndex, 0)
    selected = pages[start : start + options.PageCount if options.PageCount is not None else None]
    if not selected:
        selected = [None]

    for index, page in enumerate(selected):
        cursor_y = height - _TOP_MARGIN
        if page is not None:
            from ..model import Image, Outline, RichText, Table, TableCell

            title_nodes: set[int] = set()
            if page.Title is not None:
                if page.Title.TitleText is not None:
                    title_nodes.add(id(page.Title.TitleText))
                    cursor_y = _render_rich_text(pdf, page.Title.TitleText, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=14.0)
                elif document.DisplayName:
                    pdf.setFont(_register_font_variant("sans", True, False), 14)
                    pdf.drawString(_LEFT_MARGIN, cursor_y, document.DisplayName[:120])
                    cursor_y -= 22

                meta_nodes = []
                if page.Title.TitleDate is not None:
                    title_nodes.add(id(page.Title.TitleDate))
                    meta_nodes.append(page.Title.TitleDate)
                if page.Title.TitleTime is not None:
                    title_nodes.add(id(page.Title.TitleTime))
                    meta_nodes.append(page.Title.TitleTime)
                if meta_nodes:
                    cursor_y = _render_inline_rich_texts(pdf, meta_nodes, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=9.0)
                cursor_y -= 14
            else:
                title = document.DisplayName or "OneNote"
                pdf.setFont(_register_font_variant("sans", True, False), 14)
                pdf.drawString(_LEFT_MARGIN, cursor_y, title[:120])
                cursor_y -= 22

            content_origin_y = cursor_y
            rendered_outline_text_ids: set[int] = set()
            for outline in page.GetChildNodes(Outline):
                outline_cursor_y = _outline_y_position(content_origin_y, outline)
                outline_start_x = _outline_x_position(outline)
                for rich_text in outline.GetChildNodes(RichText):
                    rendered_outline_text_ids.add(id(rich_text))
                    if not _plain_text_from_rich_text(rich_text):
                        continue
                    outline_cursor_y = _render_rich_text(pdf, rich_text, outline_cursor_y, width, height, start_x=outline_start_x, default_font="Arial", default_size=11.0)

            for rich_text in page.GetChildNodes(RichText):
                if id(rich_text) in title_nodes or id(rich_text) in rendered_outline_text_ids or _has_ancestor_of_type(rich_text, TableCell) or _has_ancestor_of_type(rich_text, Outline):
                    continue
                if not _plain_text_from_rich_text(rich_text):
                    continue
                cursor_y = _render_rich_text(pdf, rich_text, cursor_y, width, height, start_x=_LEFT_MARGIN, default_font="Arial", default_size=11.0)

            for table in page.GetChildNodes(Table):
                if cursor_y < _BOTTOM_MARGIN + 16:
                    cursor_y = _show_page(pdf, height)
                pdf.setFont(_register_font_variant("sans", True, False), 11)
                pdf.drawString(_LEFT_MARGIN, cursor_y, "Table")
                cursor_y -= 16
                pdf.setFont(_register_font_variant("sans", False, False), 10)
                for row in table:
                    cell_texts: list[str] = []
                    for cell in row:
                        texts = [_plain_text_from_rich_text(rt) for rt in cell.GetChildNodes(RichText) if _plain_text_from_rich_text(rt)]
                        cell_texts.append(" | ".join(texts))
                    pdf.drawString(50, cursor_y, " || ".join(cell_texts)[:150])
                    cursor_y -= 14

            for image in page.GetChildNodes(Image):
                if not image.Bytes:
                    continue
                if cursor_y < 180:
                    cursor_y = _show_page(pdf, height)
                try:
                    img = ImageReader(BytesIO(bytes(image.Bytes)))
                    draw_width = min(220, image.Width or 220)
                    draw_height = min(160, image.Height or 160)
                    pdf.drawImage(img, _LEFT_MARGIN, max(_LEFT_MARGIN, cursor_y - draw_height), width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
                    cursor_y -= draw_height + 12
                except Exception:
                    pdf.setFont(_register_font_variant("sans", False, True), 10)
                    pdf.drawString(_LEFT_MARGIN, cursor_y, image.FileName or "[image]")
                    cursor_y -= 14

            if index != len(selected) - 1:
                pdf.showPage()
        else:
            pdf.setFont(_register_font_variant("sans", False, False), 12)
            pdf.drawString(_LEFT_MARGIN, cursor_y, document.DisplayName or "Empty document")

    pdf.save()
    return buffer.getvalue()