# slupkowy visualizer do obslugi przez Textual
from rich.text import Text
from textual.widgets import Static


class Visualizer(Static):
    DEFAULT_CSS = """
    Visualizer {
        width: 100%;
        height: 10;
        border: round $primary;
        padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(self, bands: int = 30, **kwargs):
        super().__init__(**kwargs)
        self._bands = bands

    def set_levels(self, levels: tuple[float, ...]) -> None:
        height = 7
        if not levels:
            levels = (0.0,) * self._bands

        display_levels = [
            max(levels[
                round(i * len(levels) / self._bands):
                max(round((i + 1) * len(levels) / self._bands), round(i * len(levels) / self._bands) + 1)
            ])
            for i in range(self._bands)
        ]
        text = Text()
        for row in range(height, 0, -1):
            for level in display_levels:
                if level >= row / height:
                    text.append("█ ", style="bold bright_cyan" if row > 4 else "cyan")
                else:
                    text.append("  ")
            if row > 1:
                text.append("\n")
        self.update(text)
