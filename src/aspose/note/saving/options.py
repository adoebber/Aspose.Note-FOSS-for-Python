from __future__ import annotations

from dataclasses import dataclass

from ..enums import SaveFormat


@dataclass(slots=True)
class SaveOptions:
    SaveFormat: SaveFormat


@dataclass(slots=True)
class PdfSaveOptions(SaveOptions):
    PageIndex: int = 0
    PageCount: int | None = None
    TagIconDir: str | None = None
    TagIconSize: float | None = None
    TagIconGap: float | None = None


@dataclass(slots=True)
class OneSaveOptions(SaveOptions):
    pass


@dataclass(slots=True)
class HtmlSaveOptions(SaveOptions):
    pass


@dataclass(slots=True)
class ImageSaveOptions(SaveOptions):
    pass