"""Upper limits, proportions and input hardening. Names carry the SRS requirement ID (NFR-07)."""
import json
import math
import random
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from jewelry import validate as validate_module
from jewelry.api import app
from jewelry.layer1 import check_parameters
from jewelry.params import HARD_MAX_MM, RingParams
from jewelry.report import FAIL, PASS
from jewelry.rules import load_rules
from jewelry.validate import nearest_buildable, validate

GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)
RULES = load_rules()
SILVER = RULES["metals"]["silver_925"]
client = TestClient(app)


def with_(**over):
    return RingParams(**{**GOOD, **over})


def status_of(results, check_id):
    return next(r.status for r in results if r.check_id == check_id)


# Extremes that used to be exportable: (field, value, check that must now fail)
EXTREMES = [
    ("band_thickness_mm", 50.0, "L1-BAND-THICKNESS"),
    ("band_thickness_mm", 5.1, "L1-BAND-THICKNESS"),
    ("prong_diameter_mm", 5.0, "L1-PRONG-DIAMETER"),
    ("ring_size_mm", 60.0, "L1-RING-SIZE"),
    ("ring_size_mm", 5.0, "L1-RING-SIZE"),
    ("band_width_mm", 50.0, "L1-BAND-WIDTH"),
    ("stone_size_mm", 50.0, "L1-STONE-SIZE"),
]


# ---------- FR-04: upper limits ----------

@pytest.mark.parametrize("field,value,expected", EXTREMES)
def test_fr04_extreme_values_fail_and_block_export(field, value, expected, monkeypatch):
    monkeypatch.setattr(validate_module, "build_ring", lambda p: pytest.fail("must not build"))
    report = validate(with_(**{field: value}))
    assert status_of(report.results, expected) == FAIL
    assert report.exportable is False


def test_fr04_a_50_mm_band_is_called_too_thick_in_plain_words():
    result = next(r for r in check_parameters(with_(band_thickness_mm=50), RULES)
                  if r.check_id == "L1-BAND-THICKNESS")
    assert "too thick" in result.message and "5 mm" in result.message
    assert result.fix == {"field": "band_thickness_mm", "value": SILVER["max_band_thickness_mm"]}


@pytest.mark.parametrize("field,value", [
    ("band_thickness_mm", SILVER["min_band_thickness_mm"]), ("band_thickness_mm", SILVER["max_band_thickness_mm"]),
    ("prong_diameter_mm", SILVER["min_prong_diameter_mm"]), ("prong_diameter_mm", SILVER["max_prong_diameter_mm"]),
    ("band_width_mm", SILVER["band_width_range_mm"][0]), ("band_width_mm", SILVER["band_width_range_mm"][1]),
    ("ring_size_mm", RULES["ring_size_range_mm"][0]), ("ring_size_mm", RULES["ring_size_range_mm"][1]),
])
def test_fr04_values_exactly_at_a_limit_are_allowed(field, value):
    # prong thickness at its maximum can still trip the coverage rule, so only look at its own check
    results = check_parameters(with_(**{field: value}), RULES)
    own = {"band_thickness_mm": "L1-BAND-THICKNESS", "prong_diameter_mm": "L1-PRONG-DIAMETER",
           "band_width_mm": "L1-BAND-WIDTH", "ring_size_mm": "L1-RING-SIZE"}[field]
    assert status_of(results, own) == PASS


@pytest.mark.parametrize("field,value,own", [
    ("band_thickness_mm", SILVER["max_band_thickness_mm"] + 0.01, "L1-BAND-THICKNESS"),
    ("band_thickness_mm", SILVER["min_band_thickness_mm"] - 0.01, "L1-BAND-THICKNESS"),
    ("prong_diameter_mm", SILVER["max_prong_diameter_mm"] + 0.01, "L1-PRONG-DIAMETER"),
    ("ring_size_mm", RULES["ring_size_range_mm"][1] + 0.01, "L1-RING-SIZE"),
    ("ring_size_mm", RULES["ring_size_range_mm"][0] - 0.01, "L1-RING-SIZE"),
])
def test_fr04_values_just_outside_a_limit_fail(field, value, own):
    assert status_of(check_parameters(with_(**{field: value}), RULES), own) == FAIL


# ---------- FR-04: prongs against the stone ----------

