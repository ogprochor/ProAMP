"""Analiza widma sygnału audio dla wizualizera."""
from __future__ import annotations
import numpy as np


class SpectrumAnalyzer:
    #Zamienia probki na poziomy pasm czestotliwosci (0.0–1.0)

    SILENCE_RMS = 0.0008
    ATTACK = 0.82
    RELEASE = 0.62
    SILENCE_RELEASE = 0.42

    def __init__(self, bands: int = 48, min_frequency: float = 35, max_frequency: float = 11000):
        self.bands = bands
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self._levels = np.zeros(bands, dtype=float)

    def analyze(self, samples: np.ndarray, sample_rate: int) -> tuple[float, ...]:
        if samples.size < 32:
            return tuple(self._levels)

        # Stereo do mono - normalizacja zapewnia podobny wykres przy roznej głośnosci
        mono = samples.mean(axis=1) if samples.ndim > 1 else samples
        mono = mono.astype(float, copy=True)
        mono -= mono.mean()
        signal_rms = float(np.sqrt(np.mean(mono ** 2)))

        if signal_rms < self.SILENCE_RMS:
            return self.silence()
        mono /= signal_rms

        window = np.hanning(len(mono))
        spectrum = np.abs(np.fft.rfft(mono * window)) / max(window.sum(), 1.0)
        frequencies = np.fft.rfftfreq(len(mono), d=1 / sample_rate)
        edges = np.geomspace(self.min_frequency, min(self.max_frequency, sample_rate / 2), self.bands + 1)

        targets = np.zeros(self.bands, dtype=float)
        for i, (low, high) in enumerate(zip(edges[:-1], edges[1:])):
            mask = (frequencies >= low) & (frequencies < high)
            if mask.any():
                targets[i] = np.sqrt(np.mean(spectrum[mask] ** 2))

        # kazde pasmo jest porownywane z najsilniejszym pasmem w tej probce,
        # temu wysokosc slupkow jest taka sama niezaleznie od glosnosci

        peak = float(targets.max())
        if peak > 0:
            relative = targets / peak
            decibels = 20 * np.log10(np.maximum(relative, 1e-4))
            targets = np.clip((decibels + 36) / 36, 0, 1)

        rates = np.where(targets > self._levels, self.ATTACK, self.RELEASE)
        self._levels += (targets - self._levels) * rates
        return tuple(float(level) for level in self._levels)

    def silence(self) -> tuple[float, ...]:
        self._levels *= self.SILENCE_RELEASE
        return tuple(float(level) for level in self._levels)
