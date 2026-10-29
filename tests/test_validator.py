"""Validator tests. Names carry the SRS requirement ID they cover (NFR-07)."""
import numpy as np
import pytest
import trimesh
from jewelry import validate as validate_module
from jewelry.layer1 import check_parameters
from jewelry.layer2 import check_mesh
from jewelry.params import RingParams
from jewelry.report import FAIL, PASS, UNVERIFIED, WARN
from jewelry.rules import load_rules
from jewelry.validate import nearest_buildable, validate

GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)

# Known-bad designs: (field, bad value, check that must fail)
KNOWN_BAD = [
    ("prong_diameter_mm", 0.4, "L1-PRONG-DIAMETER"),
    ("band_thickness_mm", 0.5, "L1-BAND-THICKNESS"),
    ("band_width_mm", 0.5, "L1-BAND-WIDTH"),
    ("stone_size_mm", 12.0, "L1-STONE-SIZE"),
    ("prong_count", 5, "L1-PRONG-COUNT"),
    ("metal", "bronze", "L1-METAL"),
]


def bad(field, value):
    return RingParams(**{**GOOD, field: value})


def status_of(results, check_id):
    return next(r.status for r in results if r.check_id == check_id)


# ---------- FR-04: layer 1, parameter rules ----------

def test_fr04_good_parameters_pass_every_layer1_check():
    results = check_parameters(RingParams(**GOOD), load_rules())
    assert len(results) == 7  # ring size, band width, band thickness, prong thickness, stone size, prong count, prong coverage
    assert all(r.status == PASS for r in results)


@pytest.mark.parametrize("field,value,expected", KNOWN_BAD)
def test_fr04_known_bad_parameters_fail_the_expected_check(field, value, expected):
    results = check_parameters(bad(field, value), load_rules())
    assert status_of(results, expected) == FAIL


# ---------- FR-04: layer 2, mesh checks (hand-made meshes, no CAD needed) ----------

def box(x, y, z):
    return trimesh.creation.box(extents=(x, y, z))


def test_fr04_thick_closed_mesh_passes_layer2():
    m = box(10, 10, 2)
    results = check_mesh(m, m.volume, RingParams(**GOOD), load_rules())
    assert [r.status for r in results] == [PASS, PASS, PASS, PASS]  # closed, one piece, thickness, volume


def test_fr04_mesh_with_a_hole_fails_watertight_and_skips_the_rest():
    m = box(10, 10, 2)
    holed = trimesh.Trimesh(vertices=m.vertices, faces=m.faces[1:], process=False)
    results = check_mesh(holed, 200.0, RingParams(**GOOD), load_rules())
    assert status_of(results, "L2-WATERTIGHT") == FAIL
    assert status_of(results, "L2-SINGLE-PIECE") == UNVERIFIED
    assert status_of(results, "L2-WALL-THICKNESS") == UNVERIFIED
    assert status_of(results, "L2-VOLUME-MATCH") == UNVERIFIED


def test_fr04_two_closed_solids_fail_the_one_piece_check():
    """Each box is watertight on its own, which is exactly why this needs its own check."""
    a = box(10, 10, 2)
    b = box(10, 10, 2)
    b.apply_translation((0, 0, 20))              # a head floating free of the band
    two = trimesh.util.concatenate([a, b])
    assert two.is_watertight
    results = check_mesh(two, two.volume, RingParams(**GOOD), load_rules())
    assert status_of(results, "L2-WATERTIGHT") == PASS
    assert status_of(results, "L2-SINGLE-PIECE") == FAIL
    assert "2 separate pieces" in next(r.message for r in results if r.check_id == "L2-SINGLE-PIECE")


def test_fr04_thin_plate_fails_wall_thickness():
    m = box(10, 10, 0.4)
    results = check_mesh(m, m.volume, RingParams(**GOOD), load_rules())
    assert status_of(results, "L2-WALL-THICKNESS") == FAIL


def test_fr04_volume_mismatch_between_exports_fails():
    m = box(10, 10, 2)
    results = check_mesh(m, m.volume * 1.05, RingParams(**GOOD), load_rules())
    assert status_of(results, "L2-VOLUME-MATCH") == FAIL


