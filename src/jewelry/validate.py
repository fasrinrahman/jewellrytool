"""Run both validation layers and suggest the nearest buildable design (FR-04 to FR-06)."""
import tempfile
from pathlib import Path
import cadquery as cq
from .engine import build_ring
from .export import export_files
from .layer1 import check_parameters
from .layer2 import check_mesh
from .params import RingParams
from .report import CheckResult, FAIL, UNVERIFIED, Report
from .rules import load_rules


def nearest_buildable(p: RingParams, rules: dict = None):
    """Return (the nearest design that passes layer 1, list of net changes).

    Fixes are applied and re-checked until nothing more can be fixed, because one fix (for example
    thinner prongs) can change what another check needs. A problem with no safe fix, such as an
    unknown metal, is left as it is and still fails layer 1."""
    rules = rules or load_rules()
    original = fixed = p
    for _ in range(6):
        fixes = [r.fix for r in check_parameters(fixed, rules) if r.status == FAIL and r.fix]
        if not fixes:
            break
        for f in fixes:
            fixed = fixed.model_copy(update={f["field"]: f["value"]})
    changes = [{"field": f, "old": getattr(original, f), "new": getattr(fixed, f)}
               for f in RingParams.model_fields if getattr(original, f) != getattr(fixed, f)]
    return fixed, changes


def validate(p: RingParams, rules: dict = None) -> Report:
    rules = rules or load_rules()
    results = check_parameters(p, rules)

    if any(r.status == FAIL for r in results):
        results.append(CheckResult("L2-NOT-RUN", 2, UNVERIFIED,
                       "The ring was not built because the parameter checks failed, so the model checks were not run."))
    else:
        try:
            shape = build_ring(p)
            with tempfile.TemporaryDirectory() as d:
                mesh = export_files(shape, Path(d) / "ring")
                step_volume = cq.importers.importStep(str(Path(d) / "ring.step")).val().Volume()
            results += check_mesh(mesh, step_volume, p, rules)
        except Exception:
            results.append(CheckResult("L2-BUILD", 2, FAIL,
                           "The 3D model could not be built from these values. Try a different size or stone."))

    if not rules.get("verified_by_jeweler"):
        results.append(CheckResult("RULES-UNVERIFIED", None, UNVERIFIED,
                       "The design rules have not been reviewed by a jeweler yet. Treat these results as a guide, not a guarantee."))
    return Report(results)
