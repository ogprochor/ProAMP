from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPixmap, QPolygon, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStyle,
    QStyleOptionSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QToolButton, QMenu,
)

from controller.app_controller import AppController, PlayerSnapshot
from model.playlist import RepeatMode


THEMES = {
    "Monochrome": {"background": "#101010", "surface": "#1b1b1b", "surface_alt": "#252525", "border": "#444444", "text": "#f2f2f2", "muted": "#aaaaaa", "accent": "#eeeeee", "accent_hover": "#ffffff", "accent_text": "#111111", "selection": "#505050", "bar_start": "#f5f5f5", "bar_end": "#777777"},
    "Neo": {"background": "#020804", "surface": "#07120b", "surface_alt": "#0d1d12", "border": "#1d6130", "text": "#d8ffe0", "muted": "#7caf87", "accent": "#00e83b", "accent_hover": "#20ff59", "accent_text": "#001505", "selection": "#145028", "bar_start": "#a6ff00", "bar_end": "#00ef51"},
    "Light": {"background": "#e9e5dd", "surface": "#f5f2ec", "surface_alt": "#e4dfd5", "border": "#c7c0b3", "text": "#292823", "muted": "#777165", "accent": "#8a7e69", "accent_hover": "#a0937c", "accent_text": "#ffffff", "selection": "#d3c5a8", "bar_start": "#9e8d6e", "bar_end": "#c4b89f"},
    "Helldiver": {"background": "#100806", "surface": "#21100b", "surface_alt": "#35170d", "border": "#713217", "text": "#ffe8ce", "muted": "#c69365", "accent": "#f04a1b", "accent_hover": "#ff6530", "accent_text": "#240800", "selection": "#762d13", "bar_start": "#ffcc27", "bar_end": "#f13a1a"},
    "Sh0ck": {"background": "#100020", "surface": "#22003b", "surface_alt": "#330052", "border": "#9c00a3", "text": "#fff0ff", "muted": "#d5a5e8", "accent": "#ff00c8", "accent_hover": "#ff42dd", "accent_text": "#220018", "selection": "#610078", "bar_start": "#00f6ff", "bar_end": "#ff00d4"},
    "Eco": {"background": "#edf1e9", "surface": "#ffffff", "surface_alt": "#e3eadd", "border": "#c2d1bd", "text": "#203024", "muted": "#66776a", "accent": "#4d9b50", "accent_hover": "#67b46a", "accent_text": "#ffffff", "selection": "#c7dfc2", "bar_start": "#a8ce54", "bar_end": "#469d54"},
    "classic": {"background": "#151718", "surface": "#222629", "surface_alt": "#2b3034", "border": "#41494d", "text": "#d9dedb", "muted": "#9ca6a2", "accent": "#ed8b24", "accent_hover": "#ffa43a", "accent_text": "#211408", "selection": "#51402b", "bar_start": "#7cf04a", "bar_end": "#ed8b24"},
    "Classic26": {"background": "#11151c", "surface": "#1a202a", "surface_alt": "#202833", "border": "#293442", "text": "#e7edf5", "muted": "#aeb9c8", "accent": "#61d6c5", "accent_hover": "#7beada", "accent_text": "#071717", "selection": "#174d55", "bar_start": "#61d6c5", "bar_end": "#8a6cff"},
}


class SpectrumBridge(QObject):
    levels_ready = Signal(object)


class SpectrumView(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._levels = (0.0,) * 30
        self._bar_start = QColor("#7cf04a")
        self._bar_end = QColor("#ed8b24")
        self.setMinimumHeight(160)

    def set_levels(self, levels: tuple[float, ...]) -> None:
        self._levels = levels
        self.update()

    def set_colors(self, start: str, end: str) -> None:
        self._bar_start = QColor(start)
        self._bar_end = QColor(end)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        count = len(self._levels)
        if not count:
            return

        left = 16
        right = self.width() - 16
        baseline = self.height() - 14
        max_height = max(10, self.height() - 30)
        gap = 4
        bar_width = max(2.0, (right - left - gap * (count - 1)) / count)

        for index, level in enumerate(self._levels):
            bar_height = max(3.0, max_height * max(0.0, min(1.0, level)))
            x = left + index * (bar_width + gap)
            y = baseline - bar_height
            ratio = index / max(1, count - 1)
            color = QColor(
                round(self._bar_start.red() * (1 - ratio) + self._bar_end.red() * ratio),
                round(self._bar_start.green() * (1 - ratio) + self._bar_end.green() * ratio),
                round(self._bar_start.blue() * (1 - ratio) + self._bar_end.blue() * ratio),
            )
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_height), 3, 3)


