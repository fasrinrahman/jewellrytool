"""Layer 1: parameter rules, checked before anything is built (FR-04, FR-06).

Every dimension has a lower AND an upper limit, and prongs are also checked against the stone,
so an absurd design (a 50 mm band, prongs covering the stone) can never be exported.
"""
import math
from .params import RingParams
from .report import CheckResult, FAIL, PASS
from .sizes import ring_sizes


def _name(metal: str) -> str:
    return metal.replace("_", " ")


def _nearest_count(value: int, allowed: list) -> int:
    return min(allowed, key=lambda c: (abs(c - value), -c))


def _us_range(lo_mm: float, hi_mm: float) -> str:
    try:
        return f" (roughly US size {ring_sizes(lo_mm)['us']:g} to {ring_sizes(hi_mm)['us']:g})"
    except ValueError:
        return ""


def _range_check(check_id, value, lo, hi, *, label, metal, too_low, too_high, field):
    """Pass inside [lo, hi]; otherwise fail with the nearest allowed value as the fix."""
    if lo <= value <= hi:
        return CheckResult(check_id, 1, PASS,
                           f"The {label} of {value:g} mm is within the {lo:g} to {hi:g} mm range for {metal}.")
    new = min(max(value, lo), hi)
    why = too_low if value < lo else too_high
    return CheckResult(check_id, 1, FAIL,
                       f"The {label} is {value:g} mm, which is {why}. For {metal} it must be between "
                       f"{lo:g} and {hi:g} mm. Use {new:g} mm.", {"field": field, "value": new})


def check_parameters(p: RingParams, rules: dict) -> list:
    metals = rules["metals"]
    if p.metal not in metals:
        options = ", ".join(_name(m) for m in metals)
        shown = p.metal if len(p.metal) <= 24 else p.metal[:24] + "..."
        return [CheckResult("L1-METAL", 1, FAIL,
                            f"The metal '{shown}' is not supported. Choose one of: {options}.")]
    m, metal = metals[p.metal], _name(p.metal)
    out = []

    lo, hi = rules["ring_size_range_mm"]
    if lo <= p.ring_size_mm <= hi:
        out.append(CheckResult("L1-RING-SIZE", 1, PASS,
                   f"The inner diameter of {p.ring_size_mm:g} mm is within the supported {lo:g} to {hi:g} mm range."))
    else:
        new = min(max(p.ring_size_mm, lo), hi)
        why = "too small to fit a finger" if p.ring_size_mm < lo else "too large to be a finger ring"
        out.append(CheckResult("L1-RING-SIZE", 1, FAIL,
                   f"An inner diameter of {p.ring_size_mm:g} mm is {why}. Supported rings are {lo:g} to {hi:g} mm"
                   f"{_us_range(lo, hi)}. The nearest supported size is {new:g} mm.",
                   {"field": "ring_size_mm", "value": new}))

    lo, hi = m["band_width_range_mm"]
    out.append(_range_check("L1-BAND-WIDTH", p.band_width_mm, lo, hi, label="band width", metal=metal,
        too_low="too narrow", too_high="too wide", field="band_width_mm"))

    out.append(_range_check("L1-BAND-THICKNESS", p.band_thickness_mm, m["min_band_thickness_mm"],
        m["max_band_thickness_mm"], label="band thickness", metal=metal,
        too_low="too thin to cast or wear safely", too_high="too thick to be comfortable or to cast sensibly",
        field="band_thickness_mm"))

    out.append(_range_check("L1-PRONG-DIAMETER", p.prong_diameter_mm, m["min_prong_diameter_mm"],
        m["max_prong_diameter_mm"], label="prong thickness", metal=metal,
        too_low="so thin it could bend or break and lose the stone", too_high="so thick it would hide the stone",
        field="prong_diameter_mm"))

    shape = rules["stone_shapes"].get(p.stone_shape)
    if shape is None:
        out.append(CheckResult("L1-STONE-SHAPE", 1, FAIL, f"The {p.stone_shape} stone shape is not supported yet."))
        return out

    lo, hi = shape["size_range_mm"]
    if lo <= p.stone_size_mm <= hi:
        out.append(CheckResult("L1-STONE-SIZE", 1, PASS,
                   f"The {p.stone_size_mm:g} mm {p.stone_shape} stone is within the supported {lo:g} to {hi:g} mm range."))
    else:
        new = min(max(p.stone_size_mm, lo), hi)
        out.append(CheckResult("L1-STONE-SIZE", 1, FAIL,
                   f"A {p.stone_size_mm:g} mm {p.stone_shape} stone is outside the supported {lo:g} to {hi:g} mm range. "
                   f"The nearest supported size is {new:g} mm.", {"field": "stone_size_mm", "value": new}))

    allowed = shape["prong_counts"]
    if p.prong_count in allowed:
        out.append(CheckResult("L1-PRONG-COUNT", 1, PASS,
                   f"{p.prong_count} prongs is supported for a {p.stone_shape} stone."))
    else:
        new = _nearest_count(p.prong_count, allowed)
        options = " or ".join(str(c) for c in allowed)
        out.append(CheckResult("L1-PRONG-COUNT", 1, FAIL,
                   f"{p.prong_count} prongs is not supported for a {p.stone_shape} stone; use {options}. "
                   f"The nearest is {new}.", {"field": "prong_count", "value": new}))

    out.append(_coverage_check(p, shape, m))
    return out


def _coverage_check(p: RingParams, shape: dict, m: dict) -> CheckResult:
    """All prongs together may cover only part of the stone's edge, or the stone cannot be seen or set."""
    limit = shape["max_prong_coverage"]
    girdle = math.pi * p.stone_size_mm
    covered = p.prong_count * p.prong_diameter_mm / girdle
    if covered <= limit:
        return CheckResult("L1-PRONG-COVERAGE", 1, PASS,
                           f"The prongs cover {covered:.0%} of the stone's edge, within the {limit:.0%} limit.")
    msg = (f"{p.prong_count} prongs of {p.prong_diameter_mm:g} mm would cover {covered:.0%} of the {p.stone_size_mm:g} mm "
           f"stone's edge, but prongs should cover at most {limit:.0%} so the stone stays visible and properly set.")
    fit = limit * girdle / p.prong_count                      # thickest prong that fits
    if fit >= m["min_prong_diameter_mm"]:
        value = max(m["min_prong_diameter_mm"], math.floor(fit * 20) / 20)
        return CheckResult("L1-PRONG-COVERAGE", 1, FAIL, msg + f" Use prongs of {value:g} mm.",
                           {"field": "prong_diameter_mm", "value": value})
    # Thinner prongs alone cannot fit. Fewer prongs might: take the most prongs whose thinnest
    # allowed size still fits. The next round of checks then thins them to fit exactly.
    fewer = [c for c in shape["prong_counts"] if c * m["min_prong_diameter_mm"] <= limit * girdle]
    if fewer:
        return CheckResult("L1-PRONG-COVERAGE", 1, FAIL, msg + f" Use {max(fewer)} prongs.",
                           {"field": "prong_count", "value": max(fewer)})
    return CheckResult("L1-PRONG-COVERAGE", 1, FAIL, msg + " Use a larger stone.")
