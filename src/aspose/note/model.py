from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from io import BufferedIOBase, BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Iterator, TypeVar

from .enums import FileFormat, HorizontalAlignment, SaveFormat
from .exceptions import IncorrectPasswordException, UnsupportedSaveFormatException
from .saving.options import PdfSaveOptions, SaveOptions

TNode = TypeVar("TNode", bound="Node")


class _classproperty:  # noqa: N801
    def __init__(self, getter):
        self._getter = getter

    def __get__(self, instance, owner):
        return self._getter(owner)


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

    @property
    def IsBold(self) -> bool:  # noqa: N802
        return self.Bold

    @IsBold.setter
    def IsBold(self, value: bool) -> None:  # noqa: N802
        self.Bold = bool(value)

    @property
    def IsItalic(self) -> bool:  # noqa: N802
        return self.Italic

    @IsItalic.setter
    def IsItalic(self, value: bool) -> None:  # noqa: N802
        self.Italic = bool(value)

    @property
    def IsUnderline(self) -> bool:  # noqa: N802
        return self.Underline

    @IsUnderline.setter
    def IsUnderline(self, value: bool) -> None:  # noqa: N802
        self.Underline = bool(value)

    @property
    def IsStrikethrough(self) -> bool:  # noqa: N802
        return self.Strikethrough

    @IsStrikethrough.setter
    def IsStrikethrough(self, value: bool) -> None:  # noqa: N802
        self.Strikethrough = bool(value)

    @property
    def IsSuperscript(self) -> bool:  # noqa: N802
        return self.Superscript

    @IsSuperscript.setter
    def IsSuperscript(self, value: bool) -> None:  # noqa: N802
        self.Superscript = bool(value)

    @property
    def IsSubscript(self) -> bool:  # noqa: N802
        return self.Subscript

    @IsSubscript.setter
    def IsSubscript(self, value: bool) -> None:  # noqa: N802
        self.Subscript = bool(value)

    @property
    def Highlight(self) -> int | None:  # noqa: N802
        return self.HighlightColor

    @Highlight.setter
    def Highlight(self, value: int | None) -> None:  # noqa: N802
        self.HighlightColor = value

    @property
    def Language(self) -> int | None:  # noqa: N802
        return self.LanguageId

    @Language.setter
    def Language(self, value: int | None) -> None:  # noqa: N802
        self.LanguageId = value

    @_classproperty
    def Default(cls) -> TextStyle:  # noqa: N802
        return cls(LanguageId=1033)

    @_classproperty
    def DefaultMsOneNoteTitleTextStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=20.0, Bold=True, LanguageId=1033)

    @_classproperty
    def DefaultMsOneNoteTitleDateStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=11.0, LanguageId=1033)

    @_classproperty
    def DefaultMsOneNoteTitleTimeStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=11.0, LanguageId=1033)


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
    ParagraphStyle: TextStyle = field(default_factory=TextStyle)
    FontSize: float | None = None
    LastModifiedTime: datetime | None = None
    SpaceBefore: float | None = None
    SpaceAfter: float | None = None
    LineSpacing: float | None = None
    Tags: list[NoteTag] = field(default_factory=list)

    def Append(self, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        start = len(self.Text)
        self.Text += text
        self.Runs.append(TextRun(Text=text, Style=style or TextStyle(), Start=start, End=len(self.Text)))
        return self

    @property
    def TextRuns(self) -> list[TextRun]:  # noqa: N802
        return self.Runs

    @property
    def Length(self) -> int:  # noqa: N802
        return len(self.Text)

    @property
    def Alignment(self) -> HorizontalAlignment | None:  # noqa: N802
        if self.ParagraphStyle.HorizontalAlignment is not None:
            return self.ParagraphStyle.HorizontalAlignment
        for run in self.Runs:
            if run.Style.HorizontalAlignment is not None:
                return run.Style.HorizontalAlignment
        return None

    @Alignment.setter
    def Alignment(self, value: HorizontalAlignment | None) -> None:  # noqa: N802
        self.ParagraphStyle.HorizontalAlignment = value
        for run in self.Runs:
            if run.Style.HorizontalAlignment is None:
                run.Style.HorizontalAlignment = value

    @property
    def IsTitleText(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleText is self)

    @property
    def IsTitleDate(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleDate is self)

    @property
    def IsTitleTime(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleTime is self)

    def AppendFront(self, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        self.Insert(0, text, style)
        return self

    def Clear(self) -> RichText:  # noqa: N802
        self.Text = ""
        self.Runs = []
        return self

    def GetEnumerator(self) -> Iterator[str]:  # noqa: N802
        return iter(self.Text)

    def Insert(self, index: int, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        index = max(0, min(index, len(self.Text)))
        self.Text = self.Text[:index] + text + self.Text[index:]
        effective_style = style or (self.Runs[0].Style if self.Runs else TextStyle())
        if self.Text:
            self.Runs = [TextRun(Text=self.Text, Style=effective_style, Start=0, End=len(self.Text))]
        else:
            self.Runs = []
        return self

    def Remove(self, start: int, count: int | None = None) -> RichText:  # noqa: N802
        start = max(0, min(start, len(self.Text)))
        end = len(self.Text) if count is None else max(start, min(start + count, len(self.Text)))
        self.Text = self.Text[:start] + self.Text[end:]
        if self.Runs:
            self.Runs = [TextRun(Text=self.Text, Style=self.Runs[0].Style, Start=0, End=len(self.Text))] if self.Text else []
        return self

    def Replace(self, old_value: str, new_value: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        if old_value is None or new_value is None:
            raise ValueError("old_value and new_value must not be None")
        if old_value == "":
            raise ValueError("old_value must not be empty")
        self.Text = self.Text.replace(old_value, new_value)
        effective_style = style or (self.Runs[0].Style if self.Runs else TextStyle())
        if self.Runs:
            self.Runs = [TextRun(Text=self.Text, Style=effective_style, Start=0, End=len(self.Text))] if self.Text else []
        elif self.Text:
            self.Runs = [TextRun(Text=self.Text, Style=effective_style, Start=0, End=len(self.Text))]
        return self

    def Trim(self) -> RichText:  # noqa: N802
        trimmed = self.Text.strip()
        if trimmed == self.Text:
            return self
        return self.Replace(self.Text, trimmed)

    def TrimStart(self) -> RichText:  # noqa: N802
        trimmed = self.Text.lstrip()
        if trimmed == self.Text:
            return self
        return self.Replace(self.Text, trimmed)

    def TrimEnd(self) -> RichText:  # noqa: N802
        trimmed = self.Text.rstrip()
        if trimmed == self.Text:
            return self
        return self.Replace(self.Text, trimmed)

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
    FilePath: str | None = None
    Format: str | None = None
    Bytes: bytes = b""
    Width: float | None = None
    Height: float | None = None
    OriginalWidth: float | None = None
    OriginalHeight: float | None = None
    HorizontalOffset: float | None = None
    VerticalOffset: float | None = None
    HorizontalAlignment: HorizontalAlignment | None = None
    IsBackground: bool = False
    LastModifiedTime: datetime | None = None
    AlternativeTextTitle: str | None = None
    AlternativeTextDescription: str | None = None
    HyperlinkUrl: str | None = None
    Tags: list[NoteTag] = field(default_factory=list)

    @property
    def Alignment(self) -> HorizontalAlignment | None:  # noqa: N802
        return self.HorizontalAlignment

    @Alignment.setter
    def Alignment(self, value: HorizontalAlignment | None) -> None:  # noqa: N802
        self.HorizontalAlignment = value

    def Replace(self, image: Image) -> None:  # noqa: N802
        self.FileName = image.FileName
        self.FilePath = image.FilePath
        self.Format = image.Format
        self.Bytes = image.Bytes
        self.Width = image.Width
        self.Height = image.Height
        self.OriginalWidth = image.OriginalWidth
        self.OriginalHeight = image.OriginalHeight
        self.HorizontalOffset = image.HorizontalOffset
        self.VerticalOffset = image.VerticalOffset
        self.HorizontalAlignment = image.HorizontalAlignment
        self.IsBackground = image.IsBackground
        self.LastModifiedTime = image.LastModifiedTime
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
    BackgroundColor: int | None = None
    Margin: Any | None = None
    SizeType: Any | None = None
    PageLayoutSize: Any | None = None
    IsConflictPage: bool = False
    PageContentRevisionSummary: Any | None = None

    def Clone(self, cloneHistory: bool = False, **kwargs: Any) -> Page:  # noqa: N802
        if "deep" in kwargs:
            cloneHistory = bool(kwargs.pop("deep"))
        if kwargs:
            raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(kwargs))}")

        cloned = deepcopy(self)
        _rebind_tree_parents(cloned, None)
        return cloned

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
            save_format = _infer_save_format(target)
            options: SaveOptions | None = PdfSaveOptions()
        elif isinstance(format_or_options, SaveFormat):
            save_format = format_or_options
            options = PdfSaveOptions()
        elif isinstance(format_or_options, SaveOptions):
            save_format = format_or_options.SaveFormat
            options = format_or_options
        else:
            raise UnsupportedSaveFormatException("Unsupported format/options argument")

        if save_format is not SaveFormat.Pdf:
            raise UnsupportedSaveFormatException("Only PDF save is supported")

        from .saving.pdf_writer import write_pdf

        data = write_pdf(self, options if isinstance(options, PdfSaveOptions) else PdfSaveOptions())
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
    "_time32_to_datetime",
    "_filetime_to_datetime",
]


def _rebind_tree_parents(node: Node, parent: Node | None) -> None:
    node.ParentNode = parent
    if isinstance(node, CompositeNode):
        for child in node:
            _rebind_tree_parents(child, node)


def _infer_save_format(target: str | Path | BinaryIO) -> SaveFormat:
    if isinstance(target, (str, Path)):
        suffix = Path(target).suffix.lower()
        if suffix == ".pdf":
            return SaveFormat.Pdf
        raise UnsupportedSaveFormatException("Only .pdf file targets are supported for save operations")
    return SaveFormat.Pdf