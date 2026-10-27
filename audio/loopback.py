#Przechwytywanie dźwięku wyjściowego systemu do wizualizera (WASAPI)
from __future__ import annotations
import threading
from collections.abc import Callable

import numpy as np
from audio.spectrum import SpectrumAnalyzer


class LoopbackSpectrum:
    """Czyta miks z domyślnego głośnika"""

    def __init__(self, on_levels: Callable[[tuple[float, ...]], None], bands: int = 48):
        self._on_levels = on_levels
        self._analyzer = SpectrumAnalyzer(bands=bands)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="audio-loopback", daemon=True)
        self._thread.start()


    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self) -> None:
        try:
            import soundcard as sc

            speaker = sc.default_speaker()
            loopback = sc.get_microphone(speaker.name, include_loopback=True)

            # bufor 4096 probek
            with loopback.recorder(samplerate=22050, channels=2, blocksize=1024) as recorder:
                window = np.empty((0, 2), dtype=float)
                while not self._stop.is_set():
                    chunk = recorder.record(numframes=1024)
                    window = np.concatenate((window, chunk), axis=0)[-4096:]
                    if len(window) == 4096:
                        self._on_levels(self._analyzer.analyze(window, 22050))

        except Exception as exc:
            self.error = str(exc)
            self._on_levels(self._analyzer.silence())
