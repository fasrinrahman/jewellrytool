"""Regression tests for geometry defects found by scanning the allowed design space (NFR-01)."""
import tempfile
from pathlib import Path
import cadquery as cq
import pytest
import trimesh
from jewelry import engine, validate as validate_module
from jewelry.engine import RingBuildError, build_ring
from jewelry.export import export_files
from jewelry.layer1 import check_parameters
from jewelry.params import RingParams
from jewelry.report import FAIL
from jewelry.rules import load_rules
from jewelry.service import build_design
from jewelry.validate import validate

BASE = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0, band_thickness_mm=1.8,
            stone_shape="round", stone_size_mm=6.0, prong_count=4, prong_diameter_mm=1.0)


def sound(p) -> bool:
    shape = build_ring(p)
    with tempfile.TemporaryDirectory() as d:
        mesh = export_files(shape, Path(d) / "r")
    return (shape.val().isValid() and len(shape.solids().vals()) == 1
            and mesh.is_watertight and len(mesh.split(only_watertight=False)) == 1)


def test_nfr01_prongs_tangent_to_the_collar_edge_no_longer_leave_a_sliver():
    """Prong thickness 1.3 mm on a 9.07 mm stone used to leave an open edge in the mesh."""
    p = RingParams(metal="gold_14k", ring_size_mm=15.61, band_width_mm=3.16, band_thickness_mm=1.25,
                   stone_shape="round", stone_size_mm=9.07, prong_count=6, prong_diameter_mm=1.3)
    assert sound(p)


@pytest.mark.parametrize("prong", [1.17, 1.18, 1.2, 1.23, 1.24])
def test_nfr01_the_ring_no_longer_splits_in_two_for_a_4_5_mm_stone(prong):
    """Prongs of 1.18 to 1.23 mm on a 4.5 mm stone used to leave the head detached from the band."""
    assert len(build_ring(RingParams(**{**BASE, "stone_size_mm": 4.5, "prong_diameter_mm": prong})).solids().vals()) == 1


def test_nfr01_the_default_ring_geometry_is_unchanged_by_the_fixes():
    assert build_ring(RingParams(**BASE)).val().Volume() == pytest.approx(473.1, abs=0.2)


def test_nfr01_scan_of_stone_and_prong_sizes_always_gives_one_closed_piece():
    rules, checked = load_rules(), 0
    for stone in (3.0, 4.5, 6.0, 9.0):
        for count in (4, 6):
            for i in range(0, 13):                       # 0.8 mm to 2.0 mm in 0.1 mm steps
                p = RingParams(**{**BASE, "stone_size_mm": stone, "prong_count": count,
                                  "prong_diameter_mm": round(0.8 + 0.1 * i, 2)})
                if any(r.status == FAIL for r in check_parameters(p, rules)):
                    continue
                checked += 1
                assert sound(p), (stone, count, p.prong_diameter_mm)
    assert checked >= 20


# ---------- the safety nets themselves ----------

def two_pieces():
    far = cq.Workplane("XY").box(1, 1, 1).translate((50, 0, 0))
    return cq.Workplane("XY").box(1, 1, 1).add(far).combine(glue=False)


def test_nfr01_a_failed_fuse_is_retried_with_a_different_overlap(monkeypatch):
    real, calls = engine._assemble, []

    def flaky(p, sink):
        calls.append(sink)
        return two_pieces() if len(calls) == 1 else real(p, sink)

    monkeypatch.setattr(engine, "_assemble", flaky)
    assert len(build_ring(RingParams(**BASE)).solids().vals()) == 1
    assert calls[:2] == [0.5, 0.55]


def test_nfr01_a_ring_that_never_fuses_is_refused_not_exported(monkeypatch):
    monkeypatch.setattr(engine, "_assemble", lambda p, sink: two_pieces())
    with pytest.raises(RingBuildError):
        build_ring(RingParams(**BASE))
    report = validate(RingParams(**BASE))
    assert not report.exportable
    assert any(r.check_id == "L2-BUILD" and r.status == FAIL for r in report.results)
    assert build_design(RingParams(**BASE))["mesh"] is None
