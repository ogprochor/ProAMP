from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from controller.app_controller import AppController, PlayerSnapshot
from model.playlist import RepeatMode
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
        self.controller = AppController()
        self._displayed_track = None

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
        if self.controller.backend_error:
            self.notify(f"Odtwarzanie niedostępne: {self.controller.backend_error}", severity="error")
        self.controller.start_spectrum(self._receive_levels)
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
        try:
            tracks = self.controller.scan_folder(Path(raw))
        except ValueError as error:
            self.notify(str(error), severity="error")
            return
        table = self.query_one(DataTable)
        table.clear()
        for index, track in enumerate(tracks):
            table.add_row(
                str(index + 1), track.title, track.artist, track.album,
                self._format_time(track.duration), key=str(index),
            )
        self.query_one("#now-playing", Static).update(
            f"Załadowano {len(tracks)} utworów · wybierz utwór z playlisty"
        )
        self._displayed_track = None

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "tracks" and self.controller.playlist.tracks:
            self._play_index(event.cursor_row)

    def action_toggle_play(self) -> None:
        self.controller.toggle_play()

    def action_next_track(self) -> None:
        self.controller.next_track()

    def action_previous_track(self) -> None:
        self.controller.previous_track()

    def action_seek_backward(self) -> None:
        self.controller.seek(-10)

    def action_seek_forward(self) -> None:
        self.controller.seek(10)

    def action_volume_up(self) -> None:
        self._change_volume(5)

    def action_volume_down(self) -> None:
        self._change_volume(-5)

    def _change_volume(self, amount: int) -> None:
        self.controller.change_volume(amount)

    def action_shuffle(self) -> None:
        self.controller.toggle_shuffle()

    def action_repeat(self) -> None:
        self.controller.cycle_repeat()

    def _play_index(self, index: int) -> None:
        try:
            track = self.controller.select_track(index)
        except IndexError:
            return
        self.query_one("#now-playing", Static).update(f"Teraz gra:  {track.artist} — {track.title}")
        self._displayed_track = track

    def _receive_levels(self, levels: tuple[float, ...]) -> None:
        try:
            self.call_from_thread(self._set_levels_ui, levels)
        except RuntimeError:
            pass

    def _set_levels_ui(self, levels: tuple[float, ...]) -> None:
        self.query_one(Visualizer).set_levels(levels)

    def _refresh_status(self) -> None:
        state = self.controller.tick()
        self._render_current_track(state)
        self._refresh_player_info(state)
        if self.controller.capture and self.controller.capture.error:
            self.notify(f"Wizualizer niedostępny: {self.controller.capture.error}", severity="error")
            self.controller.capture.error = None

    def _render_current_track(self, state: PlayerSnapshot) -> None:
        if state.current == self._displayed_track:
            return
        if state.current:
            label = f"Teraz gra: {state.current.artist} — {state.current.title}"
        else:
            label = "Nie odtwarzam utworu"
        self.query_one("#now-playing", Static).update(label)
        self._displayed_track = state.current

    def _refresh_player_info(self, state: PlayerSnapshot) -> None:
        if not self.controller.backend:
            info = "Odtwarzacz niedostępny"
        else:
            if state.is_playing:
                playback_state = "odtwarzanie"
            else:
                playback_state = "pauza / stop"
            repeat = {
                RepeatMode.OFF: "wył.",
                RepeatMode.ALL: "playlista",
                RepeatMode.ONE: "utwór",
            }[self.controller.playlist.repeat]
            info = (
                f"Czas: {self._format_time(state.position)} / {self._format_time(state.duration)}\n"
                f"Głośność: {state.volume}%\n"
                f"Stan: {playback_state}\n"
                f"Shuffle: {'wł.' if state.shuffle else 'wył.'}\n"
                f"Repeat: {repeat}"
            )
        self.query_one("#player-info", Static).update(info)

    def on_unmount(self) -> None:
        self.controller.close()

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = int(seconds)
        return f"{seconds // 60}:{seconds % 60:02d}"


if __name__ == "__main__":
    ProampApp().run()
