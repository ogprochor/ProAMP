import random
from pathlib import Path

import pytest

from model.playlist import Playlist, PlaylistEvent, RepeatMode
from model.track import Track


def make_playlist(count: int, seed: int = 0, **modes) -> Playlist:
    playlist = Playlist(rng=random.Random(seed))
    playlist.add_many(
        Track(path=Path(f"t{i}.mp3"), title=f"t{i}") for i in range(count)
    )
    if modes.get("shuffle"):
        playlist.set_shuffle(True)
    if "repeat" in modes:
        playlist.set_repeat(modes["repeat"])
    return playlist


def titles(tracks) -> list[str]:
    return [t.title for t in tracks]


def drain(playlist: Playlist) -> list[str]:
    """Zbiera utwory od bieżącego do końca (repeat OFF)."""
    result = [playlist.current.title]
    while (track := playlist.next()) is not None:
        result.append(track.title)
    return result


# ---------------------------------------------------------- pusta playlista
def test_empty_playlist():
    playlist = Playlist()
    assert playlist.current is None
    assert playlist.next() is None
    assert playlist.previous() is None
    assert playlist.peek_next() is None
    assert playlist.upcoming() == []
    assert len(playlist) == 0


# ------------------------------------------------------------------ podstawy
def test_first_added_track_becomes_current():
    playlist = make_playlist(3)
    assert playlist.current.title == "t0"
    assert playlist.current_index == 0


def test_sequential_play_ends_with_none():
    playlist = make_playlist(3)
    assert drain(playlist) == ["t0", "t1", "t2"]
    assert playlist.current.title == "t2"   # na końcu zostajemy na ostatnim


def test_repeat_all_wraps():
    playlist = make_playlist(3, repeat=RepeatMode.ALL)
    seen = [playlist.next().title for _ in range(4)]
    assert seen == ["t1", "t2", "t0", "t1"]


def test_repeat_one_only_on_auto_advance():
    playlist = make_playlist(3, repeat=RepeatMode.ONE)
    assert playlist.next(auto=True).title == "t0"   # utwór sam się skończył
    assert playlist.next(auto=False).title == "t1"  # użytkownik kliknął "następny"


def test_previous_at_start():
    playlist = make_playlist(3)
    assert playlist.previous().title == "t0"
    playlist.set_repeat(RepeatMode.ALL)
    assert playlist.previous().title == "t2"


def test_cycle_repeat_order():
    playlist = make_playlist(1)
    modes = []
    for _ in range(3):
        playlist.cycle_repeat()
        modes.append(playlist.repeat)
    assert modes == [RepeatMode.ALL, RepeatMode.ONE, RepeatMode.OFF]


# ------------------------------------------------------------------- shuffle
def test_shuffle_plays_each_track_once_starting_from_current():
    playlist = make_playlist(8, shuffle=True)
    played = drain(playlist)
    assert played[0] == "t0"
    assert sorted(played) == sorted(f"t{i}" for i in range(8))


def test_toggle_shuffle_keeps_current_track():
    playlist = make_playlist(6)
    playlist.next()
    playlist.next()
    playlist.toggle_shuffle()
    assert playlist.current.title == "t2"
    playlist.toggle_shuffle()
    assert playlist.current.title == "t2"
    assert playlist.next().title == "t3"   # po wyłączeniu shuffle idziemy po kolei


@pytest.mark.parametrize("seed", range(20))
def test_peek_next_always_matches_next(seed):
    playlist = make_playlist(5, seed=seed, shuffle=True, repeat=RepeatMode.ALL)
    for _ in range(30):               # obejmuje kilka przejść między cyklami
        expected = playlist.peek_next()
        assert playlist.next() == expected


@pytest.mark.parametrize("seed", range(20))
def test_no_immediate_repeat_between_shuffle_cycles(seed):
    playlist = make_playlist(4, seed=seed, shuffle=True, repeat=RepeatMode.ALL)
    previous = playlist.current
    for _ in range(40):
        current = playlist.next()
        assert current != previous
        previous = current


def test_select_in_shuffle_starts_new_cycle_from_selected():
    playlist = make_playlist(6, shuffle=True)
    playlist.select(4)
    assert playlist.current.title == "t4"
    assert sorted(drain(playlist)) == sorted(f"t{i}" for i in range(6))


def test_upcoming_respects_limit_and_excludes_current():
    playlist = make_playlist(5)
    assert titles(playlist.upcoming(2)) == ["t1", "t2"]


# ------------------------------------------------------ dodawanie/usuwanie
def test_remove_before_current_keeps_current_track():
    playlist = make_playlist(4)
    playlist.select(2)
    playlist.remove(0)
    assert playlist.current.title == "t2"
    assert playlist.current_index == 1


def test_remove_current_moves_to_following_track():
    playlist = make_playlist(4)
    playlist.select(1)
    playlist.remove(1)
    assert playlist.current.title == "t2"


def test_remove_last_current_stays_on_new_last():
    playlist = make_playlist(3)
    playlist.select(2)
    playlist.remove(2)
    assert playlist.current.title == "t1"


def test_remove_everything():
    playlist = make_playlist(2)
    playlist.remove(0)
    playlist.remove(0)
    assert playlist.current is None
    assert len(playlist) == 0


def test_remove_invalid_index():
    with pytest.raises(IndexError):
        make_playlist(2).remove(5)


@pytest.mark.parametrize("seed", range(10))
def test_add_in_shuffle_keeps_every_track_in_cycle(seed):
    playlist = make_playlist(4, seed=seed, shuffle=True)
    playlist.next()
    playlist.add(Track(path=Path("new.mp3"), title="new"))
    remaining = titles(playlist.upcoming(10))
    assert "new" in remaining
    assert len(remaining) == 3   # 2 pozostałe ze starego cyklu + nowy


# ------------------------------------------------------------------ zdarzenia
def test_events_are_emitted():
    playlist = make_playlist(3)
    events = []
    playlist.subscribe(events.append)

    playlist.next()
    playlist.toggle_shuffle()
    playlist.add(Track(path=Path("x.mp3"), title="x"))
    playlist.remove(0)

    assert PlaylistEvent.CURRENT_CHANGED in events
    assert PlaylistEvent.MODE_CHANGED in events
    assert PlaylistEvent.TRACKS_CHANGED in events


def test_no_event_when_nothing_changes():
    playlist = make_playlist(2)
    events = []
    playlist.subscribe(events.append)
    playlist.set_shuffle(False)
    playlist.set_repeat(RepeatMode.OFF)
    assert events == []