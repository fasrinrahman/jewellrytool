"""Layer 1: parameter rules, checked before anything is built (FR-04, FR-06)."""
from .params import RingParams
from .report import CheckResult, FAIL, PASS


def _name(metal: str) -> str:
    return metal.replace("_", " ")


def _nearest_count(value: int, allowed: list) -> int:
    return min(allowed, key=lambda c: (abs(c - value), -c))


def check_parameters(p: RingParams, rules: dict) -> list:
    metals = rules["metals"]
    if p.metal not in metals:
        options = ", ".join(_name(m) for m in metals)
        return [CheckResult("L1-METAL", 1, FAIL,
                            f"The metal '{p.metal}' is not supported. Choose one of: {options}.")]
    m, metal = metals[p.metal], _name(p.metal)
    out = []

    lo, hi = m["band_width_range_mm"]
    if lo <= p.band_width_mm <= hi:
        out.append(CheckResult("L1-BAND-WIDTH", 1, PASS,
                   f"The band width of {p.band_width_mm:g} mm is within the {lo:g} to {hi:g} mm range for {metal}."))
    else:
        new = min(max(p.band_width_mm, lo), hi)
        out.append(CheckResult("L1-BAND-WIDTH", 1, FAIL,
                   f"The band is {p.band_width_mm:g} mm wide, but {metal} bands must be between {lo:g} and {hi:g} mm wide. Use {new:g} mm.",
                   {"field": "band_width_mm", "value": new}))

    need = m["min_band_thickness_mm"]
    if p.band_thickness_mm >= need:
        out.append(CheckResult("L1-BAND-THICKNESS", 1, PASS,
                   f"The band thickness of {p.band_thickness_mm:g} mm meets the {need:g} mm minimum for {metal}."))
    else:
        out.append(CheckResult("L1-BAND-THICKNESS", 1, FAIL,
                   f"The band is {p.band_thickness_mm:g} mm thick, which is too thin to cast or wear safely in {metal}. It needs at least {need:g} mm.",
                   {"field": "band_thickness_mm", "value": need}))

    need = m["min_prong_diameter_mm"]
    if p.prong_diameter_mm >= need:
        out.append(CheckResult("L1-PRONG-DIAMETER", 1, PASS,
                   f"The prong thickness of {p.prong_diameter_mm:g} mm meets the {need:g} mm minimum for {metal}."))
    else:
        out.append(CheckResult("L1-PRONG-DIAMETER", 1, FAIL,
                   f"The prongs are {p.prong_diameter_mm:g} mm thick, so they could bend or break and lose the stone. {metal.capitalize()} prongs need at least {need:g} mm.",
                   {"field": "prong_diameter_mm", "value": need}))

    shape = rules["stone_shapes"].get(p.stone_shape)
    if shape is None:
        out.append(CheckResult("L1-STONE-SHAPE", 1, FAIL,
                   f"The {p.stone_shape} stone shape is not supported yet."))
        return out

    lo, hi = shape["size_range_mm"]
    if lo <= p.stone_size_mm <= hi:
        out.append(CheckResult("L1-STONE-SIZE", 1, PASS,
                   f"The {p.stone_size_mm:g} mm {p.stone_shape} stone is within the supported {lo:g} to {hi:g} mm range."))
    else:
        new = min(max(p.stone_size_mm, lo), hi)
        out.append(CheckResult("L1-STONE-SIZE", 1, FAIL,
                   f"A {p.stone_size_mm:g} mm {p.stone_shape} stone is outside the supported {lo:g} to {hi:g} mm range. The nearest supported size is {new:g} mm.",
                   {"field": "stone_size_mm", "value": new}))

    allowed = shape["prong_counts"]
    if p.prong_count in allowed:
        out.append(CheckResult("L1-PRONG-COUNT", 1, PASS,
                   f"{p.prong_count} prongs is supported for a {p.stone_shape} stone."))
    else:
        new = _nearest_count(p.prong_count, allowed)
        options = " or ".join(str(c) for c in allowed)
        out.append(CheckResult("L1-PRONG-COUNT", 1, FAIL,
                   f"{p.prong_count} prongs is not supported for a {p.stone_shape} stone; use {options}. The nearest is {new}.",
                   {"field": "prong_count", "value": new}))
    return out
