"""Test names carry the SRS requirement ID they cover (NFR-07)."""
import cadquery as cq
import pytest
from pydantic import ValidationError
from jewelry.engine import build_ring, seat_depth_mm
from jewelry.export import export_files
from jewelry.params import RingParams
from jewelry.rules import load_rules

GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)


def test_fr01_builds_one_valid_solid():
    shape = build_ring(RingParams(**GOOD))
    assert shape.val().isValid()
    assert len(shape.solids().vals()) == 1
    assert shape.val().Volume() > 0


def test_fr01_ring_size_sets_outer_diameter():
    bb = build_ring(RingParams(**GOOD)).val().BoundingBox()
    assert bb.xlen == pytest.approx(17.3 + 2 * 1.8, abs=0.01)


def test_fr01_seat_depth_is_derived_from_the_stone():
    assert seat_depth_mm("round", 6.0) == pytest.approx(2.58)


def test_fr12_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        RingParams(**GOOD, engraving="love")


def test_fr12_schema_rejects_wrong_types_and_values():
    with pytest.raises(ValidationError):
        RingParams(**{**GOOD, "prong_count": "many"})
    with pytest.raises(ValidationError):
        RingParams(**{**GOOD, "band_thickness_mm": -1})


def test_fr03_default_rules_load_from_file():
    rules = load_rules()
    assert "silver_925" in rules["metals"]
    assert rules["verified_by_jeweler"] is False


def test_fr03_changing_the_file_changes_the_rules(tmp_path):
    f = tmp_path / "rules.yaml"
    f.write_text("metals: {silver_925: {min_wall_mm: 1.5}}\n"
                 "stone_shapes: {}\ntolerances: {}\n")
    assert load_rules(f)["metals"]["silver_925"]["min_wall_mm"] == 1.5


def test_fr03_incomplete_rules_file_is_rejected(tmp_path):
    f = tmp_path / "rules.yaml"
    f.write_text("metals: {}\n")
    with pytest.raises(ValueError):
        load_rules(f)


def test_fr09_export_reopens_watertight_and_volumes_match(tmp_path):
    shape = build_ring(RingParams(**GOOD))
    mesh = export_files(shape, tmp_path / "ring")
    assert (tmp_path / "ring.step").exists() and (tmp_path / "ring.stl").exists()
    assert mesh.is_watertight
    step_vol = cq.importers.importStep(str(tmp_path / "ring.step")).val().Volume()
    tol = load_rules()["tolerances"]["stl_step_volume_pct"]
    assert abs(mesh.volume - step_vol) / step_vol * 100 < tol
