from abc import ABC, abstractmethod
from pathlib import Path


class AudioBackendError(Exception):
    """Backend mógł zostać uruchomiony."""

class AudioBackend(ABC):

    @abstractmethod
    def load(self, path: Path) -> None:
        """Ładuje plik (nie zaczyna jeszcze grać)."""

    @abstractmethod
    def play(self) -> None:
        """Zaczyna odtwarzanie lub wznawia je po pauzie."""

    @abstractmethod
    def pause(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def seek(self, seconds: float) -> None:
        """Przewija do podanej pozycji (w sekundach od początku utworu)."""

    @abstractmethod
    def set_volume(self, value: int) -> None:
        """Głośność 0-100."""

    @abstractmethod
    def get_volume(self) -> int: ...

    @abstractmethod
    def get_position(self) -> float:
        """Aktualna pozycja w sekundach."""

    @abstractmethod
    def get_duration(self) -> float:
        """Długość załadowanego utworu w sekundach (0, gdy jeszcze nieznana)."""

    @abstractmethod
    def is_playing(self) -> bool: ...

    @abstractmethod
    def is_finished(self) -> bool:
        """True, gdy utwór doszedł do końca sam (nie po stop) lub nie da się go odtworzyć."""

    def release(self) -> None:
        """Zwalnia zasoby przy zamykaniu aplikacji."""