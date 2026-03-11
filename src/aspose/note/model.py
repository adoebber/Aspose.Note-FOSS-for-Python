from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from io import BufferedIOBase, BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Iterator, TypeVar

from .enums import FileFormat, HorizontalAlignment, SaveFormat
from .exceptions import IncorrectPasswordException, UnsupportedSaveFormatException
from .saving.options import HtmlSaveOptions, ImageSaveOptions, OneSaveOptions, PdfSaveOptions, SaveOptions

TNode = TypeVar("TNode", bound="Node")


def _time32_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime(1980, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=int(value))


def _filetime_to_datetime(value: int | None) -> datetime | None:
    if value is None:
        return None
    return datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=int(value) / 10)


class DocumentVisitor:
    def VisitDocumentStart(self, document: Document) -> None:  # noqa: N802
        pass

    def VisitDocumentEnd(self, document: Document) -> None:  # noqa: N802
        pass

    def VisitPageStart(self, page: Page) -> None:  # noqa: N802
        pass

    def VisitPageEnd(self, page: Page) -> None:  # noqa: N802
        pass

    def VisitTitleStart(self, title: Title) -> None:  # noqa: N802
        pass

    def VisitTitleEnd(self, title: Title) -> None:  # noqa: N802
        pass

    def VisitOutlineStart(self, outline: Outline) -> None:  # noqa: N802
        pass

    def VisitOutlineEnd(self, outline: Outline) -> None:  # noqa: N802
        pass

    def VisitOutlineElementStart(self, outline_element: OutlineElement) -> None:  # noqa: N802
        pass

    def VisitOutlineElementEnd(self, outline_element: OutlineElement) -> None:  # noqa: N802
        pass

    def VisitRichTextStart(self, rich_text: RichText) -> None:  # noqa: N802
        pass

    def VisitRichTextEnd(self, rich_text: RichText) -> None:  # noqa: N802
        pass

    def VisitImageStart(self, image: Image) -> None:  # noqa: N802
        pass

    def VisitImageEnd(self, image: Image) -> None:  # noqa: N802
        pass


class License:
    def SetLicense(self, license_path_or_stream: Any) -> None:  # noqa: N802
        return None


class Metered:
    def SetMeteredKey(self, public_key: str, private_key: str) -> None:  # noqa: N802
        return None


@dataclass(slots=True)
class LoadOptions:
    DocumentPassword: str | None = None
    LoadHistory: bool = False


@dataclass(slots=True)
class Node:
    ParentNode: Node | None = None

    @property
    def Document(self) -> Document | None:
        current: Node | None = self
        while current is not None:
            if isinstance(current, Document):
                return current
            current = current.ParentNode
        return None

    def Accept(self, visitor: DocumentVisitor) -> None:  # noqa: N802
        self._accept(visitor)

    def _accept(self, visitor: DocumentVisitor) -> None:
        return None


@dataclass(slots=True)
class CompositeNode(Node):
    _children: list[Node] = field(default_factory=list)

    @property
    def FirstChild(self) -> Node | None:  # noqa: N802
        return self._children[0] if self._children else None

    @property
    def LastChild(self) -> Node | None:  # noqa: N802
        return self._children[-1] if self._children else None

    def AppendChildLast(self, node: TNode) -> TNode:  # noqa: N802
        node.ParentNode = self
        self._children.append(node)
        return node

    def AppendChildFirst(self, node: TNode) -> TNode:  # noqa: N802
        node.ParentNode = self
        self._children.insert(0, node)
        return node

    def InsertChild(self, index: int, node: TNode) -> TNode:  # noqa: N802
        node.ParentNode = self
        self._children.insert(index, node)
        return node

    def RemoveChild(self, node: Node) -> None:  # noqa: N802
        self._children.remove(node)
        node.ParentNode = None

    def GetEnumerator(self) -> Iterator[Node]:  # noqa: N802
        return iter(self._children)

    def __iter__(self) -> Iterator[Node]:
        return iter(self._children)

    def GetChildNodes(self, node_type: type[TNode]) -> list[TNode]:  # noqa: N802
        found: list[TNode] = []
        for child in self._children:
            if isinstance(child, node_type):
                found.append(child)
            if isinstance(child, CompositeNode):
                found.extend(child.GetChildNodes(node_type))
        return found


