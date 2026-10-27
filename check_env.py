import struct
import sys


def ok(msg):
    print(f"  [OK]   {msg}")


def fail(msg):
    print(f"  [BŁĄD] {msg}")


def main() -> int:
    problems = 0
    print("Sprawdzam środowisko...\n")

    # Python
    v = sys.version_info
    if v >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} - potrzebny 3.11+")
        problems += 1

    bits = struct.calcsize("P") * 8
    if bits == 64:
        ok("Python 64-bit")
    else:
        fail(f"Python {bits}-bit - zainstaluj wersję 64-bit (musi pasować do VLC)")
        problems += 1

    # Biblioteki
    for name in ("textual", "mutagen", "numpy", "pytest"):
        try:
            __import__(name)
            ok(f"biblioteka {name}")
        except ImportError:
            fail(f"brak biblioteki {name} (pip install -r requirements.txt)")
            problems += 1

    # VLC
    try:
        import vlc

        instance = vlc.Instance()
        if instance is None:
            raise RuntimeError("vlc.Instance() zwróciło None")
        ok(f"VLC działa (libvlc {vlc.libvlc_get_version().decode()})")
    except ImportError:
        fail("brak biblioteki python-vlc")
        problems += 1
    except Exception as e:
        fail(f"VLC niedostępny: {e}\n"
             "         Zainstaluj VLC 64-bit z videolan.org (ta sama bitowość co Python).")
        problems += 1

    print()
    if problems:
        print(f"Znaleziono problemów: {problems}")
        return 1
    print("Wszystko gotowe, można zaczynać.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