def test_fr04_prongs_that_cover_too_much_of_the_stone_fail_with_thinner_prongs_as_the_fix():
    r = next(x for x in check_parameters(with_(prong_diameter_mm=2.0), RULES) if x.check_id == "L1-PRONG-COVERAGE")
    assert r.status == FAIL and "cover" in r.message
    assert r.fix["field"] == "prong_diameter_mm" and r.fix["value"] < 2.0
    # the fix really does fit the rule
    assert 4 * r.fix["value"] <= RULES["stone_shapes"]["round"]["max_prong_coverage"] * math.pi * 6.0


def test_fr04_when_thinner_prongs_are_not_enough_the_fix_is_fewer_prongs():
    p = with_(stone_size_mm=4.0, prong_count=6, prong_diameter_mm=0.8)
    r = next(x for x in check_parameters(p, RULES) if x.check_id == "L1-PRONG-COVERAGE")
    assert r.status == FAIL and r.fix == {"field": "prong_count", "value": 4}


def test_fr04_a_stone_too_small_for_any_prongs_says_to_use_a_larger_stone():
    strict = load_rules()
    strict["stone_shapes"]["round"]["max_prong_coverage"] = 0.2   # even 4 thin prongs would not fit a 3 mm stone
    p = with_(stone_size_mm=3.0, prong_count=6, prong_diameter_mm=1.0)
    r = next(x for x in check_parameters(p, strict) if x.check_id == "L1-PRONG-COVERAGE")
    assert r.status == FAIL and r.fix is None and "larger stone" in r.message


# ---------- FR-06: nearest buildable handles several problems at once ----------

def test_fr06_several_extreme_values_are_all_pulled_back_in_range():
    wild = with_(band_thickness_mm=50, prong_diameter_mm=5, ring_size_mm=60, band_width_mm=40, stone_size_mm=30)
    fixed, changes = nearest_buildable(wild, RULES)
    assert all(r.status == PASS for r in check_parameters(fixed, RULES))
    assert {c["field"] for c in changes} >= {"band_thickness_mm", "ring_size_mm", "band_width_mm", "stone_size_mm"}


def test_fr06_prong_fixes_that_interact_still_end_in_a_passing_design():
    fixed, _ = nearest_buildable(with_(prong_diameter_mm=5.0, prong_count=6), RULES)
    assert all(r.status == PASS for r in check_parameters(fixed, RULES))


def test_fr06_fewer_then_thinner_prongs_fit_a_small_stone():
    fixed, changes = nearest_buildable(with_(stone_size_mm=3.0, prong_count=6, prong_diameter_mm=1.0), RULES)
    assert fixed.prong_count == 4 and fixed.prong_diameter_mm == 0.8   # 4 x 0.8 mm fits a 3 mm stone
    assert all(r.status == PASS for r in check_parameters(fixed, RULES))
    assert {c["field"] for c in changes} == {"prong_count", "prong_diameter_mm"}


def test_fr06_a_problem_with_no_safe_fix_is_left_failing_not_hidden():
    unknown, changes = nearest_buildable(with_(metal="bronze"), RULES)
    assert unknown.metal == "bronze" and changes == []
    strict = load_rules()
    strict["stone_shapes"]["round"]["max_prong_coverage"] = 0.2
    stuck, _ = nearest_buildable(with_(stone_size_mm=3.0, prong_count=6, prong_diameter_mm=1.0), strict)
    assert any(r.status == FAIL for r in check_parameters(stuck, strict))


def test_fr06_changes_are_net_old_to_new_values_only():
    _, changes = nearest_buildable(with_(band_thickness_mm=50), RULES)
    assert changes == [{"field": "band_thickness_mm", "old": 50.0, "new": 5.0}]


# ---------- NFR-01: nothing absurd passes layer 1 (property test) ----------