class ClickSlider(QSlider):
    value_committed = Signal(int)

    def __init__(self, orientation: Qt.Orientation, parent: QWidget | None = None):
        super().__init__(orientation, parent)
        self._mouse_drag_active = False

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_drag_active = True
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setSliderDown(True)
            self._set_value_from_mouse(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._mouse_drag_active:
            self._set_value_from_mouse(event.position().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._mouse_drag_active and event.button() == Qt.MouseButton.LeftButton:
            self._set_value_from_mouse(event.position().toPoint())
            self._mouse_drag_active = False
            self.setSliderDown(False)
            self.value_committed.emit(self.value())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _set_value_from_mouse(self, point) -> None:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        groove = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderGroove,
            self,
        )
        handle = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            option,
            QStyle.SubControl.SC_SliderHandle,
            self,
        )
        if self.orientation() == Qt.Orientation.Horizontal:
            start = groove.left() + handle.width() // 2
            end = groove.right() - handle.width() // 2
            position = point.x() - start
        else:
            start = groove.top() + handle.height() // 2
            end = groove.bottom() - handle.height() // 2
            position = point.y() - start
        span = max(1, end - start)
        value = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), position, span, option.upsideDown
        )
        self.setValue(value)


class MainWindow(QMainWindow):
    def __init__(self, controller: AppController | None = None):
        super().__init__()
        self.controller = controller or AppController()
        self._displayed_track = None
        self.current_theme = "Classic26"
        self._bridge = SpectrumBridge(self)

        self.setWindowTitle("Proamp 1.01")
        self.setMinimumSize(920, 640)
        self.resize(1100, 760)
        self._build_ui()
        self.apply_theme(self.current_theme)
        self._bridge.levels_ready.connect(self.spectrum.set_levels)
        self._connect_shortcuts()

        if self.controller.backend_error:
            QMessageBox.warning(self, "Odtwarzanie niedostępne", self.controller.backend_error)

        self.controller.start_spectrum(self._bridge.levels_ready.emit)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(100)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(14)

        heading_row = QHBoxLayout()
        self.theme_button = QToolButton()
        self.theme_button.setObjectName("themeButton")
        self.theme_button.setAccessibleName("Wybierz styl aplikacji")
        self.theme_menu = QMenu(self)
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions = {}
        for theme_name in THEMES:
            action = QAction(theme_name, self.theme_group)
            action.setCheckable(True)
            self.theme_group.addAction(action)
            action.triggered.connect(lambda checked=False, name=theme_name: self.apply_theme(name))
            self.theme_menu.addAction(action)
            self.theme_actions[theme_name] = action
        self.theme_button.setMenu(self.theme_menu)
        self.theme_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.theme_button.setToolTip("Wybierz paletę kolorów")
        heading = QLabel("P R O A M P")
        heading.setObjectName("heading")
        self.exit_button = QPushButton("Wyjdź")
        self.exit_button.setObjectName("exitButton")
        heading_row.addWidget(self.theme_button)
        heading_row.addWidget(heading)
        heading_row.addStretch(1)
        heading_row.addWidget(self.exit_button)
        root.addLayout(heading_row)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName("folderEdit")
        self.folder_edit.setPlaceholderText("Wklej ścieżkę do folderu z muzyką…")
        self.browse_button = QPushButton("Wybierz folder…")
        self.scan_button = QPushButton("Skanuj")
        self.scan_button.setObjectName("primaryButton")
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(self.browse_button)
        folder_row.addWidget(self.scan_button)
        root.addLayout(folder_row)

        self.track_table = QTableWidget(0, 5)
        self.track_table.setHorizontalHeaderLabels(["#", "Tytuł", "Wykonawca", "Album", "Czas"])
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.track_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.track_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.track_table.setAlternatingRowColors(True)
        self.track_table.verticalHeader().setVisible(False)
        header = self.track_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.track_table, 1)

        self.now_playing = QLabel("Nie odtwarzam utworu")
        self.now_playing.setObjectName("nowPlaying")
        root.addWidget(self.now_playing)

        display_row = QHBoxLayout()
        display_row.setSpacing(14)
        self.spectrum = SpectrumView()
        self.spectrum.setObjectName("spectrum")
        self.control_panel = QWidget()
        self.control_panel.setObjectName("controlPanel")
        self.control_panel.setMinimumWidth(250)
        panel_layout = QVBoxLayout(self.control_panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(10)

        panel_header = QHBoxLayout()
        panel_header.addStretch(1)
        self.help_button = QToolButton()
        self.help_button.setObjectName("helpButton")
        self.help_button.setText("ⓘ")
        self.help_button.setToolTipDuration(15000)
        self.help_button.setToolTip(
            "Skróty klawiaturowe:\n"
            "Spacja — odtwarzanie / pauza\n"
            "N — następny utwór\n"
            "P — poprzedni utwór\n"
            "← / → — przewiń o 10 sekund\n"
            "↑ / ↓ — zmień głośność\n"
            "S — losowa kolejność\n"
            "R — tryb powtarzania\n"
            "Q — wyjście z aplikacji"
        )
        panel_header.addWidget(self.help_button)
        panel_layout.addLayout(panel_header)

        transport = QHBoxLayout()
        self._media_icons = {
            "previous": self._make_media_icon("previous"),
            "play": self._make_media_icon("play"),
            "pause": self._make_media_icon("pause"),
            "next": self._make_media_icon("next"),
        }
        self.previous_button = QPushButton()
        self.previous_button.setIcon(self._media_icons["previous"])
        self.previous_button.setIconSize(QSize(22, 22))
        self.previous_button.setAccessibleName("Poprzedni utwór")
        self.previous_button.setToolTip("Poprzedni utwór (P)")
        self.play_button = QPushButton("Odtwórz")
        self.play_button.setIcon(self._media_icons["play"])
        self.play_button.setIconSize(QSize(20, 20))
        self.play_button.setObjectName("primaryButton")
        self.next_button = QPushButton()
        self.next_button.setIcon(self._media_icons["next"])
        self.next_button.setIconSize(QSize(22, 22))
        self.next_button.setAccessibleName("Następny utwór")
        self.next_button.setToolTip("Następny utwór (N)")
        transport.addWidget(self.previous_button)
        transport.addWidget(self.play_button, 1)
        transport.addWidget(self.next_button)
        panel_layout.addLayout(transport)

        modes = QHBoxLayout()
        self.shuffle_button = QPushButton("Losowo: wył.")
        self.repeat_button = QPushButton("Powtarzanie: wył.")
        modes.addWidget(self.shuffle_button)
        modes.addWidget(self.repeat_button)
        panel_layout.addLayout(modes)

        volume_row = QHBoxLayout()
        self.volume_label = QLabel("Głośność")
        self.volume_label.setObjectName("volumeLabel")
        self.volume_slider = ClickSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_value = QLabel("100%")
        self.volume_value.setObjectName("volumeValue")
        self.volume_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.volume_value.setMinimumWidth(40)
        volume_row.addWidget(self.volume_label)
        volume_row.addWidget(self.volume_slider, 1)
        volume_row.addWidget(self.volume_value)
        panel_layout.addLayout(volume_row)

        display_row.addWidget(self.spectrum, 2)
        display_row.addWidget(self.control_panel, 1)
        root.addLayout(display_row)

        seek_row = QHBoxLayout()
        self.position_label = QLabel("0:00")
        self.seek_slider = ClickSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.duration_label = QLabel("0:00")
        self.position_label.setMinimumWidth(48)
        self.duration_label.setMinimumWidth(48)
        seek_row.addWidget(self.position_label)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.duration_label)
        root.addLayout(seek_row)

        self.setCentralWidget(central)
        self._connect_controls()

    def _connect_controls(self) -> None:
        self.browse_button.clicked.connect(self._choose_folder)
        self.scan_button.clicked.connect(lambda: self._scan_folder())
        self.track_table.cellDoubleClicked.connect(self._play_row)
        self.play_button.clicked.connect(self._toggle_play)
        self.previous_button.clicked.connect(self.controller.previous_track)
        self.next_button.clicked.connect(self.controller.next_track)
        self.shuffle_button.clicked.connect(self._toggle_shuffle)
        self.repeat_button.clicked.connect(self._cycle_repeat)
        self.seek_slider.value_committed.connect(self._seek_to_value)
        self.volume_slider.valueChanged.connect(self._set_volume)
        self.exit_button.clicked.connect(self.close)

    def _connect_shortcuts(self) -> None:
        bindings = {
            "Space": self._toggle_play,
            "N": self.controller.next_track,
            "P": self.controller.previous_track,
            "Left": lambda: self.controller.seek(-10),
            "Right": lambda: self.controller.seek(10),
            "Up": lambda: self.controller.change_volume(5),
            "Down": lambda: self.controller.change_volume(-5),
            "S": self._toggle_shuffle,
            "R": self._cycle_repeat,
            "Q": self.close,
        }
        for key, callback in bindings.items():
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            setattr(self, f"_shortcut_{key.lower()}", shortcut)

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder z muzyką")
        if folder:
            self.folder_edit.setText(folder)
            self._scan_folder(Path(folder))

    def _scan_folder(self, folder: Path | None = None) -> None:
        raw_folder = self.folder_edit.text().strip().strip('"')
        if folder is None and not raw_folder:
            QMessageBox.information(self, "Folder z muzyką", "Wklej ścieżkę lub wybierz folder z muzyką.")
            return
        selected = folder if folder is not None else Path(raw_folder)
        try:
            tracks = self.controller.scan_folder(selected)
        except ValueError as error:
            QMessageBox.warning(self, "Nie znaleziono folderu", str(error))
            return

        self.track_table.setRowCount(len(tracks))
        for row, track in enumerate(tracks):
            values = (
                str(row + 1),
                track.title,
                track.artist,
                track.album,
                self._format_time(track.duration),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.track_table.setItem(row, column, item)
        self._displayed_track = None
        self.now_playing.setText(f"Załadowano {len(tracks)} utworów, wybierz utwór z playlisty")

    def _play_row(self, row: int, column: int) -> None:
        try:
            track = self.controller.select_track(row)
        except IndexError:
            return
        self._set_now_playing(track)

    def _toggle_play(self) -> None:
        self.controller.toggle_play()

    def _toggle_shuffle(self) -> None:
        self.controller.toggle_shuffle()
        self._refresh()

    def _cycle_repeat(self) -> None:
        self.controller.cycle_repeat()
        self._refresh()

    def _seek_to_value(self, value: int) -> None:
        target = float(value)
        snapshot = self.controller.snapshot()
        self.controller.seek(target - snapshot.position)

    def _set_volume(self, volume: int) -> None:
        snapshot = self.controller.snapshot()
        self.controller.change_volume(volume - snapshot.volume)

    def _refresh(self) -> None:
        snapshot = self.controller.tick()
        if snapshot.current != self._displayed_track:
            if snapshot.current:
                self._set_now_playing(snapshot.current)
            else:
                self._displayed_track = None
                self.now_playing.setText("Nie odtwarzam utworu")

        self.play_button.setText("Pauza" if snapshot.is_playing else "Odtwórz")
        self.play_button.setIcon(self._media_icons["pause" if snapshot.is_playing else "play"])
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(snapshot.volume)
        self.volume_slider.blockSignals(False)
        self.volume_value.setText(f"{snapshot.volume}%")
        self.shuffle_button.setText(f"Losowo: {'wł.' if snapshot.shuffle else 'wył.'}")
        repeat_names = {
            RepeatMode.OFF: "wył.",
            RepeatMode.ALL: "playlista",
            RepeatMode.ONE: "utwór",
        }
        self.repeat_button.setText(f"Powtarzanie: {repeat_names[snapshot.repeat]}")

        duration = max(0, int(snapshot.duration))
        position = max(0, int(snapshot.position))
        self.seek_slider.setRange(0, duration)
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(min(position, duration))
        self.position_label.setText(self._format_time(position))
        self.duration_label.setText(self._format_time(duration))
        if self.controller.capture and self.controller.capture.error:
            QMessageBox.warning(self, "Wizualizer niedostępny", self.controller.capture.error)
            self.controller.capture.error = None

    def _set_now_playing(self, track) -> None:
        self._displayed_track = track
        self.now_playing.setText(f"Teraz gra:  {track.artist} - {track.title}")

    def apply_theme(self, name: str) -> None:
        palette = THEMES[name]
        self.current_theme = name
        self.setStyleSheet(self._style(palette))
        self.spectrum.set_colors(palette["bar_start"], palette["bar_end"])
        self.theme_button.setIcon(self._make_menu_icon(palette["text"]))
        self.theme_actions[name].setChecked(True)

    @staticmethod
    def _make_menu_icon(color: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(3, 5, 18, 2, 1, 1)
        painter.drawRoundedRect(3, 11, 18, 2, 1, 1)
        painter.drawRoundedRect(3, 17, 18, 2, 1, 1)
        painter.end()
        return QIcon(pixmap)

    @staticmethod
    def _make_media_icon(kind: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f4f7fb"))

        if kind == "play":
            painter.drawPolygon(QPolygon([QPoint(6, 3), QPoint(21, 12), QPoint(6, 21)]))
        elif kind == "pause":
            painter.drawRoundedRect(5, 4, 5, 16, 1, 1)
            painter.drawRoundedRect(14, 4, 5, 16, 1, 1)
        elif kind == "previous":
            painter.drawRect(3, 5, 2, 14)
            painter.drawPolygon(QPolygon([QPoint(12, 5), QPoint(6, 12), QPoint(12, 19)]))
            painter.drawPolygon(QPolygon([QPoint(21, 5), QPoint(14, 12), QPoint(21, 19)]))
        else:
            painter.drawRect(19, 5, 2, 14)
            painter.drawPolygon(QPolygon([QPoint(12, 5), QPoint(18, 12), QPoint(12, 19)]))
            painter.drawPolygon(QPolygon([QPoint(3, 5), QPoint(10, 12), QPoint(3, 19)]))

        painter.end()
        return QIcon(pixmap)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self.controller.close()
        event.accept()

    @staticmethod
    def _format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60}:{seconds % 60:02d}"

    @staticmethod
    def _style(palette: dict[str, str]) -> str:
        style = """
        QWidget { background: $background; color: $text; font-size: 13px; }
        QLabel#heading { color: $accent; font-size: 16px; font-weight: 700; letter-spacing: 2px; }
        QLineEdit#folderEdit { color: $text; padding: 9px 12px; background: $surface; border: 1px solid $border; border-radius: 8px; }
        QLineEdit#folderEdit:focus { border-color: $accent; }
        QLineEdit#folderEdit::placeholder { color: $muted; }
        QLabel#volumeLabel, QLabel#volumeValue, QSlider { background: transparent; }
        QLabel#volumeValue { color: $muted; font-weight: 600; }
        QLabel#nowPlaying { color: $bar_start; font-size: 17px; font-weight: 600; padding: 6px 2px; }
        QWidget#controlPanel { background: $surface; border: 1px solid $border; border-radius: 10px; }
        QToolButton#themeButton, QToolButton#helpButton { color: $text; background: $surface_alt; border: 1px solid $border; border-radius: 14px; min-width: 30px; min-height: 30px; font-weight: 700; }
        QToolButton#themeButton:hover, QToolButton#helpButton:hover { background: $selection; border-color: $accent; }
        QPushButton#exitButton { color: $text; padding: 6px 10px; }
        QTableWidget { background: $surface; alternate-background-color: $surface_alt; border: 1px solid $border; border-radius: 10px; gridline-color: $border; selection-background-color: $selection; }
        QHeaderView::section { background: $surface_alt; color: $muted; padding: 9px; border: none; font-weight: 600; }
        QTableWidget::item { padding: 7px; }
        QPushButton { color: $text; background: $surface_alt; border: 1px solid $border; border-radius: 8px; padding: 9px 13px; }
        QPushButton:hover { background: $selection; border-color: $accent; }
        QPushButton#primaryButton { color: $accent_text; background: $accent; border-color: $accent_hover; font-weight: 600; }
        QPushButton#primaryButton:hover { background: $accent_hover; }
        QSlider::groove:horizontal { height: 5px; background: $surface_alt; border-radius: 2px; }
        QSlider::handle:horizontal { background: $accent; width: 14px; margin: -5px 0; border-radius: 7px; }
        QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
        QMenu { color: $text; background: $surface; border: 1px solid $border; padding: 5px; }
        QMenu::item { padding: 7px 28px; border-radius: 4px; }
        QMenu::item:selected { color: $text; background: $selection; }
        QToolTip { color: $text; background: $surface_alt; border: 1px solid $border; padding: 5px; }
        """
        for key in sorted(palette, key=len, reverse=True):
            style = style.replace(f"${key}", palette[key])
        return style


def run_gui() -> int:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    return app.exec()
