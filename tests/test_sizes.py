"""Size conversion tests (FR-07). Reference rows come from a published chart:
https://aquamarise.com/blogs/journal/ring-size-chart (US, diameter mm, UK, EU)."""
import pytest
from jewelry.sizes import convert, inner_diameter_mm, ring_sizes

CHART = [
    (4, 14.9, "H\u00bd", 47), (4.5, 15.3, "I\u00bd", 48), (5, 15.7, "J\u00bd", 49),
    (5.5, 16.1, "K\u00bd", 51), (6, 16.5, "L\u00bd", 52), (6.5, 16.9, "M\u00bd", 53),
    (7, 17.3, "N\u00bd", 54), (7.5, 17.7, "O\u00bd", 56), (8, 18.1, "P\u00bd", 57),
    (8.5, 18.5, "Q\u00bd", 58), (9, 18.9, "R\u00bd", 60), (9.5, 19.4, "S\u00bd", 61),
    (10, 19.8, "T\u00bd", 62), (10.5, 20.2, "U\u00bd", 63), (11, 20.6, "V\u00bd", 65),
    (11.5, 21.0, "W\u00bd", 66), (12, 21.4, "Y", 67), (12.5, 21.8, "Z", 69),
    (13, 22.2, "Z+1", 70), (13.5, 22.6, "Z+2", 71), (14, 23.0, "Z+3", 72),
    (14.5, 23.4, "Z+4", 74), (15, 23.8, "Z+5", 75),
]


# US 12 is 0.015 mm from the boundary between UK X\u00bd and Y. The chart rounds to Y; the exact
# formula lands on X\u00bd. Either is a legitimate reading of the same finger size.
UK_BOUNDARY_ROWS = {12: ("X\u00bd", "Y")}


@pytest.mark.parametrize("us,mm,uk,eu", CHART)
def test_fr07_us_size_matches_the_published_chart(us, mm, uk, eu):
    sizes = ring_sizes(inner_diameter_mm("us", us))
    assert round(sizes["mm"], 1) == mm
    assert sizes["us"] == us
    if us in UK_BOUNDARY_ROWS:
        assert sizes["uk"] in UK_BOUNDARY_ROWS[us]
    else:
        assert sizes["uk"] == uk
    # The chart rounds EU from an already-rounded diameter, so allow one step at .5 boundaries.
    assert abs(sizes["eu"] - eu) <= 1


@pytest.mark.parametrize("us,mm,uk,eu", CHART)
def test_fr07_converting_back_from_uk_and_eu_returns_the_same_us_size(us, mm, uk, eu):
    assert convert("uk", uk, "us") == us
    assert abs(convert("eu", eu, "us") - us) <= 0.5


def test_fr07_the_common_size_7_row():
    assert convert("us", 7, "mm") == pytest.approx(17.32, abs=0.01)
    assert convert("us", 7, "eu") == 54
    assert convert("us", 7, "uk") == "N\u00bd"
    assert convert("mm", 17.3, "us") == 7


def test_fr07_eu_size_is_the_inner_circumference_in_mm():
    assert inner_diameter_mm("eu", 54) == pytest.approx(54 / 3.14159265, abs=1e-6)


@pytest.mark.parametrize("text", ["N\u00bd", "N 1/2", "n1/2", "N.5"])
def test_fr07_uk_half_sizes_are_accepted_in_common_spellings(text):
    assert convert("uk", text, "us") == 7


def test_fr07_uk_whole_letter_and_beyond_z():
    assert convert("uk", "N", "us") == pytest.approx(6.5, abs=0.5)
    assert convert("uk", "Z+2", "us") == 13.5


@pytest.mark.parametrize("system,value", [("us", 0), ("us", 30), ("mm", 5), ("mm", 40), ("eu", 20)])
def test_fr07_sizes_outside_the_supported_range_are_rejected(system, value):
    with pytest.raises(ValueError, match="outside the supported"):
        inner_diameter_mm(system, value)


def test_fr07_unknown_system_and_bad_uk_text_are_rejected():
    with pytest.raises(ValueError):
        inner_diameter_mm("jp", 10)
    with pytest.raises(ValueError, match="not a UK ring size"):
        inner_diameter_mm("uk", "7")
