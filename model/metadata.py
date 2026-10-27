#Odczyt tagow z plikow audio (jak wlasciwosci w szczegółach pliku)
from pathlib import Path
import mutagen
from model.track import UNKNOWN_ALBUM, UNKNOWN_ARTIST, Track

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".m4a", ".ogg", ".opus", ".wav"}


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def _first(tags, key: str) -> str:
    #pierwsza wartosc tagu jako tekst, pusty string gdy brak tagu
    if not tags:
        return ""
    try:
        values = tags.get(key)
    except Exception:
        return ""
    if not values:
        return ""
    return str(values[0]).strip()


def _parse_int(text: str) -> int:
    try:
        return int(text.split("/")[0].strip())
    except ValueError:
        return 0


def _parse_year(text: str) -> int | None:
    try:
        return int(text.strip()[:4])
    except ValueError:
        return None


def read_track(path: Path) -> Track:
    try:
        audio = mutagen.File(path, easy=True)
    except Exception:
        audio = None

    tags = getattr(audio, "tags", None)
    length = getattr(getattr(audio, "info", None), "length", 0.0) or 0.0

    return Track(
        path=path,
        title=_first(tags, "title") or path.stem,
        artist=_first(tags, "artist") or UNKNOWN_ARTIST,
        album=_first(tags, "album") or UNKNOWN_ALBUM,
        album_artist=_first(tags, "albumartist"),
        track_number=_parse_int(_first(tags, "tracknumber")),
        disc_number=_parse_int(_first(tags, "discnumber")) or 1,
        year=_parse_year(_first(tags, "date")),
        duration=float(length),
    )