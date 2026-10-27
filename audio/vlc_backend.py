from pathlib import Path

from audio.base import AudioBackend, AudioBackendError

try:
    import vlc
    _IMPORT_ERROR: Exception | None = None
except Exception as error:   # brak pakietu python-vlc albo samego programu VLC
    vlc = None
    _IMPORT_ERROR = error


class VlcBackend(AudioBackend):
    #Odtwarzanie przez libvlc

    def __init__(self) -> None:
        if vlc is None:
            raise AudioBackendError(
                "Nie udało się załadować VLC. " + str(_IMPORT_ERROR)
            )

        self._instance = vlc.Instance("--no-video", "--quiet")
        if self._instance is None:
            raise AudioBackendError("VLC nie uruchomił się (vlc.Instance zwróciło None).")
        self._player = self._instance.media_player_new()
        self._media = None
        self._volume = 100

    def load(self, path: Path) -> None:
        self._player.stop()
        self._media = self._instance.media_new_path(str(path))
        self._player.set_media(self._media)

    def play(self) -> None:
        self._player.play()
        self._player.audio_set_volume(self._volume)

    def pause(self) -> None:
        self._player.set_pause(1)

    def stop(self) -> None:
        self._player.stop()

    def seek(self, seconds: float) -> None:
        self._player.set_time(max(0, int(seconds * 1000)))   # VLC liczy w ms

    def set_volume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))
        self._player.audio_set_volume(self._volume)

    def get_volume(self) -> int:
        return self._volume

    def get_position(self) -> float:
        return max(0, self._player.get_time()) / 1000        # -1 gdy nic nie gra

    def get_duration(self) -> float:
        return max(0, self._player.get_length()) / 1000      # -1 gdy jeszcze nieznana

    def is_playing(self) -> bool:
        return bool(self._player.is_playing())

    def is_finished(self) -> bool:
        return self._player.get_state() in (vlc.State.Ended, vlc.State.Error)

    def release(self) -> None:
        self._player.release()
        self._instance.release()