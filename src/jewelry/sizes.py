"""Ring size conversion between US, UK, EU and mm (FR-07).

Inner diameter in mm is the exact value. US, UK and EU are derived from it:
  US: 11.63 mm at size 0, +0.8128 mm per whole size
  EU: ISO 8653, the size is the inner circumference in mm
  UK: letters from A (37.5 mm circumference), +1.25 mm per letter, half sizes marked with 1/2
UK letters differ by up to half a size between published charts, so treat UK as approximate.
"""
import math
import re

MIN_MM, MAX_MM = 12.0, 25.0
US_BASE_MM, US_STEP_MM = 11.63, 0.8128
UK_BASE_CIRC, UK_STEP = 37.5, 1.25
SYSTEMS = ("mm", "us", "uk", "eu")


def _round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def _check_range(d: float) -> float:
    if not (MIN_MM <= d <= MAX_MM):
        raise ValueError(f"An inner diameter of {d:.1f} mm is outside the supported "
                         f"{MIN_MM:g} to {MAX_MM:g} mm range.")
    return d


def _uk_text(circ_mm: float) -> str:
    x = (circ_mm - UK_BASE_CIRC) / UK_STEP          # letters above A, fractional
    if x < -0.25:
        raise ValueError("This size is smaller than UK size A.")
    half = _round_half_up(x * 2)                     # nearest half step
    if half <= 50:                                   # A to Z
        letter = chr(65 + max(half, 0) // 2)
        return letter + ("\u00bd" if half % 2 else "")
    whole = _round_half_up(x)                        # beyond Z: Z+1, Z+2, ...
    return "Z" if whole <= 25 else f"Z+{whole - 25}"


def _parse_uk(text: str) -> float:
    t = text.strip().upper()
    m = re.fullmatch(r"Z\s*\+\s*(\d+)", t)
    if m:
        return UK_BASE_CIRC + UK_STEP * (25 + int(m.group(1)))
    m = re.fullmatch(r"([A-Z])\s*(\u00bd|1/2|\.5)?", t)
    if not m:
        raise ValueError(f"'{text}' is not a UK ring size. Use a letter such as N or N\u00bd.")
    idx = ord(m.group(1)) - 65 + (0.5 if m.group(2) else 0)
    return UK_BASE_CIRC + UK_STEP * idx


def inner_diameter_mm(system: str, value) -> float:
    """Convert a size in any supported system to inner diameter in mm."""
    system = system.lower()
    if system not in SYSTEMS:
        raise ValueError(f"Unknown size system '{system}'. Use one of: {', '.join(SYSTEMS)}.")
    if system == "mm":
        d = float(value)
    elif system == "us":
        d = US_BASE_MM + US_STEP_MM * float(value)
    elif system == "eu":
        d = float(value) / math.pi
    else:
        d = _parse_uk(str(value)) / math.pi
    return _check_range(d)


def ring_sizes(diameter_mm: float) -> dict:
    """All size systems for one inner diameter. US and UK are rounded to the nearest half size."""
    d = _check_range(float(diameter_mm))
    circ = d * math.pi
    return {
        "mm": round(d, 2),
        "us": _round_half_up((d - US_BASE_MM) / US_STEP_MM * 2) / 2,
        "uk": _uk_text(circ),
        "eu": _round_half_up(circ),
    }


def convert(from_system: str, value, to_system: str):
    """Convert a size from one system to another, for example convert('us', 7, 'uk')."""
    return ring_sizes(inner_diameter_mm(from_system, value))[to_system.lower()]
