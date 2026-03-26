from __future__ import annotations

from typing import Any

from ..enums import SaveFormat


class SaveOptions:
    __slots__ = ("_save_format", "PageIndex", "PageCount", "FontsSubsystem")

    def __init__(
        self,
        save_format: SaveFormat,
        *,
        PageIndex: int = 0,
        PageCount: int | None = None,
        FontsSubsystem: Any | None = None,
    ) -> None:
        if self.__class__ is SaveOptions:
            raise TypeError("SaveOptions is an abstract compatibility base type and cannot be instantiated directly")
        self._save_format = save_format
        self.PageIndex = int(PageIndex)
        self.PageCount = PageCount
        self.FontsSubsystem = FontsSubsystem

    @property
    def SaveFormat(self) -> SaveFormat:  # noqa: N802
        return self._save_format


class PdfSaveOptions(SaveOptions):
    __slots__ = ("ImageCompression", "JpegQuality", "PageSettings", "PageSplittingAlgorithm")

    def __init__(
        self,
        *,
        PageIndex: int = 0,
        PageCount: int | None = None,
        FontsSubsystem: Any | None = None,
        ImageCompression: Any | None = None,
        JpegQuality: int | None = None,
        PageSettings: Any | None = None,
        PageSplittingAlgorithm: Any | None = None,
    ) -> None:
        super().__init__(SaveFormat.Pdf, PageIndex=PageIndex, PageCount=PageCount, FontsSubsystem=FontsSubsystem)
        self.ImageCompression = ImageCompression
        self.JpegQuality = JpegQuality
        self.PageSettings = PageSettings
        self.PageSplittingAlgorithm = PageSplittingAlgorithm