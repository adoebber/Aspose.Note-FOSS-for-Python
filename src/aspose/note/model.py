from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from io import BufferedIOBase, BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Iterator, TypeVar

from .enums import FileFormat, HorizontalAlignment, SaveFormat, TagStatus
from .exceptions import IncorrectPasswordException, UnsupportedSaveFormatException
from .saving.options import PdfSaveOptions, SaveOptions

TNode = TypeVar("TNode", bound="Node")
_NOTE_TAG_INTERNAL_CREATE = object()


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


def _coerce_note_tag_datetime(value: datetime | int | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    integer_value = int(value)
    if abs(integer_value) > 0xFFFFFFFF:
        return _filetime_to_datetime(integer_value)
    return _time32_to_datetime(integer_value)


def _coerce_tag_status(value: TagStatus | int | str | None) -> TagStatus | None:
    if value is None:
        return None
    if isinstance(value, TagStatus):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return None
        for status in TagStatus:
            if normalized in {status.name.lower(), str(status.value)}:
                return status
        return None
    try:
        return TagStatus(int(value))
    except (TypeError, ValueError):
        return None


class DocumentVisitor:
    def __new__(cls, *args, **kwargs):
        if cls is DocumentVisitor:
            raise TypeError("DocumentVisitor is an abstract compatibility base type and cannot be instantiated directly")
        return object.__new__(cls)

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
    _parent_node: Node | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._parent_node = None

    def __new__(cls, *args, **kwargs):
        if cls is Node:
            raise TypeError("Node is an abstract compatibility base type and cannot be instantiated directly")
        return object.__new__(cls)

    @property
    def ParentNode(self) -> Node | None:  # noqa: N802
        return self._parent_node

    def _set_parent(self, parent: Node | None) -> None:
        self._parent_node = parent

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

    def __new__(cls, *args, **kwargs):
        if cls is CompositeNode:
            raise TypeError("CompositeNode is an abstract compatibility base type and cannot be instantiated directly")
        return object.__new__(cls)

    @property
    def FirstChild(self) -> Node | None:  # noqa: N802
        return self._children[0] if self._children else None

    @property
    def LastChild(self) -> Node | None:  # noqa: N802
        return self._children[-1] if self._children else None

    def AppendChildLast(self, node: TNode) -> TNode:  # noqa: N802
        node._set_parent(self)
        self._children.append(node)
        return node

    def AppendChildFirst(self, node: TNode) -> TNode:  # noqa: N802
        node._set_parent(self)
        self._children.insert(0, node)
        return node

    def InsertChild(self, index: int, node: TNode) -> TNode:  # noqa: N802
        node._set_parent(self)
        self._children.insert(index, node)
        return node

    def RemoveChild(self, node: Node) -> None:  # noqa: N802
        self._children.remove(node)
        node._set_parent(None)

    def GetEnumerator(self) -> Iterator[Node]:  # noqa: N802
        return iter(self._children)

    def __iter__(self) -> Iterator[Node]:
        return iter(self._children)

    def GetChildNodes(self, node_type: type[TNode]) -> list[TNode]:  # noqa: N802
        found: list[TNode] = []
        for child in self._children:
            if isinstance(child, node_type):
                found.append(child)
            if _iter_node_children(child):
                found.extend(child.GetChildNodes(node_type))
        return found


class NoteTag:
    __slots__ = ("_label", "_icon", "_status", "_highlight", "_creation_time", "_completed_time", "_font_color")

    def __new__(cls, construction_token: object | None = None, /, *args, **kwargs):
        if cls is NoteTag and construction_token is not _NOTE_TAG_INTERNAL_CREATE:
            raise TypeError("NoteTag does not expose a public constructor; use NoteTag.Create* factory methods")
        return object.__new__(cls)

    def __init__(
        self,
        construction_token: object | None = None,
        /,
        *,
        Label: str | None = None,
        Icon: int | None = None,
        Status: TagStatus | int | str | None = None,
        Highlight: int | None = None,
        CreationTime: datetime | int | None = None,
        CompletedTime: datetime | int | None = None,
        FontColor: int | None = None,
    ) -> None:
        self._label = Label
        self._icon = Icon
        self._status = _coerce_tag_status(Status)
        self._highlight = Highlight
        self._creation_time = _coerce_note_tag_datetime(CreationTime)
        self._completed_time = _coerce_note_tag_datetime(CompletedTime)
        self._font_color = FontColor

    def __copy__(self) -> NoteTag:
        return type(self)._create(
            Label=self.Label,
            Icon=self.Icon,
            Status=self._status,
            Highlight=self.Highlight,
            CreationTime=self.CreationTime,
            CompletedTime=self.CompletedTime,
            FontColor=self.FontColor,
        )

    def __deepcopy__(self, memo: dict[int, object]) -> NoteTag:
        cloned = type(self)._create(
            Label=deepcopy(self.Label, memo),
            Icon=deepcopy(self.Icon, memo),
            Status=deepcopy(self._status, memo),
            Highlight=deepcopy(self.Highlight, memo),
            CreationTime=deepcopy(self.CreationTime, memo),
            CompletedTime=deepcopy(self.CompletedTime, memo),
            FontColor=deepcopy(self.FontColor, memo),
        )
        memo[id(self)] = cloned
        return cloned

    @property
    def Label(self) -> str | None:  # noqa: N802
        return self._label

    @Label.setter
    def Label(self, value: str | None) -> None:  # noqa: N802
        self._label = value

    @property
    def Icon(self) -> int | None:  # noqa: N802
        return self._icon

    @Icon.setter
    def Icon(self, value: int | None) -> None:  # noqa: N802
        self._icon = value

    @property
    def Status(self) -> TagStatus:  # noqa: N802
        if self._status is not None:
            return self._status
        return TagStatus.Completed if self._completed_time is not None else TagStatus.Open

    @property
    def Highlight(self) -> int | None:  # noqa: N802
        return self._highlight

    @Highlight.setter
    def Highlight(self, value: int | None) -> None:  # noqa: N802
        self._highlight = value

    @property
    def CreationTime(self) -> datetime | None:  # noqa: N802
        return self._creation_time

    @CreationTime.setter
    def CreationTime(self, value: datetime | int | None) -> None:  # noqa: N802
        self._creation_time = _coerce_note_tag_datetime(value)

    @property
    def CompletedTime(self) -> datetime | None:  # noqa: N802
        return self._completed_time

    @property
    def FontColor(self) -> int | None:  # noqa: N802
        return self._font_color

    @FontColor.setter
    def FontColor(self, value: int | None) -> None:  # noqa: N802
        self._font_color = value

    @classmethod
    def _create(cls, **kwargs: Any) -> NoteTag:
        return cls(_NOTE_TAG_INTERNAL_CREATE, **kwargs)

    @staticmethod
    def CreateYellowStar(label: str | None = None) -> NoteTag:
        return NoteTag._create(Label=label or "Yellow Star", Icon=13)

    @staticmethod
    def CreateQuestionMark(label: str | None = None) -> NoteTag:
        return NoteTag._create(Label=label or "Question Mark", Icon=15)

    @staticmethod
    def CreateMusicalNote(label: str | None = None) -> NoteTag:
        return NoteTag._create(Label=label or "Musical Note", Icon=121)


class ParagraphStyle:
    __slots__ = (
        "FontName",
        "FontSize",
        "FontColor",
        "Highlight",
        "IsBold",
        "IsItalic",
        "IsUnderline",
        "IsStrikethrough",
        "IsSuperscript",
        "IsSubscript",
    )

    def __init__(
        self,
        *,
        FontName: str | None = None,
        FontSize: float | None = None,
        FontColor: int | None = None,
        Highlight: int | None = None,
        IsBold: bool = False,
        IsItalic: bool = False,
        IsUnderline: bool = False,
        IsStrikethrough: bool = False,
        IsSuperscript: bool = False,
        IsSubscript: bool = False,
    ) -> None:
        self.FontName = FontName
        self.FontSize = FontSize
        self.FontColor = FontColor
        self.Highlight = Highlight
        self.IsBold = bool(IsBold)
        self.IsItalic = bool(IsItalic)
        self.IsUnderline = bool(IsUnderline)
        self.IsStrikethrough = bool(IsStrikethrough)
        self.IsSuperscript = bool(IsSuperscript)
        self.IsSubscript = bool(IsSubscript)

    @property
    def FontStyle(self) -> int:  # noqa: N802
        style = 0
        if self.IsBold:
            style |= 1
        if self.IsItalic:
            style |= 2
        if self.IsUnderline:
            style |= 4
        if self.IsStrikethrough:
            style |= 8
        return style

    @_classproperty
    def Default(cls) -> ParagraphStyle:  # noqa: N802
        return cls()


class TextStyle:
    __slots__ = (
        "_is_hyperlink",
        "_hyperlink_address",
        "_font_name",
        "_font_size",
        "_font_color",
        "_highlight",
        "_language",
        "_is_bold",
        "_is_italic",
        "_is_underline",
        "_is_strikethrough",
        "_is_superscript",
        "_is_subscript",
        "_is_hidden",
        "_is_math_formatting",
    )

    def __init__(
        self,
        *,
        IsHyperlink: bool = False,
        HyperlinkAddress: str | None = None,
        FontName: str | None = None,
        FontSize: float | None = None,
        FontColor: int | None = None,
        Highlight: int | None = None,
        Language: int | None = None,
        IsBold: bool = False,
        IsItalic: bool = False,
        IsUnderline: bool = False,
        IsStrikethrough: bool = False,
        IsSuperscript: bool = False,
        IsSubscript: bool = False,
        IsHidden: bool = False,
        IsMathFormatting: bool = False,
    ) -> None:
        self._is_hyperlink = bool(IsHyperlink)
        self._hyperlink_address = HyperlinkAddress
        self._font_name = FontName
        self._font_size = FontSize
        self._font_color = FontColor
        self._highlight = Highlight
        self._language = Language
        self._is_bold = bool(IsBold)
        self._is_italic = bool(IsItalic)
        self._is_underline = bool(IsUnderline)
        self._is_strikethrough = bool(IsStrikethrough)
        self._is_superscript = bool(IsSuperscript)
        self._is_subscript = bool(IsSubscript)
        self._is_hidden = bool(IsHidden)
        self._is_math_formatting = bool(IsMathFormatting)

    @property
    def IsHyperlink(self) -> bool:  # noqa: N802
        return self._is_hyperlink

    @IsHyperlink.setter
    def IsHyperlink(self, value: bool) -> None:  # noqa: N802
        self._is_hyperlink = bool(value)

    @property
    def HyperlinkAddress(self) -> str | None:  # noqa: N802
        return self._hyperlink_address

    @HyperlinkAddress.setter
    def HyperlinkAddress(self, value: str | None) -> None:  # noqa: N802
        self._hyperlink_address = value

    @property
    def FontName(self) -> str | None:  # noqa: N802
        return self._font_name

    @FontName.setter
    def FontName(self, value: str | None) -> None:  # noqa: N802
        self._font_name = value

    @property
    def FontSize(self) -> float | None:  # noqa: N802
        return self._font_size

    @FontSize.setter
    def FontSize(self, value: float | None) -> None:  # noqa: N802
        self._font_size = value

    @property
    def FontColor(self) -> int | None:  # noqa: N802
        return self._font_color

    @FontColor.setter
    def FontColor(self, value: int | None) -> None:  # noqa: N802
        self._font_color = value

    @property
    def Highlight(self) -> int | None:  # noqa: N802
        return self._highlight

    @Highlight.setter
    def Highlight(self, value: int | None) -> None:  # noqa: N802
        self._highlight = value

    @property
    def Language(self) -> int | None:  # noqa: N802
        return self._language

    @Language.setter
    def Language(self, value: int | None) -> None:  # noqa: N802
        self._language = value

    @property
    def IsBold(self) -> bool:  # noqa: N802
        return self._is_bold

    @IsBold.setter
    def IsBold(self, value: bool) -> None:  # noqa: N802
        self._is_bold = bool(value)

    @property
    def IsItalic(self) -> bool:  # noqa: N802
        return self._is_italic

    @IsItalic.setter
    def IsItalic(self, value: bool) -> None:  # noqa: N802
        self._is_italic = bool(value)

    @property
    def IsUnderline(self) -> bool:  # noqa: N802
        return self._is_underline

    @IsUnderline.setter
    def IsUnderline(self, value: bool) -> None:  # noqa: N802
        self._is_underline = bool(value)

    @property
    def IsStrikethrough(self) -> bool:  # noqa: N802
        return self._is_strikethrough

    @IsStrikethrough.setter
    def IsStrikethrough(self, value: bool) -> None:  # noqa: N802
        self._is_strikethrough = bool(value)

    @property
    def IsSuperscript(self) -> bool:  # noqa: N802
        return self._is_superscript

    @IsSuperscript.setter
    def IsSuperscript(self, value: bool) -> None:  # noqa: N802
        self._is_superscript = bool(value)

    @property
    def IsSubscript(self) -> bool:  # noqa: N802
        return self._is_subscript

    @IsSubscript.setter
    def IsSubscript(self, value: bool) -> None:  # noqa: N802
        self._is_subscript = bool(value)

    @property
    def IsHidden(self) -> bool:  # noqa: N802
        return self._is_hidden

    @IsHidden.setter
    def IsHidden(self, value: bool) -> None:  # noqa: N802
        self._is_hidden = bool(value)

    @property
    def IsMathFormatting(self) -> bool:  # noqa: N802
        return self._is_math_formatting

    @IsMathFormatting.setter
    def IsMathFormatting(self, value: bool) -> None:  # noqa: N802
        self._is_math_formatting = bool(value)

    @property
    def FontStyle(self) -> int:  # noqa: N802
        style = 0
        if self.IsBold:
            style |= 1
        if self.IsItalic:
            style |= 2
        if self.IsUnderline:
            style |= 4
        if self.IsStrikethrough:
            style |= 8
        return style

    @_classproperty
    def Default(cls) -> TextStyle:  # noqa: N802
        return cls(Language=1033)

    @_classproperty
    def DefaultMsOneNoteTitleTextStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=20.0, IsBold=True, Language=1033)

    @_classproperty
    def DefaultMsOneNoteTitleDateStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=11.0, Language=1033)

    @_classproperty
    def DefaultMsOneNoteTitleTimeStyle(cls) -> TextStyle:  # noqa: N802
        return cls(FontSize=11.0, Language=1033)


