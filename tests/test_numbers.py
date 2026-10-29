"""Weight and cost tests (FR-08, NFR-02, NFR-03)."""
import pytest
import trimesh
from jewelry.engine import build_ring
from jewelry.export import export_files
from jewelry.numbers import design_numbers
from jewelry.params import RingParams
from jewelry.rules import load_prices, load_rules

GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)


def test_fr08_weight_is_volume_times_density():
    n = design_numbers(RingParams(**GOOD), 1000.0, load_rules(), load_prices())
    assert n.weight_g == pytest.approx(10.36)        # 1 cm3 of 925 silver at 10.36 g/cm3


def test_fr08_cost_range_scales_with_weight_and_price_range():
    prices = load_prices()
    n = design_numbers(RingParams(**GOOD), 1000.0, load_rules(), prices)
    low, high = prices["metals"]["silver_925"]["price_per_gram"]
    assert n.cost_low == pytest.approx(10.36 * low)
    assert n.cost_high == pytest.approx(10.36 * high)
    assert n.cost_low < n.cost_high


def test_fr08_price_source_and_date_travel_with_the_numbers():
    n = design_numbers(RingParams(**GOOD), 1000.0, load_rules(), load_prices())
    assert n.price_source and n.price_as_of
    assert n.prices_verified is False                  # placeholders are flagged, never hidden


def test_fr08_cost_text_says_what_it_excludes():
    n = design_numbers(RingParams(**GOOD), 1000.0, load_rules(), load_prices())
    assert "metal only" in n.cost_text() and "not included" in n.cost_text()


def test_fr08_missing_price_is_reported_not_guessed():
    prices = load_prices()
    prices["metals"].pop("silver_925")
    n = design_numbers(RingParams(**GOOD), 1000.0, load_rules(), prices)
    assert n.cost_low is None and n.cost_high is None
    assert "Not estimated" in n.cost_text()


def test_fr08_unknown_metal_is_rejected():
    with pytest.raises(ValueError):
        design_numbers(RingParams(**{**GOOD, "metal": "bronze"}), 1000.0, load_rules(), load_prices())


def test_fr03_prices_come_from_a_file_with_required_keys(tmp_path):
    from jewelry.rules import load_prices as lp
    f = tmp_path / "prices.yaml"
    f.write_text("currency: USD\n")
    with pytest.raises(ValueError):
        lp(f)


def test_nfr02_weight_matches_an_independent_volume_calculation(tmp_path):
    """Weight comes from the CAD solid; check it against the exported mesh volume."""
    p = RingParams(**GOOD)
    shape = build_ring(p)
    mesh = export_files(shape, tmp_path / "ring")
    n = design_numbers(p, shape.val().Volume(), load_rules(), load_prices())
    independent_g = mesh.volume / 1000 * load_rules()["metals"]["silver_925"]["density_g_cm3"]
    assert abs(n.weight_g - independent_g) / independent_g < 0.005
