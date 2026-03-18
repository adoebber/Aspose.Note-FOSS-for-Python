from __future__ import annotations

from enum import Enum


class SaveFormat(Enum):
    Pdf = "pdf"


class FileFormat(Enum):
    OneNote2010 = "onenote2010"
    OneNoteOnline = "onenoteonline"
    OneNote2007 = "onenote2007"


class HorizontalAlignment(Enum):
    Left = "left"
    Center = "center"
    Right = "right"


class NodeType(Enum):
    Document = "document"
    Page = "page"
    Outline = "outline"
    OutlineElement = "outline_element"
    RichText = "rich_text"
    Image = "image"
    Table = "table"
    AttachedFile = "attached_file"