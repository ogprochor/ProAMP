from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from model.events import Observable
from model.metadata import is_supported, read_track
from model.track import Track


class LibraryEvent(Enum):
    CHANGED = "library_changed"


@dataclass(frozen=True)
class Album:
    title: str
    artist: str
    year: int | None
    tracks: tuple[Track, ...]

    @property
    def duration(self) -> float:
        return sum(t.duration for t in self.tracks)


def _track_sort_key(track: Track):
    # utwory bez numeru (0) lądują na końcu płyty, alfabetycznie
    return (track.disc_number, track.track_number or 10**6, track.title.casefold())


class Library(Observable):

    def __init__(self, reader: Callable[[Path], Track] = read_track) -> None:
        super().__init__()
        self._reader = reader
        self._tracks: dict[Path, Track] = {}

    @property
    def tracks(self) -> list[Track]:
        return sorted(
            self._tracks.values(),
            key=lambda t: (t.artist.casefold(), t.album.casefold(), *_track_sort_key(t)),
        )

    def __len__(self) -> int:
        return len(self._tracks)

    def add_folder(self, folder: Path) -> int:
        found = 0
        for path in sorted(Path(folder).rglob("*")):
            if path.is_file() and is_supported(path):
                self._tracks[path] = self._reader(path)
                found += 1
        if found:
            self._notify(LibraryEvent.CHANGED)
        return found

    def clear(self) -> None:
        if self._tracks:
            self._tracks.clear()
            self._notify(LibraryEvent.CHANGED)

    def albums(self) -> list[Album]:
        groups: dict[tuple[str, str], list[Track]] = {}
        for track in self._tracks.values():
            key = (track.effective_album_artist.casefold(), track.album.casefold())
            groups.setdefault(key, []).append(track)

        albums = []
        for tracks in groups.values():
            tracks.sort(key=_track_sort_key)
            years = [t.year for t in tracks if t.year]
            albums.append(Album(
                title=tracks[0].album,
                artist=tracks[0].effective_album_artist,
                year=min(years) if years else None,
                tracks=tuple(tracks),
            ))

        albums.sort(key=lambda a: (a.artist.casefold(), a.title.casefold()))
        return albums

    def artists(self) -> list[str]:
        names = {a.artist for a in self.albums()}
        return sorted(names, key=str.casefold)

    def search(self, query: str) -> list[Track]:
        needle = query.strip().casefold()
        if not needle:
            return self.tracks
        return [
            t for t in self.tracks
            if needle in f"{t.title} {t.artist} {t.album}".casefold()
        ]