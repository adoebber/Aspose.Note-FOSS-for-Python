from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
import re
import struct

from ..onestore.parser import ExtendedGUID, OneStoreFile, OneStoreObject, parse_onestore_file
from ...enums import HorizontalAlignment
from .entities import LogicalDocument, LogicalNode
from ...model import (
    AttachedFile,
    Document,
    Image,
    NoteTag,
    NumberList,
    Outline,
    OutlineElement,
    Page,
    RichText,
    Table,
    TableCell,
    TableRow,
    TextRun,
    TextStyle,
    Title,
    _filetime_to_datetime,
    _time32_to_datetime,
)

ROOT_ROLE_DEFAULT_CONTENT = 0x00000001
ROOT_ROLE_METADATA = 0x00000002
STRUCTURE_PROPERTIES = {
    "ElementChildNodes",
    "ContentChildNodes",
    "StructureElementChildNodes",
    "ChildGraphSpaceElementNodes",
    "ListNodes",
    "TextRunDataObject",
}
METADATA_PROPERTIES = {"MetaDataObjectsAboveGraphSpace"}
PUBLIC_CONTAINER_KINDS = {"SectionNode", "PageSeriesNode", "OutlineGroup", "PageManifestNode", "VersionHistoryContent", "VersionProxy"}


@dataclass(slots=True)
class LoadedOneNoteDocument:
    display_name: str | None
    logical_document: LogicalDocument
    pages: list[Page]


