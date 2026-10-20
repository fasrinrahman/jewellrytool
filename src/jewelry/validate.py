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
    """Return (design that passes layer 1, list of changes made)."""
    rules = rules or load_rules()
    changes = []
    for r in check_parameters(p, rules):
        if r.status == FAIL and r.fix:
            changes.append({"field": r.fix["field"],
                            "old": getattr(p, r.fix["field"]), "new": r.fix["value"]})
            p = p.model_copy(update={r.fix["field"]: r.fix["value"]})
    return p, changes


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
