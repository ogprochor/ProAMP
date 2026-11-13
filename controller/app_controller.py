from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from audio.base import AudioBackend, AudioBackendError
from audio.loopback import LoopbackSpectrum
from audio.vlc_backend import VlcBackend
from model.library import Library
from model.playlist import Playlist, RepeatMode
from model.track import Track


@dataclass(frozen=True)
class PlayerSnapshot:
    current: Track | None
    position: float
    duration: float
    volume: int
    is_playing: bool
    shuffle: bool
    repeat: RepeatMode


class AppController:
    def __init__(self, backend: AudioBackend | None = None) -> None:
        self.library = Library()
        self.playlist = Playlist()
        self.backend = backend
        self.backend_error: str | None = None
        if self.backend is None:
            try:
                self.backend = VlcBackend()
            except AudioBackendError as error:
                self.backend_error = str(error)
        self.set_volume(50)
        self.capture: LoopbackSpectrum | None = None
        self._last_track: Track | None = None

    def scan_folder(self, folder: Path) -> tuple[Track, ...]:
        folder = Path(folder).expanduser()
        if not folder.is_dir():
            raise ValueError(f"Nie znaleziono folderu: {folder}")
        if self.backend:
            self.backend.stop()
        self._last_track = None
        self.library.clear()
        self.library.add_folder(folder)
        self.playlist.clear()
        self.playlist.add_many(self.library.tracks)
        return self.playlist.tracks

    def select_track(self, index: int) -> Track:
        track = self.playlist.select(index)
        self._load_current()
        if self.backend:
            self.backend.play()
        return track

    def toggle_play(self) -> None:
        if not self.backend:
            return
        if self.backend.is_playing():
            self.backend.pause()
        elif self.playlist.current:
            if self._last_track != self.playlist.current:
                self._load_current()
            self.backend.play()

    def next_track(self, auto: bool = False) -> Track | None:
        track = self.playlist.next(auto=auto)
        if track is not None:
            self._load_current()
            if self.backend:
                self.backend.play()
        return track

    def previous_track(self) -> Track | None:
        track = self.playlist.previous()
        if track is not None:
            self._load_current()
            if self.backend:
                self.backend.play()
        return track

    def seek(self, offset: float) -> None:
        if not self.backend:
            return
        position = max(0.0, self.backend.get_position() + offset)
        duration = self.backend.get_duration()
        if duration > 0:
            position = min(position, duration)
        self.backend.seek(position)

    def change_volume(self, amount: int) -> None:
        if self.backend:
            self.backend.set_volume(self.backend.get_volume() + amount)

    def set_volume(self, value: int) -> None:
        if self.backend:
            self.backend.set_volume(max(0, min(100, int(value))))

    def toggle_shuffle(self) -> None:
        self.playlist.toggle_shuffle()

    def cycle_repeat(self) -> None:
        self.playlist.cycle_repeat()

    def start_spectrum(self, on_levels: Callable[[tuple[float, ...]], None]) -> None:
        self.capture = LoopbackSpectrum(on_levels)
        self.capture.start()

    def tick(self) -> PlayerSnapshot:
        if self.backend and self.backend.is_finished():
            if self.next_track(auto=True) is None:
                self.backend.stop()
                self._last_track = None
        return self.snapshot()

    def snapshot(self) -> PlayerSnapshot:
        backend = self.backend
        return PlayerSnapshot(
            current=self.playlist.current,
            position=backend.get_position() if backend else 0.0,
            duration=backend.get_duration() if backend else 0.0,
            volume=backend.get_volume() if backend else 50,
            is_playing=backend.is_playing() if backend else False,
            shuffle=self.playlist.shuffle,
            repeat=self.playlist.repeat,
        )

    def close(self) -> None:
        if self.capture:
            self.capture.stop()
        if self.backend:
            self.backend.release()

    def _load_current(self) -> None:
        track = self.playlist.current
        if track is None:
            return
        self._last_track = track
        if self.backend:
            self.backend.load(track.path)
