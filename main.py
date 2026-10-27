from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from audio.base import AudioBackendError
from audio.loopback import LoopbackSpectrum
from audio.vlc_backend import VlcBackend
from model.library import Library
from model.playlist import Playlist, RepeatMode
from view.tui.visualizer import Visualizer


class ProampApp(App):

    TITLE = "Proamp"
    CSS = """
    Horizontal {
        width: 100%;
        height: 3;
    }
    #music-folder {
        width: 1fr;
    }
    #scan {
        width: 18;
    }
    #transport Button {
        width: 1fr;
    }
    #adjustments Button {
        width: 1fr;
    }
    #now-playing {
        height: 3;
        content-align: left middle;
        padding: 0 1;
        border: round $secondary;
    }
    #display-area {
        width: 100%;
        height: 10;
    }
    #visualizer {
        width: 2fr;
        height: 10;
    }
    #player-info {
        width: 1fr;
        height: 10;
        border: round $secondary;
        padding: 1;
        content-align: left middle;
    }
    """
    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pauza"),
        Binding("n", "next_track", "Następny"),
        Binding("p", "previous_track", "Poprzedni"),
        Binding("left", "seek_backward", "−10 s"),
        Binding("right", "seek_forward", "+10 s"),
        Binding("-", "volume_down", "Ciszej"),
        Binding("+", "volume_up", "Głośniej"),
        Binding("s", "shuffle", "Losowo"),
        Binding("r", "repeat", "Powtarzanie"),
        Binding("q", "quit", "Wyjście"),
    ]

    def __init__(self):
        super().__init__()
        self.library = Library()
        self.playlist = Playlist()
        self.backend = None
        self.capture = None
        self._last_track = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Input(placeholder="Ścieżka do folderu z muzyką", id="music-folder")
            yield Button("Skanuj folder", id="scan")
        yield DataTable(id="tracks")
        yield Static("Nie odtwarzam utworu", id="now-playing")
        with Horizontal(id="display-area"):
            yield Visualizer(id="visualizer")
            yield Static("Czas: 0:00 / 0:00\nGłośność: 100%\nStan: zatrzymano", id="player-info")
        with Horizontal(id="transport"):
            yield Button("◀ Poprzedni", id="previous")
            yield Button("▶⏸ Odtwórz / pauza", id="play")
            yield Button("Następny ▶", id="next")
            yield Button("Losowo", id="shuffle")
            yield Button("↻ Powtarzanie", id="repeat")
        with Horizontal(id="adjustments"):
            yield Button("−10 s", id="seek-back")
            yield Button("+10 s", id="seek-forward")
            yield Button("Głośniej +5", id="volume-up")
            yield Button("Ciszej −5", id="volume-down")
            yield Button("Wyjdź", id="exit")
        yield Footer()


    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("#", "Tytuł", "Wykonawca", "Album", "Czas")
        table.cursor_type = "row"
        try:
            self.backend = VlcBackend()
        except AudioBackendError as exc:
            self.notify(f"Odtwarzanie niedostępne: {exc}", severity="error")

        self.capture = LoopbackSpectrum(self._receive_levels)
        self.capture.start()
        self.set_interval(0.2, self._refresh_status)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        actions = {
            "previous": self.action_previous_track,
            "play": self.action_toggle_play,
            "next": self.action_next_track,
            "shuffle": self.action_shuffle,
            "repeat": self.action_repeat,
            "seek-back": self.action_seek_backward,
            "seek-forward": self.action_seek_forward,
            "volume-up": self.action_volume_up,
            "volume-down": self.action_volume_down,
            "exit": self.exit,
        }
        if event.button.id == "scan":
            self._scan_folder()
        elif event.button.id in actions:
            actions[event.button.id]()

    def _scan_folder(self) -> None:
        raw = self.query_one("#music-folder", Input).value.strip().strip('"')
        folder = Path(raw).expanduser()
        if not folder.is_dir():
            self.notify(f"Nie znaleziono folderu: {folder}", severity="error")
            return
        # nowe skanowanie zastępuje zawartosc biblioteki i kolejki
        if self.backend:
            self.backend.stop()
        self._last_track = None
        self.library.clear()
        self.library.add_folder(folder)
        self.playlist.clear()
        self.playlist.add_many(self.library.tracks)
        table = self.query_one(DataTable)
        table.clear()
        for index, track in enumerate(self.playlist.tracks):
            table.add_row(
                str(index + 1), track.title, track.artist, track.album,
                self._format_time(track.duration), key=str(index),
            )
        self.query_one("#now-playing", Static).update(
            f"Załadowano {len(self.library)} utworów · wybierz utwór z playlisty"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "tracks" and self.playlist.tracks:
            self._play_index(event.cursor_row)

    def action_toggle_play(self) -> None:
        if not self.backend:
            return
        if self.backend.is_playing():
            self.backend.pause()
        elif self.playlist.current:
            if self._last_track != self.playlist.current:
                self._load_current()
            self.backend.play()

    def action_next_track(self) -> None:
        if self.playlist.next() is not None:
            self._load_current()
            if self.backend:
                self.backend.play()

    def action_previous_track(self) -> None:
        if self.playlist.previous() is not None:
            self._load_current()
            if self.backend:
                self.backend.play()

    def action_seek_backward(self) -> None:
        self._seek(-10)

    def action_seek_forward(self) -> None:
        self._seek(10)

    def _seek(self, offset: float) -> None:
        if not self.backend:
            return
        position = max(0, self.backend.get_position() + offset)
        duration = self.backend.get_duration()
        if duration > 0:
            position = min(position, duration)
        self.backend.seek(position)

    def action_volume_up(self) -> None:
        self._change_volume(5)

    def action_volume_down(self) -> None:
        self._change_volume(-5)

    def _change_volume(self, amount: int) -> None:
        if not self.backend:
            return
        self.backend.set_volume(self.backend.get_volume() + amount)

    def action_shuffle(self) -> None:
        self.playlist.toggle_shuffle()

    def action_repeat(self) -> None:
        self.playlist.cycle_repeat()

    def _play_index(self, index: int) -> None:
        try:
            self.playlist.select(index)
        except IndexError:
            return
        self._load_current()
        if self.backend:
            self.backend.play()

    def _load_current(self) -> None:
        track = self.playlist.current
        if not track:
            return
        self._last_track = track
        if self.backend:
            self.backend.load(track.path)
        self.query_one("#now-playing", Static).update(f"♫  {track.artist} — {track.title}")

    def _receive_levels(self, levels: tuple[float, ...]) -> None:
        try:
            self.call_from_thread(self._set_levels_ui, levels)
        except RuntimeError:
            pass

    def _set_levels_ui(self, levels: tuple[float, ...]) -> None:
        self.query_one(Visualizer).set_levels(levels)

    def _refresh_status(self) -> None:
        self._refresh_player_info()
        if self.capture and self.capture.error:
            self.notify(f"Wizualizer niedostępny: {self.capture.error}", severity="error")
            self.capture.error = None
        if self.backend and self.backend.is_finished():
            next_track = self.playlist.next(auto=True)
            if next_track is not None:
                self._load_current()
                self.backend.play()
            elif self._last_track:
                self.backend.stop()
                self._last_track = None

    def _refresh_player_info(self) -> None:
        if not self.backend:
            info = "Odtwarzacz niedostępny"
        else:
            position = self.backend.get_position()
            duration = self.backend.get_duration()
            if self.backend.is_playing():
                state = "odtwarzanie"
            elif self._last_track:
                state = "pauza"
            else:
                state = "zatrzymano"
            repeat = {
                RepeatMode.OFF: "wył.",
                RepeatMode.ALL: "playlista",
                RepeatMode.ONE: "utwór",
            }[self.playlist.repeat]
            info = (
                f"Czas: {self._format_time(position)} / {self._format_time(duration)}\n"
                f"Głośność: {self.backend.get_volume()}%\n"
                f"Stan: {state}\n"
                f"Shuffle: {'wł.' if self.playlist.shuffle else 'wył.'}\n"
                f"Repeat: {repeat}"
            )
        self.query_one("#player-info", Static).update(info)

    def on_unmount(self) -> None:
        if self.capture:
            self.capture.stop()
        if self.backend:
            self.backend.release()

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = int(seconds)
        return f"{seconds // 60}:{seconds % 60:02d}"


if __name__ == "__main__":
    ProampApp().run()