def test_nfr01_whatever_passes_layer1_is_inside_every_limit():
    rnd = random.Random(7)
    passed = 0
    for _ in range(20000):
        metal = rnd.choice(list(RULES["metals"]))
        p = RingParams(
            metal=metal, ring_size_mm=rnd.uniform(10, 30), band_width_mm=rnd.uniform(1, 10),
            band_thickness_mm=rnd.uniform(0.8, 7), stone_shape="round", stone_size_mm=rnd.uniform(2.5, 12),
            prong_count=rnd.choice([3, 4, 4, 5, 6, 6, 8]), prong_diameter_mm=rnd.uniform(0.5, 2.6))
        results = check_parameters(p, RULES)
        if any(r.status == FAIL for r in results):
            continue
        passed += 1
        m = RULES["metals"][metal]
        assert RULES["ring_size_range_mm"][0] <= p.ring_size_mm <= RULES["ring_size_range_mm"][1]
        assert m["band_width_range_mm"][0] <= p.band_width_mm <= m["band_width_range_mm"][1]
        assert m["min_band_thickness_mm"] <= p.band_thickness_mm <= m["max_band_thickness_mm"]
        assert m["min_prong_diameter_mm"] <= p.prong_diameter_mm <= m["max_prong_diameter_mm"]
        assert RULES["stone_shapes"]["round"]["size_range_mm"][0] <= p.stone_size_mm <= RULES["stone_shapes"]["round"]["size_range_mm"][1]
        assert p.prong_count in RULES["stone_shapes"]["round"]["prong_counts"]
        assert p.prong_count * p.prong_diameter_mm <= 0.35 * math.pi * p.stone_size_mm + 1e-9
    assert passed > 400   # the test must actually exercise plenty of passing designs


def test_nfr01_layer1_never_crashes_on_any_input_the_schema_allows():
    rnd = random.Random(11)
    for _ in range(2000):
        p = RingParams(metal=rnd.choice(["silver_925", "gold_14k", "gold_18k", "bronze", "x" * 40]),
            ring_size_mm=rnd.choice([1e-9, 0.001, rnd.uniform(0, HARD_MAX_MM), HARD_MAX_MM]),
            band_width_mm=rnd.choice([1e-9, rnd.uniform(0, HARD_MAX_MM), HARD_MAX_MM]),
            band_thickness_mm=rnd.choice([1e-9, rnd.uniform(0, HARD_MAX_MM), HARD_MAX_MM]),
            stone_shape="round", stone_size_mm=rnd.choice([1e-9, rnd.uniform(0, HARD_MAX_MM), HARD_MAX_MM]),
            prong_count=rnd.randint(1, 50), prong_diameter_mm=rnd.choice([1e-9, rnd.uniform(0, HARD_MAX_MM), HARD_MAX_MM]))
        check_parameters(p, RULES)
        nearest_buildable(p, RULES)


# ---------- Security: hard limits at the boundary ----------

@pytest.mark.parametrize("field,value", [
    ("ring_size_mm", 1e9), ("ring_size_mm", math.inf), ("ring_size_mm", -math.inf), ("ring_size_mm", math.nan),
    ("band_width_mm", HARD_MAX_MM + 0.1), ("band_thickness_mm", 1e300), ("stone_size_mm", math.inf),
    ("prong_diameter_mm", math.nan), ("prong_count", 51), ("prong_count", 0), ("band_width_mm", 0),
    ("band_width_mm", -1), ("metal", "x" * 41), ("metal", ""),
])
def test_security_absurd_values_are_rejected_before_they_reach_the_cad_engine(field, value):
    with pytest.raises(ValidationError):
        with_(**{field: value})


def test_security_the_api_rejects_a_huge_ring_size_instantly_instead_of_hanging():
    start = time.time()
    r = client.post("/designs/build", json={**GOOD, "ring_size_mm": 1e9})
    assert r.status_code == 422 and time.time() - start < 2


def test_security_the_api_rejects_infinity_and_nan_sent_as_raw_json():
    for token in ("Infinity", "-Infinity", "NaN"):
        body = json.dumps(GOOD).replace('"ring_size_mm": 17.3', f'"ring_size_mm": {token}')
        r = client.post("/designs/build", content=body, headers={"Content-Type": "application/json"})
        assert 400 <= r.status_code < 500, token


def test_security_a_5000_character_metal_name_is_rejected():
    assert client.post("/designs/build", json={**GOOD, "metal": "x" * 5000}).status_code == 422


def test_security_an_unknown_metal_name_is_shortened_in_the_message():
    r = next(x for x in check_parameters(with_(metal="y" * 40), RULES) if x.check_id == "L1-METAL")
    assert "y" * 40 not in r.message and "..." in r.message


def test_security_export_applies_the_same_limits():
    assert client.post("/designs/export", json={**GOOD, "band_thickness_mm": 50}).status_code == 422
    assert client.post("/designs/export", json={**GOOD, "ring_size_mm": 1e9}).status_code == 422
