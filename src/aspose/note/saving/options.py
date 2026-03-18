from __future__ import annotations

from typing import Any

from ..enums import SaveFormat


class SaveOptions:
    __slots__ = ("SaveFormat", "PageIndex", "PageCount", "FontsSubsystem")

    def __init__(
        self,
        save_format: SaveFormat,
        *,
        PageIndex: int = 0,
        PageCount: int | None = None,
        FontsSubsystem: Any | None = None,
    ) -> None:
        self.SaveFormat = save_format
        self.PageIndex = int(PageIndex)
        self.PageCount = PageCount
        self.FontsSubsystem = FontsSubsystem


class PdfSaveOptions(SaveOptions):
    __slots__ = (
        "TagIconDir",
        "TagIconSize",
        "TagIconGap",
        "ImageCompression",
        "JpegQuality",
        "PageSettings",
        "PageSplittingAlgorithm",
    )

    def __init__(
        self,
        save_format: SaveFormat = SaveFormat.Pdf,
        *,
        PageIndex: int = 0,
        PageCount: int | None = None,
        FontsSubsystem: Any | None = None,
        TagIconDir: str | None = None,
        TagIconSize: float | None = None,
        TagIconGap: float | None = None,
        ImageCompression: Any | None = None,
        JpegQuality: int | None = None,
        PageSettings: Any | None = None,
        PageSplittingAlgorithm: Any | None = None,
    ) -> None:
        super().__init__(save_format, PageIndex=PageIndex, PageCount=PageCount, FontsSubsystem=FontsSubsystem)
        self.TagIconDir = TagIconDir
        self.TagIconSize = TagIconSize
        self.TagIconGap = TagIconGap
        self.ImageCompression = ImageCompression
        self.JpegQuality = JpegQuality
        self.PageSettings = PageSettings
        self.PageSplittingAlgorithm = PageSplittingAlgorithm