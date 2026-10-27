from pathlib import Path

from model.library import Library, LibraryEvent
from model.metadata import _parse_int, _parse_year, read_track
from model.track import UNKNOWN_ALBUM, UNKNOWN_ARTIST, Track


def make_library(tmp_path: Path, specs: dict[str, dict]) -> Library:
    """specs: {'sciezka/wzgledna.mp3': {pola Track}} - tworzy puste pliki
    i podstawia czytnik tagów, który zwraca dane z `specs`."""
    by_path = {}
    for relative, fields in specs.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        by_path[path] = Track(path=path, **fields)
    library = Library(reader=lambda p: by_path[p])
    library.add_folder(tmp_path)
    return library


# ----------------------------------------------------------------- skanowanie
def test_scan_is_recursive_and_ignores_other_files(tmp_path):
    (tmp_path / "notes.txt").touch()
    (tmp_path / "cover.jpg").touch()
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A"},
        "sub/deep/b.flac": {"title": "B"},
    })
    assert sorted(t.title for t in library.tracks) == ["A", "B"]


def test_rescan_does_not_duplicate(tmp_path):
    library = make_library(tmp_path, {"a.mp3": {"title": "A"}})
    library.add_folder(tmp_path)
    assert len(library) == 1


def test_event_emitted_only_when_something_found(tmp_path):
    library = Library(reader=lambda p: Track(path=p, title="x"))
    events = []
    library.subscribe(events.append)
    library.add_folder(tmp_path)              # pusty folder
    assert events == []
    (tmp_path / "a.mp3").touch()
    library.add_folder(tmp_path)
    assert events == [LibraryEvent.CHANGED]


# --------------------------------------------------------------------- albumy
def test_tracks_grouped_into_album_and_sorted_by_disc_and_number(tmp_path):
    base = {"artist": "Artysta", "album": "Płyta"}
    library = make_library(tmp_path, {
        "c.mp3": {"title": "Trzeci", "track_number": 1, "disc_number": 2, **base},
        "a.mp3": {"title": "Pierwszy", "track_number": 1, **base},
        "b.mp3": {"title": "Drugi", "track_number": 2, **base},
        "z.mp3": {"title": "Bez numeru", **base},
    })
    albums = library.albums()
    assert len(albums) == 1
    assert [t.title for t in albums[0].tracks] == [
        "Pierwszy", "Drugi", "Bez numeru", "Trzeci"
    ]


def test_same_album_title_different_artists_stay_separate(tmp_path):
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A", "artist": "Jeden", "album": "Greatest Hits"},
        "b.mp3": {"title": "B", "artist": "Dwa", "album": "Greatest Hits"},
    })
    assert [a.artist for a in library.albums()] == ["Dwa", "Jeden"]


def test_album_artist_tag_merges_compilation(tmp_path):
    common = {"album": "Składanka", "album_artist": "Różni wykonawcy"}
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A", "artist": "Jeden", **common},
        "b.mp3": {"title": "B", "artist": "Dwa", **common},
    })
    albums = library.albums()
    assert len(albums) == 1
    assert albums[0].artist == "Różni wykonawcy"


def test_grouping_ignores_letter_case(tmp_path):
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A", "artist": "Abba", "album": "Arrival"},
        "b.mp3": {"title": "B", "artist": "ABBA", "album": "arrival"},
    })
    assert len(library.albums()) == 1


def test_album_year_is_earliest_year(tmp_path):
    base = {"artist": "X", "album": "Y"}
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A", "year": 2001, **base},
        "b.mp3": {"title": "B", "year": 1999, **base},
        "c.mp3": {"title": "C", **base},
    })
    assert library.albums()[0].year == 1999


def test_artists_unique_and_sorted(tmp_path):
    library = make_library(tmp_path, {
        "a.mp3": {"title": "A", "artist": "beta", "album": "1"},
        "b.mp3": {"title": "B", "artist": "Alfa", "album": "2"},
        "c.mp3": {"title": "C", "artist": "Alfa", "album": "3"},
    })
    assert library.artists() == ["Alfa", "beta"]


# -------------------------------------------------------------------- szukanie
def test_search_matches_title_artist_and_album(tmp_path):
    library = make_library(tmp_path, {
        "a.mp3": {"title": "Wonderwall", "artist": "Oasis", "album": "Morning Glory"},
        "b.mp3": {"title": "Yellow", "artist": "Coldplay", "album": "Parachutes"},
    })
    assert [t.title for t in library.search("oasis")] == ["Wonderwall"]
    assert [t.title for t in library.search("PARACH")] == ["Yellow"]
    assert len(library.search("")) == 2
    assert library.search("nic takiego") == []


# ------------------------------------------------------------------- metadane
def test_parse_helpers():
    assert _parse_int("3/12") == 3
    assert _parse_int("07") == 7
    assert _parse_int("") == 0
    assert _parse_int("abc") == 0
    assert _parse_year("2019-05-17") == 2019
    assert _parse_year("2019") == 2019
    assert _parse_year("") is None


def test_read_track_falls_back_for_broken_file(tmp_path):
    broken = tmp_path / "Moja piosenka.mp3"
    broken.write_text("to nie jest prawdziwe audio")
    track = read_track(broken)
    assert track.title == "Moja piosenka"      # tytuł z nazwy pliku
    assert track.artist == UNKNOWN_ARTIST
    assert track.album == UNKNOWN_ALBUM
    assert track.duration == 0.0