def _ensure_paragraph_style(value: ParagraphStyle | None) -> ParagraphStyle:
    return value if value is not None else ParagraphStyle()


def _text_style_from_paragraph_style(style: ParagraphStyle | None) -> TextStyle:
    paragraph_style = _ensure_paragraph_style(style)
    return TextStyle(
        FontName=paragraph_style.FontName,
        FontSize=paragraph_style.FontSize,
        FontColor=paragraph_style.FontColor,
        Highlight=paragraph_style.Highlight,
        IsBold=paragraph_style.IsBold,
        IsItalic=paragraph_style.IsItalic,
        IsUnderline=paragraph_style.IsUnderline,
        IsStrikethrough=paragraph_style.IsStrikethrough,
        IsSuperscript=paragraph_style.IsSuperscript,
        IsSubscript=paragraph_style.IsSubscript,
    )


@dataclass(slots=True)
class TextRun:
    Text: str = ""
    Style: TextStyle = field(default_factory=TextStyle)


class RichText(Node):
    __slots__ = (
        "_text",
        "_text_runs",
        "_paragraph_style",
        "_alignment",
        "_default_text_style",
        "_tags",
        "LastModifiedTime",
        "SpaceBefore",
        "SpaceAfter",
        "LineSpacing",
    )

    def __init__(
        self,
        *,
        Text: str = "",
        TextRuns: list[TextRun] | None = None,
        ParagraphStyle: ParagraphStyle | None = None,
        Alignment: HorizontalAlignment | None = None,
        Tags: list[NoteTag] | None = None,
        LastModifiedTime: datetime | None = None,
        SpaceBefore: float | None = None,
        SpaceAfter: float | None = None,
        LineSpacing: float | None = None,
    ) -> None:
        super().__init__()
        self._paragraph_style = _ensure_paragraph_style(ParagraphStyle)
        self._alignment = Alignment
        self._default_text_style = _text_style_from_paragraph_style(self._paragraph_style)
        self._tags = list(Tags or [])
        self.LastModifiedTime = LastModifiedTime
        self.SpaceBefore = SpaceBefore
        self.SpaceAfter = SpaceAfter
        self.LineSpacing = LineSpacing
        self._text_runs = list(TextRuns or [])
        if self._text_runs:
            self._default_text_style = self._text_runs[0].Style
        self._text = Text if TextRuns is None else (Text or "".join(run.Text for run in self._text_runs))
        if not self._text_runs and self._text:
            self._text_runs = [TextRun(Text=self._text, Style=self._default_text_style)]

    def _replace_text_runs(self, value: list[TextRun] | None) -> None:
        self._text_runs = list(value or [])
        if self._text_runs:
            self._default_text_style = self._text_runs[0].Style
        self._text = "".join(run.Text for run in self._text_runs)

    @property
    def Text(self) -> str:  # noqa: N802
        if self._text_runs:
            return "".join(run.Text for run in self._text_runs)
        return self._text

    @Text.setter
    def Text(self, value: str) -> None:  # noqa: N802
        self._text = value or ""
        if self._text:
            style = self._text_runs[0].Style if self._text_runs else self._default_text_style
            self._default_text_style = style
            self._text_runs = [TextRun(Text=self._text, Style=style)]
        else:
            self._text_runs = []

    @property
    def TextRuns(self) -> list[TextRun]:  # noqa: N802
        return self._text_runs

    @property
    def ParagraphStyle(self) -> ParagraphStyle:  # noqa: N802
        return self._paragraph_style

    @ParagraphStyle.setter
    def ParagraphStyle(self, value: ParagraphStyle) -> None:  # noqa: N802
        self._paragraph_style = _ensure_paragraph_style(value)
        self._default_text_style = _text_style_from_paragraph_style(self._paragraph_style)

    @property
    def Tags(self) -> list[NoteTag]:  # noqa: N802
        return self._tags

    @property
    def Length(self) -> int:  # noqa: N802
        return len(self.Text)

    @property
    def Alignment(self) -> HorizontalAlignment | None:  # noqa: N802
        return self._alignment

    @Alignment.setter
    def Alignment(self, value: HorizontalAlignment | None) -> None:  # noqa: N802
        self._alignment = value

    @property
    def IsTitleText(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleText is self)

    @property
    def IsTitleDate(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleDate is self)

    @property
    def IsTitleTime(self) -> bool:  # noqa: N802
        return bool(isinstance(self.ParentNode, Title) and self.ParentNode.TitleTime is self)

    def Append(self, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        effective_style = style or self._default_text_style
        self._default_text_style = effective_style
        if self._text_runs:
            self._text_runs.append(TextRun(Text=text, Style=effective_style))
            self._text = "".join(run.Text for run in self._text_runs)
            return self
        combined = self.Text + text
        self._text = combined
        self._text_runs = [TextRun(Text=combined, Style=effective_style)] if combined else []
        return self

    def AppendFront(self, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        return self.Insert(0, text, style)

    def Clear(self) -> RichText:  # noqa: N802
        self._text = ""
        self._text_runs = []
        return self

    def GetEnumerator(self) -> Iterator[str]:  # noqa: N802
        return iter(self.Text)

    def IndexOf(
        self,
        value: str,
        startIndex: int = 0,
        count: int | None = None,
        comparison: str | None = None,
    ) -> int:  # noqa: N802
        haystack = self.Text
        if comparison and comparison.lower().endswith("ignorecase"):
            haystack = haystack.casefold()
            value = value.casefold()
        start_index = max(0, min(int(startIndex), len(haystack)))
        end_index = len(haystack) if count is None else max(start_index, min(start_index + int(count), len(haystack)))
        return haystack.find(value, start_index, end_index)

    def Insert(self, index: int, text: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        current_text = self.Text
        index = max(0, min(index, len(current_text)))
        self._text = current_text[:index] + text + current_text[index:]
        effective_style = style or (self._text_runs[0].Style if self._text_runs else self._default_text_style)
        self._default_text_style = effective_style
        self._text_runs = [TextRun(Text=self._text, Style=effective_style)] if self._text else []
        return self

    def Remove(self, start: int, count: int | None = None) -> RichText:  # noqa: N802
        current_text = self.Text
        start = max(0, min(start, len(current_text)))
        end = len(current_text) if count is None else max(start, min(start + count, len(current_text)))
        self._text = current_text[:start] + current_text[end:]
        if self._text:
            style = self._text_runs[0].Style if self._text_runs else self._default_text_style
            self._default_text_style = style
            self._text_runs = [TextRun(Text=self._text, Style=style)]
        else:
            self._text_runs = []
        return self

    def Replace(self, old_value: str, new_value: str, style: TextStyle | None = None) -> RichText:  # noqa: N802
        if old_value is None or new_value is None:
            raise ValueError("old_value and new_value must not be None")
        if old_value == "":
            raise ValueError("old_value must not be empty")
        self._text = self.Text.replace(old_value, new_value)
        if self._text:
            effective_style = style or (self._text_runs[0].Style if self._text_runs else self._default_text_style)
            self._default_text_style = effective_style
            self._text_runs = [TextRun(Text=self._text, Style=effective_style)]
        else:
            self._text_runs = []
        return self

    def Trim(self) -> RichText:  # noqa: N802
        current_text = self.Text
        trimmed = current_text.strip()
        if trimmed == current_text:
            return self
        self.Text = trimmed
        return self

    def TrimStart(self) -> RichText:  # noqa: N802
        current_text = self.Text
        trimmed = current_text.lstrip()
        if trimmed == current_text:
            return self
        self.Text = trimmed
        return self

    def TrimEnd(self) -> RichText:  # noqa: N802
        current_text = self.Text
        trimmed = current_text.rstrip()
        if trimmed == current_text:
            return self
        self.Text = trimmed
        return self

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitRichTextStart(self)
        visitor.VisitRichTextEnd(self)


class Title(Node):
    __slots__ = ("_title_text", "_title_date", "_title_time")

    def __init__(
        self,
        *,
        TitleText: RichText | None = None,
        TitleDate: RichText | None = None,
        TitleTime: RichText | None = None,
    ) -> None:
        super().__init__()
        self._title_text: RichText | None = None
        self._title_date: RichText | None = None
        self._title_time: RichText | None = None
        self.TitleText = TitleText
        self.TitleDate = TitleDate
        self.TitleTime = TitleTime

    def _set_title_child(self, slot_name: str, value: RichText | None) -> None:
        current = getattr(self, slot_name)
        if current is value:
            return
        if current is not None and current.ParentNode is self:
            current._set_parent(None)
        if value is not None:
            value._set_parent(self)
        setattr(self, slot_name, value)

    @property
    def TitleText(self) -> RichText | None:  # noqa: N802
        return self._title_text

    @TitleText.setter
    def TitleText(self, value: RichText | None) -> None:  # noqa: N802
        self._set_title_child("_title_text", value)

    @property
    def TitleDate(self) -> RichText | None:  # noqa: N802
        return self._title_date

    @TitleDate.setter
    def TitleDate(self, value: RichText | None) -> None:  # noqa: N802
        self._set_title_child("_title_date", value)

    @property
    def TitleTime(self) -> RichText | None:  # noqa: N802
        return self._title_time

    @TitleTime.setter
    def TitleTime(self, value: RichText | None) -> None:  # noqa: N802
        self._set_title_child("_title_time", value)

    def GetEnumerator(self) -> Iterator[Node]:  # noqa: N802
        return iter(self)

    def __iter__(self) -> Iterator[Node]:
        for child in (self._title_text, self._title_date, self._title_time):
            if child is not None:
                yield child

    def GetChildNodes(self, node_type: type[TNode]) -> list[TNode]:  # noqa: N802
        found: list[TNode] = []
        for child in self:
            if isinstance(child, node_type):
                found.append(child)
            if _iter_node_children(child):
                found.extend(child.GetChildNodes(node_type))
        return found

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitTitleStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitTitleEnd(self)


@dataclass(slots=True)
class NumberList:
    Format: str | None = None
    NumberFormat: str | None = None
    Font: str | None = None
    FontSize: float | None = None
    FontColor: int | None = None
    IsBold: bool = False
    IsItalic: bool = False
    LastModifiedTime: datetime | None = None
    Restart: int | None = None

    def GetNumberedListHeader(self, number: int) -> str:  # noqa: N802
        if self.Format is None:
            return ""
        if "{0}" in self.Format:
            return self.Format.format(number)
        return self.Format


@dataclass(slots=True)
class OutlineElement(CompositeNode):
    NumberList: NumberList | None = None

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitOutlineElementStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitOutlineElementEnd(self)


@dataclass(slots=True)
class Outline(CompositeNode):
    HorizontalOffset: float | None = None
    VerticalOffset: float | None = None
    MaxWidth: float | None = None
    MaxHeight: float | None = None
    MinWidth: float | None = None
    ReservedWidth: float | None = None
    IndentPosition: float | None = None
    DescendantsCannotBeMoved: bool = False
    LastModifiedTime: datetime | None = None

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitOutlineStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitOutlineEnd(self)


class Image(CompositeNode):
    __slots__ = (
        "_file_name",
        "_file_path",
        "_format",
        "_bytes",
        "Width",
        "Height",
        "_original_width",
        "_original_height",
        "HorizontalOffset",
        "VerticalOffset",
        "_alignment",
        "IsBackground",
        "LastModifiedTime",
        "AlternativeTextTitle",
        "AlternativeTextDescription",
        "HyperlinkUrl",
        "_tags",
    )

    def __init__(
        self,
        *,
        FileName: str | None = None,
        FilePath: str | None = None,
        Format: str | None = None,
        Bytes: bytes = b"",
        Width: float | None = None,
        Height: float | None = None,
        OriginalWidth: float | None = None,
        OriginalHeight: float | None = None,
        HorizontalOffset: float | None = None,
        VerticalOffset: float | None = None,
        Alignment: HorizontalAlignment | None = None,
        IsBackground: bool = False,
        LastModifiedTime: datetime | None = None,
        AlternativeTextTitle: str | None = None,
        AlternativeTextDescription: str | None = None,
        HyperlinkUrl: str | None = None,
        Tags: list[NoteTag] | None = None,
    ) -> None:
        super().__init__()
        self._file_name = FileName
        self._file_path = FilePath
        self._format = Format
        self._bytes = Bytes
        self.Width = Width
        self.Height = Height
        self._original_width = OriginalWidth
        self._original_height = OriginalHeight
        self.HorizontalOffset = HorizontalOffset
        self.VerticalOffset = VerticalOffset
        self._alignment = Alignment
        self.IsBackground = IsBackground
        self.LastModifiedTime = LastModifiedTime
        self.AlternativeTextTitle = AlternativeTextTitle
        self.AlternativeTextDescription = AlternativeTextDescription
        self.HyperlinkUrl = HyperlinkUrl
        self._tags = list(Tags or [])

    @property
    def FileName(self) -> str | None:  # noqa: N802
        return self._file_name

    @property
    def FilePath(self) -> str | None:  # noqa: N802
        return self._file_path

    @property
    def Format(self) -> str | None:  # noqa: N802
        return self._format

    @property
    def Bytes(self) -> bytes:  # noqa: N802
        return self._bytes

    @property
    def OriginalWidth(self) -> float | None:  # noqa: N802
        return self._original_width

    @property
    def OriginalHeight(self) -> float | None:  # noqa: N802
        return self._original_height

    @property
    def Tags(self) -> list[NoteTag]:  # noqa: N802
        return self._tags

    @property
    def Alignment(self) -> HorizontalAlignment | None:  # noqa: N802
        return self._alignment

    @Alignment.setter
    def Alignment(self, value: HorizontalAlignment | None) -> None:  # noqa: N802
        self._alignment = value

    def Replace(self, image: Image) -> None:  # noqa: N802
        self._file_name = image.FileName
        self._file_path = image.FilePath
        self._format = image.Format
        self._bytes = image.Bytes
        self.Width = image.Width
        self.Height = image.Height
        self._original_width = image.OriginalWidth
        self._original_height = image.OriginalHeight
        self.HorizontalOffset = image.HorizontalOffset
        self.VerticalOffset = image.VerticalOffset
        self._alignment = image.Alignment
        self.IsBackground = image.IsBackground
        self.LastModifiedTime = image.LastModifiedTime
        self.AlternativeTextTitle = image.AlternativeTextTitle
        self.AlternativeTextDescription = image.AlternativeTextDescription
        self.HyperlinkUrl = image.HyperlinkUrl
        self._tags = list(image.Tags)

    def _accept(self, visitor: DocumentVisitor) -> None:
        visitor.VisitImageStart(self)
        for child in self:
            child.Accept(visitor)
        visitor.VisitImageEnd(self)


class AttachedFile(Node):
    __slots__ = ("_file_name", "_bytes", "_tags")

    def __init__(
        self,
        *,
        FileName: str | None = None,
        Bytes: bytes = b"",
        Tags: list[NoteTag] | None = None,
    ) -> None:
        super().__init__()
        self._file_name = FileName
        self._bytes = Bytes
        self._tags = list(Tags or [])

    @property
    def FileName(self) -> str | None:  # noqa: N802
        return self._file_name

    @property
    def Bytes(self) -> bytes:  # noqa: N802
        return self._bytes

    @property
    def Tags(self) -> list[NoteTag]:  # noqa: N802
        return self._tags


@dataclass(slots=True)
class TableCell(CompositeNode):
    pass


@dataclass(slots=True)
class TableRow(CompositeNode):
    pass


@dataclass(slots=True)
class TableColumn:
    Width: float | None = None
    LockedWidth: bool = False


class Table(CompositeNode):
    __slots__ = ("_tags", "_columns", "IsBordersVisible", "LastModifiedTime")

    def __init__(
        self,
        *,
        Tags: list[NoteTag] | None = None,
        Columns: list[TableColumn] | None = None,
        IsBordersVisible: bool = True,
        LastModifiedTime: datetime | None = None,
    ) -> None:
        super().__init__()
        self._tags = list(Tags or [])
        self._columns = list(Columns or [])
        self.IsBordersVisible = IsBordersVisible
        self.LastModifiedTime = LastModifiedTime

    @property
    def Tags(self) -> list[NoteTag]:  # noqa: N802
        return self._tags

    @property
    def Columns(self) -> list[TableColumn]:  # noqa: N802
        return self._columns


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


class PageHistory:
    __slots__ = ("_current", "_versions")

    def __init__(self, current: Page) -> None:
        self._current = current
        self._versions: list[Page] = []

    @property
    def Count(self) -> int:  # noqa: N802
        return len(self._versions)

    @property
    def Current(self) -> Page:  # noqa: N802
        return self._current

    @property
    def IsReadOnly(self) -> bool:  # noqa: N802
        return False

    def Add(self, page: Page) -> None:  # noqa: N802
        self._versions.append(page)

    def AddRange(self, pages: list[Page]) -> None:  # noqa: N802
        self._versions.extend(pages)

    def Clear(self) -> None:  # noqa: N802
        self._versions.clear()

    def Contains(self, page: Page) -> bool:  # noqa: N802
        return page in self._versions

    def CopyTo(self, target: list[Page], index: int) -> None:  # noqa: N802
        target[index : index + len(self._versions)] = self._versions

    def GetEnumerator(self) -> Iterator[Page]:  # noqa: N802
        return iter(self._versions)

    def IndexOf(self, page: Page) -> int:  # noqa: N802
        try:
            return self._versions.index(page)
        except ValueError:
            return -1

    def Insert(self, index: int, page: Page) -> None:  # noqa: N802
        self._versions.insert(index, page)

    def Remove(self, page: Page) -> bool:  # noqa: N802
        if page not in self._versions:
            return False
        self._versions.remove(page)
        return True

    def RemoveAt(self, index: int) -> None:  # noqa: N802
        del self._versions[index]

    def RemoveRange(self, index: int, count: int) -> None:  # noqa: N802
        del self._versions[index : index + count]

    def __getitem__(self, index: int) -> Page:
        return self._versions[index]

    def __setitem__(self, index: int, value: Page) -> None:
        self._versions[index] = value

    def __iter__(self) -> Iterator[Page]:
        return iter(self._versions)

    def __len__(self) -> int:
        return len(self._versions)


class Document(CompositeNode):
    def __init__(self, source: str | Path | BinaryIO | None = None, load_options: LoadOptions | None = None) -> None:
        super().__init__()
        self.DisplayName: str | None = None
        self.CreationTime: datetime | None = None
        self._onenote_doc: Any | None = None
        self._page_histories: dict[int, PageHistory] = {}

        if source is None:
            return

        load_options = load_options or LoadOptions()
        if load_options.DocumentPassword:
            raise IncorrectPasswordException("Password-protected documents are not supported")

        from ._internal.ms_one.loader import load_onenote_document

        loaded = load_onenote_document(source, include_page_history=load_options.LoadHistory)
        self.DisplayName = loaded.display_name
        self._onenote_doc = loaded
        for page, history in zip(loaded.pages, loaded.page_histories, strict=False):
            self.AppendChildLast(page)
            ordered_history = list(history or [page])
            current_page = ordered_history[-1]
            page_history = PageHistory(current_page)
            page_history.AddRange(ordered_history[:-1])
            self._page_histories[id(page)] = page_history

    @property
    def FileFormat(self) -> FileFormat:  # noqa: N802
        return FileFormat.OneNote2010

    def DetectLayoutChanges(self) -> None:  # noqa: N802
        return None

    def GetPageHistory(self, page: Page) -> PageHistory:  # noqa: N802
        return self._page_histories.get(id(page), PageHistory(page))

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
    "ParagraphStyle",
    "TextStyle",
    "TextRun",
    "RichText",
    "Title",
    "NumberList",
    "OutlineElement",
    "Outline",
    "Image",
    "AttachedFile",
    "TableColumn",
    "TableCell",
    "TableRow",
    "Table",
    "Page",
    "PageHistory",
    "Document",
    "SaveOptions",
    "PdfSaveOptions",
    "_time32_to_datetime",
    "_filetime_to_datetime",
]


def _iter_node_children(node: Node) -> tuple[Node, ...]:
    if isinstance(node, CompositeNode):
        return tuple(node)
    if isinstance(node, Title):
        return tuple(node)
    return ()


def _rebind_tree_parents(node: Node, parent: Node | None) -> None:
    node._set_parent(parent)
    for child in _iter_node_children(node):
        _rebind_tree_parents(child, node)


def _infer_save_format(target: str | Path | BinaryIO) -> SaveFormat:
    if isinstance(target, (str, Path)):
        suffix = Path(target).suffix.lower()
        if suffix == ".pdf":
            return SaveFormat.Pdf
        raise UnsupportedSaveFormatException("Only .pdf file targets are supported for save operations")
    return SaveFormat.Pdf