@dataclass(slots=True)
class NoteTag(Node):
    shape: int | None = None
    label: str | None = None
    text_color: int | None = None
    highlight_color: int | None = None
    created: int | None = None
    completed: int | None = None

    @staticmethod
    def CreateYellowStar() -> NoteTag:
        return NoteTag(label="Yellow Star")


@dataclass(slots=True)
class TextStyle(Node):
    IsHyperlink: bool = False
    HyperlinkAddress: str | None = None
    HorizontalAlignment: HorizontalAlignment | None = None
    FontName: str | None = None
    FontSize: float | None = None
    FontColor: int | None = None
    HighlightColor: int | None = None
    LanguageId: int | None = None
    Bold: bool = False
    Italic: bool = False
    Underline: bool = False
    Strikethrough: bool = False
    Superscript: bool = False
    Subscript: bool = False


@dataclass(slots=True)
class TextRun(Node):
    Text: str = ""
    Style: TextStyle = field(default_factory=TextStyle)
    Start: int | None = None
    End: int | None = None


@dataclass(slots=True)
class RichText(CompositeNode):
    Text: str = ""
    Runs: list[TextRun] = field(default_factory=list)
    FontSize: float | None = None
    Tags: list[NoteTag] = field(default_factory=list)

    def Append(self, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        start = len(self.Text)
        self.Text += text
        self.Runs.append(TextRun(Text=text, Style=style or TextStyle(), Start=start, End=len(self.Text)))
        return self

    def Replace(self, old_value: str, new_value: str) -> None:  # noqa: N802
        self.Text = self.Text.replace(old_value, new_value)
        if self.Runs:
            self.Runs = [TextRun(Text=self.Text, Style=self.Runs[0].Style, Start=0, End=len(self.Text))]

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitRichTextStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitRichTextEnd(self)


@dataclass(slots=True)
class Title(CompositeNode):
    TitleText: RichText | None = None
    TitleDate: RichText | None = None
    TitleTime: RichText | None = None

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitTitleStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitTitleEnd(self)


@dataclass(slots=True)
class NumberList(Node):
    Format: str | None = None
    Restart: int | None = None
    IsNumbered: bool = False


@dataclass(slots=True)
class OutlineElement(CompositeNode):
    Tags: list[NoteTag] = field(default_factory=list)
    IndentLevel: int = 0
    NumberList: NumberList | None = None

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitOutlineElementStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitOutlineElementEnd(self)


@dataclass(slots=True)
class Outline(CompositeNode):
    X: float | None = None
    Y: float | None = None
    Width: float | None = None

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitOutlineStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitOutlineEnd(self)


@dataclass(slots=True)
class Image(CompositeNode):
    FileName: str | None = None
    Bytes: bytes = b""
    Width: float | None = None
    Height: float | None = None
    HorizontalAlignment: HorizontalAlignment | None = None
    AlternativeTextTitle: str | None = None
    AlternativeTextDescription: str | None = None
    HyperlinkUrl: str | None = None
    Tags: list[NoteTag] = field(default_factory=list)

    def Replace(self, image: Image) -> None:  # noqa: N802
        self.FileName = image.FileName
        self.Bytes = image.Bytes
        self.Width = image.Width
        self.Height = image.Height
        self.HorizontalAlignment = image.HorizontalAlignment
        self.AlternativeTextTitle = image.AlternativeTextTitle
        self.AlternativeTextDescription = image.AlternativeTextDescription
        self.HyperlinkUrl = image.HyperlinkUrl
        self.Tags = list(image.Tags)

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitImageStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitImageEnd(self)


@dataclass(slots=True)
class AttachedFile(CompositeNode):
    FileName: str | None = None
    Bytes: bytes = b""
    Tags: list[NoteTag] = field(default_factory=list)


@dataclass(slots=True)
class TableCell(CompositeNode):
    pass


@dataclass(slots=True)
class TableRow(CompositeNode):
    pass


@dataclass(slots=True)
class Table(CompositeNode):
    Tags: list[NoteTag] = field(default_factory=list)
    ColumnWidths: list[float] = field(default_factory=list)
    BordersVisible: bool = True


@dataclass(slots=True)
class Page(CompositeNode):
    Title: Title | None = None
    Author: str | None = None
    CreationTime: datetime | None = None
    LastModifiedTime: datetime | None = None
    Level: int | None = None

    def Clone(self, deep: bool = False) -> Page:  # noqa: N802
        return deepcopy(self) if deep else Page(
            Title=self.Title,
            Author=self.Author,
            CreationTime=self.CreationTime,
            LastModifiedTime=self.LastModifiedTime,
            Level=self.Level,
        )

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitPageStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitPageEnd(self)


class Document(CompositeNode):
    def __init__(self, source: str | Path | BinaryIO | None = None, load_options: LoadOptions | None = None) -> None:
        super().__init__()
        self.DisplayName: str | None = None
        self.CreationTime: datetime | None = None
        self._onenote_doc: Any | None = None

        if source is None:
            return

        load_options = load_options or LoadOptions()
        if load_options.DocumentPassword:
            raise IncorrectPasswordException("Password-protected documents are not supported")

        from ._internal.ms_one.loader import load_onenote_document

        loaded = load_onenote_document(source)
        self.DisplayName = loaded.display_name
        self._onenote_doc = loaded
        for page in loaded.pages:
            self.AppendChildLast(page)

    @property
    def FileFormat(self) -> FileFormat:  # noqa: N802
        return FileFormat.OneNote2010

    def Count(self) -> int:  # noqa: N802
        return len(self._children)

    def DetectLayoutChanges(self) -> None:  # noqa: N802
        return None

    def GetPageHistory(self, page: Page) -> list[Page]:  # noqa: N802
        return [page]

    def Save(self, target: str | Path | BinaryIO, format_or_options: SaveFormat | SaveOptions | None = None) -> None:  # noqa: N802
        if format_or_options is None:
            save_format = SaveFormat.One
            options: SaveOptions | None = None
        elif isinstance(format_or_options, SaveFormat):
            save_format = format_or_options
            options = PdfSaveOptions(SaveFormat.Pdf) if save_format is SaveFormat.Pdf else None
        else:
            save_format = format_or_options.SaveFormat
            options = format_or_options

        if save_format is not SaveFormat.Pdf:
            raise UnsupportedSaveFormatException(f"Save format {save_format.value!r} is not supported")

        from .saving.pdf_writer import write_pdf

        data = write_pdf(self, options if isinstance(options, PdfSaveOptions) else PdfSaveOptions(SaveFormat.Pdf))
        if isinstance(target, (str, Path)):
            Path(target).write_bytes(data)
            return
        if isinstance(target, (BytesIO, BufferedIOBase)) or hasattr(target, "write"):
            target.write(data)
            return
        raise TypeError("Unsupported save target")

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitDocumentStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitDocumentEnd(self)


__all__ = [
    "DocumentVisitor",
    "License",
    "Metered",
    "LoadOptions",
    "Node",
    "CompositeNode",
    "NoteTag",
    "TextStyle",
    "TextRun",
    "RichText",
    "Title",
    "NumberList",
    "OutlineElement",
    "Outline",
    "Image",
    "AttachedFile",
    "TableCell",
    "TableRow",
    "Table",
    "Page",
    "Document",
    "SaveOptions",
    "PdfSaveOptions",
    "OneSaveOptions",
    "HtmlSaveOptions",
    "ImageSaveOptions",
    "_time32_to_datetime",
    "_filetime_to_datetime",
]