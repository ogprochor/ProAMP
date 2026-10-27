import sys
from pathlib import Path

from audio.base import AudioBackendError
from audio.vlc_backend import VlcBackend

HELP = (
    "Komendy: p = odtwarzaj/pauza | s = stop | f = +10 s | b = -10 s | "
    "+ / - = głośność | Enter = odśwież status | q = wyjście"
)


def fmt(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"

def path_from_args() -> Path | None:
    raw = " ".join(sys.argv[1:]).strip().strip('"')
    if not raw:
        raw = input("Podaj ścieżkę do pliku: ").strip().strip('"')
    return Path(raw) if raw else None

def main() -> None:
    path = path_from_args()
    if path is None or not path.is_file():
        print(f"Nie znaleziono pliku: {path}")
        return
    try:
        backend = VlcBackend()
    except AudioBackendError as error:
        print(error)
        return

    backend.load(path)
    backend.play()
    print(HELP)
    try:
        while True:
            if backend.is_finished():
                state = "koniec"
            elif backend.is_playing():
                state = "gra"
            else:
                state = "nie gra"
            prompt = (
                f"[{state}] {fmt(backend.get_position())} / "
                f"{fmt(backend.get_duration())}  vol {backend.get_volume()}% > "
            )
            command = input(prompt).strip().lower()
            if command == "q":
                break
            elif command == "p":
                backend.pause() if backend.is_playing() else backend.play()
            elif command == "s":
                backend.stop()
            elif command == "f":
                backend.seek(backend.get_position() + 10)
            elif command == "b":
                backend.seek(backend.get_position() - 10)
            elif command == "+":
                backend.set_volume(backend.get_volume() + 5)
            elif command == "-":
                backend.set_volume(backend.get_volume() - 5)
    finally:
        backend.release()


if __name__ == "__main__":
    main()