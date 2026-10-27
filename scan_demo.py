import sys
from pathlib import Path

from model.library import Library


def fmt(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def folder_from_args() -> Path:
    raw = " ".join(sys.argv[1:]).strip().strip('"')
    return Path(raw) if raw else Path.home() / "Music"


def main() -> None:
    folder = folder_from_args()
    if not folder.is_dir():
        print(f"Nie znaleziono folderu: {folder}")
        return

    library = Library()
    count = library.add_folder(folder)
    print(f"Folder: {folder}\nZnaleziono plików: {count}\n")

    for album in library.albums():
        year = f" ({album.year})" if album.year else ""
        print(f"{album.artist} - {album.title}{year}  [{fmt(album.duration)}]")
        for track in album.tracks:
            number = f"{track.track_number:>2}" if track.track_number else " ?"
            print(f"   {number}. {track.title}  {fmt(track.duration)}")
        print()


if __name__ == "__main__":
    main()