def test_fr04_wall_exactly_at_the_minimum_is_not_flagged_for_mesh_rounding():
    m = box(10, 10, 0.8 - 0.005)  # measures a hair under 0.8 because of mesh rounding
    results = check_mesh(m, m.volume, RingParams(**GOOD), load_rules())
    assert status_of(results, "L2-WALL-THICKNESS") == PASS


# ---------- Full pipeline on a real ring ----------

def test_fr04_good_ring_passes_all_checks_and_is_exportable():
    report = validate(RingParams(**GOOD))
    assert report.exportable
    assert not report.with_status(FAIL) and not report.with_status(WARN)
    assert status_of(report.results, "L2-WALL-THICKNESS") == PASS


# ---------- FR-05: plain-language report ----------

@pytest.mark.parametrize("field,value,expected", KNOWN_BAD)
def test_fr05_every_failure_explains_itself_in_plain_words(field, value, expected):
    report = validate(bad(field, value))
    for r in report.results:
        if r.status != PASS:
            assert len(r.message) > 20
            assert "_mm" not in r.message


def test_fr05_failures_with_a_known_safe_value_carry_a_fix():
    for field, value, expected in KNOWN_BAD:
        if expected == "L1-METAL":
            continue
        result = next(r for r in check_parameters(bad(field, value), load_rules())
                      if r.check_id == expected)
        assert result.fix and result.fix["field"] == field


def test_fr05_report_text_and_dict_cover_every_check():
    report = validate(bad("prong_diameter_mm", 0.4))
    text = report.to_text()
    assert "FAIL" in text and "Not ready to export" in text
    assert len(report.to_dict()["results"]) == len(report.results)


# ---------- FR-06: nearest buildable version ----------

@pytest.mark.parametrize("field,value,expected",
                         [c for c in KNOWN_BAD if c[2] != "L1-METAL"])
def test_fr06_nearest_buildable_passes_layer1(field, value, expected):
    fixed, changes = nearest_buildable(bad(field, value))
    assert changes and changes[0]["field"] == field
    assert all(r.status == PASS for r in check_parameters(fixed, load_rules()))


def test_fr06_paper_thin_band_with_large_stone_gets_a_buildable_alternative():
    design = RingParams(**{**GOOD, "band_thickness_mm": 0.5, "stone_size_mm": 12.0})
    report = validate(design)
    assert not report.exportable
    fixed, changes = nearest_buildable(design)
    assert {c["field"] for c in changes} == {"band_thickness_mm", "stone_size_mm"}
    fixed_report = validate(fixed)
    assert fixed_report.exportable
    assert not fixed_report.with_status(WARN)  # built exactly at the minimums, still clean


def test_fr06_unchanged_when_design_is_already_buildable():
    fixed, changes = nearest_buildable(RingParams(**GOOD))
    assert changes == [] and fixed == RingParams(**GOOD)


# ---------- NFR-01: never export a failed design ----------

@pytest.mark.parametrize("field,value,expected", KNOWN_BAD)
def test_nfr01_every_known_bad_design_is_blocked(field, value, expected):
    assert validate(bad(field, value)).exportable is False


def test_nfr01_layer1_failure_skips_the_build(monkeypatch):
    def boom(_):
        raise AssertionError("must not build a design that failed layer 1")
    monkeypatch.setattr(validate_module, "build_ring", boom)
    report = validate(bad("prong_diameter_mm", 0.4))
    assert not report.exportable
    assert status_of(report.results, "L2-NOT-RUN") == UNVERIFIED


def test_nfr01_a_build_crash_blocks_export(monkeypatch):
    def crash(_):
        raise RuntimeError("geometry kernel error")
    monkeypatch.setattr(validate_module, "build_ring", crash)
    report = validate(RingParams(**GOOD))
    assert not report.exportable
    assert status_of(report.results, "L2-BUILD") == FAIL


# ---------- NFR-04: honest about what is unverified ----------

def test_nfr04_unreviewed_rules_are_listed_as_unverified():
    report = validate(bad("prong_diameter_mm", 0.4))
    assert status_of(report.results, "RULES-UNVERIFIED") == UNVERIFIED


def test_nfr04_no_unverified_rules_note_once_a_jeweler_has_reviewed_them():
    rules = load_rules()
    rules["verified_by_jeweler"] = True
    report = validate(bad("prong_diameter_mm", 0.4), rules)
    assert all(r.check_id != "RULES-UNVERIFIED" for r in report.results)
