"""Preview formats and bounded, read-only ZIP inspection for completed work.

Previews never unpack a package into its output directory. Only the selected
member is read, with a 256 MiB limit; the original download remains unchanged.
"""
from pathlib import PurePosixPath
from zipfile import ZipInfo

MAX_PREVIEW_BYTES = 256 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 2000

PREVIEW_FORMATS = {
    ".png": ("image", "image/png"),
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".webp": ("image", "image/webp"),
    ".gif": ("image", "image/gif"),
    ".mp4": ("video", "video/mp4"),
    ".mov": ("video", "video/quicktime"),
    ".webm": ("video", "video/webm"),
    ".mp3": ("audio", "audio/mpeg"),
    ".wav": ("audio", "audio/wav"),
    ".ogg": ("audio", "audio/ogg"),
    ".glb": ("model_3d", "model/gltf-binary"),
    ".pdf": ("document", "application/pdf"),
    ".html": ("document", "text/html"),
    ".htm": ("document", "text/html"),
    ".txt": ("text", "text/plain"),
    ".md": ("text", "text/plain"),
    ".csv": ("text", "text/plain"),
    ".json": ("text", "text/plain"),
}


def preview_format(filename: str):
    return PREVIEW_FORMATS.get(PurePosixPath(filename).suffix.lower())


def safe_archive_member(info: ZipInfo) -> bool:
    name = info.filename.replace("\\", "/")
    path = PurePosixPath(name)
    return (
        not info.is_dir()
        and not path.is_absolute()
        and ".." not in path.parts
        and ":" not in name
        and "\x00" not in name
        and not info.flag_bits & 1
        and (info.external_attr >> 16) & 0o170000 != 0o120000
    )
