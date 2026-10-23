"""Build a design for the preview: report, numbers, sizes and a mesh from one call (FR-11).

The preview mesh and the validation report come from the same call so they can never disagree.
"""
from .engine import build_ring
from .numbers import design_numbers
from .params import RingParams
from .rules import load_prices, load_rules
from .sizes import ring_sizes
from .validate import nearest_buildable, validate

PREVIEW_TOLERANCE_MM, PREVIEW_ANGULAR = 0.05, 0.2


def tessellate(shape, tolerance=PREVIEW_TOLERANCE_MM, angular=PREVIEW_ANGULAR) -> dict:
    """Triangle mesh in mm as flat lists: [x, y, z, ...] and [i, j, k, ...]."""
    verts, tris = shape.val().tessellate(tolerance, angular)
    flat = [round(c, 3) for v in verts for c in (v.x, v.y, v.z)]
    return {"vertices": flat, "indices": [i for t in tris for i in t]}


def _bbox(vertices: list) -> dict:
    xs, ys, zs = vertices[0::3], vertices[1::3], vertices[2::3]
    return {"min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]}


def build_design(p: RingParams, rules: dict = None, prices: dict = None) -> dict:
    rules = rules or load_rules()
    prices = prices or load_prices()
    report = validate(p, rules)
    out = {"params": p.model_dump(), "exportable": report.exportable,
           "report": report.to_dict()["results"], "mesh": None, "bbox_mm": None,
           "numbers": None, "sizes": None, "suggestion": None}

    try:
        out["sizes"] = ring_sizes(p.ring_size_mm)
    except ValueError:
        pass  # outside the conversion range; the mm value is still shown

    layer1_failed = any(r.status == "fail" and r.check_id.startswith("L1-") for r in report.results)
    if not layer1_failed:
        try:
            shape = build_ring(p)
            out["mesh"] = tessellate(shape)
            out["bbox_mm"] = _bbox(out["mesh"]["vertices"])
            n = design_numbers(p, shape.val().Volume(), rules, prices)
            out["numbers"] = {"weight_g": n.weight_g, "density_g_cm3": n.density_g_cm3,
                              "currency": n.currency, "cost_low": n.cost_low, "cost_high": n.cost_high,
                              "cost_text": n.cost_text(), "price_source": n.price_source,
                              "price_as_of": n.price_as_of, "prices_verified": n.prices_verified}
        except Exception:
            pass  # L2-BUILD is already in the report; there is simply nothing to draw

    if not report.exportable:
        fixed, changes = nearest_buildable(p, rules)
        if changes:
            out["suggestion"] = {"params": fixed.model_dump(), "changes": changes}
    return out
