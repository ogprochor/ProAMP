from typing import Callable


class Observable:

    def __init__(self) -> None:
        self._listeners: list[Callable] = []

    def subscribe(self, callback: Callable) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify(self, event) -> None:
        for callback in list(self._listeners):
            callback(event)