import random
from collections.abc import Iterable
from enum import Enum

from model.events import Observable
from model.track import Track


class RepeatMode(Enum):
    OFF = "off"
    ALL = "all"
    ONE = "one"


class PlaylistEvent(Enum):
    TRACKS_CHANGED = "tracks_changed"    # dodano/usunięto utwory
    CURRENT_CHANGED = "current_changed"  # zmienił się bieżący utwór
    MODE_CHANGED = "mode_changed"        # zmieniono shuffle lub repeat


class Playlist(Observable):
    def __init__(self, rng: random.Random | None = None) -> None:
        super().__init__()
        self._rng = rng or random.Random()
        self._tracks: list[Track] = []
        self._order: list[int] = []
        self._pos: int | None = None
        self._next_order: list[int] | None = None  # kolejnosc następnego cyklu
        self._shuffle = False
        self._repeat = RepeatMode.OFF

    #odczyt ------------
    @property
    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks)  # kopia tylko do odczytu

    def __len__(self) -> int:
        return len(self._tracks)

    @property
    def current_index(self) -> int | None:
        return None if self._pos is None else self._order[self._pos]

    @property
    def current(self) -> Track | None:
        index = self.current_index
        return None if index is None else self._tracks[index]

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    def upcoming(self, limit: int = 5) -> list[Track]:
        if self._pos is None:
            return []
        indices = self._order[self._pos + 1:]

        if self._repeat is RepeatMode.ALL and len(indices) < limit:
            indices = indices + self._upcoming_order()
        return [self._tracks[i] for i in indices[:limit]]

    def peek_next(self) -> Track | None:
        upcoming = self.upcoming(1)
        return upcoming[0] if upcoming else None

    def add(self, track: Track) -> None:
        self.add_many([track])

    def add_many(self, tracks: Iterable[Track]) -> None:
        new_tracks = list(tracks)
        if not new_tracks:
            return
        was_empty = not self._tracks

        for track in new_tracks:
            self._tracks.append(track)
            new_index = len(self._tracks) - 1
            if self._pos is None:            # pierwszy utwor na playliccie
                self._order = [new_index]
                self._pos = 0
            elif self._shuffle:              # losowe miejsce w utworach przed nami
                insert_at = self._rng.randint(self._pos + 1, len(self._order))
                self._order.insert(insert_at, new_index)
            else:
                self._order.append(new_index)
        self._next_order = None
        self._notify(PlaylistEvent.TRACKS_CHANGED)
        if was_empty:
            self._notify(PlaylistEvent.CURRENT_CHANGED)

    def remove(self, index: int) -> None:
        self._check_index(index)
        removed_current = index == self.current_index
        pos_removed = self._order.index(index)

        del self._tracks[index]
        del self._order[pos_removed]

        self._order = [i - 1 if i > index else i for i in self._order]
        self._next_order = None

        if not self._tracks:
            self._pos = None
        elif pos_removed < self._pos:
            self._pos -= 1
        elif pos_removed == self._pos:

            self._pos = min(self._pos, len(self._order) - 1)

        self._notify(PlaylistEvent.TRACKS_CHANGED)
        if removed_current:
            self._notify(PlaylistEvent.CURRENT_CHANGED)

    def clear(self) -> None:
        if not self._tracks:
            return
        self._tracks.clear()
        self._order = []
        self._pos = None
        self._next_order = None
        self._notify(PlaylistEvent.TRACKS_CHANGED)
        self._notify(PlaylistEvent.CURRENT_CHANGED)

    # nawigacja ------
    def select(self, index: int) -> Track:

        self._check_index(index)
        self._order, self._pos = self._make_order(index)
        self._next_order = None
        self._notify(PlaylistEvent.CURRENT_CHANGED)
        return self._tracks[index]

    def next(self, auto: bool = False) -> Track | None:

        if self._pos is None:
            return None
        if auto and self._repeat is RepeatMode.ONE:
            return self.current

        if self._pos + 1 < len(self._order):
            self._pos += 1
        elif self._repeat is RepeatMode.ALL:
            self._order = self._upcoming_order()
            self._next_order = None
            self._pos = 0
        else:
            return None
        self._notify(PlaylistEvent.CURRENT_CHANGED)
        return self.current

    def previous(self) -> Track | None:
        if self._pos is None:
            return None
        if self._pos > 0:
            self._pos -= 1
        elif self._repeat is RepeatMode.ALL:
            self._pos = len(self._order) - 1
        else:
            return self.current
        self._notify(PlaylistEvent.CURRENT_CHANGED)
        return self.current

    # tryby ----------
    def set_shuffle(self, enabled: bool) -> None:
        if enabled == self._shuffle:
            return
        self._shuffle = enabled
        # nowa kolejność, bieżący się nie zmienia
        self._order, self._pos = self._make_order(self.current_index)
        self._next_order = None
        self._notify(PlaylistEvent.MODE_CHANGED)

    def toggle_shuffle(self) -> None:
        self.set_shuffle(not self._shuffle)

    def set_repeat(self, mode: RepeatMode) -> None:
        if mode is self._repeat:
            return
        self._repeat = mode
        self._notify(PlaylistEvent.MODE_CHANGED)

    def cycle_repeat(self) -> None:
        sequence = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        self.set_repeat(sequence[(sequence.index(self._repeat) + 1) % 3])

    # pomocnicze -----------
    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self._tracks):
            raise IndexError(f"Brak utworu o indeksie {index}")

    def _make_order(self, current: int | None) -> tuple[list[int], int | None]:
        # budowanie kolejnosci zeby current byl obecnym utworem
        count = len(self._tracks)
        if count == 0:
            return [], None
        if not self._shuffle:
            return list(range(count)), current

        rest = [i for i in range(count) if i != current]
        self._rng.shuffle(rest)
        return [current] + rest, 0

    def _upcoming_order(self) -> list[int]:
        # kolejnosc nastepnego cyklu dla truby REPEAT ALL
        if self._next_order is None:
            order = list(range(len(self._tracks)))
            if self._shuffle:
                self._rng.shuffle(order)
                # zabezpieczenie zeby ten sam utwor nie gral na stykach cykli
                if len(order) > 1 and order[0] == self._order[-1]:
                    swap = self._rng.randrange(1, len(order))
                    order[0], order[swap] = order[swap], order[0]
            self._next_order = order

        return self._next_order