"""Export and spec sheet tests (FR-09, FR-10, NFR-01, NFR-03, NFR-04)."""
import datetime
import pytest
import trimesh
from pypdf import PdfReader
from jewelry.design_export import ExportRefused, export_design
from jewelry.numbers import design_numbers
from jewelry.params import RingParams
from jewelry.report import CheckResult, Report
from jewelry.rules import load_prices, load_rules
from jewelry.spec_sheet import build_spec_sheet, spec_sheet_data

GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)
TODAY = datetime.date(2026, 10, 14)


def pdf_text(path):
    reader = PdfReader(str(path))
    return len(reader.pages), "\n".join(page.extract_text() for page in reader.pages)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    folder = tmp_path_factory.mktemp("export")
    return export_design(RingParams(**{**GOOD, "finish": "satin"}), folder, today=TODAY)


def test_fr09_export_writes_stl_step_and_spec_sheet(exported):
    assert exported.stl.exists() and exported.step.exists() and exported.spec_sheet.exists()


def test_fr09_exported_stl_is_watertight(exported):
    assert trimesh.load(str(exported.stl), process=True).is_watertight


def test_fr10_spec_sheet_is_exactly_one_page(exported):
    pages, _ = pdf_text(exported.spec_sheet)
    assert pages == 1


def test_fr10_spec_sheet_has_every_required_field(exported):
    _, text = pdf_text(exported.spec_sheet)
    for needed in ["Ring spec sheet", "Dimensions", "Band width", "Band thickness", "Stone",
                   "round, 6 mm", "Metal", "silver 925", "Metal weight", "Finish", "satin",
                   "Validation results", "US size", "EU size", "Metal cost range"]:
        assert needed in text, f"spec sheet is missing: {needed}"


def test_fr10_spec_sheet_weight_matches_the_numbers(exported):
    _, text = pdf_text(exported.spec_sheet)
    assert f"{exported.numbers.weight_g:.2f} g" in text


def test_fr10_spec_sheet_lists_every_validation_result(exported):
    _, text = pdf_text(exported.spec_sheet)
    flat = " ".join(text.split())
    assert "closed solid" in flat and "thinnest metal" in flat
    assert len(exported.report.results) >= 8


def test_nfr03_spec_sheet_shows_density_price_source_and_date(exported):
    _, text = pdf_text(exported.spec_sheet)
    flat = " ".join(text.split())
    assert "density of 10.36" in flat
    assert "PLACEHOLDER" in flat and "2026-10-14" in flat
    assert "have not been verified" in flat


def test_fr08_spec_sheet_says_the_cost_uses_finished_weight_not_cast_weight(exported):
    _, text = pdf_text(exported.spec_sheet)
    flat = " ".join(text.split())
    assert "finished weight" in flat and "lost in casting" in flat


def test_nfr04_spec_sheet_says_rules_were_not_reviewed_by_a_jeweler(exported):
    _, text = pdf_text(exported.spec_sheet)
    flat = " ".join(text.split())
    assert "reviewed by a jeweler: no" in flat
    assert "does not replace a human check" in flat


def test_nfr01_export_is_refused_for_a_failed_design_and_writes_nothing(tmp_path):
    bad = RingParams(**{**GOOD, "prong_diameter_mm": 0.4})
    folder = tmp_path / "out"
    with pytest.raises(ExportRefused) as info:
        export_design(bad, folder)
    assert not info.value.report.exportable
    assert not folder.exists() or not any(folder.iterdir())


def test_fr10_long_validation_reports_still_fit_on_one_page(tmp_path):
    p = RingParams(**GOOD)
    long = "This check has a very long explanation that wraps across several lines. " * 3
    report = Report([CheckResult(f"X{i}", 1, "warn", long) for i in range(10)])
    n = design_numbers(p, 430.0, load_rules(), load_prices())
    path = build_spec_sheet(p, report, n, load_rules(), tmp_path / "s.pdf", TODAY)
    pages, _ = pdf_text(path)
    assert pages == 1


def test_fr10_size_outside_the_conversion_range_does_not_break_the_sheet():
    p = RingParams(**{**GOOD, "ring_size_mm": 30.0})
    n = design_numbers(p, 430.0, load_rules(), load_prices())
    data = spec_sheet_data(p, Report([]), n, load_rules(), TODAY)
    assert ("US, UK and EU sizes", "outside the supported conversion range") in data["Ring size"]
