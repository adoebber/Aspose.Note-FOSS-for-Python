from __future__ import annotations

from .enums import FileFormat


_FILE_FORMAT_GUID_MAP = {
    "7b5c52e4-d88c-4da7-aeb1-5378d02996d3": FileFormat.OneNote2010,
}


def _coerce_file_format(value: FileFormat | str | None) -> FileFormat:
    if isinstance(value, FileFormat):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return FileFormat.Unknown
        for file_format in FileFormat:
            if normalized in {file_format.name.lower(), str(file_format.value).lower()}:
                return file_format
        return _FILE_FORMAT_GUID_MAP.get(normalized, FileFormat.Unknown)
    return FileFormat.Unknown


class AsposeNoteError(Exception):
    pass


class FileCorruptedException(AsposeNoteError):
    pass


class IncorrectDocumentStructureException(AsposeNoteError):
    pass


class IncorrectPasswordException(AsposeNoteError):
    pass


class UnsupportedFileFormatException(AsposeNoteError):
    __slots__ = ("_file_format",)

    def __init__(
        self,
        message: str = "Unsupported file format",
        file_format: FileFormat | str | None = None,
    ) -> None:
        super().__init__(message)
        self._file_format = _coerce_file_format(file_format)

    @property
    def FileFormat(self) -> FileFormat:  # noqa: N802
        return self._file_format


class UnsupportedSaveFormatException(AsposeNoteError):
    pass