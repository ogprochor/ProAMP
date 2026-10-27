from dataclasses import dataclass
from pathlib import Path

UNKNOWN_ARTIST = "Nieznany wykonawca"
UNKNOWN_ALBUM = "Nieznany album"


@dataclass(frozen=True)
class Track:
    path: Path
    title: str
    artist: str = UNKNOWN_ARTIST
    album: str = UNKNOWN_ALBUM
    album_artist: str = ""
    track_number: int = 0         # 0 = brak numeru
    disc_number: int = 1
    year: int | None = None
    duration: float = 0.0         #sekundy

    @property
    def display_name(self) -> str:
        return f"{self.artist} - {self.title}"

    @property
    def effective_album_artist(self) -> str:
        return self.album_artist or self.artist