def _decode_utf16(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-16le", errors="ignore").rstrip("\x00") or None
    return str(value)


def _decode_ascii_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        for encoding in ("utf-8", "latin-1"):
            try:
                return value.decode(encoding, errors="ignore").rstrip("\x00") or None
            except Exception:
                continue
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _u32_to_float(value: int | None) -> float | None:
    if value is None:
        return None
    return struct.unpack("<f", struct.pack("<I", int(value)))[0]


def _bytes_to_float_list(value: Any) -> list[float]:
    if not isinstance(value, (bytes, bytearray)):
        return []
    result: list[float] = []
    for offset in range(0, len(value) - (len(value) % 4), 4):
        result.append(struct.unpack("<f", value[offset : offset + 4])[0])
    return result


def _decode_paragraph_alignment(value: Any) -> HorizontalAlignment | None:
    if not isinstance(value, int):
        return None
    return {
        0: HorizontalAlignment.Left,
        1: HorizontalAlignment.Center,
        2: HorizontalAlignment.Right,
    }.get(value)


def _decode_layout_alignment(value: Any) -> HorizontalAlignment | None:
    if not isinstance(value, int) or value == 0:
        return None
    horizontal_alignment = value & 0x7
    return {
        1: HorizontalAlignment.Left,
        2: HorizontalAlignment.Center,
        3: HorizontalAlignment.Right,
        4: HorizontalAlignment.Left,
        5: HorizontalAlignment.Right,
    }.get(horizontal_alignment)


def _flatten_refs(value: Any) -> list[ExtendedGUID]:
    if isinstance(value, ExtendedGUID):
        return [value]
    if isinstance(value, list):
        result: list[ExtendedGUID] = []
        for item in value:
            result.extend(_flatten_refs(item))
        return result
    if isinstance(value, dict):
        result: list[ExtendedGUID] = []
        for item in value.values():
            result.extend(_flatten_refs(item))
        return result
    return []


def _decode_number_list_format(value: Any) -> str | None:
    text = _decode_utf16(value)
    if text:
        return text
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return None


def _unique_tags(tags: list[NoteTag]) -> list[NoteTag]:
    seen: set[tuple[Any, ...]] = set()
    result: list[NoteTag] = []
    for tag in tags:
        key = (tag.label, tag.shape, tag.text_color, tag.highlight_color, tag.created, tag.completed)
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
    return result


class _Builder:
    def __init__(self, parsed: OneStoreFile) -> None:
        self.parsed = parsed
        self.section_space = self._select_section_space(parsed)
        self.content_space = self._select_content_space(parsed)
        self.space = self.content_space or self.section_space
        self.objects = self.space.objects if self.space is not None else {}

    def build(self) -> LoadedOneNoteDocument:
        logical_root = self._build_logical_root()
        pages = self._build_pages(logical_root)
        display_name = None
        if self.section_space and self.section_space.section_display_name:
            display_name = self.section_space.section_display_name
        elif self.content_space and self.content_space.section_display_name:
            display_name = self.content_space.section_display_name
        else:
            display_name = self.parsed.display_name
        if display_name is None and pages:
            display_name = pages[0].Title.TitleText.Text if pages[0].Title and pages[0].Title.TitleText else None
        return LoadedOneNoteDocument(display_name=display_name, logical_document=LogicalDocument(logical_root), pages=pages)

    def _select_section_space(self, parsed: OneStoreFile):
        for space in parsed.object_spaces:
            root = space.root_roles.get(ROOT_ROLE_DEFAULT_CONTENT)
            if root is None:
                continue
            record = space.objects.get(root)
            if record and record.jcid_name == "SectionNode":
                return space
        return None

    def _select_content_space(self, parsed: OneStoreFile):
        best_space = None
        best_score = -1
        for space in parsed.object_spaces:
            score = sum(1 for obj in space.objects.values() if obj.jcid_name in {"PageNode", "OutlineNode", "RichTextOENode", "ImageNode", "TableNode", "EmbeddedFileNode"})
            if score > best_score:
                best_space = space
                best_score = score
        return best_space or self._select_section_space(parsed)

    def _build_logical_root(self) -> LogicalNode | None:
        if self.space is None:
            return None
        root = self.space.root_roles.get(ROOT_ROLE_DEFAULT_CONTENT)
        if root is None:
            return None
        return self._build_logical_node(root, set())

    def _ordered_property_refs(self, record: OneStoreObject, allowed: set[str]) -> list[ExtendedGUID]:
        refs: list[ExtendedGUID] = []
        for name, value in record.raw_properties:
            if name not in allowed:
                continue
            refs.extend(_flatten_refs(value))
        return refs

    def _build_logical_node(self, oid: ExtendedGUID, stack: set[ExtendedGUID]) -> LogicalNode | None:
        record = self.objects.get(oid)
        if record is None:
            return None
        if oid in stack:
            return LogicalNode(kind=record.jcid_name, oid=oid, properties=record.properties)
        next_stack = set(stack)
        next_stack.add(oid)
        children = [child for child in (self._build_logical_node(ref, next_stack) for ref in self._ordered_property_refs(record, STRUCTURE_PROPERTIES)) if child is not None]
        metadata = [child for child in (self._build_logical_node(ref, next_stack) for ref in self._ordered_property_refs(record, METADATA_PROPERTIES)) if child is not None]
        return LogicalNode(kind=record.jcid_name, oid=oid, properties=record.properties, children=children, metadata=metadata)

    def _find_metadata_record(self, node: LogicalNode | None, kind: str) -> OneStoreObject | None:
        if node is None:
            return None
        for metadata in node.metadata:
            record = self.objects.get(metadata.oid)
            if record and record.jcid_name == kind:
                return record
        return None

    def _descendants(self, node: LogicalNode | None) -> list[LogicalNode]:
        if node is None:
            return []
        result: list[LogicalNode] = []
        stack = [node]
        while stack:
            current = stack.pop()
            result.append(current)
            stack.extend(reversed(current.children))
        return result

    def _build_pages(self, root: LogicalNode | None) -> list[Page]:
        pages: list[Page] = []
        for node in self._descendants(root):
            if node.kind == "PageNode":
                pages.append(self._build_page(node))
        if pages:
            return pages

        page_nodes = [obj.oid for obj in self.objects.values() if obj.jcid_name == "PageNode"]
        for oid in page_nodes:
            logical_page = self._build_logical_node(oid, set())
            if logical_page is not None:
                pages.append(self._build_page(logical_page))
        return pages

    def _build_page(self, node: LogicalNode) -> Page:
        page = Page()
        record = self.objects.get(node.oid)
        metadata = self._find_metadata_record(node, "PageMetaData")
        if record is not None:
            page.Author = _decode_utf16(record.properties.get("Author"))
            page.CreationTime = _time32_to_datetime(record.properties.get("CreationTimeStamp"))
            page.LastModifiedTime = _filetime_to_datetime(record.properties.get("LastModifiedTimeStamp")) or _time32_to_datetime(record.properties.get("LastModifiedTime"))
            level = record.properties.get("PageLevel")
            page.Level = int(level) if isinstance(level, int) else None
        if metadata is not None:
            page.Author = page.Author or _decode_utf16(metadata.properties.get("Author"))
            page.CreationTime = page.CreationTime or _time32_to_datetime(metadata.properties.get("CreationTimeStamp"))
            page.LastModifiedTime = page.LastModifiedTime or _filetime_to_datetime(metadata.properties.get("LastModifiedTimeStamp")) or _time32_to_datetime(metadata.properties.get("LastModifiedTime"))
            level = metadata.properties.get("PageLevel")
            if page.Level is None and isinstance(level, int):
                page.Level = int(level)

        title_node = next((child for child in node.children if child.kind == "TitleNode"), None)
        if title_node is not None:
            page.Title = self._build_title(title_node)
            page.AppendChildLast(page.Title)

        for child in node.children:
            if child.kind == "TitleNode":
                continue
            public_child = self._build_public_node(child)
            if public_child is not None:
                page.AppendChildLast(public_child)

        if page.Title is None:
            title_text = None
            if metadata is not None:
                title_text = _decode_utf16(metadata.properties.get("CachedTitleString")) or _decode_utf16(metadata.properties.get("CachedTitleStringFromPage"))
            if title_text:
                title = Title()
                title.TitleText = RichText(Text=title_text, Runs=[TextRun(Text=title_text, Start=0, End=len(title_text))])
                title.AppendChildLast(title.TitleText)
                page.Title = title
                page.AppendChildFirst(title)

        return page

    def _collect_richtexts(self, node: LogicalNode) -> list[LogicalNode]:
        return [candidate for candidate in self._descendants(node) if candidate.kind == "RichTextOENode"]

    def _build_title(self, node: LogicalNode) -> Title:
        title = Title()
        richtexts = self._collect_richtexts(node)
        if richtexts:
            title.TitleText = self._build_richtext(richtexts[0])
            title.AppendChildLast(title.TitleText)
        if len(richtexts) > 1:
            title.TitleDate = self._build_richtext(richtexts[1])
            title.AppendChildLast(title.TitleDate)
        if len(richtexts) > 2:
            title.TitleTime = self._build_richtext(richtexts[2])
            title.AppendChildLast(title.TitleTime)
        return title

    def _build_public_node(self, node: LogicalNode):
        if node.kind in PUBLIC_CONTAINER_KINDS:
            return None
        if node.kind == "OutlineNode":
            return self._build_outline(node)
        if node.kind == "OutlineElementNode":
            return self._build_outline_element(node)
        if node.kind == "RichTextOENode":
            return self._build_richtext(node)
        if node.kind == "ImageNode":
            return self._build_image(node)
        if node.kind == "EmbeddedFileNode":
            return self._build_attached_file(node)
        if node.kind == "TableNode":
            return self._build_table(node)
        if node.kind == "TableRowNode":
            return self._build_table_row(node)
        if node.kind == "TableCellNode":
            return self._build_table_cell(node)
        return None

    def _append_public_children(self, parent, node: LogicalNode) -> None:
        for child in node.children:
            public_child = self._build_public_node(child)
            if public_child is not None:
                parent.AppendChildLast(public_child)
            elif child.kind in PUBLIC_CONTAINER_KINDS:
                self._append_public_children(parent, child)

    def _build_outline(self, node: LogicalNode) -> Outline:
        record = self.objects[node.oid]
        outline = Outline(
            X=_u32_to_float(record.properties.get("OffsetFromParentHoriz")),
            Y=_u32_to_float(record.properties.get("OffsetFromParentVert")),
            Width=_u32_to_float(record.properties.get("LayoutMaxWidth")),
        )
        self._append_public_children(outline, node)
        return outline

    def _build_outline_element(self, node: LogicalNode) -> OutlineElement:
        record = self.objects[node.oid]
        outline_element = OutlineElement(
            IndentLevel=int(record.properties.get("OutlineElementChildLevel") or 0),
            Tags=self._collect_tags(record),
        )

        list_nodes = [child for child in node.children if child.kind == "NumberListNode"]
        if list_nodes:
            outline_element.NumberList = self._build_number_list(list_nodes[0])

        ordered_children = [child for child in node.children if child.kind not in {"NumberListNode", "OutlineElementNode"}]
        ordered_children.extend(child for child in node.children if child.kind == "OutlineElementNode")

        for child in ordered_children:
            public_child = self._build_public_node(child)
            if public_child is not None:
                if isinstance(public_child, RichText) and not public_child.Tags and outline_element.Tags:
                    public_child.Tags = list(outline_element.Tags)
                outline_element.AppendChildLast(public_child)
        return outline_element

    def _resolve_style_properties(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, ExtendedGUID):
            target = self.objects.get(value)
            if target is not None:
                return target.properties
        return {}

    def _style_from_properties(self, properties: Any) -> TextStyle:
        resolved = self._resolve_style_properties(properties)
        return TextStyle(
            IsHyperlink=bool(resolved.get("Hyperlink") or resolved.get("WzHyperlinkUrl")),
            HyperlinkAddress=_decode_utf16(resolved.get("WzHyperlinkUrl")),
            HorizontalAlignment=_decode_paragraph_alignment(resolved.get("ParagraphAlignment")),
            FontName=_decode_utf16(resolved.get("Font")),
            FontSize=(float(resolved["FontSize"]) / 2.0) if isinstance(resolved.get("FontSize"), int) else None,
            FontColor=resolved.get("FontColor") if isinstance(resolved.get("FontColor"), int) else None,
            HighlightColor=resolved.get("Highlight") if isinstance(resolved.get("Highlight"), int) else None,
            LanguageId=resolved.get("LanguageID") if isinstance(resolved.get("LanguageID"), int) else None,
            Bold=bool(resolved.get("Bold")),
            Italic=bool(resolved.get("Italic")),
            Underline=bool(resolved.get("Underline")),
            Strikethrough=bool(resolved.get("Strikethrough")),
            Superscript=bool(resolved.get("Superscript")),
            Subscript=bool(resolved.get("Subscript")),
        )

    def _decode_run_boundaries(self, raw: Any, run_count: int, text_length: int) -> list[int]:
        if not isinstance(raw, (bytes, bytearray)) or run_count <= 0:
            return [0] * run_count
        for width in (4, 2):
            if len(raw) % width != 0:
                continue
            values = [int.from_bytes(raw[index : index + width], "little") for index in range(0, len(raw), width)]
            if len(values) not in {run_count - 1, run_count}:
                continue
            if values and all(0 <= value <= text_length for value in values) and values == sorted(values):
                return values[:run_count]
        return [0] * run_count

    def _build_richtext(self, node: LogicalNode) -> RichText:
        record = self.objects[node.oid]
        text = _decode_utf16(record.properties.get("RichEditTextUnicode")) or _decode_ascii_text(record.properties.get("TextExtendedAscii")) or ""
        rich_text = RichText(Text=text, FontSize=(float(record.properties["FontSize"]) / 2.0) if isinstance(record.properties.get("FontSize"), int) else None, Tags=self._collect_tags(record))

        run_styles_raw = record.properties.get("TextRunFormatting")
        base_style = self._style_from_properties(record.properties)

        if isinstance(run_styles_raw, list) and run_styles_raw:
            boundaries = self._decode_run_boundaries(record.properties.get("TextRunIndex"), len(run_styles_raw), len(text))
            if not boundaries or boundaries[0] != 0:
                boundaries = [0] + boundaries
            boundaries = sorted(boundaries[: len(run_styles_raw)] + [len(text)])
            for index, style_props in enumerate(run_styles_raw):
                start = boundaries[index] if index < len(boundaries) else 0
                end = boundaries[index + 1] if index + 1 < len(boundaries) else len(text)
                run_text = text[start:end]
                rich_text.Runs.append(TextRun(Text=run_text, Style=self._style_from_properties(style_props), Start=start, End=end))
        elif text:
            rich_text.Runs.append(TextRun(Text=text, Style=base_style, Start=0, End=len(text)))

        return rich_text

    def _resolve_file_bytes(self, record: OneStoreObject, property_name: str) -> bytes:
        ref = record.properties.get(property_name)
        if not isinstance(ref, ExtendedGUID):
            return b""
        target = self.objects.get(ref)
        if target is None:
            return b""
        reference = target.file_data_reference or ""
        if reference.lower().startswith("<ifndf>"):
            match = re.search(r"([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})", reference)
            if match is not None:
                return self.parsed.file_data_store.get(match.group(1).lower(), b"")
        return b""

    def _build_image(self, node: LogicalNode) -> Image:
        record = self.objects[node.oid]
        image = Image(
            FileName=_decode_utf16(record.properties.get("ImageFilename")),
            Bytes=self._resolve_file_bytes(record, "PictureContainer") or self._resolve_file_bytes(record, "WebPictureContainer14"),
            Width=_u32_to_float(record.properties.get("PictureWidth")),
            Height=_u32_to_float(record.properties.get("PictureHeight")),
            HorizontalAlignment=_decode_layout_alignment(record.properties.get("LayoutAlignmentSelf"))
            or _decode_layout_alignment(record.properties.get("LayoutAlignmentInParent")),
            AlternativeTextDescription=_decode_utf16(record.properties.get("ImageAltText")),
            HyperlinkUrl=_decode_utf16(record.properties.get("WzHyperlinkUrl")),
            Tags=self._collect_tags(record),
        )
        return image

    def _build_attached_file(self, node: LogicalNode) -> AttachedFile:
        record = self.objects[node.oid]
        return AttachedFile(
            FileName=_decode_utf16(record.properties.get("EmbeddedFileName")) or _decode_utf16(record.properties.get("SourceFilepath")),
            Bytes=self._resolve_file_bytes(record, "EmbeddedFileContainer"),
            Tags=self._collect_tags(record),
        )

    def _build_table(self, node: LogicalNode) -> Table:
        record = self.objects[node.oid]
        table = Table(
            Tags=self._collect_tags(record),
            ColumnWidths=_bytes_to_float_list(record.properties.get("TableColumnWidths")),
            BordersVisible=bool(record.properties.get("TableBordersVisible", True)),
        )
        for child in node.children:
            if child.kind == "TableRowNode":
                table.AppendChildLast(self._build_table_row(child))
        return table

    def _build_table_row(self, node: LogicalNode) -> TableRow:
        row = TableRow()
        for child in node.children:
            if child.kind == "TableCellNode":
                row.AppendChildLast(self._build_table_cell(child))
        return row

    def _build_table_cell(self, node: LogicalNode) -> TableCell:
        cell = TableCell()
        self._append_public_children(cell, node)
        return cell

    def _build_number_list(self, node: LogicalNode) -> NumberList:
        record = self.objects[node.oid]
        fmt = _decode_number_list_format(record.properties.get("NumberListFormat"))
        restart = record.properties.get("ListRestart") if isinstance(record.properties.get("ListRestart"), int) else None
        return NumberList(Format=fmt, Restart=restart, IsNumbered=bool(fmt))

    def _tag_from_record(self, record: OneStoreObject | None) -> list[NoteTag]:
        if record is None:
            return []
        label = _decode_utf16(record.properties.get("NoteTagLabel"))
        tag = NoteTag(
            shape=record.properties.get("NoteTagShape") if isinstance(record.properties.get("NoteTagShape"), int) else None,
            label=label,
            text_color=record.properties.get("NoteTagTextColor") if isinstance(record.properties.get("NoteTagTextColor"), int) else None,
            highlight_color=record.properties.get("NoteTagHighlightColor") if isinstance(record.properties.get("NoteTagHighlightColor"), int) else None,
            created=record.properties.get("NoteTagCreated") if isinstance(record.properties.get("NoteTagCreated"), int) else None,
            completed=record.properties.get("NoteTagCompleted") if isinstance(record.properties.get("NoteTagCompleted"), int) else None,
        )
        if tag.label or tag.shape is not None:
            return [tag]
        return []

    def _tag_from_state(self, state_value: Any) -> list[NoteTag]:
        if not isinstance(state_value, dict):
            return []
        tags: list[NoteTag] = []
        definition_ref = state_value.get("NoteTagDefinitionOid")
        if isinstance(definition_ref, ExtendedGUID):
            tags.extend(self._tag_from_record(self.objects.get(definition_ref)))
        inline = NoteTag(
            shape=state_value.get("NoteTagShape") if isinstance(state_value.get("NoteTagShape"), int) else None,
            label=_decode_utf16(state_value.get("NoteTagLabel")),
            text_color=state_value.get("NoteTagTextColor") if isinstance(state_value.get("NoteTagTextColor"), int) else None,
            highlight_color=state_value.get("NoteTagHighlightColor") if isinstance(state_value.get("NoteTagHighlightColor"), int) else None,
            created=state_value.get("NoteTagCreated") if isinstance(state_value.get("NoteTagCreated"), int) else None,
            completed=state_value.get("NoteTagCompleted") if isinstance(state_value.get("NoteTagCompleted"), int) else None,
        )
        if inline.label or inline.shape is not None:
            tags.append(inline)
        return tags

    def _collect_tags(self, record: OneStoreObject) -> list[NoteTag]:
        tags = self._tag_from_record(record)
        note_tag_states = record.properties.get("NoteTagStates")
        if isinstance(note_tag_states, list):
            for state in note_tag_states:
                tags.extend(self._tag_from_state(state))
        for name, value in record.raw_properties:
            if name not in {"NoteTagDefinitionOid", "MetaDataObjectsAboveGraphSpace", "NoteTagStates"}:
                continue
            for ref in _flatten_refs(value):
                target = self.objects.get(ref)
                if target is None:
                    continue
                tags.extend(self._tag_from_record(target))
                nested_ref = target.properties.get("NoteTagDefinitionOid")
                if isinstance(nested_ref, ExtendedGUID):
                    tags.extend(self._tag_from_record(self.objects.get(nested_ref)))
        return _unique_tags(tags)


def load_onenote_document(source: str | Path | BinaryIO) -> LoadedOneNoteDocument:
    parsed = parse_onestore_file(source)
    return _Builder(parsed).build()